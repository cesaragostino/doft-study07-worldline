#!/usr/bin/env python3
"""Gate E: rehace salud a 60 u.t. sin mezclar endpoints de films 60/120."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

from baseline_census import auc, indexar_reportes, indexar_views_w8, safe_output

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from study07.instruments.par import _rw_movil


HORIZON_UT = 60.0
LATE_UT = 10.0
FIRM_THRESHOLD = 0.95
FALSE_FIRM_DW = 1.1 / 8.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verdict_at_60(view: Path) -> dict:
    manifest = json.loads(view.with_name("manifest.json").read_text())
    dt = float(manifest["dt"])
    with np.load(view, allow_pickle=False) as data:
        ticks_all = np.asarray(data["ticks"])
        select = ticks_all * dt <= HORIZON_UT + dt * 0.25
        ticks = ticks_all[select]
        theta = np.asarray(data["theta"])[select]
        stored = {key: np.asarray(data[key]).copy()
                  for key in ("rw_final", "dw_tardia", "estado")}
    if not len(ticks) or ticks[-1] * dt < HORIZON_UT - dt:
        raise RuntimeError(f"view no alcanza 60 u.t.: {view}")
    w_ticks = int(round(8.0 / dt))
    late_ticks = int(round(LATE_UT / dt))
    unw = np.unwrap(theta, axis=0)
    grad = np.gradient(unw, dt, axis=0)
    phases = []
    for node in range(theta.shape[1]):
        omega_full = abs(float(np.mean(grad[:, node])))
        phases.append(np.unwrap(np.arctan2(
            np.sin(theta[:, node]) / max(omega_full, 1e-9),
            np.cos(theta[:, node]))))
    dphi = phases[0] - phases[1]
    rw = _rw_movil(dphi, w_ticks)
    rw_final = float(np.mean(rw[-w_ticks:]))
    omega_late = [abs(float(np.mean(grad[-late_ticks:, node])))
                  for node in range(theta.shape[1])]
    dw_late = float(abs(omega_late[0] - omega_late[1]))
    firm = rw_final >= FIRM_THRESHOLD
    close = dw_late < FALSE_FIRM_DW
    original_horizon = float(ticks_all[-1] * dt)
    replication = None
    if original_horizon <= HORIZON_UT + dt:
        replication = {
            "rw_abs_error": abs(rw_final - float(stored["rw_final"][0])),
            "dw_abs_error": abs(dw_late - float(stored["dw_tardia"][0])),
            "state_matches": bool(firm == (int(stored["estado"][0]) == 2)),
        }
    return {
        "original_horizon_ut": original_horizon,
        "rw_final_60": rw_final, "dw_tardia_60": dw_late,
        "firme_60": firm, "cierre_60": close, "salud_60": bool(firm and close),
        "view": str(view), "view_hash": manifest["view_hash"],
        "worldline_hash": manifest["worldline_hash"], "replication": replication,
    }


def metric(rows: list[dict], key: str, smaller: bool) -> dict:
    yes = [float(row[key]) for row in rows if row["salud_60"]]
    no = [float(row[key]) for row in rows if not row["salud_60"]]
    score = auc(yes, no)
    if score is not None and smaller:
        score = 1.0 - score
    return {"n_salud": len(yes), "n_no_salud": len(no),
            "mediana_salud": float(np.median(yes)) if yes else None,
            "mediana_no_salud": float(np.median(no)) if no else None,
            "auc_direccion": score, "direccion": "menor" if smaller else "mayor"}


def threshold(rows: list[dict], predicate) -> dict:
    selected = [row for row in rows if predicate(row)]
    rejected = [row for row in rows if not predicate(row)]
    return {
        "si": {"n": len(selected), "n_salud": sum(row["salud_60"] for row in selected),
               "fraccion_salud": float(np.mean([row["salud_60"] for row in selected]))
               if selected else None},
        "no": {"n": len(rejected), "n_salud": sum(row["salud_60"] for row in rejected),
               "fraccion_salud": float(np.mean([row["salud_60"] for row in rejected]))
               if rejected else None},
    }


def summarize(rows: list[dict]) -> dict:
    return {
        "n": len(rows), "n_salud_60": sum(row["salud_60"] for row in rows),
        "error_fase": metric(rows, "error_fase_fria", True),
        "error_complejo": metric(rows, "error_complejo_fria", True),
        "rho_observada": metric(rows, "rho_observada", False),
        "rho_predicha": metric(rows, "rho_predicha_fria", False),
        "cierre_complejo": threshold(rows, lambda row: row["cierre_complejo"]),
        "dominancia_y_cierre_complejo": threshold(
            rows, lambda row: row["cierre_complejo"] and row["rho_predicha_fria"] > 1.0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables-root", required=True, type=Path)
    parser.add_argument("--gate-d", required=True, type=Path)
    parser.add_argument("--reuse-records", type=Path,
                        help="reusa veredictos Gate E; no relee views")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    tables_root = args.tables_root.expanduser().resolve()
    gate_d_path = args.gate_d.expanduser().resolve()
    gate_d = json.loads(gate_d_path.read_text())
    gate_c_path = Path(gate_d["_meta"]["gate_c"])
    gate_c = json.loads(gate_c_path.read_text())
    gate_c_by_id = {row["run_id"]: row for row in gate_c["records"]}
    reuse_path = args.reuse_records.expanduser().resolve() if args.reuse_records else None
    reused = json.loads(reuse_path.read_text()) if reuse_path else None
    reports = indexar_reportes(tables_root)
    views = indexar_views_w8(tables_root)
    discovery_ids = set(gate_d["summary"]["ids_banco_descubrimiento_retirados"])
    rows = list(reused["records"]) if reused else []
    sources = [] if reused else gate_d["records"]
    for index, source in enumerate(sources, 1):
        report = reports[source["run_id"]]
        view = views[str(report["worldline_hash"])[:16]]
        row = dict(source)
        row.update(verdict_at_60(view))
        rows.append(row)
        if index % 20 == 0 or index == len(sources):
            print(f"[link-grumo] Gate E {index}/{len(sources)}", flush=True)

    for row in rows:
        row["rho_observada"] = float(gate_c_by_id[row["run_id"]]["rho_W8_temprano"])

    replications = [row["replication"] for row in rows if row["replication"] is not None]
    if not all(rep["rw_abs_error"] < 1e-12 and rep["dw_abs_error"] < 1e-10
               and rep["state_matches"] for rep in replications):
        raise RuntimeError("la reconstrucción no replica exactamente los films nativos de 60")
    flat = [row for row in rows if not row["chi_no_plana_W8"]]
    holdout = [row for row in rows if row["run_id"] not in discovery_ids]
    result = {
        "_meta": {"tables_root": str(tables_root),
                  "gate_d": str(gate_d_path), "gate_d_sha256": sha256(gate_d_path),
                  "gate_c": str(gate_c_path), "gate_c_sha256": sha256(gate_c_path),
                  "reuse_records": str(reuse_path) if reuse_path else None,
                  "reuse_records_sha256": sha256(reuse_path) if reuse_path else None,
                  "policy": "views locales sólo lectura; no toca tablas ni worldlines"},
        "metodo": {
            "horizon_ut": HORIZON_UT, "W_ut": 8.0, "late_ut": LATE_UT,
            "firme": f"rw_final_60>={FIRM_THRESHOLD}",
            "cierre": f"dw_[50,60] < {FALSE_FIRM_DW}",
            "salud": "firme AND cierre",
            "replica": "mismo algoritmo par_link v1.1 sobre theta truncada a 60",
        },
        "summary": {
            "combined": summarize(rows),
            "transported": summarize([row for row in rows if row["brazo"] == "t"]),
            "fresh": summarize([row for row in rows if row["brazo"] == "f"]),
            "banda_chi_plana_W8": summarize(flat),
            "holdout": summarize(holdout),
            "holdout_transportado": summarize([
                row for row in holdout if row["brazo"] == "t"]),
            "holdout_fresh": summarize([
                row for row in holdout if row["brazo"] == "f"]),
            "replication_60_native": {
                "n": len(replications),
                "max_rw_abs_error": max(rep["rw_abs_error"] for rep in replications),
                "max_dw_abs_error": max(rep["dw_abs_error"] for rep in replications),
                "all_state_match": all(rep["state_matches"] for rep in replications),
            },
            "horizons": {str(horizon): sum(abs(row["original_horizon_ut"] - horizon) < 0.01
                                            for row in rows)
                         for horizon in (60.0, 120.0)},
            "n_changed_vs_mixed_endpoint": sum(row["salud_60"] != row["salud_final"]
                                                for row in rows),
            "ids_banco_descubrimiento_retirados": sorted(discovery_ids),
        },
        "advertencias": [
            "Salud_60 es estado a un horizonte común, no supervivencia asintótica.",
            "La fase corregida se recalcula tras truncar, como exige par_link.",
            "No se reevalúa mudez/armónicos: Gate B3 ya excluyó esas banderas.",
            "Holdout transported conserva un solo positivo; no alcanza cierre inferencial.",
        ],
        "records": rows,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate E horizonte fijo: {len(rows)} films")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
