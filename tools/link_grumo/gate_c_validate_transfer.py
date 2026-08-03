#!/usr/bin/env python3
"""Valida el cálculo χ propio contra notches ya arbitrados, sin releer films largos."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from baseline_census import safe_output
from linear_response import (chi_modes, jacobian_fd, load_blocks, local_minima,
                             parse_block)


CASES = {
    "par134_receptor": {"prefix": "61b484288817", "range": [32.0, 36.0],
                        "expected": {"Q0": 33.69, "Q1": 34.37}},
    "par129_receptor": {"prefix": "9c2256bc8e73", "range": [20.4, 28.0],
                        "expected": {}},
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    blocks_path = args.blocks.expanduser().resolve()
    blocks = load_blocks(blocks_path)

    result_cases = {}
    for name, case in CASES.items():
        matches = [block for block_id, block in blocks.items()
                   if block_id.startswith(case["prefix"])]
        if len(matches) != 1:
            raise RuntimeError(f"{name}: prefijo no unívoco")
        block = matches[0]
        spec = parse_block(block)
        matrix, drive_vector = jacobian_fd(spec)
        sigma = float(np.max(np.linalg.eigvals(matrix).real))
        omega = np.arange(case["range"][0], case["range"][1] + 0.0025, 0.005)
        chi = np.abs(chi_modes(matrix, drive_vector, omega, spec.n_modes))
        modes = {}
        for index in range(3):
            minima = local_minima(omega, chi[:, index])
            modes[f"Q{index}"] = {"minimos": minima,
                                  "min": float(np.min(chi[:, index])),
                                  "max": float(np.max(chi[:, index]))}
        checks = []
        for mode, expected in case["expected"].items():
            found = min(modes[mode]["minimos"],
                        key=lambda item: abs(item["omega"] - expected))["omega"]
            checks.append({"mode": mode, "expected": expected, "found": found,
                           "abs_error": abs(found - expected),
                           "passes_0.03": abs(found - expected) <= 0.03})
        if not case["expected"]:
            checks.append({"expected": "sin mínimos Q0/Q1/Q2",
                           "found_count": sum(len(modes[f"Q{i}"]["minimos"])
                                              for i in range(3)),
                           "passes": all(not modes[f"Q{i}"]["minimos"] for i in range(3))})
        result_cases[name] = {"block_id": block["block_id"], "sigma": sigma,
                              "omega_range": case["range"], "modes": modes,
                              "checks": checks}

    result = {
        "_meta": {"blocks": str(blocks_path),
                  "blocks_sha256": __import__("hashlib").sha256(
                      blocks_path.read_bytes()).hexdigest(),
                  "metodo": "Jacobian FD (x,v,z), b=e=0; drive externo unitario"},
        "cases": result_cases,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("[link-grumo] Gate C validación χ: par134 notches + par129 control")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
