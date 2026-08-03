#!/usr/bin/env python3
"""Gate F0: congela el banco de salud60 y sus controles apareados exactos.

La selección del control no usa el outcome: para cada positivo de Gate E toma el otro
brazo del mismo par/semilla. Las worldlines externas se abren sólo para verificar su
manifiesto; los veredictos faltantes se reconstruyen desde las views locales W8.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from baseline_census import cargar_filas, indexar_reportes, indexar_views_w8, safe_output
from gate_e_fixed_horizon import verdict_at_60


RUN_RE = re.compile(r"^(?P<pair>.+)_(?P<arm>[tf])_k03_tau02$")
RAYLEIGH_W8 = 2.0 * math.pi / 8.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index_runs(root: Path) -> dict[str, Path]:
    return {path.name: path for path in root.glob("*/unidades/*")
            if path.is_dir() and (path / "manifest.json").is_file()}


def pair_and_arm(run_id: str) -> tuple[str, str]:
    match = RUN_RE.fullmatch(run_id)
    if match is None:
        raise RuntimeError(f"run_id fuera del contrato census: {run_id}")
    return match.group("pair"), match.group("arm")


def genome_vector(manifest: dict) -> list[str]:
    return [str(node["genome_hash"]) for node in manifest["composicion"]["por_nodo"]]


def fixed_outcome(run_id: str, gate_e_by_id: dict[str, dict], tables_by_id: dict[str, dict],
                  reports: dict[str, dict], views: dict[str, Path]) -> dict:
    if run_id in gate_e_by_id:
        row = gate_e_by_id[run_id]
        return {key: row[key] for key in (
            "salud_60", "firme_60", "cierre_60", "rw_final_60", "dw_tardia_60",
            "original_horizon_ut", "view", "view_hash", "worldline_hash")}
    if run_id not in tables_by_id or run_id not in reports:
        raise RuntimeError(f"sin tabla/reporte para outcome fijo: {run_id}")
    report = reports[run_id]
    view = views.get(str(report["worldline_hash"])[:16])
    if view is None:
        raise RuntimeError(f"sin view W8 para outcome fijo: {run_id}")
    return verdict_at_60(view)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-e", required=True, type=Path)
    parser.add_argument("--tables-root", required=True, type=Path)
    parser.add_argument("--worldlines-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    gate_e_path = args.gate_e.expanduser().resolve()
    tables_root = args.tables_root.expanduser().resolve()
    worldlines_root = args.worldlines_root.expanduser().resolve()
    gate_e = json.loads(gate_e_path.read_text())
    gate_e_by_id = {row["run_id"]: row for row in gate_e["records"]}
    table_rows, table_hashes = cargar_filas(tables_root)
    tables_by_id = {row["run_id"]: row for row in table_rows}
    reports = indexar_reportes(tables_root)
    views = indexar_views_w8(tables_root)
    runs = index_runs(worldlines_root)

    targets = sorted((row for row in gate_e["records"] if row["salud_60"]),
                     key=lambda row: row["run_id"])
    pairs = []
    for target in targets:
        pair_id, arm = pair_and_arm(target["run_id"])
        control_arm = "f" if arm == "t" else "t"
        control_id = f"{pair_id}_{control_arm}_k03_tau02"
        if target["run_id"] not in runs or control_id not in runs:
            raise RuntimeError(f"falta brazo exacto para {target['run_id']}: {control_id}")
        target_manifest_path = runs[target["run_id"]] / "manifest.json"
        control_manifest_path = runs[control_id] / "manifest.json"
        target_manifest = json.loads(target_manifest_path.read_text())
        control_manifest = json.loads(control_manifest_path.read_text())
        exact_checks = {
            "same_seed": target_manifest["seed"] == control_manifest["seed"],
            "same_genomes_ordered": genome_vector(target_manifest) == genome_vector(control_manifest),
            "same_dt": target_manifest["dt"] == control_manifest["dt"],
            "same_k_gamma_topology": all(
                target_manifest[key] == control_manifest[key]
                for key in ("k_global", "gamma_c", "topologia")),
            "target_arm_origin": [node["origen"]
                                  for node in target_manifest["composicion"]["por_nodo"]],
            "control_arm_origin": [node["origen"]
                                   for node in control_manifest["composicion"]["por_nodo"]],
        }
        if not all(exact_checks[key] for key in (
                "same_seed", "same_genomes_ordered", "same_dt", "same_k_gamma_topology")):
            raise RuntimeError(f"control no apareado exactamente: {target['run_id']}")
        target_outcome = fixed_outcome(
            target["run_id"], gate_e_by_id, tables_by_id, reports, views)
        control_outcome = fixed_outcome(
            control_id, gate_e_by_id, tables_by_id, reports, views)
        if not target_outcome["salud_60"]:
            raise RuntimeError(f"target dejó de ser saludable: {target['run_id']}")
        pairs.append({
            "pair_id": pair_id,
            "target": {
                "run_id": target["run_id"], "arm": arm,
                "run_dir": str(runs[target["run_id"]]),
                "manifest_sha256": sha256(target_manifest_path),
                "in_gate_e_population": True,
                "resolvable_W8_gate_b": bool(
                    float(tables_by_id[target["run_id"]]["W8"]["dw_temprana"])
                    >= RAYLEIGH_W8),
                "outcome": target_outcome,
            },
            "control": {
                "run_id": control_id, "arm": control_arm,
                "run_dir": str(runs[control_id]),
                "manifest_sha256": sha256(control_manifest_path),
                "in_gate_e_population": control_id in gate_e_by_id,
                "resolvable_W8_gate_b": bool(
                    float(tables_by_id[control_id]["W8"]["dw_temprana"])
                    >= RAYLEIGH_W8),
                "outcome": control_outcome,
            },
            "exact_pair_checks": exact_checks,
            "outcome_relation": ("discordant" if target_outcome["salud_60"]
                                   != control_outcome["salud_60"] else "concordant"),
        })

    films = [side for pair in pairs for side in (pair["target"], pair["control"])]
    result = {
        "_meta": {
            "gate_e": str(gate_e_path), "gate_e_sha256": sha256(gate_e_path),
            "tables_root": str(tables_root), "table_sha256": table_hashes,
            "worldlines_root": str(worldlines_root),
            "policy": "worldlines externas read-only; salida sólo logs/link_grumo",
        },
        "selection_contract": {
            "targets": "todos los salud_60=True de la población elegible Gate E",
            "control": "otro brazo del mismo par y semilla, sin seleccionar por outcome",
            "status": ("banco congelado después de conocer Gate E; no es preregistro "
                       "prospectivo, pero la regla de control es outcome-independent"),
            "horizon_ut": 60.0,
            "health": "rw_final_W8>=0.95 AND dw_[50,60]<0.1375",
        },
        "gate_f_timeline_contract": {
            "Q_transfer": {
                "window_ut": 8.0, "hop_ut": 1.0,
                "directed_channels": "se calculan 0->1 y 1->0; no se elige post hoc",
                "line": "pico Q del emisor en [2,50] rad/u.t. por ventana",
                "occupation": "rho_pred=|chi_Q| A_force/A_competitor >1",
                "observed_occupation": "rho_obs=A_line_follower/A_competitor >1",
                "complex_capture": "|arg R|<=15deg y 0.5<=|R|<=2; R=(Q/F)/chi_Q",
                "sustain_ut": 2.0,
            },
            "layers": {
                "window_ut": 4.0, "hop_ut": 1.0,
                "signal": "sumas x,v por Q/S1/S2 y fase corregida con omega local de ventana",
                "capture": "rw_local>=0.90 sostenido 4 u.t.",
                "mute": ("std de ventana < max(1e-12,1e-3*max std causal previo) "
                         "en cualquier nodo"),
            },
            "ordering": "comparar t_S1, t_S2, t_Q_complex, t_Q_occupation y releases",
            "interpretation": ("elegibilidad, captura y persistencia son estados distintos; "
                               "ninguno se declara por sí solo ley de salud"),
        },
        "summary": {
            "n_targets_gate_e": len(targets), "n_pairs": len(pairs),
            "n_unique_films": len({film["run_id"] for film in films}),
            "n_discordant": sum(pair["outcome_relation"] == "discordant" for pair in pairs),
            "n_control_healthy": sum(pair["control"]["outcome"]["salud_60"] for pair in pairs),
            "n_controls_outside_gate_e_population": sum(
                not pair["control"]["in_gate_e_population"] for pair in pairs),
        },
        "warnings": [
            "Gate E cubre sólo films no-self, resolubles W8 y sin banderas; no es todo el census.",
            "Un control exacto puede compartir el outcome: sirve para dinámica, no como negativo.",
            "Los targets fueron descubiertos en estos datos; las frecuencias de éxito son descriptivas.",
            "El endpoint salud60 no prueba supervivencia asintótica.",
        ],
        "pairs": pairs,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate F0: {len(pairs)} pares, {result['summary']['n_discordant']} discordantes")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
