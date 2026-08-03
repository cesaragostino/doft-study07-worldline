#!/usr/bin/env python3
"""Gate G0: congela pares no abiertos por capas para early[0,20] -> late[50,60]."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from baseline_census import cargar_filas, safe_output


SEED = "gate-g-20260802"
QUOTAS = {
    ("YN", "t1"): 6, ("YN", "t2"): 6,
    ("NY", "t1"): 2, ("NY", "t2"): 2,
    ("YY", "t1"): 1, ("YY", "t2"): 5,
    ("NN", "t1"): 4, ("NN", "t2"): 4,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index_runs(root: Path) -> dict[str, Path]:
    return {path.name: path for path in root.glob("*/unidades/*")
            if path.is_dir() and (path / "manifest.json").is_file()}


def rank(pair_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{pair_id}".encode()).hexdigest()


def genome_vector(manifest: dict) -> list[str]:
    return [str(node["genome_hash"]) for node in manifest["composicion"]["por_nodo"]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health", required=True, type=Path)
    parser.add_argument("--gate-f-bank", required=True, type=Path)
    parser.add_argument("--tables-root", required=True, type=Path)
    parser.add_argument("--worldlines-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    health_path = args.health.expanduser().resolve()
    gate_f_path = args.gate_f_bank.expanduser().resolve()
    tables_root = args.tables_root.expanduser().resolve()
    worldlines_root = args.worldlines_root.expanduser().resolve()
    health = json.loads(health_path.read_text())
    gate_f = json.loads(gate_f_path.read_text())
    table_rows, table_hashes = cargar_filas(tables_root)
    table_by_id = {row["run_id"]: row for row in table_rows}
    runs = index_runs(worldlines_root)
    excluded = {side["run_id"] for pair in gate_f["pairs"]
                for side in (pair["target"], pair["control"])}
    pairs: dict[str, dict[str, dict]] = {}
    for record in health["records"]:
        pairs.setdefault(record["pair"], {})[record["arm"]] = record

    eligible = []
    for pair_id, pair in pairs.items():
        if set(pair) != {"t", "f"}:
            continue
        if any(side["run_id"] in excluded for side in pair.values()):
            continue
        category = ("Y" if pair["t"]["coordinate_health"] else "N") + (
            "Y" if pair["f"]["coordinate_health"] else "N")
        tanda = pair_id[:2]
        eligible.append({"pair_id": pair_id, "category": category, "tanda": tanda,
                         "rank": rank(pair_id), "source": pair})

    selected = []
    for stratum, quota in QUOTAS.items():
        candidates = sorted((item for item in eligible
                             if (item["category"], item["tanda"]) == stratum),
                            key=lambda item: item["rank"])
        if len(candidates) < quota:
            raise RuntimeError(f"estrato {stratum} tiene {len(candidates)} < {quota}")
        selected.extend(candidates[:quota])
    selected.sort(key=lambda item: (item["category"], item["tanda"], item["rank"]))

    output_pairs = []
    for item in selected:
        sides = {}
        manifests = {}
        for arm in ("t", "f"):
            source = item["source"][arm]
            run_id = source["run_id"]
            if run_id not in runs:
                raise RuntimeError(f"worldline ausente: {run_id}")
            manifest_path = runs[run_id] / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifests[arm] = manifest
            table = table_by_id[run_id]
            sides[arm] = {
                "run_id": run_id, "arm": arm, "run_dir": str(runs[run_id]),
                "manifest_sha256": sha256(manifest_path),
                "coordinate_health": bool(source["coordinate_health"]),
                "raw_health": bool(source["raw_health"]),
                "rw_final_60": source["rw_final_60"],
                "raw_dw_50_60": source["raw_dw_50_60"],
                "corrected_slope_50_60": source["corrected_slope_50_60"],
                "resolvable_W8": source["resolvable_W8"],
                "flagged": source["flagged"],
                "W8_t_lock_ut": table["W8"]["t_lock_ut"],
                "W8_dw_temprana": table["W8"]["dw_temprana"],
            }
        exact = {
            "same_seed": manifests["t"]["seed"] == manifests["f"]["seed"],
            "same_genomes_ordered": genome_vector(manifests["t"])
                                    == genome_vector(manifests["f"]),
            "same_dt": manifests["t"]["dt"] == manifests["f"]["dt"],
            "same_topology": all(manifests["t"][key] == manifests["f"][key]
                                 for key in ("k_global", "gamma_c", "topologia")),
        }
        if not all(exact.values()):
            raise RuntimeError(f"par no exacto: {item['pair_id']}")
        output_pairs.append({
            "pair_id": item["pair_id"], "category": item["category"],
            "tanda": item["tanda"], "selection_rank": item["rank"],
            "t": sides["t"], "f": sides["f"], "exact_pair_checks": exact,
        })

    category_counts = {category: sum(pair["category"] == category for pair in output_pairs)
                       for category in ("YN", "NY", "YY", "NN")}
    result = {
        "_meta": {
            "health": str(health_path), "health_sha256": sha256(health_path),
            "gate_f_bank": str(gate_f_path), "gate_f_bank_sha256": sha256(gate_f_path),
            "tables_root": str(tables_root), "table_sha256": table_hashes,
            "worldlines_root": str(worldlines_root),
            "policy": "worldlines externas sólo lectura; salida logs/link_grumo",
        },
        "selection_contract": {
            "status": ("retrospectivo balanceado por outcome; selección sellada antes de "
                       "abrir las capas Q/S1/S2 de estos films"),
            "excluded": "los 16 films usados en Gate F",
            "outcome": "coordinate_health a 60 de Gate F3",
            "predictor_window_ut": [0.0, 20.0],
            "outcome_window_ut": [50.0, 60.0],
            "rank": f"sha256('{SEED}:'+pair_id)",
            "quotas": {f"{category}_{tanda}": quota
                       for (category, tanda), quota in QUOTAS.items()},
            "category": "primera letra transported, segunda fresh; Y=coordinate_health",
        },
        "summary": {
            "n_pairs": len(output_pairs), "n_films": 2 * len(output_pairs),
            "categories": category_counts,
            "n_positive_films": sum(pair[arm]["coordinate_health"]
                                    for pair in output_pairs for arm in ("t", "f")),
            "n_negative_films": sum(not pair[arm]["coordinate_health"]
                                    for pair in output_pairs for arm in ("t", "f")),
            "n_flagged": sum(pair[arm]["flagged"]
                             for pair in output_pairs for arm in ("t", "f")),
        },
        "warnings": [
            "El balance por outcome impide estimar prevalencia o valores predictivos poblacionales.",
            "Sí permite contraste apareado de mecanismos tempranos dentro de cada categoría.",
            "Las capas estaban sin abrir en este frente, pero los outcomes y tablas eran conocidos.",
        ],
        "pairs": output_pairs,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate G0: {len(output_pairs)} pares / {2 * len(output_pairs)} films")
    print(f"[link-grumo] categorías: {category_counts}")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
