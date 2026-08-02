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


def run(wl: Dict, observation_config: Dict | None = None) -> View:
    cfg = armar_config(DEFAULTS, observation_config)
    if int(cfg["stride"]) != 1:
        raise RuntimeError(
            "link_power exige stride=1 para calcular la caja a tasa completa; "
            "use hop_ut para abaratar la salida sin redefinir el estimando"
        )
    exigir_canales(wl, ["estados", "drive", "manifest", "worldline_hash", "ticks"])
    exigir_completo(wl, cfg["permitir_incompleto"])
    man = wl["manifest"]
    dt = float(man["dt"])
    if not np.isfinite(dt) or dt <= 0.0:
        raise RuntimeError(f"dt invalido para potencia: {dt}")
    box_ut = float(cfg["box_ut"])
    hop_ut = float(cfg["hop_ut"])
    if not np.isfinite(box_ut) or box_ut <= 0.0:
        raise RuntimeError(f"box_ut={box_ut}: debe ser finito y > 0")
    if not np.isfinite(hop_ut) or hop_ut <= 0.0:
        raise RuntimeError(f"hop_ut={hop_ut}: debe ser finito y > 0")

    sel = ventana(wl, cfg)
    if int(sel[0]) < 1:
        raise RuntimeError(
            "link_power exige t0_tick>=1: drive[k] parte de estados[k-1] y tick 0 "
            "no representa un paso aplicado"
        )
    if not np.array_equal(np.diff(sel), np.ones(max(len(sel) - 1, 0), dtype=int)):
        raise RuntimeError("la caja causal exige selección full-rate contigua")

    ticks = np.asarray(wl["ticks"])
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
    if not np.isfinite(force).all() or not np.isfinite(v_sum_pre).all():
        raise RuntimeError("drive o velocidades no finitos: la potencia falla, no imputa")

    p_instant = force * v_sum_pre
    box_ticks = max(int(round(box_ut / dt)), 1)
    if len(sel) < box_ticks:
        raise RuntimeError(
            f"ventana observada de {len(sel)} pasos no contiene una caja de "
            f"{box_ticks} pasos ({box_ut} u.t.)"
        )
    work = np.cumsum(p_instant, axis=0) * dt

    hop_ticks = max(int(round(hop_ut / dt)), 1)
    out = np.arange(0, len(sel), hop_ticks, dtype=int)
    final_index_appended = bool(out[-1] != len(sel) - 1)
    if final_index_appended:
        out = np.append(out, len(sel) - 1)
    p_mean = _trailing_at(p_instant, box_ticks, out)
    fraction_negative = _trailing_at(
        (p_instant < 0.0).astype(float), box_ticks, out)
    force2_mean = _trailing_at(force * force, box_ticks, out)
    force_rms = np.sqrt(force2_mean)
    p_over_force2 = np.full_like(p_mean, np.nan)
    np.divide(p_mean, force2_mean, out=p_over_force2, where=force2_mean > 0.0)
    complete = out >= box_ticks - 1
    topology = _topology(man, n_nodes)
    step_ticks = ticks[sel[out]]
    return View(
        INSTRUMENT_ID,
        VERSION,
        cfg,
        wl["worldline_hash"],
        {
            "ticks_step": step_ticks,
            "t_force_ut": (step_ticks - 1) * dt,
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
