#!/usr/bin/env python3
"""Mide tiempos directos en ticks sobre films libres de dos onions.

La lectura tiene dos alcances deliberadamente distintos:

1. confirma el retardo causal configurado reconstruyendo ``drive[k]`` desde
   ``state[k-1]`` y ``state[k-1-N_edge]``;
2. tabula cruces ascendentes llegada->Q/S1/S2 como observables. Esos cruces
   NO se interpretan automáticamente como un delay interno.

No integra, filtra, interpola ni consulta outcomes de lock o salud.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np


RUN_IDS = (
    "s120_par129_t_k03_tau02",
    "s120_par131_t_k03_tau02",
    "s120_par132_t_k03_tau02",
    "s120_par134_t_k03_tau02",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def safe_output(path: Path) -> Path:
    resolved = path.resolve()
    external = Path("/Volumes/ExternalDisk").resolve()
    if resolved == external or external in resolved.parents:
        raise RuntimeError("la salida no puede estar en /Volumes/ExternalDisk")
    allowed = (Path.cwd() / "logs" / "link_grumo").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise RuntimeError(f"la salida debe quedar bajo {allowed}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def upward_crossings(values: np.ndarray) -> np.ndarray:
    """Ticks k con values[k-1] < 0 y values[k] >= 0, sin interpolar."""
    values = np.asarray(values, dtype=np.float64)
    return np.flatnonzero((values[:-1] < 0.0) & (values[1:] >= 0.0)).astype(
        np.int64
    ) + 1


def integer_summary(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=np.int64)
    if values.size == 0:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {
        "n": int(values.size),
        "min": int(np.min(values)),
        "median": float(np.median(values)),
        "max": int(np.max(values)),
    }


def validate_manifest(manifest: dict, run_id: str) -> tuple[float, int]:
    if manifest.get("run_id") != run_id:
        raise RuntimeError(f"{run_id}: run_id del manifiesto no coincide")
    if int(manifest.get("n_nodes", -1)) != 2:
        raise RuntimeError(f"{run_id}: se requieren exactamente dos nodos")
    topology = manifest.get("topologia", {})
    if topology.get("edges_ij") != [[0, 1]]:
        raise RuntimeError(f"{run_id}: se requiere una única arista [0,1]")
    dt = float(manifest["dt"])
    tau = float(topology["tau"][0])
    ratio = tau / dt
    edge_ticks = int(round(ratio))
    if not np.isfinite(dt) or dt <= 0.0 or not np.isfinite(tau) or tau < 0.0:
        raise RuntimeError(f"{run_id}: dt/tau inválidos")
    if abs(ratio - edge_ticks) > 1e-12:
        raise RuntimeError(f"{run_id}: tau/dt no es entero: {ratio!r}")
    for node, info in enumerate(manifest["por_nodo"]):
        n_modes = int(info["n_modes"])
        layers = list(info["capas_por_modo"])
        if len(layers) != n_modes:
            raise RuntimeError(f"{run_id}: capas y modos difieren en nodo {node}")
        if set(layers) != {"Q", "S1", "S2"}:
            raise RuntimeError(f"{run_id}: faltan capas Q/S1/S2 en nodo {node}")
        if not np.isfinite(float(info["emission_scale"])):
            raise RuntimeError(f"{run_id}: emission_scale inválida en nodo {node}")
    return dt, edge_ticks


def read_verified_run(run_dir: Path) -> tuple[dict, dict, dict]:
    run_id = run_dir.name
    manifest_path = run_dir / "manifest.json"
    complete_path = run_dir / "COMPLETE"
    manifest_raw = manifest_path.read_bytes()
    complete = json.loads(complete_path.read_text())
    manifest = json.loads(manifest_raw)
    manifest_sha = sha256_bytes(manifest_raw)
    if manifest_sha != complete.get("manifest_sha"):
        raise RuntimeError(f"{run_id}: SHA de manifest no coincide con COMPLETE")
    dt, edge_ticks = validate_manifest(manifest, run_id)

    chunk_paths = sorted((run_dir / "worldline").glob("chunk_*.npz"))
    expected_shas = list(complete["chunk_shas"])
    if len(chunk_paths) != int(complete["chunks"]) or len(chunk_paths) != len(expected_shas):
        raise RuntimeError(f"{run_id}: cantidad de chunks no coincide con COMPLETE")

    ticks_parts: list[np.ndarray] = []
    drive_parts: list[np.ndarray] = []
    node_parts: list[dict[str, list[np.ndarray]]] = [
        {"x": [], "v": [], "Q": [], "S1": [], "S2": []} for _ in range(2)
    ]
    verified_chunks: list[dict] = []

    for path, expected_sha in zip(chunk_paths, expected_shas):
        raw = path.read_bytes()
        observed_sha = sha256_bytes(raw)
        if observed_sha != expected_sha:
            raise RuntimeError(f"{run_id}/{path.name}: SHA no coincide con COMPLETE")
        verified_chunks.append({"file": path.name, "sha256": observed_sha})
        with np.load(io.BytesIO(raw), allow_pickle=False) as data:
            ticks = np.asarray(data["ticks"], dtype=np.int64)
            drive = np.asarray(data["drive"], dtype=np.float64)
            if drive.shape != (ticks.size, 2):
                raise RuntimeError(f"{run_id}/{path.name}: forma de drive inválida")
            ticks_parts.append(ticks)
            drive_parts.append(drive)
            for node, info in enumerate(manifest["por_nodo"]):
                state = np.asarray(data[f"estados_nodo{node}"], dtype=np.float64)
                n_modes = int(info["n_modes"])
                if state.shape != (ticks.size, int(manifest["dims"][node])):
                    raise RuntimeError(f"{run_id}/{path.name}: estado nodo {node} inválido")
                x = state[:, :n_modes]
                v = state[:, n_modes : 2 * n_modes]
                scale = float(info["emission_scale"])
                node_parts[node]["x"].append(scale * np.sum(x, axis=1))
                node_parts[node]["v"].append(scale * np.sum(v, axis=1))
                layers = np.asarray(info["capas_por_modo"])
                for layer in ("Q", "S1", "S2"):
                    node_parts[node][layer].append(np.sum(x[:, layers == layer], axis=1))

    ticks = np.concatenate(ticks_parts)
    expected_ticks = np.arange(int(complete["ticks"]) + 1, dtype=np.int64)
    if not np.array_equal(ticks, expected_ticks):
        raise RuntimeError(f"{run_id}: ticks perdidos, repetidos o no contiguos")
    series = {
        "ticks": ticks,
        "drive": np.concatenate(drive_parts, axis=0),
        "nodes": [
            {name: np.concatenate(parts) for name, parts in node.items()}
            for node in node_parts
        ],
    }
    provenance = {
        "run_dir": str(run_dir),
        "manifest_sha256": manifest_sha,
        "complete_sha256": hashlib.sha256(complete_path.read_bytes()).hexdigest(),
        "chunks_verified": verified_chunks,
    }
    clock = {"dt": dt, "edge_ticks": edge_ticks}
    return manifest, series, {"clock": clock, "provenance": provenance}


def reconstruct_drive(manifest: dict, series: dict, edge_ticks: int) -> dict:
    x0, x1 = series["nodes"][0]["x"], series["nodes"][1]["x"]
    v0, v1 = series["nodes"][0]["v"], series["nodes"][1]["v"]
    drive = series["drive"]
    # drive[k] parte de state[k-1]. Para k=N+1, la muestra retardada ya es state[0].
    drive_ticks = np.arange(edge_ticks + 1, drive.shape[0], dtype=np.int64)
    current_ticks = drive_ticks - 1
    delayed_ticks = current_ticks - edge_ticks
    spring = float(manifest["k_global"])
    damp = float(manifest["gamma_c"])
    predicted0 = (
        spring * (x1[delayed_ticks] - x0[current_ticks])
        + damp * (v1[delayed_ticks] - v0[current_ticks])
    )
    predicted1 = (
        spring * (x0[delayed_ticks] - x1[current_ticks])
        + damp * (v0[delayed_ticks] - v1[current_ticks])
    )
    predicted = np.column_stack((predicted0, predicted1))
    residual = predicted - drive[drive_ticks]
    return {
        "semantics": {
            "drive_row": "drive[k]",
            "current_state_row": "state[k-1]",
            "delayed_state_row": f"state[k-1-{edge_ticks}]",
            "first_reconstructable_drive_tick": int(edge_ticks + 1),
        },
        "n_rows": int(residual.shape[0]),
        "max_abs_residual": float(np.max(np.abs(residual))),
        "rms_residual": float(np.sqrt(np.mean(np.square(residual)))),
        "n_bit_exact": int(np.sum(residual == 0.0)),
        "n_scalar_values": int(residual.size),
    }


def crossing_table(series: dict, dt: float, edge_ticks: int, source: int) -> dict:
    receiver = 1 - source
    source_crossings = upward_crossings(series["nodes"][source]["x"])
    arrivals = source_crossings + edge_ticks
    keep = arrivals < series["ticks"].size
    source_crossings = source_crossings[keep]
    arrivals = arrivals[keep]
    result = {
        "reference_node": int(source),
        "receiver_node": int(receiver),
        "event_rule": "upcross: value[k-1] < 0 and value[k] >= 0; no interpolation",
        "arrival_rule": "arrival_state_tick = emission_state_tick + edge_ticks",
        "reference_emission_upcross_ticks": source_crossings.tolist(),
        "reference_period_delta_ticks": np.diff(source_crossings).astype(int).tolist(),
        "reference_period_summary_ticks": integer_summary(np.diff(source_crossings)),
        "layers": {},
    }
    for layer in ("Q", "S1", "S2"):
        response = upward_crossings(series["nodes"][receiver][layer])
        indices = np.searchsorted(response, arrivals, side="left")
        valid = indices < response.size
        mapped_response = np.full(arrivals.shape, -1, dtype=np.int64)
        mapped_response[valid] = response[indices[valid]]
        delta = mapped_response - arrivals
        valid_delta = delta[valid]
        used = mapped_response[valid]
        mappings = []
        for emission_tick, arrival_tick, response_tick in zip(
            source_crossings.tolist(), arrivals.tolist(), mapped_response.tolist()
        ):
            if response_tick < 0:
                mappings.append(
                    {
                        "tick_origen_emision": int(emission_tick),
                        "tick_llegada": int(arrival_tick),
                        "tick_destino_respuesta": None,
                        "delta_llegada_respuesta_ticks": None,
                        "delta_llegada_respuesta_ut": None,
                        "delta_emision_respuesta_ticks": None,
                        "delta_emision_respuesta_ut": None,
                    }
                )
                continue
            delta_arrival = int(response_tick - arrival_tick)
            delta_total = int(response_tick - emission_tick)
            mappings.append(
                {
                    "tick_origen_emision": int(emission_tick),
                    "tick_llegada": int(arrival_tick),
                    "tick_destino_respuesta": int(response_tick),
                    "delta_llegada_respuesta_ticks": delta_arrival,
                    "delta_llegada_respuesta_ut": float(delta_arrival * dt),
                    "delta_emision_respuesta_ticks": delta_total,
                    "delta_emision_respuesta_ut": float(delta_total * dt),
                }
            )
        unique_used = int(np.unique(used).size) if used.size else 0
        result["layers"][layer] = {
            "receiver_upcross_ticks": response.tolist(),
            "receiver_period_delta_ticks": np.diff(response).astype(int).tolist(),
            "receiver_period_summary_ticks": integer_summary(np.diff(response)),
            "n_arrivals": int(arrivals.size),
            "n_mapped": int(np.sum(valid)),
            "n_unmapped": int(np.sum(~valid)),
            "n_distinct_response_ticks_used": unique_used,
            "n_arrivals_sharing_response": int(np.sum(valid) - unique_used),
            "arrival_to_response_summary_ticks": integer_summary(valid_delta),
            "mappings": mappings,
        }
    return result


def analyze_run(run_dir: Path, source: int) -> dict:
    manifest, series, custody = read_verified_run(run_dir)
    dt = float(custody["clock"]["dt"])
    edge_ticks = int(custody["clock"]["edge_ticks"])
    return {
        "run_id": run_dir.name,
        "custody": custody["provenance"],
        "clock": {
            "dt": dt,
            "tau_config_ut": float(manifest["topologia"]["tau"][0]),
            "tau_over_dt": float(manifest["topologia"]["tau"][0]) / dt,
            "edge_ticks": edge_ticks,
            "n_state_rows": int(series["ticks"].size),
            "last_state_tick": int(series["ticks"][-1]),
        },
        "drive_reconstruction": reconstruct_drive(manifest, series, edge_ticks),
        "crossing_observations": crossing_table(series, dt, edge_ticks, source),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runs-root",
        type=Path,
        required=True,
        help="directorio read-only que contiene las unidades s120",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-node", type=int, choices=(0, 1), default=0)
    args = parser.parse_args()
    output = safe_output(args.output)
    runs = []
    for run_id in RUN_IDS:
        run_dir = args.runs_root / run_id
        if not run_dir.is_dir():
            raise RuntimeError(f"falta unidad: {run_dir}")
        print(f"[leer] {run_id}", flush=True)
        runs.append(analyze_run(run_dir, args.source_node))
    payload = {
        "schema": "link_grumo_tiempos_ticks_v1",
        "scope": {
            "runs": list(RUN_IDS),
            "source_node_operational": int(args.source_node),
            "no_fft": True,
            "no_filter": True,
            "no_interpolation": True,
            "no_lock_or_health_outcomes": True,
            "interpretation_limit": (
                "los cruces llegada->capa son tiempos observados modulo la dinamica periodica; "
                "no prueban un delay interno causal"
            ),
        },
        "runs": runs,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[salida] {output}")


if __name__ == "__main__":
    main()
