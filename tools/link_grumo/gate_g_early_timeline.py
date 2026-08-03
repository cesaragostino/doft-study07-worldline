#!/usr/bin/env python3
"""Gate G1: abre sólo [0,20] de los films congelados por G0."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from baseline_census import safe_output
from gate_f_timeline import (film_summary, layer_timeline, load_film, q_timeline)
from linear_response import jacobian_fd, load_blocks, parse_block
from study07.artifacts.checkpoint import spec_fingerprint


EARLY_END_UT = 20.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    bank_path = args.bank.expanduser().resolve()
    blocks_path = args.blocks.expanduser().resolve()
    bank = json.loads(bank_path.read_text())
    blocks = load_blocks(blocks_path)
    models: dict[str, tuple] = {}
    chi_cache: dict[tuple, tuple] = {}
    films = []

    for pair in bank["pairs"]:
        transported_manifest = json.loads(
            (Path(pair["t"]["run_dir"]) / "manifest.json").read_text())
        block_ids = [str(node["block_id"])
                     for node in transported_manifest["composicion"]["por_nodo"]]
        for block_id in block_ids:
            if block_id not in models:
                spec = parse_block(blocks[block_id])
                matrix, drive = jacobian_fd(spec)
                models[block_id] = (spec, matrix, drive)
        for arm in ("t", "f"):
            side = pair[arm]
            manifest, provenance, arrays = load_film(
                Path(side["run_dir"]), limit_ut=EARLY_END_UT)
            for node, block_id in enumerate(block_ids):
                if spec_fingerprint(models[block_id][0]) != manifest["spec_fingerprints"][node]:
                    raise RuntimeError(f"constitución no coincide: {side['run_id']} nodo {node}")
            dt_effective = float(manifest["dt"]) * int(provenance["stride"])
            channels, primary = q_timeline(
                arrays, dt_effective, block_ids, models, chi_cache)
            layers = layer_timeline(arrays, dt_effective)
            summary = film_summary(channels, primary, layers)
            films.append({
                "pair_id": pair["pair_id"], "category": pair["category"],
                "tanda": pair["tanda"], "run_id": side["run_id"], "arm": arm,
                "coordinate_health": side["coordinate_health"],
                "raw_health": side["raw_health"],
                "outcome60": {
                    key: side[key] for key in (
                        "rw_final_60", "raw_dw_50_60", "corrected_slope_50_60",
                        "W8_t_lock_ut", "W8_dw_temprana", "resolvable_W8")
                },
                "block_ids": block_ids, "summary": summary,
                "Q_channels": channels, "primary_Q": primary[0], "layers": layers,
                "provenance": provenance,
            })
            print(f"[link-grumo] G1 {len(films)}/{bank['summary']['n_films']} "
                  f"{side['run_id']}", flush=True)

    result = {
        "_meta": {
            "bank": str(bank_path), "bank_sha256": sha256(bank_path),
            "blocks": str(blocks_path), "blocks_sha256": sha256(blocks_path),
            "policy": "worldlines externas read-only; sólo chunks necesarios para [0,20]",
        },
        "method": {
            "predictor_window_ut": [0.0, EARLY_END_UT],
            "outcome_window_ut": [50.0, 60.0],
            "bank_contract": bank["selection_contract"],
            "Q_transfer": ("W8/hop1; ocupación predicha y observada, R complejo y "
                           "continuidad de línea exactamente como Gate F"),
            "extractor": ("mismos W8/hop1 para Q y W4/hop1 para capas que Gate F; "
                          "episodios cortados ante salto de línea >2 Rayleigh"),
        },
        "summary": {
            "n_films": len(films),
            "n_coordinate_health": sum(film["coordinate_health"] for film in films),
            "n_chi_cache_points": len(chi_cache),
            "max_chunks_verified": max(film["provenance"]["n_chunks_verified"]
                                       for film in films),
            "all_limits_20": all(film["provenance"]["requested_limit_ut"] == EARLY_END_UT
                                 for film in films),
        },
        "warnings": [
            "Outcomes conocidos al seleccionar; capas de estos films no se habían abierto en Gate F.",
            "Un evento ausente puede ser captura posterior a 20, no incapacidad constitucional.",
            "La última ventana está censurada por el borde t=20.",
            "R≈1 sigue midiendo compatibilidad con respuesta forzada, no causalidad.",
        ],
        "films": films,
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"[link-grumo] Gate G1 completo: {len(films)} films hasta {EARLY_END_UT} u.t.")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
