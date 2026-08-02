#!/usr/bin/env python3
"""Gate J: calcula/reusa vistas causales de potencia sobre films archivados.

Las entradas son read-only. Tanto las vistas como el ledger deben quedar debajo de
``logs/link_grumo`` del worktree. Este paso publica magnitudes y signos; no modifica
el veredicto de lock ni construye una regla de fitness.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time

import numpy as np

from baseline_census import EXTERNAL_ROOT, SAFE_OUTPUT_ROOT, safe_output


def safe_views_root(path: Path) -> Path:
    root = SAFE_OUTPUT_ROOT.resolve()
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = Path(__file__).resolve().parents[2] / candidate
    resolved = candidate.resolve()
    if resolved.is_relative_to(EXTERNAL_ROOT.resolve()):
        raise SystemExit("La salida de vistas bajo /Volumes/ExternalDisk está prohibida")
    if not resolved.is_relative_to(root):
        raise SystemExit(f"Las vistas deben quedar bajo {root}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def index_runs(root: Path) -> list[Path]:
    runs = sorted({complete.parent.resolve() for complete in root.rglob("COMPLETE")
                   if complete.parent.parent.name == "unidades"})
    if not runs:
        raise SystemExit(f"No se encontraron unidades COMPLETE bajo {root}")
    return runs


def summarize(arrays: dict, manifest: dict) -> dict:
    valid = np.asarray(arrays["window_complete"], dtype=bool)
    p_mean = np.asarray(arrays["p_node_mean"], dtype=float)
    force_rms = np.asarray(arrays["force_rms"], dtype=float)
    ratio = np.asarray(arrays["p_over_force2"], dtype=float)
    fneg = np.asarray(arrays["fraction_negative"], dtype=float)
    work = np.asarray(arrays["work_node"], dtype=float)
    if not np.any(valid):
        raise RuntimeError("vista sin una caja causal completa")
    vv = np.flatnonzero(valid)
    last = int(vv[-1])
    duration = float((arrays["ticks_step"][-1] - arrays["ticks_step"][0] + 1)
                     * manifest["dt"])
    node = []
    for j in range(p_mean.shape[1]):
        finite_ratio = ratio[valid, j][np.isfinite(ratio[valid, j])]
        node.append({
            "node": j,
            "work_total": float(work[-1, j]),
            "mean_power_total": float(work[-1, j] / max(duration, 1e-300)),
            "p_mean_final": float(p_mean[last, j]),
            "fraction_negative_final": float(fneg[last, j]),
            "force_rms_final": float(force_rms[last, j]),
            "p_over_force2_final": (
                float(ratio[last, j]) if np.isfinite(ratio[last, j]) else None),
            "median_p_over_force2": (
                float(np.median(finite_ratio)) if finite_ratio.size else None),
            "fraction_windows_positive": float(np.mean(p_mean[valid, j] > 0.0)),
            "fraction_windows_negative": float(np.mean(p_mean[valid, j] < 0.0)),
        })
    pair = None
    if bool(manifest["single_edge_pair_identifiable"]):
        p0, p1 = p_mean[valid, 0], p_mean[valid, 1]
        pair = {
            "opposed_sign_fraction": float(np.mean((p0 * p1) < 0.0)),
            "both_positive_fraction": float(np.mean((p0 > 0.0) & (p1 > 0.0))),
            "both_negative_fraction": float(np.mean((p0 < 0.0) & (p1 < 0.0))),
            "net_work": float(work[-1, 0] + work[-1, 1]),
        }
    return {
        "n_published": int(len(arrays["ticks_step"])),
        "n_complete_windows": int(np.sum(valid)),
        "t_force_range_ut": [float(arrays["t_force_ut"][0]),
                             float(arrays["t_force_ut"][-1])],
        "nodes": node,
        "pair": pair,
    }


def evaluate_one(args: tuple[str, str, dict]) -> dict:
    run_dir_s, views_root_s, observation_config = args
    run_dir = Path(run_dir_s)
    views_root = Path(views_root_s)
    try:
        from study07.instruments import api, link_power
        cfg = {**link_power.DEFAULTS, **observation_config}
        wl_hash = api.worldline_hash(run_dir)
        view_dir = (views_root / wl_hash[:16] / link_power.INSTRUMENT_ID
                    / api.config_hash(link_power.INSTRUMENT_ID, link_power.VERSION, cfg))
        if (view_dir / "manifest.json").is_file():
            loaded = api.load_view(view_dir)
            arrays, manifest = loaded["arrays"], loaded["manifest"]
            view_hash, status = loaded["view_hash"], "reused"
        else:
            wl = api.load_run(run_dir)
            view = link_power.run(wl, observation_config)
            path = view.write(views_root)
            loaded = api.load_view(path)
            arrays, manifest = loaded["arrays"], loaded["manifest"]
            view_hash, status = loaded["view_hash"], "computed"
        return {
            "run_id": str(manifest.get("run_id", run_dir.name)),
            "run_dir": str(run_dir),
            "worldline_hash": manifest["worldline_hash"],
            "view_hash_power": view_hash,
            "status": status,
            "single_edge_pair_identifiable": bool(
                manifest["single_edge_pair_identifiable"]),
            "node_degree": manifest["node_degree"],
            "summary": summarize(arrays, manifest),
        }
    except Exception as exc:
        return {
            "run_id": run_dir.name,
            "run_dir": str(run_dir),
            "status": "failed",
            "error_class": type(exc).__name__,
            "error": str(exc)[:800],
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worldlines-root", required=True, type=Path)
    parser.add_argument("--views-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--box-ut", type=float, default=2.0)
    parser.add_argument("--hop-ut", type=float, default=0.25)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers debe ser >=1")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit debe ser >=1")
    root = args.worldlines_root.expanduser().resolve()
    output = safe_output(args.output)
    views_root = safe_views_root(args.views_root)
    runs = index_runs(root)
    if args.limit is not None:
        runs = runs[:args.limit]
    observation_config = {"box_ut": args.box_ut, "hop_ut": args.hop_ut}
    jobs = [(str(run), str(views_root), observation_config) for run in runs]
    started = time.time()
    records = []
    print(f"[link-grumo] Gate J: {len(jobs)} films, {args.workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for index, record in enumerate(executor.map(evaluate_one, jobs, chunksize=1), 1):
            records.append(record)
            if index % 10 == 0 or index == len(jobs):
                failed = sum(item["status"] == "failed" for item in records)
                print(f"[{index}/{len(jobs)}] fallidas={failed} "
                      f"elapsed={time.time()-started:.1f}s", flush=True)
    records.sort(key=lambda item: item["run_id"])
    result = {
        "_meta": {
            "worldlines_root": str(root),
            "views_root": str(views_root),
            "policy": "entradas read-only; vistas y ledger bajo logs/link_grumo",
            "instrument": "link_power v1.1",
            "observation_config": observation_config,
            "workers": args.workers,
            "limit": args.limit,
        },
        "summary": {
            "n": len(records),
            "computed": sum(item["status"] == "computed" for item in records),
            "reused": sum(item["status"] == "reused" for item in records),
            "failed": sum(item["status"] == "failed" for item in records),
            "single_edge_identifiable": sum(
                item.get("single_edge_pair_identifiable", False) for item in records),
            "elapsed_seconds": float(time.time() - started),
        },
        "records": records,
        "warnings": [
            "No hay umbral de signo: magnitudes diminutas deben cruzarse con force_rms.",
            "Los resúmenes son simultáneos; no prueban early-power -> late-survival.",
            "En redes multiarista P es neta por nodo y no se atribuye a edges.",
        ],
    }
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    tmp.replace(output)
    print(f"[link-grumo] salida: {output}", flush=True)


if __name__ == "__main__":
    main()
