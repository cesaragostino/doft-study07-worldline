#!/usr/bin/env python3
"""Evaluación C0 de los records B3, sin volver a leer worldlines."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from baseline_census import auc, safe_output


ENDPOINTS = ("cierre_final", "firme_final", "salud_final")
SEED = 20260802
N_PERM = 100_000


def endpoint_stats(rows: list[dict], outcome: str) -> dict:
    positive = [r["rho_W8_temprano"] for r in rows if r[outcome]]
    negative = [r["rho_W8_temprano"] for r in rows if not r[outcome]]
    return {
        "n_si": len(positive), "n_no": len(negative),
        "mediana_rho_si": float(np.median(positive)) if positive else None,
        "mediana_rho_no": float(np.median(negative)) if negative else None,
        "auc_rho": auc(positive, negative),
    }


def permutation_auc(rows: list[dict], outcome: str) -> dict:
    values = np.array([r["rho_W8_temprano"] for r in rows], dtype=float)
    labels = np.array([bool(r[outcome]) for r in rows])
    n_positive = int(np.sum(labels))
    observed = auc(values[labels].tolist(), values[~labels].tolist())
    if observed is None or n_positive == 0 or n_positive == len(labels):
        return {"observed_auc": observed, "n_perm": 0}
    rng = np.random.default_rng(SEED + len(rows) + n_positive)
    exceed = 0
    for _ in range(N_PERM):
        indices = rng.choice(len(labels), n_positive, replace=False)
        mask = np.zeros(len(labels), dtype=bool)
        mask[indices] = True
        candidate = auc(values[mask].tolist(), values[~mask].tolist())
        exceed += candidate >= observed
    return {"observed_auc": observed, "n_perm": N_PERM,
            "p_one_sided_add_one": float((exceed + 1) / (N_PERM + 1)),
            "exceed": exceed,
            "advertencia": "sin clustering por nodo; exploratorio, no citable como p final"}


def matched_controls(rows: list[dict]) -> dict:
    transported = [r for r in rows if r["brazo"] == "t"]
    positive = [r for r in transported if r["salud_final"]]
    negative = [r for r in transported if not r["salud_final"]]
    keys = ("E0", "A_force_linea_seguidor", "dw_temprana")
    all_x = np.array([[np.log10(max(float(r[k]), 1e-300)) for k in keys]
                      for r in transported])
    mean = np.mean(all_x, axis=0)
    std = np.std(all_x, axis=0)
    std[std == 0.0] = 1.0

    matches = []
    for case in positive:
        case_x = (np.log10([max(float(case[k]), 1e-300) for k in keys]) - mean) / std
        candidates = []
        for control in negative:
            control_x = (np.log10([max(float(control[k]), 1e-300)
                                   for k in keys]) - mean) / std
            candidates.append((float(np.linalg.norm(case_x - control_x)), control))
        distance, control = min(candidates, key=lambda item: item[0])
        matches.append({
            "caso": case["run_id"], "control": control["run_id"],
            "distancia_estandarizada": distance,
            "rho_caso": float(case["rho_W8_temprano"]),
            "rho_control": float(control["rho_W8_temprano"]),
            "rho_caso_mayor": bool(case["rho_W8_temprano"]
                                    > control["rho_W8_temprano"]),
            "covariables_caso": {key: case[key] for key in keys},
            "covariables_control": {key: control[key] for key in keys},
        })
    return {
        "metodo": "nearest neighbor con reemplazo en log10(E0,F_linea,dw), estandarizado",
        "n": len(matches),
        "n_rho_caso_mayor": sum(m["rho_caso_mayor"] for m in matches),
        "advertencia": "chequeo descriptivo; controles pueden repetirse y n positivo es pequeño",
        "matches": matches,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--discovery", required=True, type=Path,
                        help="Gate B2 cuyos casos originaron la hipótesis rho")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    source = args.input.expanduser().resolve()
    data = json.loads(source.read_text())
    records = data["records"]
    discovery_path = args.discovery.expanduser().resolve()
    discovery_data = json.loads(discovery_path.read_text())
    discovery_ids = {p["transported"]["run_id"] for p in discovery_data["pairs"]}
    holdout = [r for r in records if r["run_id"] not in discovery_ids]
    by_arm = {"combined": records,
              "transported": [r for r in records if r["brazo"] == "t"],
              "fresh": [r for r in records if r["brazo"] == "f"]}
    endpoints = {arm: {endpoint: endpoint_stats(rows, endpoint)
                       for endpoint in ENDPOINTS}
                 for arm, rows in by_arm.items()}
    holdout_by_arm = {"combined": holdout,
                      "transported": [r for r in holdout if r["brazo"] == "t"],
                      "fresh": [r for r in holdout if r["brazo"] == "f"]}
    holdout_endpoints = {arm: {endpoint: endpoint_stats(rows, endpoint)
                               for endpoint in ENDPOINTS}
                         for arm, rows in holdout_by_arm.items()}
    disagreements = {
        "cierre_sin_firme": [{"run_id": r["run_id"], "brazo": r["brazo"],
                               "rho": r["rho_W8_temprano"]}
                              for r in records if r["cierre_final"] and not r["firme_final"]],
        "firme_sin_cierre": [{"run_id": r["run_id"], "brazo": r["brazo"],
                               "rho": r["rho_W8_temprano"]}
                              for r in records if r["firme_final"] and not r["cierre_final"]],
    }
    result = {
        "_meta": {"source": str(source), "discovery": str(discovery_path),
                  "pregunta": "B3-eval: rho predice cierre, firmeza o su conjunción"},
        "endpoints": endpoints,
        "holdout_sin_banco_descubrimiento": {
            "ids_retirados": sorted(discovery_ids),
            "n": len(holdout),
            "n_positivos_conjuncion": sum(r["salud_final"] for r in holdout),
            "endpoints": holdout_endpoints,
            "advertencia": ("transported queda con un solo positivo independiente; "
                             "no alcanza para cierre inferencial"),
        },
        "permutation_transportada_conjuncion": permutation_auc(
            by_arm["transported"], "salud_final"),
        "matched_transportada_conjuncion": matched_controls(records),
        "desacuerdos_endpoint": disagreements,
        "interpretacion_limitada": (
            "salud_final es firmeza+cierre a 60 u.t.; no equivale a supervivencia asintotica"),
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] evaluación B3: {len(records)} records, sin releer films")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
