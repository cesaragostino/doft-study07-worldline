"""Trending full-rate de fuerza, potencia por capa y orden de fase del link.

Dominio v1: dos nodos, una arista. El estimando consume cada tick del film; ``hop_ut``
sólo decide qué finales de ventana se publican. No ejecuta el motor ni decide salud.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
from typing import Dict, Iterable

import numpy as np

from .api import View, armar_config


INSTRUMENT_ID = "link_bond_trend"
VERSION = "1.1"
LAYERS = ("Q", "S1", "S2")
DEFAULTS = {
    "lock_window_ut": 4.0,
    "power_window_ut": 2.0,
    "hop_ut": 0.25,
    "ratios": ("1:1",),
    "lock_threshold": 0.90,
    "mute_rel": 1e-3,
    "mute_abs": 1e-12,
    "t1_tick": None,
    "retain_dt": False,
}

CANALES = {
    "ticks_end": "dato (tick final de cada caja publicada)",
    "t_end_ut": "dato transformado (ticks_end*dt)",
    "theta_endpoint_raw": "dato transformado (atan2(sum v_layer,sum x_layer))",
    "omega_reference_full": "inferencia (frecuencia media de todo el film observado)",
    "lock_raw": "inferencia (L_pq trailing, stride de entrada 1)",
    "lock_corrected_fixed": "inferencia no causal (L_pq con referencia de film completo)",
    "dphi_corrected_wrapped": "inferencia (fase p:q al final de caja, envuelta)",
    "dphi_corrected_unwrapped": "inferencia (fase p:q acumulada al final de caja)",
    "phase_drift_rate": "inferencia (deriva absoluta p:q entre extremos de caja)",
    "x_std": "inferencia (std trailing full-rate por nodo/capa)",
    "mute": "veredicto causal de soporte por nodo/capa",
    "locked": "veredicto de caja (L_corrected>=threshold y ambos extremos no mudos)",
    "force_rms": "inferencia (RMS trailing full-rate de drive nodal)",
    "power_layer_mean": "inferencia (media trailing de drive[k]*sum v_layer[k-1])",
    "power_layer_fraction_negative": "inferencia (fracción trailing P_layer<0)",
    "work_layer": "inferencia (integral rectangular desde tick 1)",
    "net_power_layer_mean": "inferencia (suma de potencia media de ambos extremos)",
    "opposed_power_fraction_layer": "inferencia (fracción P0_layer*P1_layer<0)",
    "ticks_lock_dt": "dato (cada tick con una caja Wlock completa)",
    "lock_raw_dt": "inferencia (L_pq en cada final de dt admisible)",
    "lock_corrected_fixed_dt": (
        "inferencia no causal (L_pq corregido en cada final de dt admisible)"
    ),
}


def _validated_config(observation_config: Dict | None) -> tuple[dict, tuple[tuple[int, int], ...]]:
    cfg = armar_config(DEFAULTS, observation_config)
    for key in ("lock_window_ut", "power_window_ut", "hop_ut"):
        value = float(cfg[key])
        if not np.isfinite(value) or value <= 0.0:
            raise RuntimeError(f"{key}={value}: debe ser finito y >0")
    threshold = float(cfg["lock_threshold"])
    if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise RuntimeError("lock_threshold debe estar en [0,1]")
    for key in ("mute_rel", "mute_abs"):
        value = float(cfg[key])
        if not np.isfinite(value) or value < 0.0:
            raise RuntimeError(f"{key} debe ser finito y >=0")
    raw = cfg["ratios"]
    if isinstance(raw, str):
        raw = (raw,)
    if not isinstance(raw, (list, tuple)) or not raw:
        raise RuntimeError("ratios debe ser una lista no vacía de strings p:q")
    parsed = []
    for item in raw:
        pieces = str(item).split(":")
        if len(pieces) != 2:
            raise RuntimeError(f"ratio inválido {item!r}; se espera p:q")
        p, q = (int(piece) for piece in pieces)
        if p < 1 or q < 1 or p > 32 or q > 32 or math.gcd(p, q) != 1:
            raise RuntimeError(f"ratio {item!r}: p/q coprimos en [1,32]")
        if (p, q) in parsed:
            raise RuntimeError(f"ratio duplicado {p}:{q}")
        parsed.append((p, q))
    cfg["ratios"] = [f"{p}:{q}" for p, q in parsed]
    cfg["retain_dt"] = bool(cfg["retain_dt"])
    cfg["t1_tick"] = None if cfg["t1_tick"] is None else int(cfg["t1_tick"])
    return cfg, tuple(parsed)


def _single_edge_topology(manifest: dict) -> None:
    if int(manifest.get("n_nodes", -1)) != 2:
        raise RuntimeError("link_bond_trend v1 exige exactamente dos nodos")
    raw = manifest.get("topologia", {}).get("edges_ij")
    edges = np.asarray(raw, dtype=int) if raw is not None else np.empty((0, 2), dtype=int)
    if edges.shape != (1, 2) or set(map(int, edges[0])) != {0, 1}:
        raise RuntimeError("link_bond_trend v1 exige dos nodos y una sola arista 0-1")


def _worldline_hash(complete: dict) -> str:
    return hashlib.sha256(
        (str(complete["sha_total"]) + str(complete["manifest_sha"])).encode("utf-8")
    ).hexdigest()


def _read_path(run_dir: Path, t1_tick: int | None
               ) -> tuple[dict, str, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    """Lee y verifica una worldline; devuelve ticks, drive, X_layer y V_layer full-rate."""
    run_dir = Path(run_dir)
    man_path, complete_path = run_dir / "manifest.json", run_dir / "COMPLETE"
    if not man_path.is_file() or not complete_path.is_file():
        raise RuntimeError(f"{run_dir}: falta manifest.json o COMPLETE")
    man_text = man_path.read_text()
    manifest = json.loads(man_text)
    complete = json.loads(complete_path.read_text())
    manifest_sha = hashlib.sha256(man_text.encode("utf-8")).hexdigest()
    if complete.get("manifest_sha") != manifest_sha:
        raise RuntimeError("manifest.json no coincide con COMPLETE")
    _single_edge_topology(manifest)
    infos = manifest.get("por_nodo")
    if not isinstance(infos, list) or len(infos) != 2:
        raise RuntimeError("manifest sin layout por_nodo para dos nodos")

    chunks = sorted((run_dir / "worldline").glob("chunk_*.npz"))
    expected_hashes = complete.get("chunk_shas", [])
    if len(chunks) != int(complete.get("chunks", -1)) or len(chunks) != len(expected_hashes):
        raise RuntimeError("cantidad de chunks/SHAs incompatible con COMPLETE")

    tick_parts: list[np.ndarray] = []
    drive_parts: list[np.ndarray] = []
    x_parts: list[np.ndarray] = []
    v_parts: list[np.ndarray] = []
    expected_tick = 0
    chunks_loaded = 0
    for path, expected_sha in zip(chunks, expected_hashes):
        raw = path.read_bytes()
        observed_sha = hashlib.sha256(raw).hexdigest()
        if observed_sha != expected_sha:
            raise RuntimeError(f"{path.name}: sha {observed_sha[:12]} != {expected_sha[:12]}")
        with np.load(io.BytesIO(raw), allow_pickle=False) as data:
            ticks = np.asarray(data["ticks"], dtype=np.int64)
            if not np.array_equal(ticks, np.arange(expected_tick, expected_tick + len(ticks))):
                raise RuntimeError(f"{path.name}: ticks no contiguos desde {expected_tick}")
            expected_tick += len(ticks)
            if t1_tick is not None:
                select = ticks <= t1_tick
            else:
                select = np.ones(len(ticks), dtype=bool)
            if np.any(select):
                drive = np.asarray(data["drive"], dtype=float)
                if drive.shape != (len(ticks), 2):
                    raise RuntimeError(f"{path.name}: drive con forma {drive.shape}")
                node_x, node_v = [], []
                for node, info in enumerate(infos):
                    n_modes = int(info["n_modes"])
                    names = np.asarray(info.get("capas_por_modo"), dtype=str)
                    if names.shape != (n_modes,) or any(name not in LAYERS for name in names):
                        raise RuntimeError(f"nodo {node}: layout de capas inválido {names.tolist()}")
                    state = np.asarray(data[f"estados_nodo{node}"], dtype=float)
                    if state.shape[0] != len(ticks) or state.shape[1] < 2 * n_modes:
                        raise RuntimeError(f"{path.name}: estado nodo {node} forma {state.shape}")
                    x_layer, v_layer = [], []
                    for layer in LAYERS:
                        idx = np.flatnonzero(names == layer)
                        x_layer.append(np.sum(state[:, idx], axis=1))
                        v_layer.append(np.sum(state[:, n_modes + idx], axis=1))
                    node_x.append(np.stack(x_layer, axis=1))
                    node_v.append(np.stack(v_layer, axis=1))
                tick_parts.append(ticks[select])
                drive_parts.append(drive[select])
                x_parts.append(np.stack(node_x, axis=1)[select])
                v_parts.append(np.stack(node_v, axis=1)[select])
                chunks_loaded += 1

    if not tick_parts:
        raise RuntimeError("ventana solicitada sin ticks")
    ticks = np.concatenate(tick_parts)
    drive = np.concatenate(drive_parts)
    x_layer = np.concatenate(x_parts)
    v_layer = np.concatenate(v_parts)
    if ticks[0] != 0 or not np.array_equal(ticks, np.arange(len(ticks))):
        raise RuntimeError("v1 exige observación contigua desde tick 0")
    if not all(np.isfinite(array).all() for array in (drive, x_layer, v_layer)):
        raise RuntimeError("drive/x/v contienen NaN o Inf")
    provenance = {
        "run_dir": str(run_dir.resolve()),
        "manifest_sha256": manifest_sha,
        "complete_sha256": hashlib.sha256(complete_path.read_bytes()).hexdigest(),
        "chunks_verified": len(chunks),
        "chunks_loaded": chunks_loaded,
    }
    return (manifest, _worldline_hash(complete), ticks, drive, x_layer, v_layer,
            provenance)


def _window_complex(values: np.ndarray, width: int, ends: np.ndarray) -> np.ndarray:
    cumulative = np.concatenate([
        np.zeros((1,) + values.shape[1:], dtype=np.complex128),
        np.cumsum(values, axis=0, dtype=np.complex128),
    ], axis=0)
    return (cumulative[ends + 1] - cumulative[ends - width + 1]) / float(width)


def _local_window_reductions(power: np.ndarray, drive: np.ndarray, x_layer: np.ndarray,
                             power_width: int, lock_width: int,
                             ends: np.ndarray) -> tuple[np.ndarray, ...]:
    n_out = len(ends)
    p_mean = np.empty((n_out, 2, len(LAYERS)), dtype=float)
    p_negative = np.empty_like(p_mean)
    opposed = np.empty((n_out, len(LAYERS)), dtype=float)
    force_rms = np.empty((n_out, 2), dtype=float)
    x_std = np.empty((n_out, 2, len(LAYERS)), dtype=float)
    for row, end in enumerate(ends):
        p_slice = power[end - power_width + 1:end + 1]
        d_slice = drive[end - power_width + 1:end + 1]
        x_slice = x_layer[end - lock_width + 1:end + 1]
        p_mean[row] = np.mean(p_slice, axis=0)
        p_negative[row] = np.mean(p_slice < 0.0, axis=0)
        opposed[row] = np.mean((p_slice[:, 0, :] * p_slice[:, 1, :]) < 0.0, axis=0)
        force_rms[row] = np.sqrt(np.mean(d_slice * d_slice, axis=0))
        x_std[row] = np.std(x_slice, axis=0)
    return p_mean, p_negative, opposed, force_rms, x_std


def _view_from_series(manifest: dict, wl_hash: str, ticks: np.ndarray,
                      drive: np.ndarray, x_layer: np.ndarray, v_layer: np.ndarray,
                      cfg: dict, ratios: Iterable[tuple[int, int]],
                      provenance: dict | None = None) -> View:
    _single_edge_topology(manifest)
    dt = float(manifest["dt"])
    if not np.isfinite(dt) or dt <= 0.0:
        raise RuntimeError(f"dt inválido {dt}")
    n = len(ticks)
    if n < 2 or drive.shape != (n, 2) or x_layer.shape != (n, 2, 3) \
            or v_layer.shape != (n, 2, 3):
        raise RuntimeError("formas incompatibles para trending")
    if not np.array_equal(ticks, np.arange(n)):
        raise RuntimeError("ticks deben ser contiguos desde cero")
    if not all(np.isfinite(array).all() for array in (drive, x_layer, v_layer)):
        raise RuntimeError("serie contiene NaN o Inf")

    lock_width = max(int(round(float(cfg["lock_window_ut"]) / dt)), 2)
    power_width = max(int(round(float(cfg["power_window_ut"]) / dt)), 1)
    hop_ticks = max(int(round(float(cfg["hop_ut"]) / dt)), 1)
    first_end = max(lock_width - 1, power_width)
    if first_end >= n:
        raise RuntimeError(
            f"film de {n} ticks no contiene Wlock={lock_width} y Wpower={power_width}"
        )
    ends = np.arange(first_end, n, hop_ticks, dtype=np.int64)
    if ends[-1] != n - 1:
        ends = np.append(ends, n - 1)

    theta = np.arctan2(v_layer, x_layer)
    unwrapped = np.unwrap(theta, axis=0)
    omega_reference = np.empty((2, 3), dtype=float)
    corrected = np.empty_like(theta)
    for node in range(2):
        for layer in range(3):
            series = unwrapped[:, node, layer]
            omega = abs(float(np.mean(np.gradient(series, dt))))
            omega_reference[node, layer] = omega
            corrected[:, node, layer] = np.unwrap(np.arctan2(
                np.sin(theta[:, node, layer]) / max(omega, 1e-9),
                np.cos(theta[:, node, layer]),
            ))

    ratio_list = tuple(ratios)
    shape = (len(ends), len(ratio_list), 3)
    lock_raw = np.empty(shape, dtype=float)
    lock_corrected = np.empty(shape, dtype=float)
    lock_ends_dt = np.arange(lock_width - 1, n, dtype=np.int64)
    lock_raw_dt = np.empty((len(lock_ends_dt), len(ratio_list), 3), dtype=float)
    lock_corrected_dt = np.empty_like(lock_raw_dt)
    phase_wrapped = np.empty(shape, dtype=float)
    phase_unwrapped = np.empty(shape, dtype=float)
    drift = np.empty(shape, dtype=float)
    duration = max((lock_width - 1) * dt, dt)
    for ratio_index, (p, q) in enumerate(ratio_list):
        combo_raw = q * unwrapped[:, 0, :] - p * unwrapped[:, 1, :]
        combo_corrected = q * corrected[:, 0, :] - p * corrected[:, 1, :]
        # L se evalúa en cada final de dt. La grilla ``ends`` es sólo el índice
        # compacto de trending; no es la resolución a la que se calculó el lock.
        z_raw_dt = _window_complex(
            np.exp(1j * combo_raw), lock_width, lock_ends_dt
        )
        z_corrected_dt = _window_complex(
            np.exp(1j * combo_corrected), lock_width, lock_ends_dt
        )
        lock_raw_dt[:, ratio_index, :] = np.abs(z_raw_dt)
        lock_corrected_dt[:, ratio_index, :] = np.abs(z_corrected_dt)
        trend_rows = ends - (lock_width - 1)
        z_corrected = z_corrected_dt[trend_rows]
        lock_raw[:, ratio_index, :] = lock_raw_dt[trend_rows, ratio_index, :]
        lock_corrected[:, ratio_index, :] = lock_corrected_dt[
            trend_rows, ratio_index, :
        ]
        phase_wrapped[:, ratio_index, :] = np.angle(z_corrected)
        phase_unwrapped[:, ratio_index, :] = combo_corrected[ends]
        drift[:, ratio_index, :] = np.abs(
            combo_corrected[ends] - combo_corrected[ends - lock_width + 1]
        ) / duration

    # Potencia full-rate alineada al comienzo del paso: fila 0 no representa trabajo aplicado.
    power = np.zeros((n, 2, 3), dtype=float)
    power[1:] = drive[1:, :, None] * v_layer[:-1]
    direct = drive[1:] * np.sum(v_layer[:-1], axis=2)
    closure = np.sum(power[1:], axis=2) - direct
    closure_max = float(np.max(np.abs(closure))) if closure.size else 0.0
    scale = float(np.max(np.abs(direct))) if direct.size else 0.0
    closure_tol = max(64.0 * np.finfo(float).eps * max(scale, 1.0), 1e-18)
    if closure_max > closure_tol:
        raise RuntimeError(
            f"potencia por capa no cierra: residuo {closure_max:.6g} > {closure_tol:.6g}"
        )

    p_mean, p_negative, opposed, force_rms, x_std = _local_window_reductions(
        power, drive, x_layer, power_width, lock_width, ends
    )
    work = np.cumsum(power, axis=0, dtype=float) * dt
    causal_peak = np.maximum.accumulate(x_std, axis=0)
    mute = x_std < np.maximum(float(cfg["mute_abs"]),
                              float(cfg["mute_rel"]) * causal_peak)
    mute_pair = np.any(mute, axis=1)
    locked = ((lock_corrected >= float(cfg["lock_threshold"]))
              & (~mute_pair[:, None, :]))

    arrays = {
        "ticks_end": ticks[ends],
        "t_end_ut": ticks[ends] * dt,
        "theta_endpoint_raw": theta[ends],
        "omega_reference_full": omega_reference,
        "ratios_pq": np.asarray(ratio_list, dtype=np.int64),
        "lock_raw": lock_raw,
        "lock_corrected_fixed": lock_corrected,
        "dphi_corrected_wrapped": phase_wrapped,
        "dphi_corrected_unwrapped": phase_unwrapped,
        "phase_drift_rate": drift,
        "x_std": x_std,
        "mute": mute,
        "locked": locked,
        "force_rms": force_rms,
        "power_layer_mean": p_mean,
        "power_layer_fraction_negative": p_negative,
        "work_layer": work[ends],
        "net_power_layer_mean": np.sum(p_mean, axis=1),
        "opposed_power_fraction_layer": opposed,
    }
    if bool(cfg["retain_dt"]):
        arrays.update({
            "ticks_dt": ticks,
            "theta_raw_dt": theta,
            "phi_corrected_fixed_dt": corrected,
            "power_layer_instant_dt": power,
            "power_valid_dt": ticks >= 1,
            "ticks_lock_dt": ticks[lock_ends_dt],
            "lock_raw_dt": lock_raw_dt,
            "lock_corrected_fixed_dt": lock_corrected_dt,
        })

    return View(
        INSTRUMENT_ID, VERSION, cfg, wl_hash, arrays,
        {
            "run_id": manifest.get("run_id"),
            "canales": dict(CANALES),
            "dt": dt,
            "stride_input": 1,
            "n_input_ticks": int(n),
            "lock_window_ticks": int(lock_width),
            "lock_window_ut_effective": float(lock_width * dt),
            "power_window_ticks": int(power_width),
            "power_window_ut_effective": float(power_width * dt),
            "hop_ticks": int(hop_ticks),
            "hop_ut_effective": float(hop_ticks * dt),
            "layers": list(LAYERS),
            "ratio_convention": "p:q significa q*omega_node0 ~= p*omega_node1",
            "phase_reference": (
                "raw y corrected_fixed; corrected_fixed usa omega media de todo el film "
                "observado y NO es causal"
            ),
            "power_alignment": "P_layer[k]=drive[k]*sum(v_layer[k-1]); tick0 invalido",
            "power_layer_closure_max_abs": closure_max,
            "power_layer_closure_tolerance": closure_tol,
            "single_edge_pair_identifiable": True,
            "retain_dt": bool(cfg["retain_dt"]),
            "lock_evaluated_every_dt": True,
            "provenance": dict(provenance or {}),
            "warnings": [
                "locked es estado de caja, no salud ni supervivencia futura",
                "potencia por capa particiona el input uniforme v1; no identifica endpoint",
                "corrected_fixed usa futuro del film y no puede decidir online",
            ],
        },
    )


def run_path(run_dir: Path, observation_config: Dict | None = None) -> View:
    cfg, ratios = _validated_config(observation_config)
    manifest, wl_hash, ticks, drive, x_layer, v_layer, provenance = _read_path(
        Path(run_dir), cfg["t1_tick"]
    )
    return _view_from_series(
        manifest, wl_hash, ticks, drive, x_layer, v_layer, cfg, ratios, provenance
    )
