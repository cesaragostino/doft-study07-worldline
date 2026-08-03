#!/usr/bin/env python3
"""Reproduce la identidad de transferencia en los films largos ya extraídos."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from baseline_census import safe_output
from linear_response import chi_modes, jacobian_fd
from study07.compat.study06_v4 import parse_theta_v2


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--series-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    spec_path = args.spec.expanduser().resolve()
    series_root = args.series_root.expanduser().resolve()
    campaign = json.loads(spec_path.read_text())

    results = {}
    all_medians = []
    calibration_medians = []
    series_hashes = {}
    for unit in campaign["unidades"]:
        par = unit["run_id"].split("_")[1]
        constituent = unit["constituyentes"][1]
        spec, _ = parse_theta_v2(constituent["theta"], emission_scale=0.1)
        matrix, drive_vector = jacobian_fd(spec)
        series_path = series_root / f"jz_series_{par}.npz"
        series_hashes[series_path.name] = sha256(series_path)
        with np.load(series_path) as data:
            omega = data["wl"]
            force = data["F_hat"]
            amplitude = data["A_L"]
        chi = np.abs(chi_modes(matrix, drive_vector, omega, spec.n_modes))[:, :3].T
        modes = {}
        for index in range(3):
            ratio = amplitude[index] / np.maximum(chi[index] * force, 1e-300)
            selected = amplitude[index] > 1e-6 * np.max(amplitude[index])
            quantiles = np.percentile(ratio[selected], [2, 50, 98])
            all_medians.append(float(quantiles[1]))
            calibration_eligible = not (par == "par132" and index == 0)
            if calibration_eligible:
                calibration_medians.append(float(quantiles[1]))
            modes[f"Q{index}"] = {
                "n": int(np.sum(selected)),
                "r_p2_p50_p98": [float(value) for value in quantiles],
                "mediana_pasa_2pct": bool(abs(quantiles[1] - 1.0) <= 0.02),
                "calibration_eligible": calibration_eligible,
                "exclusion_reason": ("fuga espectral autónoma ya arbitrada"
                                     if not calibration_eligible else None),
            }
        results[par] = {
            "block_id": constituent["block_id"],
            "sigma": float(np.max(np.linalg.eigvals(matrix).real)),
            "modes": modes,
        }

    payload = {
        "_meta": {
            "spec": str(spec_path),
            "spec_sha256": sha256(spec_path),
            "series_root": str(series_root),
            "series_sha256": series_hashes,
            "metodo": "A_L/(|chi_xvz(omega_linea)| F_hat); mascara A_L>1e-6 max",
            "nota": "Las series son extracción cacheada de films externos; no se reescriben.",
        },
        "summary": {
            "n_modes": len(all_medians),
            "median_of_mode_medians": float(np.median(all_medians)),
            "max_abs_mode_median_error": float(np.max(np.abs(np.asarray(all_medians) - 1.0))),
            "n_calibration_eligible": len(calibration_medians),
            "max_abs_calibration_median_error": float(np.max(
                np.abs(np.asarray(calibration_medians) - 1.0))),
            "all_calibration_medians_within_2pct": bool(np.all(
                np.abs(np.asarray(calibration_medians) - 1.0) <= 0.02)),
        },
        "cases": results,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[link-grumo] Gate C identidad larga: {payload['summary']}")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
