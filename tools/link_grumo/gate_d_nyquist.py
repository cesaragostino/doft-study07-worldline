#!/usr/bin/env python3
"""Gate D1: ¿la geometría de lazo frío distingue la línea elegida y el link sano?"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from baseline_census import auc, safe_output
from linear_response import chi_emitted, jacobian_fd, load_blocks, parse_block
from study07.artifacts.checkpoint import spec_fingerprint


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model(block_id: str, blocks: dict[str, dict], cache: dict) -> tuple:
    if block_id not in cache:
        spec = parse_block(blocks[block_id])
        matrix, drive = jacobian_fd(spec)
        cache[block_id] = (spec, matrix, drive)
    return cache[block_id]


def loop_geometry(models: list[tuple], omega: float, k: float,
                  gamma: float, tau: float, follower: int) -> dict:
    chis = [complex(chi_emitted(spec, matrix, drive, omega))
            for spec, matrix, drive in models]
    direct = complex(k, gamma * omega)
    local = [chi * direct for chi in chis]
    loop = (local[0] * local[1] * np.exp(-2j * omega * tau)
            / ((1.0 + local[0]) * (1.0 + local[1])))
    one_pass = (chis[follower] * direct * np.exp(-1j * omega * tau)
                / (1.0 + local[follower]))
    return {
        "loop_abs": float(abs(loop)),
        "loop_phase": float(np.angle(loop)),
        "phase_mismatch": float(abs(np.angle(loop))),
        "gain_log_mismatch": float(abs(math.log(max(abs(loop), 1e-300)))),
        "nyquist_distance": float(abs(1.0 - loop)),
        "one_pass_abs_follower": float(abs(one_pass)),
        "one_pass_phase_follower": float(np.angle(one_pass)),
        "chi_emit_abs": [float(abs(value)) for value in chis],
        "chi_emit_phase": [float(np.angle(value)) for value in chis],
    }


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


def summarize(rows: list[dict]) -> dict:
    return {
        "n": len(rows), "n_salud": sum(row["salud_final"] for row in rows),
        "nyquist_distance_line": metric(rows, "nyquist_distance_line", True),
        "phase_mismatch_line": metric(rows, "phase_mismatch_line", True),
        "gain_log_mismatch_line": metric(rows, "gain_log_mismatch_line", True),
        "loop_abs_line": metric(rows, "loop_abs_line", False),
        "one_pass_abs_follower_line": metric(rows, "one_pass_abs_follower_line", False),
        "advantage_line_vs_competitor": metric(rows, "advantage_line_vs_competitor", False),
        "fraccion_linea_mas_cerca_Nyquist_que_competidor": float(np.mean([
            row["advantage_line_vs_competitor"] > 0.0 for row in rows])) if rows else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--gate-c", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    blocks_path = args.blocks.expanduser().resolve()
    gate_c_path = args.gate_c.expanduser().resolve()
    blocks = load_blocks(blocks_path)
    gate_c = json.loads(gate_c_path.read_text())
    discovery_ids = set(gate_c["summary"]["ids_banco_descubrimiento_retirados"])
    cache: dict[str, tuple] = {}
    rows = []

    for source in gate_c["records"]:
        block_ids = [source["block_i"], source["block_j"]]
        models = [model(block_id, blocks, cache) for block_id in block_ids]
        manifest_path = Path(source["procedencia"]["run_dir"]) / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for index, ((spec, _, _), expected) in enumerate(zip(models, manifest["spec_fingerprints"])):
            if spec_fingerprint(spec) != expected:
                raise RuntimeError(f"constitución no coincide: {source['run_id']} nodo {index}")
        topology = manifest["topologia"]
        k = float(manifest["k_global"]) * float(topology["w_k"][0])
        gamma = float(manifest["gamma_c"]) * float(topology["w_gamma"][0])
        tau = float(topology["tau"][0])
        follower = int(source["follower_candidate"])
        line = loop_geometry(models, float(source["omega_linea_temprana"]),
                             k, gamma, tau, follower)
        competitor = loop_geometry(models, float(source["omega_competidor_temprano"]),
                                   k, gamma, tau, follower)
        row = {
            "run_id": source["run_id"], "brazo": source["brazo"],
            "salud_final": source["salud_final"], "block_ids": block_ids,
            "source_candidate": source["source_candidate"],
            "follower_candidate": follower,
            "omega_linea": source["omega_linea_temprana"],
            "omega_competidor": source["omega_competidor_temprano"],
            "k": k, "gamma": gamma, "tau": tau,
            "nyquist_distance_line": line["nyquist_distance"],
            "phase_mismatch_line": line["phase_mismatch"],
            "gain_log_mismatch_line": line["gain_log_mismatch"],
            "loop_abs_line": line["loop_abs"],
            "one_pass_abs_follower_line": line["one_pass_abs_follower"],
            "nyquist_distance_competitor": competitor["nyquist_distance"],
            "advantage_line_vs_competitor": (competitor["nyquist_distance"]
                                               - line["nyquist_distance"]),
            "line": line, "competitor": competitor,
        }
        rows.append(row)

    holdout = [row for row in rows if row["run_id"] not in discovery_ids]
    result = {
        "_meta": {"blocks": str(blocks_path), "blocks_sha256": sha256(blocks_path),
                  "gate_c": str(gate_c_path), "gate_c_sha256": sha256(gate_c_path),
                  "policy": "entradas sólo lectura; salida sólo logs/link_grumo"},
        "hipotesis": {
            "ecuacion": "L=chi_i D chi_j D exp(-2 i omega tau)/[(1+chi_i D)(1+chi_j D)]",
            "D": "k+i gamma omega",
            "criterio_candidato": "L cercano a +1 (Nyquist/Barkhausen frío)",
            "comparador": "misma geometría en la línea competidora del seguidor",
        },
        "summary": {
            "combined": summarize(rows),
            "transported": summarize([row for row in rows if row["brazo"] == "t"]),
            "fresh": summarize([row for row in rows if row["brazo"] == "f"]),
            "holdout_sin_banco_descubrimiento": summarize(holdout),
            "n_unique_onions": len(cache),
            "ids_banco_descubrimiento_retirados": sorted(discovery_ids),
        },
        "advertencias": [
            "Exploratorio: evalúa frecuencias seleccionadas en el film; no es predictor sin film.",
            "Es una linealización fría de nodos autónomos con estado inicial no nulo.",
            "Cercanía a +1 sería suficiente para auto-oscilación lineal, no necesaria para entrainment forzado.",
        ],
        "records": rows,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate D1 Nyquist: {len(rows)} films, {len(cache)} onions")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
