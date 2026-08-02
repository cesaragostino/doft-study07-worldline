#!/usr/bin/env python3
"""Gate C: transferencia constitucional fría en la población y vestido en el banco B1."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from baseline_census import auc, safe_output
from linear_response import chi_layer_sum, jacobian_fd, load_blocks, parse_block
from study07.artifacts.checkpoint import spec_fingerprint


RAYLEIGH_W8 = 2.0 * math.pi / 8.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(rows: list[dict], key: str, higher: bool = True) -> dict:
    positive = [float(row[key]) for row in rows if row["salud_final"]]
    negative = [float(row[key]) for row in rows if not row["salud_final"]]
    score = auc(positive, negative)
    if score is not None and not higher:
        score = 1.0 - score
    return {
        "n_salud": len(positive), "n_no_salud": len(negative),
        "mediana_salud": float(np.median(positive)) if positive else None,
        "mediana_no_salud": float(np.median(negative)) if negative else None,
        "auc_direccion_declarada": score,
        "direccion": "mayor" if higher else "menor",
    }


def summarize(rows: list[dict]) -> dict:
    return {
        "n": len(rows),
        "n_salud": sum(row["salud_final"] for row in rows),
        "chi_Q_fria": describe(rows, "chi_Q_fria"),
        "A_linea_predicha_fria": describe(rows, "A_linea_predicha_fria"),
        "rho_predicha_fria": describe(rows, "rho_predicha_fria"),
        "residuo_r_fria": describe(rows, "residuo_r_fria"),
        "error_abs_log_r_fria": describe(rows, "error_abs_log_r_fria", higher=False),
        "rho_observada": describe(rows, "rho_W8_temprano"),
        "fraccion_r_dentro_factor2": float(np.mean([
            0.5 <= row["residuo_r_fria"] <= 2.0 for row in rows])) if rows else None,
        "mediana_variacion_chi_en_Rayleigh": float(np.median([
            row["variacion_chi_en_Rayleigh"] for row in rows])) if rows else None,
    }


def model_for(block_id: str, blocks: dict[str, dict], cache: dict) -> tuple:
    if block_id not in cache:
        if block_id not in blocks:
            raise RuntimeError(f"bloque ausente del canónico: {block_id}")
        spec = parse_block(blocks[block_id])
        matrix, drive_vector = jacobian_fd(spec)
        cache[block_id] = (spec, matrix, drive_vector)
    return cache[block_id]


def chi_at(spec, matrix, drive_vector, omega: float) -> float:
    return float(abs(chi_layer_sum(spec, matrix, drive_vector, omega, "Q")))


def manifest_verified(record: dict, spec, node: int) -> dict:
    path = Path(record["procedencia"]["run_dir"]) / "manifest.json"
    observed_hash = sha256(path)
    expected_hash = record["procedencia"]["manifest_sha256"]
    if observed_hash != expected_hash:
        raise RuntimeError(f"manifest cambió: {record['run_id']}")
    manifest = json.loads(path.read_text())
    observed_fp = spec_fingerprint(spec)
    expected_fp = manifest["spec_fingerprints"][node]
    if observed_fp != expected_fp:
        raise RuntimeError(f"constitución no coincide con film: {record['run_id']} nodo {node}")
    return {"manifest_sha256": observed_hash, "spec_fingerprint": observed_fp}


def dressed_bank(arrival: dict, blocks: dict[str, dict], cache: dict) -> list[dict]:
    rows = []
    for pair in arrival["pairs"]:
        transported_manifest = json.loads((Path(
            pair["transported"]["procedencia"]["run_dir"]) / "manifest.json").read_text())
        pair_block_ids = [item["block_id"]
                          for item in transported_manifest["composicion"]["por_nodo"]]
        for arm_name in ("transported", "fresh"):
            arm = pair[arm_name]
            line = arm["linea_compartida_llegada"]
            follower = int(line["nodo_seguidor_candidato"])
            manifest_path = Path(arm["procedencia"]["run_dir"]) / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            block_id = pair_block_ids[follower]
            spec, cold_matrix, cold_drive = model_for(block_id, blocks, cache)
            if spec_fingerprint(spec) != manifest["spec_fingerprints"][follower]:
                raise RuntimeError(f"B1 constitución no coincide: {arm['run_id']}")
            slow = arm["nodos"][follower]["estado_lento"]
            b0 = np.asarray(slow["b_inicio"], dtype=float)
            e0 = np.asarray(slow["e_inicio"], dtype=float)
            dressed_matrix, dressed_drive = jacobian_fd(spec, b_fixed=b0, e_fixed=e0)
            omega = float(line["omega_linea"])
            empirical = float(line["por_nodo"][follower]["ganancia_empirica_AQ_sobre_AF"])
            cold = chi_at(spec, cold_matrix, cold_drive, omega)
            dressed = chi_at(spec, dressed_matrix, dressed_drive, omega)
            r_cold = empirical / max(cold, 1e-300)
            r_dressed = empirical / max(dressed, 1e-300)
            rows.append({
                "run_id": arm["run_id"], "arm": "t" if arm_name == "transported" else "f",
                "block_id": block_id, "follower": follower, "omega_linea": omega,
                "norma_b_inicio": float(np.linalg.norm(b0)),
                "ganancia_empirica": empirical,
                "chi_Q_fria": cold, "chi_Q_vestida": dressed,
                "r_fria": r_cold, "r_vestida": r_dressed,
                "error_abs_log_r_fria": abs(math.log(max(r_cold, 1e-300))),
                "error_abs_log_r_vestida": abs(math.log(max(r_dressed, 1e-300))),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--gate-b", required=True, type=Path)
    parser.add_argument("--gate-b-evaluate", required=True, type=Path)
    parser.add_argument("--arrival", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    blocks_path = args.blocks.expanduser().resolve()
    gate_b_path = args.gate_b.expanduser().resolve()
    gate_b_evaluate_path = args.gate_b_evaluate.expanduser().resolve()
    arrival_path = args.arrival.expanduser().resolve()
    blocks = load_blocks(blocks_path)
    gate_b = json.loads(gate_b_path.read_text())
    gate_b_evaluate = json.loads(gate_b_evaluate_path.read_text())
    arrival = json.loads(arrival_path.read_text())
    cache: dict[str, tuple] = {}

    records = []
    for source in gate_b["records"]:
        follower = 1 - int(source["source_candidate"])
        block_id = [source["block_i"], source["block_j"]][follower]
        spec, matrix, drive_vector = model_for(block_id, blocks, cache)
        provenance = manifest_verified(source, spec, follower)
        omega = float(source["omega_linea_temprana"])
        sample_omega = np.array([max(omega - RAYLEIGH_W8 / 2.0, 1e-6),
                                 omega, omega + RAYLEIGH_W8 / 2.0])
        samples = np.abs(chi_layer_sum(spec, matrix, drive_vector, sample_omega, "Q"))
        chi = float(samples[1])
        variation = float(np.max(samples) / max(float(np.min(samples)), 1e-300))
        force = float(source["A_force_linea_seguidor"])
        empirical_gain = float(source["ganancia_empirica"])
        observed_line = empirical_gain * force
        competitor = observed_line / max(float(source["rho_W8_temprano"]), 1e-300)
        predicted_line = chi * force
        ratio = empirical_gain / max(chi, 1e-300)
        row = dict(source)
        row.update({
            "follower_candidate": follower, "follower_block_id": block_id,
            "chi_Q_fria": chi,
            "A_linea_observada_reconstruida": observed_line,
            "A_competidor_observado_reconstruido": competitor,
            "A_linea_predicha_fria": predicted_line,
            "rho_predicha_fria": predicted_line / max(competitor, 1e-300),
            "residuo_r_fria": ratio,
            "error_abs_log_r_fria": abs(math.log(max(ratio, 1e-300))),
            "variacion_chi_en_Rayleigh": variation,
            "chi_no_plana_W8": variation > 2.0,
            "verificacion": provenance,
        })
        records.append(row)

    clean = [row for row in records if not row["chi_no_plana_W8"]]
    by_arm = {arm: [row for row in records if row["brazo"] == arm] for arm in ("t", "f")}
    discovery_ids = set(gate_b_evaluate["holdout_sin_banco_descubrimiento"]["ids_retirados"])
    holdout = [row for row in records if row["run_id"] not in discovery_ids]
    population_followers = {row["follower_block_id"] for row in records}
    dressed = dressed_bank(arrival, blocks, cache)
    dress_summary = {}
    for arm in ("t", "f"):
        selected = [row for row in dressed if row["arm"] == arm]
        dress_summary[arm] = {
            "n": len(selected),
            "mediana_norma_b": float(np.median([row["norma_b_inicio"] for row in selected])),
            "mediana_chi_vestida_sobre_fria": float(np.median([
                row["chi_Q_vestida"] / max(row["chi_Q_fria"], 1e-300) for row in selected])),
            "mediana_error_abs_log_r_fria": float(np.median([
                row["error_abs_log_r_fria"] for row in selected])),
            "mediana_error_abs_log_r_vestida": float(np.median([
                row["error_abs_log_r_vestida"] for row in selected])),
            "n_vestido_mejora_error": sum(row["error_abs_log_r_vestida"] <
                                          row["error_abs_log_r_fria"] for row in selected),
        }

    result = {
        "_meta": {
            "blocks": str(blocks_path), "blocks_sha256": sha256(blocks_path),
            "gate_b": str(gate_b_path), "gate_b_sha256": sha256(gate_b_path),
            "gate_b_evaluate": str(gate_b_evaluate_path),
            "gate_b_evaluate_sha256": sha256(gate_b_evaluate_path),
            "arrival": str(arrival_path), "arrival_sha256": sha256(arrival_path),
            "policy": "entradas sólo lectura; salida sólo logs/link_grumo",
        },
        "prereg": {
            "transferencia": "Q_sum = |sum_m in Q chi_m|; drive uniforme a todos los modos",
            "prediccion": "A_linea_pred = chi_Q_fria * A_force_linea",
            "residuo": "r=A_linea_observada/A_linea_predicha",
            "chi_no_plana_W8": "max/min chi en omega±Rayleigh/2 > 2; no implica notch",
            "outcome": gate_b["prereg"]["outcome"],
        },
        "summary": {
            "combined": summarize(records),
            "transported": summarize(by_arm["t"]),
            "fresh": summarize(by_arm["f"]),
            "banda_chi_plana_W8": summarize(clean),
            "banda_chi_plana_transported": summarize([
                row for row in clean if row["brazo"] == "t"]),
            "banda_chi_plana_fresh": summarize([
                row for row in clean if row["brazo"] == "f"]),
            "holdout_sin_banco_descubrimiento": summarize(holdout),
            "holdout_banda_chi_plana": summarize([
                row for row in holdout if not row["chi_no_plana_W8"]]),
            "ids_banco_descubrimiento_retirados": sorted(discovery_ids),
            "n_unique_followers_population": len(population_followers),
            "n_chi_no_plana_W8": len(records) - len(clean),
            "banco_B1_vestido": dress_summary,
        },
        "advertencias": [
            "Exploratorio: source y omega se estimaron dentro de la primera W8.",
            "La respuesta fría no incorpora el estado transportado ni el transitorio homogéneo.",
            "r distinto de 1 mezcla transitorio, no-estacionariedad, leakage y no-linealidad; no es por sí solo causal.",
            "La variante vestida congela b al inicio sólo en el banco B1; e no entra directamente al Jacobiano rápido.",
        ],
        "records": records,
        "banco_B1_vestido": dressed,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate C población: {len(records)} films, {len(cache)} receptores")
    print(f"[link-grumo] chi no plana en W8: {len(records) - len(clean)}")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
