#!/usr/bin/env python3
"""Gate D2: identidad compleja Q/F en llegada, transported contra fresh apareado."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from baseline_census import safe_output
from gate_b_arrival import T0_UT, T1_UT, verify_and_load_chunk0
from linear_response import chi_layer_sum, jacobian_fd, load_blocks, parse_block
from study07.artifacts.checkpoint import spec_fingerprint


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def complex_coefficient(values: np.ndarray, times: np.ndarray, omega: float) -> complex:
    y = np.asarray(values, dtype=float)
    y = y - float(np.mean(y))
    window = np.hanning(len(y))
    return complex(2.0 * np.sum(y * window * np.exp(-1j * omega * times))
                   / max(float(np.sum(window)), 1e-300))


def angle_abs(value: complex) -> float:
    return float(abs(np.angle(value)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--arrival", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    blocks_path = args.blocks.expanduser().resolve()
    arrival_path = args.arrival.expanduser().resolve()
    blocks = load_blocks(blocks_path)
    arrival = json.loads(arrival_path.read_text())
    cache: dict[str, tuple] = {}
    pairs = []

    for pair in arrival["pairs"]:
        transported_manifest = json.loads((Path(
            pair["transported"]["procedencia"]["run_dir"]) / "manifest.json").read_text())
        block_ids = [item["block_id"]
                     for item in transported_manifest["composicion"]["por_nodo"]]
        arms = {}
        for arm_name in ("transported", "fresh"):
            source = pair[arm_name]
            run_dir = Path(source["procedencia"]["run_dir"])
            manifest, provenance, arrays = verify_and_load_chunk0(run_dir)
            line = source["linea_compartida_llegada"]
            follower = int(line["nodo_seguidor_candidato"])
            block_id = block_ids[follower]
            if block_id not in cache:
                spec = parse_block(blocks[block_id])
                matrix, drive_vector = jacobian_fd(spec)
                cache[block_id] = (spec, matrix, drive_vector)
            spec, cold_matrix, cold_drive = cache[block_id]
            if spec_fingerprint(spec) != manifest["spec_fingerprints"][follower]:
                raise RuntimeError(f"constitución no coincide: {source['run_id']}")

            ticks = arrays["ticks"]
            dt = float(manifest["dt"])
            absolute_times = ticks * dt
            mask = (absolute_times >= T0_UT) & (absolute_times < T1_UT)
            times = absolute_times[mask]
            state = arrays[f"estados_nodo{follower}"]
            info = manifest["por_nodo"][follower]
            n_modes = int(info["n_modes"])
            q_indices = np.array([index for index, layer in enumerate(info["capas_por_modo"])
                                  if layer == "Q"], dtype=int)
            q = np.sum(state[mask, :n_modes][:, q_indices], axis=1)
            force = arrays["drive"][mask, follower]
            omega = float(line["omega_linea"])
            q_hat = complex_coefficient(q, times, omega)
            f_hat = complex_coefficient(force, times, omega)
            measured = q_hat / f_hat

            slow = source["nodos"][follower]["estado_lento"]
            dressed_matrix, dressed_drive = jacobian_fd(
                spec, np.asarray(slow["b_inicio"]), np.asarray(slow["e_inicio"]))
            chi_cold = complex(chi_layer_sum(spec, cold_matrix, cold_drive, omega, "Q"))
            chi_dressed = complex(chi_layer_sum(spec, dressed_matrix, dressed_drive,
                                                omega, "Q"))
            residual_cold = measured / chi_cold
            residual_dressed = measured / chi_dressed
            half_errors = []
            midpoint = 0.5 * (T0_UT + T1_UT)
            for lo, hi in ((T0_UT, midpoint), (midpoint, T1_UT)):
                half_mask = (absolute_times >= lo) & (absolute_times < hi)
                half_times = absolute_times[half_mask]
                half_q = np.sum(state[half_mask, :n_modes][:, q_indices], axis=1)
                half_force = arrays["drive"][half_mask, follower]
                half_h = (complex_coefficient(half_q, half_times, omega)
                          / complex_coefficient(half_force, half_times, omega))
                half_errors.append(angle_abs(half_h / chi_cold))
            resolvable = bool(line["por_nodo"][follower]["resoluble_rayleigh"])
            separation_self = float(line["por_nodo"][follower]["separacion_omega"])
            half_rayleigh = 2.0 * math.pi / ((T1_UT - T0_UT) / 2.0)
            arms[arm_name] = {
                "run_id": source["run_id"], "arm": "t" if arm_name == "transported" else "f",
                "follower": follower, "block_id": block_id, "omega": omega,
                "Q_hat_abs": float(abs(q_hat)), "F_hat_abs": float(abs(f_hat)),
                "H_medido_abs": float(abs(measured)), "H_medido_phase": float(np.angle(measured)),
                "chi_fria_abs": float(abs(chi_cold)), "chi_fria_phase": float(np.angle(chi_cold)),
                "chi_vestida_abs": float(abs(chi_dressed)),
                "chi_vestida_phase": float(np.angle(chi_dressed)),
                "r_amp_fria": float(abs(residual_cold)),
                "r_amp_vestida": float(abs(residual_dressed)),
                "error_fase_fria": angle_abs(residual_cold),
                "error_fase_vestida": angle_abs(residual_dressed),
                "error_complejo_fria": float(abs(residual_cold - 1.0)),
                "error_complejo_vestida": float(abs(residual_dressed - 1.0)),
                "resoluble_rayleigh": resolvable,
                "separacion_self": separation_self,
                "resoluble_en_cada_mitad": separation_self >= half_rayleigh,
                "error_fase_fria_por_mitad": half_errors,
                "max_error_fase_fria_mitades": float(max(half_errors)),
                "norma_b_inicio": float(np.linalg.norm(slow["b_inicio"])),
                "procedencia": provenance,
            }
        pairs.append(arms)

    flat = [pair[arm] for pair in pairs for arm in ("transported", "fresh")]
    summary = {}
    for arm, label in (("transported", "t"), ("fresh", "f")):
        selected = [pair[arm] for pair in pairs]
        summary[label] = {
            "n": len(selected),
            "mediana_error_fase_fria_rad": float(np.median([
                row["error_fase_fria"] for row in selected])),
            "mediana_error_fase_fria_grados": float(np.degrees(np.median([
                row["error_fase_fria"] for row in selected]))),
            "mediana_error_complejo_fria": float(np.median([
                row["error_complejo_fria"] for row in selected])),
            "mediana_r_amp_fria": float(np.median([row["r_amp_fria"] for row in selected])),
            "n_fase_dentro_15grados": sum(row["error_fase_fria"] <= math.radians(15.0)
                                           for row in selected),
            "n_complejo_dentro_25pct": sum(row["error_complejo_fria"] <= 0.25
                                             for row in selected),
        }
    summary["paired"] = {
        "n": len(pairs),
        "n_t_menor_error_fase": sum(pair["transported"]["error_fase_fria"] <
                                    pair["fresh"]["error_fase_fria"] for pair in pairs),
        "n_t_menor_error_complejo": sum(pair["transported"]["error_complejo_fria"] <
                                        pair["fresh"]["error_complejo_fria"] for pair in pairs),
        "mediana_delta_error_fase_t_menos_f": float(np.median([
            pair["transported"]["error_fase_fria"] - pair["fresh"]["error_fase_fria"]
            for pair in pairs])),
        "mediana_delta_error_complejo_t_menos_f": float(np.median([
            pair["transported"]["error_complejo_fria"] - pair["fresh"]["error_complejo_fria"]
            for pair in pairs])),
    }
    summary["resolubles"] = {}
    for arm, label in (("transported", "t"), ("fresh", "f")):
        selected = [pair[arm] for pair in pairs if pair[arm]["resoluble_rayleigh"]]
        summary["resolubles"][label] = {
            "n": len(selected),
            "mediana_error_fase_grados": float(np.degrees(np.median([
                row["error_fase_fria"] for row in selected]))) if selected else None,
            "max_error_fase_grados": float(np.degrees(max(
                row["error_fase_fria"] for row in selected))) if selected else None,
            "n_fase_dentro_15grados": sum(row["error_fase_fria"] <= math.radians(15.0)
                                           for row in selected),
            "mitades_resolubles": {
                "n": sum(row["resoluble_en_cada_mitad"] for row in selected),
                "n_ambas_dentro_15grados": sum(
                    row["resoluble_en_cada_mitad"] and
                    row["max_error_fase_fria_mitades"] <= math.radians(15.0)
                    for row in selected),
                "mediana_max_error_grados": (float(np.degrees(np.median([
                    row["max_error_fase_fria_mitades"] for row in selected
                    if row["resoluble_en_cada_mitad"]])))
                    if any(row["resoluble_en_cada_mitad"] for row in selected) else None),
            },
        }
    both_resolvable = [pair for pair in pairs
                       if pair["transported"]["resoluble_rayleigh"]
                       and pair["fresh"]["resoluble_rayleigh"]]
    summary["resolubles"]["paired_both"] = {
        "n": len(both_resolvable),
        "n_t_menor_error_fase": sum(pair["transported"]["error_fase_fria"] <
                                    pair["fresh"]["error_fase_fria"]
                                    for pair in both_resolvable),
    }
    result = {
        "_meta": {"blocks": str(blocks_path), "blocks_sha256": sha256(blocks_path),
                  "arrival": str(arrival_path), "arrival_sha256": sha256(arrival_path),
                  "policy": "18 chunk_00000 verificados; external sólo lectura"},
        "metodo": {
            "ventana_ut": [T0_UT, T1_UT],
            "H_medido": "coeficiente complejo Hann Q_sum / coeficiente complejo Hann drive",
            "residuo": "H_medido / chi_Q_xvz",
            "linea": "pico Q del dominante ya fijado por Gate B1",
        },
        "summary": summary,
        "advertencias": [
            "Banco seleccionado por éxito transported: contrasta mecanismo, no prevalencia.",
            "Una sola ventana no separa coherencia sostenida de coincidencia transitoria.",
            "La línea y el follower pueden diferir entre brazos porque fresh cambia la dinámica.",
        ],
        "pairs": pairs,
        "records": flat,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate D2 fase: {len(pairs)} pares, 18 chunks verificados")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
