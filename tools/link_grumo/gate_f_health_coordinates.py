#!/usr/bin/env python3
"""Gate F3: audita salud60 usando frecuencia y coherencia en la misma fase corregida.

El veredicto vigente combina rw de fase corregida con dw de theta cruda. Este gate no lo
reemplaza: cuantifica qué cambia si el guard de deriva 1.1/W se aplica a la pendiente de
la propia diferencia de fase corregida. Sólo lee views locales ya construidas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from baseline_census import (auc, cargar_filas, indexar_reportes, indexar_views_w8,
                             safe_output)
from study07.instruments.par import _rw_movil


HORIZON_UT = 60.0
LATE_UT = 10.0
W_UT = 8.0
FIRM_THRESHOLD = 0.95
DRIFT_THRESHOLD = 1.1 / W_UT
RAYLEIGH = 2.0 * np.pi / W_UT


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corrected_verdict(view: Path) -> dict:
    manifest = json.loads(view.with_name("manifest.json").read_text())
    dt = float(manifest["dt"])
    with np.load(view, allow_pickle=False) as data:
        ticks_all = np.asarray(data["ticks"])
        select = ticks_all * dt <= HORIZON_UT + dt * 0.25
        ticks = ticks_all[select]
        theta = np.asarray(data["theta"])[select]
    if ticks[-1] * dt < HORIZON_UT - dt:
        raise RuntimeError(f"view no alcanza 60 u.t.: {view}")
    times = ticks * dt
    unwrapped = np.unwrap(theta, axis=0)
    gradient = np.gradient(unwrapped, dt, axis=0)
    phases = []
    for node in range(theta.shape[1]):
        omega_full = abs(float(np.mean(gradient[:, node])))
        phases.append(np.unwrap(np.arctan2(
            np.sin(theta[:, node]) / max(omega_full, 1e-9),
            np.cos(theta[:, node]))))
    dphi = phases[0] - phases[1]
    w_ticks = int(round(W_UT / dt))
    rw = _rw_movil(dphi, w_ticks)
    rw_final = float(np.mean(rw[-w_ticks:]))
    late_ticks = int(round(LATE_UT / dt))
    raw_omega = [abs(float(np.mean(gradient[-late_ticks:, node])))
                 for node in range(theta.shape[1])]
    raw_dw = float(abs(raw_omega[0] - raw_omega[1]))
    late = times >= HORIZON_UT - LATE_UT
    corrected_slope = float(abs(np.polyfit(times[late], dphi[late], 1)[0]))
    corrected_net = float(abs((dphi[late][-1] - dphi[late][0])
                              / (times[late][-1] - times[late][0])))
    corrected_rw10 = float(abs(np.mean(np.exp(1j * dphi[late]))))
    firm = rw_final >= FIRM_THRESHOLD
    return {
        "rw_final_60": rw_final, "raw_dw_50_60": raw_dw,
        "corrected_slope_50_60": corrected_slope,
        "corrected_net_50_60": corrected_net, "corrected_rw_50_60": corrected_rw10,
        "firm": firm, "raw_close": raw_dw < DRIFT_THRESHOLD,
        "corrected_close": corrected_slope < DRIFT_THRESHOLD,
        "raw_health": bool(firm and raw_dw < DRIFT_THRESHOLD),
        "coordinate_health": bool(firm and corrected_slope < DRIFT_THRESHOLD),
        "original_horizon_ut": float(ticks_all[-1] * dt),
        "view": str(view), "view_hash": manifest["view_hash"],
        "worldline_hash": manifest["worldline_hash"],
        "nodos_mudos": manifest.get("nodos_mudos", []),
        "nodos_armonico": manifest.get("nodos_armonico", []),
    }


def rates(rows: list[dict], key: str) -> dict:
    result = {"n": len(rows), "n_yes": sum(row[key] for row in rows)}
    result["rate"] = float(result["n_yes"] / len(rows)) if rows else None
    return result


def stratified(rows: list[dict], key: str) -> dict:
    return {
        "combined": rates(rows, key),
        "transported": rates([row for row in rows if row["arm"] == "t"], key),
        "fresh": rates([row for row in rows if row["arm"] == "f"], key),
    }


def paired_delta(rows: list[dict], key: str) -> dict:
    pairs: dict[str, dict[str, dict]] = {}
    for row in rows:
        pairs.setdefault(row["pair"], {})[row["arm"]] = row
    complete = [pair for pair in pairs.values() if "t" in pair and "f" in pair]
    return {
        "n": len(complete),
        "t_yes_f_no": sum(pair["t"][key] and not pair["f"][key] for pair in complete),
        "f_yes_t_no": sum(pair["f"][key] and not pair["t"][key] for pair in complete),
        "both_yes": sum(pair["f"][key] and pair["t"][key] for pair in complete),
        "both_no": sum(not pair["f"][key] and not pair["t"][key] for pair in complete),
        "mean_t_minus_f": float(np.mean([
            int(pair["t"][key]) - int(pair["f"][key]) for pair in complete]))
        if complete else None,
    }


def predictor_summary(rows: list[dict], gate_e: dict, outcome: str) -> dict:
    by_id = {row["run_id"]: row for row in rows}
    joined = [(source, by_id[source["run_id"]]) for source in gate_e["records"]]
    positive = [float(source["rho_predicha_fria"]) for source, row in joined if row[outcome]]
    negative = [float(source["rho_predicha_fria"]) for source, row in joined if not row[outcome]]
    return {
        "n": len(joined), "n_positive": len(positive), "n_negative": len(negative),
        "rho_pred_auc": auc(positive, negative),
        "median_positive": float(np.median(positive)) if positive else None,
        "median_negative": float(np.median(negative)) if negative else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables-root", required=True, type=Path)
    parser.add_argument("--gate-e", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    tables_root = args.tables_root.expanduser().resolve()
    gate_e_path = args.gate_e.expanduser().resolve()
    gate_e = json.loads(gate_e_path.read_text())
    table_rows, table_hashes = cargar_filas(tables_root)
    reports = indexar_reportes(tables_root)
    views = indexar_views_w8(tables_root)
    records = []
    for index, source in enumerate(table_rows, 1):
        if source["_self"]:
            continue
        report = reports[source["run_id"]]
        view = views[str(report["worldline_hash"])[:16]]
        record = {
            "run_id": source["run_id"], "pair": source["_par"],
            "arm": source["brazo"], "isolated_dw": source["_dw"],
            "resolvable_W8": bool(float(source["W8"]["dw_temprana"]) >= RAYLEIGH),
        }
        record.update(corrected_verdict(view))
        record["flagged"] = bool(record["nodos_mudos"] or record["nodos_armonico"])
        records.append(record)
        if index % 50 == 0 or index == len(table_rows):
            print(f"[link-grumo] F3 {index}/{len(table_rows)}", flush=True)

    native = [row for row in records if row["original_horizon_ut"] <= HORIZON_UT + 1e-3]
    table_by_id = {row["run_id"]: row for row in table_rows}
    replication = [{
        "rw_error": abs(row["rw_final_60"]
                        - float(table_by_id[row["run_id"]]["W8"]["rw_final"])),
        "dw_error": abs(row["raw_dw_50_60"]
                        - float(table_by_id[row["run_id"]]["W8"]["dw_tardia"])),
    } for row in native]
    if replication and (max(item["rw_error"] for item in replication) > 1e-12
                        or max(item["dw_error"] for item in replication) > 1e-10):
        raise RuntimeError("F3 no replica las vistas nativas de 60 u.t.")

    clean = [row for row in records if not row["flagged"]]
    eligible = [row for row in clean if row["resolvable_W8"]]
    flips = [row for row in records if row["raw_health"] != row["coordinate_health"]]
    result = {
        "_meta": {
            "tables_root": str(tables_root), "table_sha256": table_hashes,
            "gate_e": str(gate_e_path), "gate_e_sha256": sha256(gate_e_path),
            "policy": "sólo views locales; no lee ni escribe worldlines externas",
        },
        "method": {
            "status": "auditoría exploratoria; NO reemplaza el outcome sellado Gate E",
            "common": "rw_final corregido W8>=0.95",
            "raw_guard": f"dw theta cruda [50,60] < {DRIFT_THRESHOLD}",
            "coordinate_guard": ("|pendiente OLS de dphi corregida en [50,60]| < "
                                 f"{DRIFT_THRESHOLD}"),
            "reason": "aplicar coherencia y guard de deriva en la misma coordenada de fase",
        },
        "summary": {
            "all": {
                "raw": stratified(records, "raw_health"),
                "coordinate": stratified(records, "coordinate_health"),
                "paired_raw": paired_delta(records, "raw_health"),
                "paired_coordinate": paired_delta(records, "coordinate_health"),
            },
            "clean": {
                "raw": stratified(clean, "raw_health"),
                "coordinate": stratified(clean, "coordinate_health"),
            },
            "eligible_like_gate_e": {
                "n": len(eligible),
                "raw": stratified(eligible, "raw_health"),
                "coordinate": stratified(eligible, "coordinate_health"),
                "predictor_raw": predictor_summary(records, gate_e, "raw_health"),
                "predictor_coordinate": predictor_summary(
                    records, gate_e, "coordinate_health"),
            },
            "flips": {
                "n": len(flips),
                "raw_false_coordinate_true": sum(
                    not row["raw_health"] and row["coordinate_health"] for row in flips),
                "raw_true_coordinate_false": sum(
                    row["raw_health"] and not row["coordinate_health"] for row in flips),
                "run_ids": [row["run_id"] for row in flips],
            },
            "replication_native60": {
                "n": len(replication),
                "max_rw_error": max(item["rw_error"] for item in replication)
                if replication else None,
                "max_dw_error": max(item["dw_error"] for item in replication)
                if replication else None,
            },
        },
        "warnings": [
            "La pendiente OLS fue elegida después de observar la contradicción par013_t.",
            "El corte 1.1/W se hereda del tap de deriva; no fue recalibrado para OLS.",
            "Coordinate_health es sensibilidad de medición, no nueva verdad ni ley de salud.",
            "La población incluye films de 60/120 truncados todos a 60.",
        ],
        "records": records,
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"[link-grumo] Gate F3: {len(records)} films, {len(flips)} flips de coordenada")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
