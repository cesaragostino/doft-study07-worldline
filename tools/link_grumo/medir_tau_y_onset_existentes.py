#!/usr/bin/env python3
"""Reproduce dos lecturas temporales sobre datos ya existentes.

1. Cuenta cruces por intervalo de llegada en los tres pares ``tau`` discordantes
   del census (selección retrospectiva y explícita).
2. Localiza el primer tick distinto en dos cirugías ON/OFF deterministas y
   exactamente apareadas.

No clasifica supervivencia, no integra y no escribe en el disco externo.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path

import numpy as np

import medir_tiempos_ticks as base


DISCORDANT_PAIRS = (56, 68, 72)
TAU_LABELS = ("005", "02")
ON_OFF_CASES = (
    ("34b", "fase0/unidades/cir0_off_34b",
     "fase1A/unidades/cir1a_34b_w30.17_m2.0"),
    ("61b", "fase0/unidades/cir0_off_61b",
     "fase1A/unidades/cir1a_61b_w33.69_m2.0"),
)
TAIL_UT = 10.0


def index_worldlines(root: Path) -> dict[str, Path]:
    result = {}
    for path in root.glob("olaB_sub*/unidades/*/manifest.json"):
        run_id = path.parent.name
        if run_id in result:
            raise RuntimeError(f"run_id duplicado: {run_id}")
        result[run_id] = path.parent
    return result


def arrival_interval_counts(source: np.ndarray, receiver: np.ndarray, edge_ticks: int,
                            last_tick: int, tail_ticks: int) -> dict:
    """Cuenta cruces receptores entre llegadas fuente consecutivas."""
    arrivals = base.upward_crossings(source) + int(edge_ticks)
    arrivals = arrivals[arrivals <= last_tick]
    response = base.upward_crossings(receiver)
    intervals = []
    for start, stop in zip(arrivals[:-1], arrivals[1:]):
        if int(start) < last_tick - tail_ticks:
            continue
        count = int(np.searchsorted(response, stop, side="left")
                    - np.searchsorted(response, start, side="left"))
        intervals.append({"tick_inicio_llegada": int(start),
                          "tick_fin_llegada": int(stop),
                          "cruces_receptor": count})
    final_run = 0
    for row in reversed(intervals):
        if row["cruces_receptor"] != 1:
            break
        final_run += 1
    counts = Counter(row["cruces_receptor"] for row in intervals)
    return {
        "n_intervals": len(intervals),
        "counts": {str(key): int(value) for key, value in sorted(counts.items())},
        "n_exactly_one": int(counts.get(1, 0)),
        "final_run_exactly_one": final_run,
        "first_tick_of_final_run": (
            intervals[len(intervals) - final_run]["tick_inicio_llegada"]
            if final_run else None
        ),
        "intervals": intervals,
    }


def analyze_tau_run(run_dir: Path) -> dict:
    manifest, series, custody = base.read_verified_run(run_dir)
    dt = float(custody["clock"]["dt"])
    edge_ticks = int(custody["clock"]["edge_ticks"])
    last_tick = int(series["ticks"][-1])
    tail_ticks = int(round(TAIL_UT / dt))
    layers = {}
    for layer in ("Q", "S1", "S2"):
        layers[layer] = {}
        for source in (0, 1):
            receiver = 1 - source
            layers[layer][f"{source}_to_{receiver}"] = arrival_interval_counts(
                series["nodes"][source][layer],
                series["nodes"][receiver][layer],
                edge_ticks,
                last_tick,
                tail_ticks,
            )
    origins = manifest["composicion"]["por_nodo"]
    return {
        "run_id": run_dir.name,
        "dt": dt,
        "tau_ut": float(manifest["topologia"]["tau"][0]),
        "edge_ticks": edge_ticks,
        "tail_ut": TAIL_UT,
        "tail_ticks": tail_ticks,
        "last_tick": last_tick,
        "pairing_signature": {
            "seed": int(manifest["seed"]),
            "dt": dt,
            "last_tick": last_tick,
            "k_global": float(manifest["k_global"]),
            "gamma_c": float(manifest["gamma_c"]),
            "spec_fingerprints": list(manifest["spec_fingerprints"]),
            "source_state_content_sha256": [
                origin["source_state_content_sha256"] for origin in origins
            ],
            "capsule_sha256": [origin["capsule_sha256"] for origin in origins],
        },
        "custody": custody["provenance"],
        "drive_reconstruction": base.reconstruct_drive(manifest, series, edge_ticks),
        "same_layer_arrival_intervals": layers,
    }


def load_first_chunk(run_dir: Path) -> tuple[dict, dict, dict]:
    manifest_path = run_dir / "manifest.json"
    complete_path = run_dir / "COMPLETE"
    manifest_raw = manifest_path.read_bytes()
    complete_raw = complete_path.read_bytes()
    manifest = json.loads(manifest_raw)
    complete = json.loads(complete_raw)
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    if manifest_sha != complete.get("manifest_sha"):
        raise RuntimeError(f"{run_dir.name}: manifest no coincide con COMPLETE")
    chunk_path = run_dir / "worldline" / "chunk_00000.npz"
    raw = chunk_path.read_bytes()
    chunk_sha = hashlib.sha256(raw).hexdigest()
    if chunk_sha != complete["chunk_shas"][0]:
        raise RuntimeError(f"{run_dir.name}: chunk_00000 no coincide con COMPLETE")
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        arrays = {key: np.asarray(data[key])
                  for key in ("ticks", "drive", "estados_nodo0")}
    custody = {
        "run_dir": str(run_dir),
        "manifest_sha256": manifest_sha,
        "complete_sha256": hashlib.sha256(complete_raw).hexdigest(),
        "chunk_00000_sha256": chunk_sha,
    }
    return manifest, arrays, custody


def first_different_tick(left: np.ndarray, right: np.ndarray) -> int | None:
    if left.shape != right.shape:
        raise RuntimeError(f"formas no apareadas: {left.shape} != {right.shape}")
    mask = np.any(left != right, axis=1) if left.ndim == 2 else left != right
    positions = np.flatnonzero(mask)
    return int(positions[0]) if positions.size else None


def analyze_on_off(label: str, off_dir: Path, on_dir: Path) -> dict:
    off_manifest, off, off_custody = load_first_chunk(off_dir)
    on_manifest, on, on_custody = load_first_chunk(on_dir)
    for field in ("dt", "seed", "dims"):
        if off_manifest[field] != on_manifest[field]:
            raise RuntimeError(f"{label}: OFF/ON difieren en {field}")
    off_origin = off_manifest["composicion"]["por_nodo"][0]
    on_origin = on_manifest["composicion"]["por_nodo"][0]
    if off_origin["source_state_content_sha256"] != on_origin["source_state_content_sha256"]:
        raise RuntimeError(f"{label}: OFF/ON no parten del mismo estado")
    if not np.array_equal(off["estados_nodo0"][0], on["estados_nodo0"][0]):
        raise RuntimeError(f"{label}: fila 0 OFF/ON no es bit-exacta")

    info = on_manifest["por_nodo"][0]
    n_modes = int(info["n_modes"])
    n_z = int(info["n_z"])
    n_layers = int(info["n_layers"])
    mode_layers = np.asarray(info["capas_por_modo"])
    state_off = np.asarray(off["estados_nodo0"], dtype=np.float64)
    state_on = np.asarray(on["estados_nodo0"], dtype=np.float64)
    layers = {}
    for layer in ("Q", "S1", "S2"):
        indices = np.flatnonzero(mode_layers == layer)
        x_off, x_on = state_off[:, :n_modes][:, indices], state_on[:, :n_modes][:, indices]
        v_off = state_off[:, n_modes:2 * n_modes][:, indices]
        v_on = state_on[:, n_modes:2 * n_modes][:, indices]
        layers[layer] = {
            "first_x_difference_tick": first_different_tick(x_off, x_on),
            "first_v_difference_tick": first_different_tick(v_off, v_on),
            "max_abs_delta_x_at_tick1": float(np.max(np.abs(x_on[1] - x_off[1]))),
            "max_abs_delta_v_at_tick1": float(np.max(np.abs(v_on[1] - v_off[1]))),
        }
    slow_start = 2 * n_modes + n_z
    b_slice = slice(slow_start, slow_start + n_layers)
    e_slice = slice(slow_start + n_layers, slow_start + 2 * n_layers)
    return {
        "label": label,
        "off_run_id": off_manifest["run_id"],
        "on_run_id": on_manifest["run_id"],
        "program": on_manifest["programa"],
        "dt": float(on_manifest["dt"]),
        "source_state_content_sha256": on_origin["source_state_content_sha256"],
        "row0_state_bit_exact": True,
        "first_drive_difference_tick": first_different_tick(
            off["drive"][:, 0], on["drive"][:, 0]),
        "drive_off_at_tick1": float(off["drive"][1, 0]),
        "drive_on_at_tick1": float(on["drive"][1, 0]),
        "layers": layers,
        "first_b_difference_tick": first_different_tick(
            state_off[:, b_slice], state_on[:, b_slice]),
        "first_e_difference_tick": first_different_tick(
            state_off[:, e_slice], state_on[:, e_slice]),
        "custody": {"off": off_custody, "on": on_custody},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census-root", type=Path, required=True)
    parser.add_argument("--cirugia-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = base.safe_output(args.output)

    index = index_worldlines(args.census_root)
    tau_runs = []
    for pair in DISCORDANT_PAIRS:
        paired_rows = []
        for tau_label in TAU_LABELS:
            run_id = f"olaB_par{pair:03d}_t_k03_tau{tau_label}"
            if run_id not in index:
                raise RuntimeError(f"falta {run_id}")
            print(f"[leer tau] {run_id}", flush=True)
            paired_rows.append(analyze_tau_run(index[run_id]))
        if paired_rows[0]["pairing_signature"] != paired_rows[1]["pairing_signature"]:
            raise RuntimeError(f"par{pair:03d}: tau005/tau02 no son gemelos exactos")
        tau_runs.extend(paired_rows)

    onset = []
    for label, off_relative, on_relative in ON_OFF_CASES:
        print(f"[leer onset] {label}", flush=True)
        onset.append(analyze_on_off(label, args.cirugia_root / off_relative,
                                    args.cirugia_root / on_relative))
    payload = {
        "schema": "link_grumo_tau_onset_existentes_v1",
        "scope": {
            "tau_panel_selection": (
                "RETROSPECTIVA: pares 56/68/72 elegidos despues de abrir las "
                "discordancias W4/W8; valida fenomenologia, no estima prevalencia"
            ),
            "tau_only_difference_checked": (
                "mismos constituyentes, source_state_content, seed, horizonte, dt, k y gamma"
            ),
            "tail_rule": (
                "en los ultimos 10 u.t., numero de cruces ascendentes receptores entre "
                "dos llegadas consecutivas de la misma capa; sin FFT/filtro/interpolacion"
            ),
            "onset_rule": "primer tick con diferencia bit-exacta ON vs OFF",
            "no_survival_classification": True,
        },
        "tau_runs": tau_runs,
        "onset_cases": onset,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[salida] {output}")


if __name__ == "__main__":
    main()
