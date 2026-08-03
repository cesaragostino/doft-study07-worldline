"""Potencia causal del puerto de red, derivada offline de la worldline.

El recorder guarda ``drive[k,j]``: la fuerza total aplicada al nodo ``j`` en el
subpaso 0 del paso k. Ese subpaso parte de ``estados[k-1]``. Como la fuerza se
superpone por igual sobre todos los modos (§1.5), la potencia instantánea es

    P[k,j] = drive[k,j] * sum_m v_j,m[k-1].

La caja temporal se calcula a tasa completa y sólo después se submuestrea la salida.
Así ``hop_ut`` cambia el costo de publicación, no el estimando.

Para un par de dos nodos y una arista, P es identificable por link y extremo. En una
red multiarista, ``drive`` ya trae la suma nodal: este instrumento publica potencia
neta de puerto y declara que no puede repartirla honestamente entre edges.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Dict

import numpy as np

from .api import View, armar_config, exigir_canales, exigir_completo, ventana


INSTRUMENT_ID = "link_power"
VERSION = "1.1"
DEFAULTS = {
    "box_ut": 2.0,
    "hop_ut": 0.25,
    "t0_tick": 1,
    "t1_tick": None,
    "stride": 1,
    "permitir_incompleto": False,
}

CANALES = {
    "ticks_step": "dato (paso k cuya fuerza subpaso-0 se observa)",
    "t_force_ut": "dato transformado ((ticks_step-1)*dt)",
    "force_node": "dato (drive[k,j] de la worldline)",
    "v_sum_pre": "dato transformado (suma modal de v_j[k-1])",
    "p_node_instant": "dato transformado (drive[k,j]*sum_m v_j,m[k-1])",
    "p_node_mean": "inferencia (media trailing causal de caja)",
    "fraction_negative": "inferencia (fraccion trailing con P<0; sin umbral)",
    "force_rms": "inferencia (RMS trailing causal de drive)",
    "p_over_force2": "inferencia (P_mean/force_rms^2; NaN si force_rms=0)",
    "work_node": "inferencia (integral rectangular causal desde t0_tick)",
    "window_complete": "veredicto de soporte (la caja trailing esta completa)",
}


def _trailing_at(values: np.ndarray, width: int, output_indices: np.ndarray) -> np.ndarray:
    """Media trailing sólo donde se publica, sin cancelar acumulados de épocas remotas.

    P puede caer doce décadas. Restar dos cumsums globales tardíos perdería justamente
    la cola cuyo signo interesa. Las pocas cajas publicadas se reducen localmente sobre
    las muestras full-rate; sigue siendo causal y O(n) para los defaults poblacionales.
    """
    out = np.full((len(output_indices), values.shape[1]), np.nan, dtype=float)
    for row, index in enumerate(output_indices):
        if index >= width - 1:
            out[row] = np.mean(values[index - width + 1:index + 1], axis=0)
    return out


def _topology(manifest: Dict, n_nodes: int) -> dict:
    raw = manifest.get("topologia", {}).get("edges_ij")
    if raw is None:
        return {
            "topology_declared": False,
            "node_degree": [-1] * n_nodes,
            "single_edge_pair_identifiable": False,
            "n_edges": None,
        }
    edges = np.asarray(raw, dtype=int)
    if edges.size == 0:
        edges = edges.reshape(0, 2)
    if edges.ndim != 2 or edges.shape[1] != 2:
        raise RuntimeError(f"topologia.edges_ij con forma invalida {edges.shape}")
    degree = np.zeros(n_nodes, dtype=int)
    for i, j in edges:
        if not (0 <= i < n_nodes and 0 <= j < n_nodes) or i == j:
            raise RuntimeError(f"edge declarado ({i},{j}) fuera de rango o degenerado")
        degree[i] += 1
        degree[j] += 1
    single = bool(
        n_nodes == 2 and len(edges) == 1 and set(map(int, edges[0])) == {0, 1}
    )
    return {
        "topology_declared": True,
        "node_degree": degree.tolist(),
        "single_edge_pair_identifiable": single,
        "n_edges": int(len(edges)),
    }


def _validated_config(observation_config: Dict | None) -> dict:
    cfg = armar_config(DEFAULTS, observation_config)
    if int(cfg["stride"]) != 1:
        raise RuntimeError(
            "link_power exige stride=1 para calcular la caja a tasa completa; "
            "use hop_ut para abaratar la salida sin redefinir el estimando"
        )
    for name in ("box_ut", "hop_ut"):
        value = float(cfg[name])
        if not np.isfinite(value) or value <= 0.0:
            raise RuntimeError(f"{name}={value}: debe ser finito y > 0")
    if int(cfg["t0_tick"]) < 1:
        raise RuntimeError(
            "link_power exige t0_tick>=1: drive[k] parte de estados[k-1] y tick 0 "
            "no representa un paso aplicado"
        )
    return cfg


def _view_from_series(man: Dict, cfg: dict, wl_hash: str,
                      step_ticks: np.ndarray, force: np.ndarray,
                      v_sum_pre: np.ndarray) -> View:
    dt = float(man["dt"])
    if not np.isfinite(dt) or dt <= 0.0:
        raise RuntimeError(f"dt invalido para potencia: {dt}")
    n_nodes = int(man["n_nodes"])
    if force.shape != (len(step_ticks), n_nodes):
        raise RuntimeError(f"force con forma {force.shape} incompatible con la serie")
    if v_sum_pre.shape != force.shape:
        raise RuntimeError(f"v_sum_pre con forma {v_sum_pre.shape} != {force.shape}")
    if not np.array_equal(np.diff(step_ticks),
                          np.ones(max(len(step_ticks) - 1, 0), dtype=int)):
        raise RuntimeError("la caja causal exige ticks de paso full-rate contiguos")
    if not np.isfinite(force).all() or not np.isfinite(v_sum_pre).all():
        raise RuntimeError("drive o velocidades no finitos: la potencia falla, no imputa")

    p_instant = force * v_sum_pre
    box_ticks = max(int(round(float(cfg["box_ut"]) / dt)), 1)
    if len(step_ticks) < box_ticks:
        raise RuntimeError(
            f"ventana observada de {len(step_ticks)} pasos no contiene una caja de "
            f"{box_ticks} pasos ({cfg['box_ut']} u.t.)"
        )
    work = np.cumsum(p_instant, axis=0) * dt
    hop_ticks = max(int(round(float(cfg["hop_ut"]) / dt)), 1)
    out = np.arange(0, len(step_ticks), hop_ticks, dtype=int)
    final_index_appended = bool(out[-1] != len(step_ticks) - 1)
    if final_index_appended:
        out = np.append(out, len(step_ticks) - 1)
    p_mean = _trailing_at(p_instant, box_ticks, out)
    fraction_negative = _trailing_at(
        (p_instant < 0.0).astype(float), box_ticks, out)
    force2_mean = _trailing_at(force * force, box_ticks, out)
    force_rms = np.sqrt(force2_mean)
    p_over_force2 = np.full_like(p_mean, np.nan)
    np.divide(p_mean, force2_mean, out=p_over_force2, where=force2_mean > 0.0)
    complete = out >= box_ticks - 1
    topology = _topology(man, n_nodes)
    published_ticks = step_ticks[out]
    return View(
        INSTRUMENT_ID, VERSION, cfg, wl_hash,
        {
            "ticks_step": published_ticks,
            "t_force_ut": (published_ticks - 1) * dt,
            "force_node": force[out],
            "v_sum_pre": v_sum_pre[out],
            "p_node_instant": p_instant[out],
            "p_node_mean": p_mean,
            "fraction_negative": fraction_negative,
            "force_rms": force_rms,
            "p_over_force2": p_over_force2,
            "work_node": work[out],
            "window_complete": complete,
        },
        {
            "canales": dict(CANALES),
            "dt": dt,
            "box_ticks": int(box_ticks),
            "box_ut_effective": float(box_ticks * dt),
            "hop_ticks": int(hop_ticks),
            "hop_ut_effective": float(hop_ticks * dt),
            "final_index_appended": final_index_appended,
            **topology,
            "film_intervenida": bool(man.get("intervenida", False)),
            "film_linaje_intervenido": bool(
                man.get("linaje_intervenido", man.get("intervenida", False))
            ),
            "convencion": (
                "P[k,j]=drive[k,j]*sum_m v_j,m[k-1]; P>0 inyecta al nodo; "
                "caja trailing causal full-rate; p_over_force2 no se interpreta sin "
                "force_rms; multiarista=potencia neta nodal, no potencia por edge"
            ),
        },
    )


def run(wl: Dict, observation_config: Dict | None = None) -> View:
    cfg = _validated_config(observation_config)
    exigir_canales(wl, ["estados", "drive", "manifest", "worldline_hash", "ticks"])
    exigir_completo(wl, cfg["permitir_incompleto"])
    man = wl["manifest"]
    ticks = np.asarray(wl["ticks"])
    sel = ventana(wl, cfg)
    drive_all = np.asarray(wl["drive"], dtype=float)
    n_nodes = int(man["n_nodes"])
    if drive_all.shape != (len(ticks), n_nodes):
        raise RuntimeError(
            f"drive con forma {drive_all.shape} != ({len(ticks)}, {n_nodes})"
        )
    if len(wl["estados"]) != n_nodes:
        raise RuntimeError("cantidad de canales estados no coincide con n_nodes")
    force = drive_all[sel]
    v_sum_pre = np.empty((len(sel), n_nodes), dtype=float)
    for j, info in enumerate(man["por_nodo"]):
        n_modes = int(info["n_modes"])
        state = np.asarray(wl["estados"][j], dtype=float)
        if state.shape[0] != len(ticks) or state.shape[1] < 2 * n_modes:
            raise RuntimeError(
                f"estados nodo {j} con forma {state.shape}: no contiene x/v declarados"
            )
        v_sum_pre[:, j] = np.sum(state[sel - 1, n_modes:2 * n_modes], axis=1)
    return _view_from_series(
        man, cfg, wl["worldline_hash"], ticks[sel], force, v_sum_pre)


def run_path(run_dir: Path, observation_config: Dict | None = None) -> View:
    """Streaming verificado para población; produce la misma View que ``run``."""
    cfg = _validated_config(observation_config)
    if bool(cfg["permitir_incompleto"]):
        raise RuntimeError("run_path sólo acepta films COMPLETE")
    run_dir = Path(run_dir)
    man_path, complete_path = run_dir / "manifest.json", run_dir / "COMPLETE"
    if not man_path.is_file() or not complete_path.is_file():
        raise RuntimeError(f"{run_dir}: falta manifest.json o COMPLETE")
    man_text = man_path.read_text()
    man = json.loads(man_text)
    complete = json.loads(complete_path.read_text())
    manifest_sha = hashlib.sha256(man_text.encode("utf-8")).hexdigest()
    if complete.get("manifest_sha") != manifest_sha:
        raise RuntimeError("manifest.json no coincide con el hash sellado en COMPLETE")
    chunks = sorted((run_dir / "worldline").glob("chunk_*.npz"))
    expected_hashes = complete.get("chunk_shas", [])
    if len(chunks) != int(complete.get("chunks", -1)) or len(expected_hashes) != len(chunks):
        raise RuntimeError("cantidad de chunks o SHAs no coincide con COMPLETE")

    n_nodes = int(man["n_nodes"])
    t0 = int(cfg["t0_tick"])
    t1 = int(cfg["t1_tick"]) if cfg["t1_tick"] is not None else None
    tick_parts, force_parts, velocity_parts = [], [], []
    previous_v_sum = None
    expected_tick = 0
    for path, expected_sha in zip(chunks, expected_hashes):
        raw = path.read_bytes()
        measured_sha = hashlib.sha256(raw).hexdigest()
        if measured_sha != expected_sha:
            raise RuntimeError(
                f"{path.name}: sha {measured_sha[:12]} != {expected_sha[:12]}"
            )
        with np.load(io.BytesIO(raw), allow_pickle=False) as data:
            ticks = np.asarray(data["ticks"], dtype=np.int64)
            drive = np.asarray(data["drive"], dtype=float)
            if not np.array_equal(ticks, np.arange(expected_tick,
                                                   expected_tick + len(ticks))):
                raise RuntimeError(f"{path.name}: ticks no consecutivos")
            if drive.shape != (len(ticks), n_nodes):
                raise RuntimeError(f"{path.name}: drive con forma {drive.shape}")
            v_current = np.empty((len(ticks), n_nodes), dtype=float)
            for j, info in enumerate(man["por_nodo"]):
                n_modes = int(info["n_modes"])
                state = np.asarray(data[f"estados_nodo{j}"], dtype=float)
                if state.shape[0] != len(ticks) or state.shape[1] < 2 * n_modes:
                    raise RuntimeError(
                        f"{path.name}: estados nodo {j} con forma {state.shape}"
                    )
                v_current[:, j] = np.sum(state[:, n_modes:2 * n_modes], axis=1)
        v_pre = np.empty_like(v_current)
        v_pre[0] = np.nan if previous_v_sum is None else previous_v_sum
        v_pre[1:] = v_current[:-1]
        selected = ticks >= t0
        if t1 is not None:
            selected &= ticks <= t1
        if np.any(selected):
            tick_parts.append(ticks[selected])
            force_parts.append(drive[selected])
            velocity_parts.append(v_pre[selected])
        previous_v_sum = v_current[-1].copy()
        expected_tick += len(ticks)

    last_tick = expected_tick - 1
    target_t1 = last_tick if t1 is None else t1
    if not (1 <= t0 <= target_t1 <= last_tick):
        raise RuntimeError(
            f"ventana inválida: t0_tick={t0}, t1_tick={target_t1}, film 0..{last_tick}"
        )
    if not tick_parts:
        raise RuntimeError("ventana vacía en run_path")
    step_ticks = np.concatenate(tick_parts)
    if not np.array_equal(step_ticks, np.arange(t0, target_t1 + 1)):
        raise RuntimeError("run_path no reconstruyó la ventana causal completa")
    wl_hash = hashlib.sha256(
        (complete["sha_total"] + complete["manifest_sha"]).encode("utf-8")
    ).hexdigest()
    return _view_from_series(
        man, cfg, wl_hash, step_ticks,
        np.concatenate(force_parts), np.concatenate(velocity_parts))
