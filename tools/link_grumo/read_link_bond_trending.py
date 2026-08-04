#!/usr/bin/env python3
"""Panel descriptivo de la cosecha link_bond_trend; no decide salud ni fitness."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np


LAYERS = ("Q", "S1", "S2")


def _arm(run_id: str) -> str:
    found = [arm for arm in ("t", "f") if f"_{arm}_" in run_id]
    if len(found) != 1:
        raise RuntimeError(f"run_id sin brazo inequívoco: {run_id}")
    return found[0]


def _pair_key(run_id: str) -> str:
    return run_id.replace("_t_", "_X_").replace("_f_", "_X_")


def _category(states: np.ndarray) -> tuple[str, float, int]:
    states = np.asarray(states, dtype=bool)
    fraction = float(np.mean(states))
    changes = int(np.sum(states[1:] != states[:-1])) if len(states) > 1 else 0
    if fraction == 1.0:
        category = "stable"
    elif fraction == 0.0:
        category = "never"
    else:
        category = "intermittent"
    return category, fraction, changes


def _quantiles(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.isfinite(array).all():
        raise RuntimeError("grupo vacío o no finito en panel")
    return {
        "q10": float(np.quantile(array, 0.10)),
        "median": float(np.median(array)),
        "q90": float(np.quantile(array, 0.90)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


def _phase_summary(record: dict, layer_index: int) -> dict:
    return record["summary"]["phase"][0]["layers"][layer_index]


def _power_summary(record: dict, layer_index: int) -> dict:
    return record["summary"]["power"][layer_index]


def read_panel(ledger_path: Path) -> dict:
    ledger_path = ledger_path.resolve()
    ledger_bytes = ledger_path.read_bytes()
    ledger = json.loads(ledger_bytes)
    records = ledger.get("records", [])
    if len(records) != int(ledger.get("summary", {}).get("n", -1)):
        raise RuntimeError("cantidad de records no coincide con summary.n")
    failures = [record for record in records if record.get("status") == "failed"]
    if failures:
        raise RuntimeError(f"ledger contiene {len(failures)} fallos; panel no imputa")

    enriched = []
    energy_rows = 0
    energy_positive = []
    film_net_medians = []
    correction_counts: Counter = Counter()
    for record in records:
        run_id = str(record["run_id"])
        horizon = int(round(float(record["summary"]["t_range_ut"][1])))
        view_dir = Path(record["view_dir"])
        manifest = json.loads((view_dir / "manifest.json").read_text())
        if manifest.get("view_hash") != record.get("view_hash_trending"):
            raise RuntimeError(f"{run_id}: view_hash no coincide con ledger")
        with np.load(view_dir / "data.npz", allow_pickle=False) as arrays:
            raw = np.asarray(arrays["lock_raw"], dtype=float)[:, 0, :]
            corrected = np.asarray(
                arrays["lock_corrected_fixed"], dtype=float
            )[:, 0, :]
            mute = np.any(np.asarray(arrays["mute"], dtype=bool), axis=1)
            ticks = np.asarray(arrays["ticks_end"], dtype=np.int64)
            times = np.asarray(arrays["t_end_ut"], dtype=float)
            net_layers = np.asarray(
                arrays["net_power_layer_mean"], dtype=float
            )
        if raw.shape != corrected.shape or raw.shape[1] != len(LAYERS):
            raise RuntimeError(f"{run_id}: forma de lock incompatible {raw.shape}")
        if mute.shape != raw.shape or net_layers.shape != raw.shape:
            raise RuntimeError(f"{run_id}: grillas compactas no coinciden")
        net = np.sum(net_layers, axis=1)
        energy_rows += len(net)
        film_net_medians.append(float(np.median(net)))
        for index in np.flatnonzero(net > 0.0):
            energy_positive.append({
                "run_id": run_id,
                "tick": int(ticks[index]),
                "t_ut": float(times[index]),
                "net_power": float(net[index]),
                "net_power_by_layer": [float(value) for value in net_layers[index]],
            })

        layer_rows = []
        for layer_index, layer in enumerate(LAYERS):
            raw_category, raw_fraction, raw_changes = _category(
                (raw[:, layer_index] >= 0.90) & (~mute[:, layer_index])
            )
            corrected_category, corrected_fraction, corrected_changes = _category(
                (corrected[:, layer_index] >= 0.90) & (~mute[:, layer_index])
            )
            key = (horizon, _arm(run_id), layer)
            correction_counts[key + ("n",)] += 1
            correction_counts[key + ("category_changed",)] += int(
                raw_category != corrected_category
            )
            layer_rows.append({
                "layer": layer,
                "raw_lock_median": float(np.median(raw[:, layer_index])),
                "corrected_lock_median": float(np.median(corrected[:, layer_index])),
                "corrected_minus_raw_lock_median": float(
                    np.median(corrected[:, layer_index])
                    - np.median(raw[:, layer_index])
                ),
                "raw_category": raw_category,
                "raw_locked_fraction": raw_fraction,
                "raw_state_changes": raw_changes,
                "corrected_category": corrected_category,
                "corrected_locked_fraction": corrected_fraction,
                "corrected_state_changes": corrected_changes,
            })
        enriched.append({
            "record": record,
            "run_id": run_id,
            "arm": _arm(run_id),
            "horizon_ut": horizon,
            "layers": layer_rows,
        })

    groups = []
    for horizon in sorted({row["horizon_ut"] for row in enriched}):
        for arm in ("t", "f"):
            subset = [row for row in enriched
                      if row["horizon_ut"] == horizon and row["arm"] == arm]
            if not subset:
                continue
            for layer_index, layer in enumerate(LAYERS):
                compact = [_phase_summary(row["record"], layer_index) for row in subset]
                power = [_power_summary(row["record"], layer_index) for row in subset]
                categories = Counter(row["layers"][layer_index]["corrected_category"]
                                     for row in subset)
                raw_categories = Counter(row["layers"][layer_index]["raw_category"]
                                         for row in subset)
                changes = [int(value["locked_state_changes"]) for value in compact]
                groups.append({
                    "horizon_ut": horizon,
                    "arm": arm,
                    "layer": layer,
                    "n": len(subset),
                    "raw_category_counts": dict(sorted(raw_categories.items())),
                    "corrected_category_counts": dict(sorted(categories.items())),
                    "films_with_state_changes": int(sum(value > 0 for value in changes)),
                    "state_changes": _quantiles([float(value) for value in changes]),
                    "lock_median_across_film": _quantiles([
                        float(value["lock_median"]) for value in compact
                    ]),
                    "within_film_lock_swing_q90_minus_q10": _quantiles([
                        float(value["lock_q90"] - value["lock_q10"])
                        for value in compact
                    ]),
                    "phase_drift_median": _quantiles([
                        float(value["drift_median"]) for value in compact
                    ]),
                    "raw_corrected_median_abs_delta": _quantiles([
                        float(value["raw_corrected_median_abs_delta"])
                        for value in compact
                    ]),
                    "phase_category_changed_raw_to_corrected": int(
                        correction_counts[(horizon, arm, layer, "category_changed")]
                    ),
                    "net_power_median": _quantiles([
                        float(value["net_power_median"]) for value in power
                    ]),
                    "films_with_negative_layer_net_power_median": int(sum(
                        float(value["net_power_median"]) < 0.0 for value in power
                    )),
                })

    by_pair: dict[str, dict[str, dict]] = {}
    for row in enriched:
        by_pair.setdefault(_pair_key(row["run_id"]), {})[row["arm"]] = row
    pairs = [pair for pair in by_pair.values() if set(pair) == {"t", "f"}]
    paired = []
    reversals = []
    for horizon in sorted({pair["t"]["horizon_ut"] for pair in pairs}):
        subset = [pair for pair in pairs if pair["t"]["horizon_ut"] == horizon]
        for layer_index, layer in enumerate(LAYERS):
            corrected_values = []
            raw_values = []
            for pair in subset:
                t_value = float(_phase_summary(pair["t"]["record"], layer_index)[
                    "lock_median"
                ])
                f_value = float(_phase_summary(pair["f"]["record"], layer_index)[
                    "lock_median"
                ])
                corrected_values.append(t_value - f_value)
                raw_values.append(
                    pair["t"]["layers"][layer_index]["raw_lock_median"]
                    - pair["f"]["layers"][layer_index]["raw_lock_median"]
                )
                reversals.append({
                    "horizon_ut": horizon,
                    "layer": layer,
                    "run_id_t": pair["t"]["run_id"],
                    "delta_t_minus_f": t_value - f_value,
                    "lock_median_t": t_value,
                    "lock_median_f": f_value,
                })
            corrected_array = np.asarray(corrected_values)
            raw_array = np.asarray(raw_values)
            paired.append({
                "horizon_ut": horizon,
                "layer": layer,
                "n_pairs": len(corrected_values),
                "raw_delta_lock_median_t_minus_f": _quantiles(raw_values),
                "raw_t_greater": int(np.sum(raw_array > 0.0)),
                "raw_f_greater": int(np.sum(raw_array < 0.0)),
                "raw_ties": int(np.sum(raw_array == 0.0)),
                "corrected_delta_lock_median_t_minus_f": _quantiles(
                    corrected_values
                ),
                "corrected_t_greater": int(np.sum(corrected_array > 0.0)),
                "corrected_f_greater": int(np.sum(corrected_array < 0.0)),
                "corrected_ties": int(np.sum(corrected_array == 0.0)),
            })

    state_outliers = []
    correction_outliers = []
    for layer_index, layer in enumerate(LAYERS):
        state_outliers.extend(sorted(({
            "layer": layer,
            "run_id": row["run_id"],
            "horizon_ut": row["horizon_ut"],
            "arm": row["arm"],
            "state_changes": int(_phase_summary(row["record"], layer_index)[
                "locked_state_changes"
            ]),
            "locked_fraction": float(_phase_summary(row["record"], layer_index)[
                "locked_fraction"
            ]),
            "lock_median": float(_phase_summary(row["record"], layer_index)[
                "lock_median"
            ]),
        } for row in enriched), key=lambda value: value["state_changes"],
            reverse=True)[:8])
        correction_outliers.extend(sorted(({
            "layer": layer,
            "run_id": row["run_id"],
            "horizon_ut": row["horizon_ut"],
            **row["layers"][layer_index],
        } for row in enriched), key=lambda value: abs(
            value["corrected_minus_raw_lock_median"]
        ), reverse=True)[:8])

    return {
        "_meta": {
            "source_ledger": str(ledger_path),
            "source_ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
            "analysis_status": "DESCRIPTIVE_POST_HOC",
            "lock_ratio": "1:1",
            "category_rule": (
                "stable=locked every compact row; never=locked no compact row; "
                "intermittent=otherwise; locked requires L>=0.90 and non-mute"
            ),
            "warnings": [
                "No hay outcome, AUC, fitness ni score de salud.",
                "Los horizontes 60/120 se informan separados.",
                "corrected_fixed es no causal y se audita contra raw.",
                "Los cruces de estado usan la grilla compacta; la vista conserva L por dt.",
            ],
        },
        "custody": {
            "n_records": len(records),
            "n_pairs_t_f": len(pairs),
            "n_unpaired": len(records) - 2 * len(pairs),
            "by_arm_horizon": dict(sorted(Counter(
                f"{row['arm']}@{row['horizon_ut']}"
                for row in enriched
            ).items())),
        },
        "groups": groups,
        "paired": paired,
        "phase_correction_sensitivity": {
            "n_layer_films": len(enriched) * len(LAYERS),
            "n_temporal_categories_changed": int(sum(
                count for key, count in correction_counts.items()
                if key[-1] == "category_changed"
            )),
            "definition": (
                "categoría raw vs corrected_fixed sobre la misma grilla, umbral y "
                "guard de mudez"
            ),
        },
        "energy_support": {
            "n_compact_boxes": energy_rows,
            "n_positive_total_net_power_boxes": len(energy_positive),
            "n_films_with_positive_total_net_power_box": len({
                row["run_id"] for row in energy_positive
            }),
            "all_film_total_net_power_medians_negative": bool(
                all(value < 0.0 for value in film_net_medians)
            ),
            "film_total_net_power_median": _quantiles(film_net_medians),
            "positive_exceptions": energy_positive,
        },
        "outliers": {
            "top_state_changes_per_layer": state_outliers,
            "top_raw_corrected_disagreement_per_layer": correction_outliers,
            "strongest_paired_reversals_t_below_f": sorted(
                reversals, key=lambda value: value["delta_t_minus_f"]
            )[:24],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    ledger = args.ledger.resolve()
    output = args.output.resolve()
    if output.parent != ledger.parent:
        raise SystemExit("el panel debe escribirse junto al ledger fuente")
    panel = read_panel(ledger)
    tmp = output.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(panel, indent=2, allow_nan=False) + "\n")
    tmp.replace(output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"[bond-trending-read] output={output} sha256={digest}")


if __name__ == "__main__":
    main()
