#!/usr/bin/env python3
"""Gate G2: early[0,20] -> late[50,60] y transiciones Q hasta 60 desde views locales."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from baseline_census import auc, safe_output
from gate_f_timeline import LAYER_SUSTAIN_UT, runs


STRIDE = 100
W_UT = 4.0
HOP_UT = 1.0
RW_THRESHOLD = 0.90
EARLY_ACTIVE_END = 19.9
FINAL_ACTIVE_END = 59.9


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def channel_final(film: dict, key: str) -> bool:
    return any(episode["last_window_end_ut"] >= EARLY_ACTIVE_END
               for channel in film["Q_channels"].values()
               for episode in channel["events"][key]["episodes"])


def layer_final(film: dict, layer: str) -> bool:
    return any(episode["last_window_end_ut"] >= EARLY_ACTIVE_END
               for episode in film["layers"][layer]["events"]["episodes"])


def primary_final(film: dict) -> bool:
    return any(episode["last_window_end_ut"] >= EARLY_ACTIVE_END
               for episode in film["primary_Q"]["events"]["episodes"])


def early_metrics(film: dict) -> dict:
    direction_last = [channel["series"][-1] for channel in film["Q_channels"].values()]
    r_errors = [record["R_complex_error"] for record in direction_last
                if record["R_complex_error"] is not None]
    return {
        "rho_pred_end20": max(record["rho_pred"] for record in direction_last),
        "rho_observed_end20": max(record["rho_observed"] for record in direction_last),
        "min_R_complex_error_end20": min(r_errors) if r_errors else None,
        "Q_rw_end20": film["layers"]["Q"]["series"][-1]["rw_local_W4"],
        "S1_rw_end20": film["layers"]["S1"]["series"][-1]["rw_local_W4"],
        "S2_rw_end20": film["layers"]["S2"]["series"][-1]["rw_local_W4"],
        "primary_rw_end20": film["primary_Q"]["series"][-1]["rw_Q_local_W8"],
        "primary_dw_end20": film["primary_Q"]["series"][-1]["dw_Q_local_W8"],
        "active20": {
            "rho_pred_occupation": channel_final(film, "occupation"),
            "rho_observed_occupation": channel_final(film, "occupation_observed"),
            "complex_capture_flat": channel_final(film, "complex_capture_flat"),
            "joint_flat": channel_final(film, "joint_flat"),
            "Q": layer_final(film, "Q"), "S1": layer_final(film, "S1"),
            "S2": layer_final(film, "S2"), "primary": primary_final(film),
        },
    }


def theta_window_metrics(theta: np.ndarray, dt: float) -> tuple[float, float]:
    phases = []
    for node in (0, 1):
        raw = theta[:, node]
        unwrapped = np.unwrap(raw)
        omega = abs(float(np.mean(np.gradient(unwrapped, dt))))
        phases.append(np.unwrap(np.arctan2(
            np.sin(raw) / max(omega, 1e-9), np.cos(raw))))
    dphi = phases[0] - phases[1]
    rw = float(abs(np.mean(np.exp(1j * dphi))))
    slope = float(abs(np.polyfit(np.arange(len(dphi)) * dt, dphi, 1)[0]))
    return rw, slope


def full_q_timeline(view: Path) -> dict:
    manifest = json.loads(view.with_name("manifest.json").read_text())
    dt_full = float(manifest["dt"])
    with np.load(view, allow_pickle=False) as data:
        ticks_all = np.asarray(data["ticks"])
        select = (ticks_all % STRIDE == 0) & (ticks_all * dt_full <= 60.0 + dt_full)
        ticks = ticks_all[select]
        theta = np.asarray(data["theta"])[select]
    dt = dt_full * STRIDE
    n_window = int(round(W_UT / dt))
    n_hop = int(round(HOP_UT / dt))
    starts = np.arange(0, len(theta) - n_window + 1, n_hop, dtype=int)
    records = []
    for start in starts:
        stop = start + n_window
        rw, slope = theta_window_metrics(theta[start:stop], dt)
        records.append({
            "t_start_ut": float(ticks[start] * dt_full),
            "t_end_ut": float(ticks[stop - 1] * dt_full),
            "rw_Q_local_W4": rw, "corrected_drift_local_W4": slope,
            "capture": bool(rw >= RW_THRESHOLD),
        })
    episodes = runs(records, "capture", LAYER_SUSTAIN_UT)
    return {"series": records, "episodes": episodes,
            "first": episodes[0] if episodes else None}


def metric_summary(records: list[dict], key: str, smaller: bool = False) -> dict:
    positive = [float(record["early"][key]) for record in records
                if record["coordinate_health"] and record["early"][key] is not None]
    negative = [float(record["early"][key]) for record in records
                if not record["coordinate_health"] and record["early"][key] is not None]
    score = auc(positive, negative)
    if score is not None and smaller:
        score = 1.0 - score
    return {
        "n_positive": len(positive), "n_negative": len(negative),
        "median_positive": float(np.median(positive)) if positive else None,
        "median_negative": float(np.median(negative)) if negative else None,
        "auc_declared_direction": score, "direction": "smaller" if smaller else "larger",
    }


def threshold_table(records: list[dict], key: str) -> dict:
    selected = [record for record in records if record["early"]["active20"][key]]
    rejected = [record for record in records if not record["early"]["active20"][key]]
    return {
        "active": {"n": len(selected),
                   "coordinate_health": sum(record["coordinate_health"]
                                            for record in selected)},
        "inactive": {"n": len(rejected),
                     "coordinate_health": sum(record["coordinate_health"]
                                              for record in rejected)},
    }


def paired_ranking(records: list[dict], key: str, smaller: bool = False) -> dict:
    pairs: dict[str, dict[str, dict]] = {}
    for record in records:
        pairs.setdefault(record["pair_id"], {})[record["arm"]] = record
    discordant = [pair for pair in pairs.values()
                  if pair["t"]["coordinate_health"] != pair["f"]["coordinate_health"]]
    win = loss = tie = 0
    ratios = []
    for pair in discordant:
        healthy = pair["t"] if pair["t"]["coordinate_health"] else pair["f"]
        unhealthy = pair["f"] if healthy is pair["t"] else pair["t"]
        a = healthy["early"][key]
        b = unhealthy["early"][key]
        if a is None or b is None:
            continue
        left, right = (-a, -b) if smaller else (a, b)
        if left > right:
            win += 1
        elif left < right:
            loss += 1
        else:
            tie += 1
        ratios.append(float(a / max(abs(float(b)), 1e-300)))
    return {"n": win + loss + tie, "healthy_better": win, "unhealthy_better": loss,
            "ties": tie, "median_healthy_over_unhealthy": float(np.median(ratios))
            if ratios else None}


def paired_active(records: list[dict], key: str) -> dict:
    pairs: dict[str, dict[str, dict]] = {}
    for record in records:
        pairs.setdefault(record["pair_id"], {})[record["arm"]] = record
    values = []
    for pair in pairs.values():
        if pair["t"]["coordinate_health"] == pair["f"]["coordinate_health"]:
            continue
        healthy = pair["t"] if pair["t"]["coordinate_health"] else pair["f"]
        unhealthy = pair["f"] if healthy is pair["t"] else pair["t"]
        values.append((healthy["early"]["active20"][key],
                       unhealthy["early"]["active20"][key]))
    return {
        "n": len(values),
        "healthy_only": sum(a and not b for a, b in values),
        "unhealthy_only": sum(b and not a for a, b in values),
        "both": sum(a and b for a, b in values),
        "neither": sum(not a and not b for a, b in values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--early", required=True, type=Path)
    parser.add_argument("--health", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    early_path = args.early.expanduser().resolve()
    health_path = args.health.expanduser().resolve()
    early_data = json.loads(early_path.read_text())
    health_data = json.loads(health_path.read_text())
    health_by_id = {record["run_id"]: record for record in health_data["records"]}
    records = []
    max_replication_error = 0.0
    for index, film in enumerate(early_data["films"], 1):
        early = early_metrics(film)
        health = health_by_id[film["run_id"]]
        full_q = full_q_timeline(Path(health["view"]))
        early_q_series = film["layers"]["Q"]["series"]
        overlap = min(len(early_q_series), len(full_q["series"]))
        error = max(abs(early_q_series[i]["rw_local_W4"]
                        - full_q["series"][i]["rw_Q_local_W4"])
                    for i in range(overlap))
        max_replication_error = max(max_replication_error, error)
        records.append({
            "pair_id": film["pair_id"], "category": film["category"],
            "run_id": film["run_id"], "arm": film["arm"],
            "coordinate_health": film["coordinate_health"],
            "early": early, "full_Q": full_q,
            "early_events": {
                "Q_occupation": film["summary"]["first_Q_occupation"],
                "Q_joint_flat": film["summary"]["first_Q_joint_flat"],
                "S1": film["summary"]["first_S1"],
                "S2": film["summary"]["first_S2"],
                "primary": film["summary"]["first_primary_close"],
            },
            "outcome60": film["outcome60"],
        })
        if index % 10 == 0 or index == len(early_data["films"]):
            print(f"[link-grumo] G2 {index}/{len(early_data['films'])}", flush=True)
    if max_replication_error > 1e-12:
        raise RuntimeError(f"Q de view no replica raw temprano: {max_replication_error}")

    continuous = {
        "rho_pred_end20": False, "rho_observed_end20": False,
        "min_R_complex_error_end20": True, "Q_rw_end20": False,
        "S1_rw_end20": False, "S2_rw_end20": False,
        "primary_rw_end20": False, "primary_dw_end20": True,
    }
    active_keys = ("rho_pred_occupation", "rho_observed_occupation",
                   "complex_capture_flat", "joint_flat", "Q", "S1", "S2", "primary")
    transition = {"active20_health": [], "active20_fail": [],
                  "inactive20_health": [], "inactive20_fail": []}
    for record in records:
        active20 = record["early"]["active20"]["Q"]
        key = ("active20_" if active20 else "inactive20_") + (
            "health" if record["coordinate_health"] else "fail")
        transition[key].append(record)

    def first_confirmation(record: dict) -> float | None:
        first = record["full_Q"]["first"]
        return first["confirmation_end_ut"] if first else None

    def first_release(record: dict) -> float | None:
        episodes = record["full_Q"]["episodes"]
        ended = [episode["last_window_end_ut"] for episode in episodes
                 if episode["last_window_end_ut"] < FINAL_ACTIVE_END]
        return ended[0] if ended else None

    def chronology(first_key: str, second_key: str) -> dict:
        selected = []
        for record in records:
            if not record["coordinate_health"]:
                continue
            first = record["early_events"][first_key]
            second = record["early_events"][second_key]
            if first is None or second is None:
                continue
            delta = first["confirmation_end_ut"] - second["confirmation_end_ut"]
            if first["confirmation_end_ut"] < second["support_start_ut"]:
                relation = "first_definitely_before"
            elif second["confirmation_end_ut"] < first["support_start_ut"]:
                relation = "second_definitely_before"
            else:
                relation = "supports_overlap"
            selected.append((delta, relation))
        return {
            "n_both": len(selected),
            "confirmation_first_before": sum(delta < 0 for delta, _ in selected),
            "confirmation_within_2ut": sum(abs(delta) <= 2 for delta, _ in selected),
            "confirmation_first_after_gt2": sum(delta > 2 for delta, _ in selected),
            "median_confirmation_delta_first_minus_second_ut": (
                float(np.median([delta for delta, _ in selected])) if selected else None),
            "first_definitely_before": sum(relation == "first_definitely_before"
                                           for _, relation in selected),
            "second_definitely_before": sum(relation == "second_definitely_before"
                                            for _, relation in selected),
            "supports_overlap": sum(relation == "supports_overlap"
                                    for _, relation in selected),
        }

    result = {
        "_meta": {
            "early": str(early_path), "early_sha256": sha256(early_path),
            "health": str(health_path), "health_sha256": sha256(health_path),
            "policy": "G2 sólo lee views locales; no relee worldlines externas",
        },
        "method": {
            "predictor": "estado de la última ventana disponible antes de t=20",
            "outcome": "coordinate_health [50,60] sellado por Gate F3",
            "full_Q": "W4/hop1 local-causal desde view Q hasta 60; replica raw [0,20]",
            "interpretation": "case-control apareado; rankings, no prevalencia",
        },
        "summary": {
            "n": len(records), "n_health": sum(record["coordinate_health"] for record in records),
            "continuous": {key: metric_summary(records, key, smaller)
                           for key, smaller in continuous.items()},
            "continuous_by_arm": {
                arm: {key: metric_summary(
                    [record for record in records if record["arm"] == arm], key, smaller)
                      for key, smaller in continuous.items()}
                for arm in ("t", "f")
            },
            "paired_ranking": {key: paired_ranking(records, key, smaller)
                               for key, smaller in continuous.items()},
            "active20": {key: threshold_table(records, key) for key in active_keys},
            "paired_active20": {key: paired_active(records, key) for key in active_keys},
            "chronology_healthy": {
                "Q_occupation_to_primary": chronology("Q_occupation", "primary"),
                "S1_to_primary": chronology("S1", "primary"),
                "S2_to_primary": chronology("S2", "primary"),
            },
            "Q_transitions": {
                key: {
                    "n": len(group), "run_ids": [record["run_id"] for record in group],
                    "median_first_confirmation_ut": float(np.median([
                        value for value in (first_confirmation(record) for record in group)
                        if value is not None])) if any(first_confirmation(record) is not None
                                                   for record in group) else None,
                    "first_release_ut": {record["run_id"]: first_release(record)
                                         for record in group},
                } for key, group in transition.items()
            },
            "Q_view_replication": {"max_rw_abs_error_0_20": max_replication_error},
        },
        "warnings": [
            "Banco balanceado por outcome: AUC/rates son descriptivos, no prevalencia poblacional.",
            "El estado a t=20 puede liberar después o un link ausente puede capturar más tarde.",
            "S1/S2 no fueron intervenidos; orden temporal no prueba causalidad.",
            "La ruta no plana invalida usar chi fría puntual como ley universal.",
        ],
        "records": records,
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"[link-grumo] Gate G2: {len(records)} films evaluados")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
