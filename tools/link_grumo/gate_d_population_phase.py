#!/usr/bin/env python3
"""Gate D3: cierre temprano de transferencia compleja contra salud tardía."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from baseline_census import auc, safe_output
from gate_b_dominance import WINDOW_UT, read_series
from gate_d_phase_transfer import complex_coefficient
from linear_response import chi_layer_sum, jacobian_fd, load_blocks, parse_block
from study07.artifacts.checkpoint import spec_fingerprint


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model(block_id: str, blocks: dict[str, dict], cache: dict) -> tuple:
    if block_id not in cache:
        spec = parse_block(blocks[block_id])
        matrix, drive = jacobian_fd(spec)
        cache[block_id] = (spec, matrix, drive)
    return cache[block_id]


def metric(rows: list[dict], key: str, smaller: bool) -> dict:
    yes = [float(row[key]) for row in rows if row["salud_final"]]
    no = [float(row[key]) for row in rows if not row["salud_final"]]
    score = auc(yes, no)
    if score is not None and smaller:
        score = 1.0 - score
    return {
        "n_salud": len(yes), "n_no_salud": len(no),
        "mediana_salud": float(np.median(yes)) if yes else None,
        "mediana_no_salud": float(np.median(no)) if no else None,
        "auc_direccion": score, "direccion": "menor" if smaller else "mayor",
    }


def threshold(rows: list[dict], predicate) -> dict:
    selected = [row for row in rows if predicate(row)]
    rejected = [row for row in rows if not predicate(row)]
    return {
        "si": {"n": len(selected), "n_salud": sum(row["salud_final"] for row in selected),
               "fraccion_salud": float(np.mean([row["salud_final"] for row in selected]))
               if selected else None},
        "no": {"n": len(rejected), "n_salud": sum(row["salud_final"] for row in rejected),
               "fraccion_salud": float(np.mean([row["salud_final"] for row in rejected]))
               if rejected else None},
    }


def summarize(rows: list[dict]) -> dict:
    return {
        "n": len(rows), "n_salud": sum(row["salud_final"] for row in rows),
        "error_fase": metric(rows, "error_fase_fria", True),
        "error_complejo": metric(rows, "error_complejo_fria", True),
        "error_amp_log": metric(rows, "error_amp_log_fria", True),
        "rho_predicha": metric(rows, "rho_predicha_fria", False),
        "cierre_fase_15deg": threshold(
            rows, lambda row: row["error_fase_fria"] <= math.radians(15.0)),
        "cierre_complejo": threshold(rows, lambda row: row["cierre_complejo"]),
        "dominancia_y_cierre_complejo": threshold(
            rows, lambda row: row["rho_predicha_fria"] > 1.0 and row["cierre_complejo"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--gate-c", required=True, type=Path)
    parser.add_argument("--reuse-records", type=Path,
                        help="reusa records D3 ya extraídos; no relee worldlines")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    blocks_path = args.blocks.expanduser().resolve()
    gate_c_path = args.gate_c.expanduser().resolve()
    blocks = load_blocks(blocks_path)
    gate_c = json.loads(gate_c_path.read_text())
    reuse_path = args.reuse_records.expanduser().resolve() if args.reuse_records else None
    reused = json.loads(reuse_path.read_text()) if reuse_path else None
    discovery_ids = set(gate_c["summary"]["ids_banco_descubrimiento_retirados"])
    cache: dict[str, tuple] = {}
    rows = list(reused["records"]) if reused else []

    sources = [] if reused else gate_c["records"]
    for index, source in enumerate(sources, 1):
        raw, provenance = read_series(Path(source["procedencia"]["run_dir"]), WINDOW_UT)
        follower = int(source["follower_candidate"])
        block_id = source["follower_block_id"]
        spec, matrix, drive_vector = model(block_id, blocks, cache)
        if spec_fingerprint(spec) != source["verificacion"]["spec_fingerprint"]:
            raise RuntimeError(f"fingerprint interno cambió: {source['run_id']}")
        omega = float(source["omega_linea_temprana"])
        times = np.arange(len(raw["Q"]), dtype=float) * float(raw["dt"])
        q_hat = complex_coefficient(np.asarray(raw["Q"])[:, follower], times, omega)
        f_hat = complex_coefficient(np.asarray(raw["drive"])[:, follower], times, omega)
        measured = q_hat / f_hat
        chi = complex(chi_layer_sum(spec, matrix, drive_vector, omega, "Q"))
        residual = measured / chi
        phase_error = float(abs(np.angle(residual)))
        amp_ratio = float(abs(residual))
        row = {
            "run_id": source["run_id"], "par": source["par"], "brazo": source["brazo"],
            "salud_final": source["salud_final"], "cierre_final": source["cierre_final"],
            "firme_final": source["firme_final"], "follower_block_id": block_id,
            "omega_linea": omega, "chi_no_plana_W8": source["chi_no_plana_W8"],
            "rho_predicha_fria": source["rho_predicha_fria"],
            "Q_hat_abs": float(abs(q_hat)), "F_hat_abs": float(abs(f_hat)),
            "H_medido_abs": float(abs(measured)), "H_medido_phase": float(np.angle(measured)),
            "chi_fria_abs": float(abs(chi)), "chi_fria_phase": float(np.angle(chi)),
            "r_amp_fria": amp_ratio,
            "error_amp_log_fria": float(abs(math.log(max(amp_ratio, 1e-300)))),
            "error_fase_fria": phase_error,
            "error_complejo_fria": float(abs(residual - 1.0)),
            "cierre_complejo": bool(phase_error <= math.radians(15.0)
                                     and 0.5 <= amp_ratio <= 2.0),
            "procedencia": provenance,
        }
        rows.append(row)
        if index % 20 == 0 or index == len(sources):
            print(f"[link-grumo] D3 {index}/{len(sources)}", flush=True)

    flat = [row for row in rows if not row["chi_no_plana_W8"]]
    holdout = [row for row in rows if row["run_id"] not in discovery_ids]
    paired: dict[str, dict[str, dict]] = {}
    for row in rows:
        paired.setdefault(row["par"], {})[row["brazo"]] = row
    complete_pairs = [pair for pair in paired.values() if "t" in pair and "f" in pair]
    result = {
        "_meta": {"blocks": str(blocks_path), "blocks_sha256": sha256(blocks_path),
                  "gate_c": str(gate_c_path), "gate_c_sha256": sha256(gate_c_path),
                  "reuse_records": str(reuse_path) if reuse_path else None,
                  "reuse_records_sha256": sha256(reuse_path) if reuse_path else None,
                  "policy": "worldlines read-only; chunks verificados; salida logs/link_grumo"},
        "prereg": {
            "predictor_window": [0.0, WINDOW_UT],
            "outcome_window": ("endpoint heredado de Gate B3, mezcla films 60/120; "
                               "sólo diagnóstico, Gate E fija salud a 60"),
            "residuo": "R=(Q_hat/F_hat)/chi_Q_fria",
            "cierre_fase": "|arg R|<=15 grados",
            "cierre_complejo": "cierre fase AND 0.5<=|R|<=2",
            "dominancia": "rho_predicha_fria>1",
        },
        "summary": {
            "combined": summarize(rows),
            "transported": summarize([row for row in rows if row["brazo"] == "t"]),
            "fresh": summarize([row for row in rows if row["brazo"] == "f"]),
            "banda_chi_plana_W8": summarize(flat),
            "banda_chi_plana_transported": summarize([
                row for row in flat if row["brazo"] == "t"]),
            "banda_chi_plana_fresh": summarize([
                row for row in flat if row["brazo"] == "f"]),
            "holdout_sin_banco_descubrimiento": summarize(holdout),
            "holdout_transportado": summarize([
                row for row in holdout if row["brazo"] == "t"]),
            "holdout_fresh": summarize([
                row for row in holdout if row["brazo"] == "f"]),
            "holdout_banda_chi_plana": summarize([
                row for row in holdout if not row["chi_no_plana_W8"]]),
            "paired": {
                "n": len(complete_pairs),
                "n_t_menor_error_fase": sum(pair["t"]["error_fase_fria"] <
                                            pair["f"]["error_fase_fria"]
                                            for pair in complete_pairs),
                "n_t_cierre_complejo_f_no": sum(pair["t"]["cierre_complejo"] and
                                                 not pair["f"]["cierre_complejo"]
                                                 for pair in complete_pairs),
                "n_f_cierre_complejo_t_no": sum(pair["f"]["cierre_complejo"] and
                                                 not pair["t"]["cierre_complejo"]
                                                 for pair in complete_pairs),
            },
            "n_unique_followers": len({row["follower_block_id"] for row in rows}),
            "ids_banco_descubrimiento_retirados": sorted(discovery_ids),
        },
        "advertencias": [
            "Exploratorio: umbrales físicos simples, sin optimización en esta población.",
            "La línea se seleccionó en la misma W8; predictor y outcome sí están separados en tiempo.",
            "chi no plana dentro de Rayleigh invalida la aproximación puntual; se publica estrato plano.",
            "Cierre de transferencia no implica todavía persistencia asintótica ni causalidad de S2.",
            "Las asociaciones de salud de este archivo quedan supersedidas por Gate E (horizonte fijo).",
        ],
        "records": rows,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate D3 población fase: {len(rows)} films")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
