#!/usr/bin/env python3
"""Cosecha/reusa trends full-dt de potencia por capa y lock de pares single-edge."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time

import numpy as np


REPO = Path(__file__).resolve().parents[2]
EXTERNAL = Path("/Volumes/ExternalDisk").resolve()
EXTERNAL_TREND_ROOT = (EXTERNAL / "study07_link_bond_trending_v1").resolve()
LOCAL_TREND_ROOT = (REPO / "logs" / "link_grumo" / "bond_trending_v1").resolve()


def safe_output_root(path: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = REPO / candidate
    resolved = candidate.resolve()
    allowed = (resolved == EXTERNAL_TREND_ROOT
               or resolved.is_relative_to(EXTERNAL_TREND_ROOT)
               or resolved == LOCAL_TREND_ROOT
               or resolved.is_relative_to(LOCAL_TREND_ROOT))
    if not allowed:
        raise SystemExit(
            f"salida fuera de raíces permitidas: {resolved}; use "
            f"{EXTERNAL_TREND_ROOT} o {LOCAL_TREND_ROOT}"
        )
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def index_runs(root: Path) -> list[Path]:
    runs = sorted({complete.parent.resolve() for complete in root.rglob("COMPLETE")
                   if complete.parent.parent.name == "unidades"})
    if not runs:
        raise SystemExit(f"sin unidades COMPLETE bajo {root}")
    return runs


def _changes(values: np.ndarray) -> int:
    return int(np.sum(values[1:] != values[:-1])) if len(values) > 1 else 0


def summarize(arrays: dict, manifest: dict) -> dict:
    layers = list(manifest["layers"])
    ratios = [f"{int(p)}:{int(q)}" for p, q in np.asarray(arrays["ratios_pq"])]
    lock = np.asarray(arrays["lock_corrected_fixed"], dtype=float)
    lock_raw = np.asarray(arrays["lock_raw"], dtype=float)
    locked = np.asarray(arrays["locked"], dtype=bool)
    drift = np.asarray(arrays["phase_drift_rate"], dtype=float)
    dphi = np.asarray(arrays["dphi_corrected_unwrapped"], dtype=float)
    p_mean = np.asarray(arrays["power_layer_mean"], dtype=float)
    work = np.asarray(arrays["work_layer"], dtype=float)
    net = np.asarray(arrays["net_power_layer_mean"], dtype=float)
    opposed = np.asarray(arrays["opposed_power_fraction_layer"], dtype=float)
    force = np.asarray(arrays["force_rms"], dtype=float)
    mute = np.asarray(arrays["mute"], dtype=bool)
    if not all(np.isfinite(array).all() for array in
               (lock, lock_raw, drift, dphi, p_mean, work, net, opposed, force)):
        raise RuntimeError("vista trending con NaN/Inf")

    phase_summary = []
    for ratio_index, ratio in enumerate(ratios):
        by_layer = []
        for layer_index, layer in enumerate(layers):
            values = lock[:, ratio_index, layer_index]
            states = locked[:, ratio_index, layer_index]
            phase = dphi[:, ratio_index, layer_index]
            by_layer.append({
                "layer": layer,
                "lock_median": float(np.median(values)),
                "lock_q10": float(np.quantile(values, 0.10)),
                "lock_q90": float(np.quantile(values, 0.90)),
                "lock_min": float(np.min(values)),
                "lock_max": float(np.max(values)),
                "raw_corrected_median_abs_delta": float(np.median(np.abs(
                    values - lock_raw[:, ratio_index, layer_index]))),
                "locked_fraction": float(np.mean(states)),
                "locked_state_changes": _changes(states),
                "phase_excursion": float(np.max(phase) - np.min(phase)),
                "drift_median": float(np.median(drift[:, ratio_index, layer_index])),
                "drift_max": float(np.max(drift[:, ratio_index, layer_index])),
                "mute_fraction": float(np.mean(np.any(mute[:, :, layer_index], axis=1))),
            })
        phase_summary.append({"ratio": ratio, "layers": by_layer})

    power_summary = []
    for layer_index, layer in enumerate(layers):
        power_summary.append({
            "layer": layer,
            "nodes": [{
                "node": node,
                "p_mean_median": float(np.median(p_mean[:, node, layer_index])),
                "p_mean_min": float(np.min(p_mean[:, node, layer_index])),
                "p_mean_max": float(np.max(p_mean[:, node, layer_index])),
                "work_final": float(work[-1, node, layer_index]),
                "power_sign_changes": _changes(p_mean[:, node, layer_index] >= 0.0),
            } for node in range(2)],
            "net_power_median": float(np.median(net[:, layer_index])),
            "net_power_min": float(np.min(net[:, layer_index])),
            "net_power_max": float(np.max(net[:, layer_index])),
            "net_power_sign_changes": _changes(net[:, layer_index] >= 0.0),
            "opposed_power_fraction_median": float(np.median(opposed[:, layer_index])),
        })

    return {
        "n_trend_rows": int(len(arrays["ticks_end"])),
        "t_range_ut": [float(arrays["t_end_ut"][0]), float(arrays["t_end_ut"][-1])],
        "force_rms_median_by_node": [float(value) for value in np.median(force, axis=0)],
        "phase": phase_summary,
        "power": power_summary,
    }


def evaluate_one(job: tuple[str, str, dict]) -> dict:
    run_dir_s, views_root_s, observation_config = job
    run_dir, views_root = Path(run_dir_s), Path(views_root_s)
    try:
        from study07.instruments import api, link_bond_trend
        cfg, _ = link_bond_trend._validated_config(observation_config)
        wl_hash = api.worldline_hash(run_dir)
        view_dir = (views_root / wl_hash[:16] / link_bond_trend.INSTRUMENT_ID
                    / api.config_hash(link_bond_trend.INSTRUMENT_ID,
                                      link_bond_trend.VERSION, cfg))
        if (view_dir / "manifest.json").is_file():
            loaded = api.load_view(view_dir)
            status = "reused"
        else:
            view = link_bond_trend.run_path(run_dir, observation_config)
            written = view.write(views_root)
            loaded = api.load_view(written)
            status = "computed"
        manifest, arrays = loaded["manifest"], loaded["arrays"]
        return {
            "run_id": str(manifest.get("run_id") or run_dir.name),
            "run_dir": str(run_dir),
            "status": status,
            "worldline_hash": manifest["worldline_hash"],
            "view_hash_trending": loaded["view_hash"],
            "view_dir": str(view_dir),
            "summary": summarize(arrays, manifest),
        }
    except Exception as exc:
        return {
            "run_id": run_dir.name,
            "run_dir": str(run_dir),
            "status": "failed",
            "error_class": type(exc).__name__,
            "error": str(exc)[:1200],
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worldlines-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--lock-window-ut", type=float, default=4.0)
    parser.add_argument("--power-window-ut", type=float, default=2.0)
    parser.add_argument("--hop-ut", type=float, default=0.25)
    parser.add_argument("--ratios", default="1:1")
    parser.add_argument("--lock-threshold", type=float, default=0.90)
    parser.add_argument("--retain-dt", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers debe ser >=1")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit debe ser >=1")
    source = args.worldlines_root.expanduser().resolve()
    output_root = safe_output_root(args.output_root)
    if output_root == source or output_root.is_relative_to(source):
        raise SystemExit("la salida trending no puede vivir dentro de la fuente")
    views_root = output_root / "views"
    views_root.mkdir(parents=True, exist_ok=True)
    ratios = [item.strip() for item in args.ratios.split(",") if item.strip()]
    observation_config = {
        "lock_window_ut": args.lock_window_ut,
        "power_window_ut": args.power_window_ut,
        "hop_ut": args.hop_ut,
        "ratios": ratios,
        "lock_threshold": args.lock_threshold,
        "retain_dt": bool(args.retain_dt),
    }
    # Valida antes de abrir 190 GB.
    from study07.instruments import link_bond_trend
    normalized_config, _ = link_bond_trend._validated_config(observation_config)

    runs = index_runs(source)
    if args.limit is not None:
        runs = runs[:args.limit]
    jobs = [(str(run), str(views_root), observation_config) for run in runs]
    started = time.time()
    records = []
    print(f"[bond-trending] {len(jobs)} films, workers={args.workers}, "
          f"ratios={ratios}, retain_dt={args.retain_dt}", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for index, record in enumerate(executor.map(evaluate_one, jobs, chunksize=1), 1):
            records.append(record)
            if index % 5 == 0 or index == len(jobs):
                failed = sum(item["status"] == "failed" for item in records)
                print(f"[{index}/{len(jobs)}] failed={failed} "
                      f"elapsed={time.time()-started:.1f}s", flush=True)
    records.sort(key=lambda item: item["run_id"])
    result = {
        "_meta": {
            "source": str(source),
            "output_root": str(output_root),
            "source_policy": "read-only",
            "instrument": f"{link_bond_trend.INSTRUMENT_ID} v{link_bond_trend.VERSION}",
            "observation_config": normalized_config,
            "workers": args.workers,
            "limit": args.limit,
        },
        "summary": {
            "n": len(records),
            "computed": sum(record["status"] == "computed" for record in records),
            "reused": sum(record["status"] == "reused" for record in records),
            "failed": sum(record["status"] == "failed" for record in records),
            "elapsed_seconds": float(time.time() - started),
        },
        "records": records,
        "warnings": [
            "No hay outcome, AUC ni score de salud en esta cosecha.",
            "corrected_fixed usa omega media del film completo: descriptor, no predictor causal.",
            "Potencia por capa particiona el input uniforme de v1; no identifica endpoint.",
            "La primera cosecha p:q queda fijada en 1:1 salvo config explícita distinta.",
        ],
    }
    ledger = output_root / "population.json"
    tmp = ledger.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    tmp.replace(ledger)
    ledger_sha = hashlib.sha256(ledger.read_bytes()).hexdigest()
    print(f"[bond-trending] ledger={ledger} sha256={ledger_sha}", flush=True)


if __name__ == "__main__":
    main()
