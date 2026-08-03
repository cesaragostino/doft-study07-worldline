#!/usr/bin/env python3
"""Une shards exhaustivos de Gate M y reconstruye el resumen canónico."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tools/link_grumo")]

import gate_l_bidirectional_transient as gate_l  # noqa: E402
import gate_m_nonlinear_fast as gate_m  # noqa: E402


def merge_parts(parts: list[dict], simulator_sha: str) -> dict:
    if not parts:
        raise ValueError("faltan shards")
    counts = {part["_meta"]["shard"]["count"] for part in parts}
    if len(counts) != 1:
        raise RuntimeError("shard_count inconsistente")
    count = counts.pop()
    indices = sorted(part["_meta"]["shard"]["index"] for part in parts)
    if indices != list(range(count)) or len(parts) != count:
        raise RuntimeError(f"shards incompletos/duplicados: {indices} de {count}")
    reference = parts[0]
    for part in parts:
        if part["_meta"]["script_sha256"] != simulator_sha:
            raise RuntimeError("shard generado por otra versión del simulador")
        for key in ("prereg_sha256", "input_sha256", "dt_production", "dt_observed",
                    "dt_convergence", "horizon_ut"):
            if part["_meta"][key] != reference["_meta"][key]:
                raise RuntimeError(f"metadato inconsistente entre shards: {key}")
        if part["model"] != reference["model"]:
            raise RuntimeError("modelo inconsistente entre shards")

    records = sorted((record for part in parts for record in part["records"]),
                     key=lambda row: row["panel_index"])
    if len(records) != 16 or [row["panel_index"] for row in records] != list(range(1, 17)):
        raise RuntimeError("merge no cubre exactamente las 16 posiciones del panel")
    if len({row["run_id"] for row in records}) != 16:
        raise RuntimeError("run_id duplicado en merge")
    if any(row["max_abs_drift_b"] != 0.0 or row["max_abs_drift_e"] != 0.0
           for row in records):
        raise RuntimeError("algún shard violó SLOW_FROZEN")

    groups = {
        "all": records,
        "healthy": [row for row in records if row["health60"]],
        "not_healthy": [row for row in records if not row["health60"]],
        "transported": [row for row in records if row["arm"] == "t"],
        "fresh": [row for row in records if row["arm"] == "f"],
    }
    unresolved = [row["run_id"] for row in records
                  if row["numeric_status"] != "RESOLVED"]
    meta = dict(reference["_meta"])
    meta.pop("shard", None)
    meta["merge_script"] = "tools/link_grumo/gate_m_merge.py"
    meta["merge_script_sha256"] = gate_m.sha256(Path(__file__))
    meta["execution_shards"] = [part["_meta"]["shard"] for part in parts]
    warnings = list(dict.fromkeys(
        warning for part in parts for warning in part["warnings"]
    ))
    warnings.append(
        "Cicatriz de ejecución: la primera pasada serial se interrumpió tras 1/16 al medir "
        "~4 min/unidad; no escribió salida. Se reraneó la población exhaustiva en cuatro "
        "shards por índice predeclarado, sin seleccionar por resultado."
    )
    return {
        "_meta": meta,
        "model": reference["model"],
        "summary": {
            "n": len(records), "n_numeric_unresolved": len(unresolved),
            "numeric_unresolved": unresolved,
            "primary": gate_m.classify_primary(records),
            "fresh_priority_controls": gate_m.fresh_priority_controls(records),
            "groups": {name: gate_m.summarize_rows(rows) for name, rows in groups.items()},
        },
        "warnings": warnings,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parts", required=True, nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise RuntimeError(f"salida ya existe, no se pisa: {output}")
    if str(output).startswith("/Volumes/ExternalDisk/"):
        raise RuntimeError("escribir en el disco externo está prohibido")
    simulator = REPO / "tools/link_grumo/gate_m_nonlinear_fast.py"
    parts = [json.loads(path.expanduser().resolve().read_text()) for path in args.parts]
    result = gate_l.round_floats(merge_parts(parts, gate_m.sha256(simulator)))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[Gate M merge] salida: {output}")


if __name__ == "__main__":
    main()
