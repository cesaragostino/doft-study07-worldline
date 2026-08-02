#!/usr/bin/env python3
"""Gate B3: test early→late de dominancia en toda la población W8 resoluble.

Predictor fijado en la primera ventana [0,8] u.t.; outcome físico en la ventana tardía del
film. Lee dos chunks por film, verifica hashes y no genera simulaciones.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from baseline_census import (FALSE_ZONE, auc, cargar_filas, indexar_reportes,
                             indexar_views_w8, safe_output)
from gate_b_dominance import (WINDOW_UT, dominance_series, index_runs, read_series)


RAYLEIGH = 2.0 * np.pi / WINDOW_UT


def describe(rows: list[dict], key: str) -> dict:
    positive = [float(r[key]) for r in rows if r["salud_final"]]
    negative = [float(r[key]) for r in rows if not r["salud_final"]]
    return {
        "n_salud": len(positive), "n_no_salud": len(negative),
        "mediana_salud": float(np.median(positive)) if positive else None,
        "mediana_no_salud": float(np.median(negative)) if negative else None,
        "auc_mayor_predice_salud": auc(positive, negative),
    }


def rho_table(rows: list[dict]) -> dict:
    high = [r for r in rows if r["rho_W8_temprano"] > 1.0]
    low = [r for r in rows if r["rho_W8_temprano"] <= 1.0]
    return {
        "rho_gt_1": {"n": len(high), "n_salud": sum(r["salud_final"] for r in high),
                     "fraccion_salud": (float(np.mean([r["salud_final"] for r in high]))
                                        if high else None)},
        "rho_le_1": {"n": len(low), "n_salud": sum(r["salud_final"] for r in low),
                     "fraccion_salud": (float(np.mean([r["salud_final"] for r in low]))
                                        if low else None)},
    }


def summaries(rows: list[dict]) -> dict:
    out = {"n": len(rows), "n_salud_final": sum(r["salud_final"] for r in rows),
           "rho_threshold": rho_table(rows)}
    for key in ("rho_W8_temprano", "A_linea_source", "A_force_linea_seguidor",
                "ganancia_empirica", "E0", "dw_temprana"):
        out[key] = describe(rows, key)
    late_detector_free = [r for r in rows if r["t_lock_W8"] is None
                          or float(r["t_lock_W8"]) > WINDOW_UT]
    out["sin_tlock_en_primera_W8"] = {
        "n": len(late_detector_free),
        "rho": describe(late_detector_free, "rho_W8_temprano"),
        "threshold": rho_table(late_detector_free),
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables-root", required=True, type=Path)
    parser.add_argument("--worldlines-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    tables_root = args.tables_root.expanduser().resolve()
    worldlines_root = args.worldlines_root.expanduser().resolve()

    filas, input_hashes = cargar_filas(tables_root)
    reports = indexar_reportes(tables_root)
    views = indexar_views_w8(tables_root)
    runs = index_runs(worldlines_root)
    eligible = []
    exclusions = {"self": 0, "dw_bajo_Rayleigh": 0, "armonico_o_mudo": 0}
    for row in filas:
        if row["_self"]:
            exclusions["self"] += 1
            continue
        if float(row["W8"]["dw_temprana"]) < RAYLEIGH:
            exclusions["dw_bajo_Rayleigh"] += 1
            continue
        report = reports.get(row["run_id"])
        if report is None:
            raise RuntimeError(f"sin REPORTE: {row['run_id']}")
        view = views.get(str(report["worldline_hash"])[:16])
        if view is None:
            raise RuntimeError(f"sin vista W8: {row['run_id']}")
        manifest_view = json.loads(view.with_name("manifest.json").read_text())
        if manifest_view.get("nodos_armonico") or manifest_view.get("nodos_mudos"):
            exclusions["armonico_o_mudo"] += 1
            continue
        eligible.append(row)

    records = []
    for index, row in enumerate(eligible, 1):
        run_id = row["run_id"]
        if run_id not in runs:
            raise RuntimeError(f"worldline ausente: {run_id}")
        raw, provenance = read_series(runs[run_id], WINDOW_UT)
        source = int(np.argmax(np.sqrt(np.mean(np.asarray(raw["Q"]) ** 2, axis=0))))
        dom = dominance_series(raw, source)
        first = dom["serie"][0]
        report = reports[run_id]
        metrics = report.get("metricas", {})
        e0 = float(metrics.get("E0_nodo0", 0.0) + metrics.get("E0_nodo1", 0.0))
        final_close = float(row["W8"]["dw_tardia"]) < FALSE_ZONE["W8"]
        final_firm = int(row["W8"]["estado"]) == 2
        records.append({
            "run_id": run_id, "par": row["_par"], "brazo": row["brazo"],
            "block_i": row["block_i"], "block_j": row["block_j"],
            "source_candidate": source,
            "rho_W8_temprano": float(first["rho_dominancia"]),
            "omega_linea_temprana": float(first["omega_linea"]),
            "omega_competidor_temprano": float(first["omega_competidor"]),
            "A_linea_source": float(first["A_linea_source"]),
            "A_force_linea_seguidor": float(first["A_force_linea_sobre_seguidor"]),
            "ganancia_empirica": float(first["ganancia_empirica_seguidor"]),
            "E0": e0,
            "dw_temprana": float(row["W8"]["dw_temprana"]),
            "dw_tardia": float(row["W8"]["dw_tardia"]),
            "estado_final_W8": int(row["W8"]["estado"]),
            "t_lock_W8": row["W8"]["t_lock_ut"],
            "cierre_final": final_close, "firme_final": final_firm,
            "salud_final": bool(final_close and final_firm),
            "procedencia": provenance,
        })
        if index % 20 == 0 or index == len(eligible):
            print(f"[link-grumo] B3 {index}/{len(eligible)}", flush=True)

    by_arm = {arm: [r for r in records if r["brazo"] == arm] for arm in ("t", "f")}
    bins = [(RAYLEIGH, 1.5), (1.5, 3.0), (3.0, 10.0), (10.0, 50.0)]
    strata = []
    for lo, hi in bins:
        selected = [r for r in records if lo <= r["dw_temprana"] < hi]
        strata.append({"dw": [lo, hi], "combined": rho_table(selected),
                       "transported": rho_table([r for r in selected if r["brazo"] == "t"]),
                       "fresh": rho_table([r for r in selected if r["brazo"] == "f"])})

    paired = {}
    for record in records:
        paired.setdefault(record["par"], {})[record["brazo"]] = record
    complete_pairs = [p for p in paired.values() if "t" in p and "f" in p]
    paired_summary = {
        "n": len(complete_pairs),
        "n_rho_t_mayor": sum(p["t"]["rho_W8_temprano"] > p["f"]["rho_W8_temprano"]
                             for p in complete_pairs),
        "mediana_delta_rho_t_menos_f": (float(np.median([
            p["t"]["rho_W8_temprano"] - p["f"]["rho_W8_temprano"]
            for p in complete_pairs])) if complete_pairs else None),
    }
    result = {
        "_meta": {
            "pregunta": "B3: rho en [0,8] predice salud final física",
            "tables_root": str(tables_root), "worldlines_root": str(worldlines_root),
            "input_sha256": input_hashes,
            "policy": "read-only; dos chunks verificados por film; salida logs/link_grumo",
        },
        "prereg": {
            "predictor": "rho=A_linea/A_competidor del seguidor en primera W8",
            "outcome": "estado_final_W8==2 AND dw_tardia<0.1375",
            "separacion": "predictor [0,8], outcome frecuencia tardía [50,60]",
            "poblacion": "no-self, dw_temprana>=2pi/8, sin banderas armónico/mudo",
        },
        "exclusions": exclusions,
        "summary": {"combined": summaries(records),
                    "transported": summaries(by_arm["t"]),
                    "fresh": summaries(by_arm["f"]),
                    "paired": paired_summary,
                    "strata_dw": strata},
        "advertencias": [
            "exploratorio: sin p inferencial ni corrección por nodos compartidos",
            "rho mide selección espectral, no autonomía ni signo energético",
            "source_candidate se elige por Q_rms dentro de la misma ventana temprana",
            "t_lock puede estar dentro de predictor; se publica subconjunto t_lock>8/None",
        ],
        "records": records,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate B3: {len(records)} films resolubles")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
