#!/usr/bin/env python3
"""Gate I: catálogo exploratorio de residuos temporales y familias s600.

No cambia Gate H ni estima una nueva regla. Usa únicamente derivados existentes para
preguntar qué comparten y en qué difieren los casos que una foto temprana o un estado
escalar describen mal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from baseline_census import safe_output


FALSE_DRIFT_W8 = 1.1 / 8.0
EARLY_FEATURES = (
    "log_rho_pred", "log_rho_observed", "Q_rw", "S1_rw", "S2_rw",
    "primary_rw", "log_primary_dw", "log_R_error",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def residual_kind(record: dict) -> str | None:
    active = bool(record["early"]["active20"]["Q"])
    health = bool(record["coordinate_health"])
    if active and not health:
        if len(record["full_Q"]["episodes"]) > 1:
            return "INTERMITTENT_PHASE_CAPTURE"
        if record["outcome60"]["corrected_slope_50_60"] >= FALSE_DRIFT_W8:
            return "SLIDING_WINDOW_COHERENCE"
        return "EARLY_CAPTURE_OTHER_FAILURE"
    if not active and health:
        if record["early"]["active20"]["joint_flat"]:
            return "SELECTED_FLAT_BEFORE_PHASE"
        if record["early"]["active20"]["rho_observed_occupation"]:
            return "NONFLAT_PROVISIONAL_BEFORE_PHASE"
        return "LATE_NUCLEATION"
    return None


def feature_vector(record: dict) -> np.ndarray:
    early = record["early"]
    error = early["min_R_complex_error_end20"]
    return np.asarray([
        math.log(max(float(early["rho_pred_end20"]), 1e-12)),
        math.log(max(float(early["rho_observed_end20"]), 1e-12)),
        float(early["Q_rw_end20"]), float(early["S1_rw_end20"]),
        float(early["S2_rw_end20"]), float(early["primary_rw_end20"]),
        math.log1p(float(early["primary_dw_end20"])),
        math.log1p(float(error)) if error is not None else math.log(101.0),
    ])


def robust_scaled(vectors: np.ndarray) -> np.ndarray:
    median = np.median(vectors, axis=0)
    q25, q75 = np.quantile(vectors, [0.25, 0.75], axis=0)
    scale = q75 - q25
    fallback = np.std(vectors, axis=0)
    scale = np.where(scale > 1e-12, scale, np.where(fallback > 1e-12, fallback, 1.0))
    return (vectors - median) / scale


def nearest(records: list[dict], scaled: np.ndarray, index: int,
            health: bool, limit: int = 3) -> list[dict]:
    distances = np.sqrt(np.sum((scaled - scaled[index]) ** 2, axis=1))
    candidates = [j for j, record in enumerate(records)
                  if j != index and bool(record["coordinate_health"]) == health]
    candidates.sort(key=lambda j: float(distances[j]))
    return [{
        "run_id": records[j]["run_id"], "arm": records[j]["arm"],
        "coordinate_health": records[j]["coordinate_health"],
        "early_Q_active": records[j]["early"]["active20"]["Q"],
        "joint_flat": records[j]["early"]["active20"]["joint_flat"],
        "distance_early_robust": float(distances[j]),
    } for j in candidates[:limit]]


def dynamic_summary(record: dict) -> dict:
    series = record["full_Q"]["series"]
    episodes = record["full_Q"]["episodes"]
    active_fraction = float(np.mean([row["capture"] for row in series]))
    longest = max((event["duration_grid_ut"] for event in episodes), default=0.0)
    return {
        "n_Q_episodes_to60": len(episodes),
        "first_Q_confirmation_ut": (
            episodes[0]["confirmation_end_ut"] if episodes else None),
        "longest_Q_episode_grid_ut": float(longest),
        "Q_active_fraction_to60": active_fraction,
        "Q_rw_last_W4": float(series[-1]["rw_Q_local_W4"]),
        "Q_drift_last_W4": float(series[-1]["corrected_drift_local_W4"]),
        "rw_final_60_W8": float(record["outcome60"]["rw_final_60"]),
        "corrected_slope_50_60": float(record["outcome60"]["corrected_slope_50_60"]),
        "historical_W8_t_lock_ut": record["outcome60"]["W8_t_lock_ut"],
    }


def crosstab(records: list[dict], predicate) -> dict:
    selected = [record for record in records if predicate(record)]
    return {
        "n": len(selected),
        "n_health": sum(record["coordinate_health"] for record in selected),
        "n_early_Q_active": sum(record["early"]["active20"]["Q"] for record in selected),
        "arms": {
            arm: sum(record["arm"] == arm for record in selected)
            for arm in ("t", "f")
        },
        "run_ids": [record["run_id"] for record in selected],
    }


def s600_catalog(gate_h: dict, long_reader: dict) -> tuple[list[dict], dict]:
    records = []
    for state in gate_h["records"]:
        par = state["par"]
        reading = long_reader[par]
        events = state["events"]
        gap_starts = [event["t_ut"] for event in events if event["kind"] == "gap_start"]
        final = state["summary"]["final"]
        p4 = reading["p4_biografia"]
        if final["connection"] == "DOMINANT" and final["vitality"] == "SOURCE_FADED":
            kind = "SPECTRAL_TAIL_ON_FADING_SOURCE"
        elif final["connection"] == "RELEASED" and p4["t_pico"] > max(gap_starts, default=-1):
            kind = "MEMORY_PEAK_AFTER_LAST_CHANNEL"
        else:
            kind = "OTHER_LONG_RESIDUAL"
        records.append({
            "par": par, "leader_family": f"C~{round(float(reading['C_fit']), 2)}",
            "residual_kind": kind,
            "channel_present_fraction": state["summary"]["channel_present_fraction"],
            "n_release": state["summary"]["n_release"],
            "n_link_recapture": state["summary"]["n_recapture"],
            "n_mode_recapture": state["summary"]["n_mode_recapture"],
            "first_source_faded_ut": state["summary"]["first_source_faded_ut"],
            "final_connection": final["connection"],
            "final_vitality": final["vitality"],
            "last_gap_start_ut": max(gap_starts) if gap_starts else None,
            "b_S1_peak_ut": p4["t_pico"], "b_S1_peak": p4["pico"],
            "b_S1_peak_minus_last_gap_start_ut": (
                float(p4["t_pico"] - max(gap_starts)) if gap_starts else None),
        })
    families = {}
    for family in sorted({record["leader_family"] for record in records}):
        group = [record for record in records if record["leader_family"] == family]
        fades = [record["first_source_faded_ut"] for record in group]
        families[family] = {
            "pars": [record["par"] for record in group],
            "source_faded_spread_ut": float(max(fades) - min(fades)),
            "source_faded_range_ut": [float(min(fades)), float(max(fades))],
            "release_counts": {record["par"]: record["n_release"] for record in group},
            "coverage": {record["par"]: record["channel_present_fraction"]
                         for record in group},
            "final_connections": sorted({record["final_connection"] for record in group}),
        }
    return records, families


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-g", required=True, type=Path)
    parser.add_argument("--gate-h", required=True, type=Path)
    parser.add_argument("--long-reader", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    paths = {name: path.expanduser().resolve() for name, path in (
        ("gate_g", args.gate_g), ("gate_h", args.gate_h),
        ("long_reader", args.long_reader),
    )}
    gate_g = json.loads(paths["gate_g"].read_text())
    gate_h = json.loads(paths["gate_h"].read_text())
    long_reader = json.loads(paths["long_reader"].read_text())
    records = gate_g["records"]
    vectors = np.stack([feature_vector(record) for record in records])
    scaled = robust_scaled(vectors)
    by_pair = {}
    for record in records:
        by_pair.setdefault(record["pair_id"], {})[record["arm"]] = record

    residuals = []
    for index, record in enumerate(records):
        kind = residual_kind(record)
        if kind is None:
            continue
        other = by_pair[record["pair_id"]]["f" if record["arm"] == "t" else "t"]
        residuals.append({
            "kind": kind, "run_id": record["run_id"], "pair_id": record["pair_id"],
            "arm": record["arm"], "category": record["category"],
            "coordinate_health": record["coordinate_health"],
            "early": record["early"], "dynamic": dynamic_summary(record),
            "paired_other": {
                "run_id": other["run_id"], "arm": other["arm"],
                "coordinate_health": other["coordinate_health"],
                "early_Q_active": other["early"]["active20"]["Q"],
                "joint_flat": other["early"]["active20"]["joint_flat"],
                "delta_target_minus_other": {
                    key: float(record["early"][key] - other["early"][key])
                    for key in ("rho_pred_end20", "rho_observed_end20", "Q_rw_end20",
                                "S1_rw_end20", "S2_rw_end20", "primary_rw_end20",
                                "primary_dw_end20")
                },
            },
            "nearest_healthy_early": nearest(records, scaled, index, True),
            "nearest_unhealthy_early": nearest(records, scaled, index, False),
        })

    s600, leader_families = s600_catalog(gate_h, long_reader)
    result = {
        "_meta": {
            **{name: str(path) for name, path in paths.items()},
            **{f"{name}_sha256": sha256(path) for name, path in paths.items()},
            "policy": "exploratorio; sólo derivados existentes; no cambia Gate H",
        },
        "method": {
            "residual": "early_Q_active XOR coordinate_health",
            "classification": {
                "early_fail": "intermitencia; si no, deriva W8; si no, otro",
                "late_health": "joint_flat; si no, ocupación observada; si no, nucleación tardía",
            },
            "nearest_neighbors": {
                "features": list(EARLY_FEATURES),
                "scaling": "mediana/IQR poblacional, fallback SD",
                "distance": "euclídea; sólo información disponible a t=20",
            },
        },
        "summary": {
            "n_gate_g": len(records), "n_residuals": len(residuals),
            "residual_kinds": {
                kind: sum(record["kind"] == kind for record in residuals)
                for kind in sorted({record["kind"] for record in residuals})
            },
            "cross_tabs": {
                "early_Q_active": crosstab(records, lambda r: r["early"]["active20"]["Q"]),
                "early_Q_active_and_joint_flat": crosstab(
                    records, lambda r: r["early"]["active20"]["Q"]
                    and r["early"]["active20"]["joint_flat"]),
                "early_Q_active_nonflat_no_joint": crosstab(
                    records, lambda r: r["early"]["active20"]["Q"]
                    and not r["early"]["active20"]["joint_flat"]),
                "early_Q_inactive_joint_flat": crosstab(
                    records, lambda r: not r["early"]["active20"]["Q"]
                    and r["early"]["active20"]["joint_flat"]),
                "early_Q_inactive_observed_nonflat": crosstab(
                    records, lambda r: not r["early"]["active20"]["Q"]
                    and r["early"]["active20"]["rho_observed_occupation"]
                    and not r["early"]["active20"]["joint_flat"]),
                "early_Q_inactive_no_observed_line": crosstab(
                    records, lambda r: not r["early"]["active20"]["Q"]
                    and not r["early"]["active20"]["rho_observed_occupation"]),
                # Firmas vistas después de abrir los residuos: se reportan como
                # descripción post hoc, nunca como reglas de selección.
                "posthoc_sliding_signature": crosstab(
                    records, lambda r: r["early"]["active20"]["Q"]
                    and not r["early"]["active20"]["joint_flat"]
                    and not r["early"]["active20"]["rho_pred_occupation"]
                    and r["early"]["active20"]["S1"]
                    and r["early"]["active20"]["S2"]
                    and not r["early"]["active20"]["primary"]),
                "posthoc_intermittent_signature": crosstab(
                    records, lambda r: r["early"]["active20"]["Q"]
                    and not r["early"]["active20"]["joint_flat"]
                    and r["early"]["active20"]["rho_pred_occupation"]
                    and not r["early"]["active20"]["S1"]
                    and r["early"]["active20"]["S2"]
                    and not r["early"]["active20"]["primary"]),
            },
            "leader_families_s600": leader_families,
        },
        "residuals_gate_g": residuals,
        "residuals_s600": s600,
        "warnings": [
            "Análisis exploratorio post hoc: las clases nombran patrones, no prueban mecanismos.",
            "El outcome Gate G es fase a 60, no supervivencia energética.",
            "Nearest-neighbor describe semejanza temprana; no es un clasificador validado.",
            "Familias s600 tienen n=2: la separación líder/receptor es una pista, no inferencia.",
        ],
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"[link-grumo] Gate I: {len(residuals)} residuos Gate G, {len(s600)} s600")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
