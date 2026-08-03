#!/usr/bin/env python3
"""Gate F2: evalúa rutas, releases y orden temporal sobre Gate F1, sin releer films."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from baseline_census import safe_output
from gate_f_timeline import Q_SUSTAIN_UT, runs


FINAL_END_MIN = 58.9
EARLY_CONFIRM_MAX = 20.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_observed_occupation(film: dict) -> None:
    """Deriva rho observado de amplitudes ya guardadas; compatible con F1 inicial."""
    for channel in film["Q_channels"].values():
        records = channel["series"]
        for record in records:
            rho = float(record["A_line_follower"]
                        / max(float(record["A_competitor_follower"]), 1e-300))
            record["rho_observed"] = rho
            record["occupation_observed"] = bool(rho > 1.0)
        episodes = runs(records, "occupation_observed", Q_SUSTAIN_UT, continuity=True)
        channel["events"]["occupation_observed"] = {
            "first": episodes[0] if episodes else None, "episodes": episodes,
        }


def channel_episodes(film: dict, key: str) -> list[dict]:
    return [episode for channel in film["Q_channels"].values()
            for episode in channel["events"][key]["episodes"]]


def channel_final(film: dict, key: str) -> bool:
    return any(episode["last_window_end_ut"] >= FINAL_END_MIN
               for episode in channel_episodes(film, key))


def channel_first(film: dict, key: str) -> dict | None:
    candidates = []
    for direction, channel in film["Q_channels"].items():
        event = channel["events"][key]["first"]
        if event is not None:
            candidates.append({"direction": direction, **event})
    return min(candidates, key=lambda event: event["confirmation_end_ut"]) \
        if candidates else None


def layer_final(film: dict, layer: str) -> bool:
    return any(episode["last_window_end_ut"] >= FINAL_END_MIN
               for episode in film["layers"][layer]["events"]["episodes"])


def primary_final(film: dict) -> bool:
    return any(episode["last_window_end_ut"] >= FINAL_END_MIN
               for episode in film["primary_Q"]["events"]["episodes"])


def early(event: dict | None) -> bool:
    return event is not None and event["confirmation_end_ut"] <= EARLY_CONFIRM_MAX


def endpoint_features(film: dict) -> dict:
    pred = channel_final(film, "occupation")
    observed = channel_final(film, "occupation_observed")
    complex_flat = channel_final(film, "complex_capture_flat")
    joint_flat = channel_final(film, "joint_flat")
    s1 = layer_final(film, "S1")
    s2 = layer_final(film, "S2")
    q_layer = layer_final(film, "Q")
    primary = primary_final(film)
    if pred and s1 and joint_flat:
        route = "linear_selected"
    elif pred and s1:
        route = "selected_nonflat_or_nonlinear"
    elif complex_flat and not pred:
        route = "passive_linear_response_below_selection"
    elif observed and not pred:
        route = "observed_cross_response_without_cold_selection"
    else:
        route = "no_persistent_selected_channel"
    return {
        "predicted_occupation": pred, "observed_occupation": observed,
        "complex_capture_flat": complex_flat, "joint_flat": joint_flat,
        "Q_layer_capture": q_layer, "S1_capture": s1, "S2_capture": s2,
        "primary_close_local": primary,
        "candidate_dynamic_link": bool(pred and s1),
        "route": route,
    }


def early_features(film: dict) -> dict:
    return {
        "predicted_occupation": early(channel_first(film, "occupation")),
        "observed_occupation": early(channel_first(film, "occupation_observed")),
        "complex_capture_flat": early(channel_first(film, "complex_capture_flat")),
        "joint_flat": early(channel_first(film, "joint_flat")),
        "S1": early(film["summary"]["first_S1"]),
        "S2": early(film["summary"]["first_S2"]),
    }


def count_table(records: list[dict], selector) -> dict:
    yes = [record for record in records if selector(record)]
    no = [record for record in records if not selector(record)]
    return {
        "yes": {"n": len(yes), "health60": sum(record["health60"] for record in yes)},
        "no": {"n": len(no), "health60": sum(record["health60"] for record in no)},
    }


def order_relation(first: dict | None, second: dict | None) -> str:
    if first is None or second is None:
        return "missing"
    if first["confirmation_end_ut"] < second["support_start_ut"]:
        return "first_definitely_before"
    if second["confirmation_end_ut"] < first["support_start_ut"]:
        return "second_definitely_before"
    return "supports_overlap"


def relation_counts(relations: list[str]) -> dict:
    return {name: relations.count(name) for name in (
        "first_definitely_before", "second_definitely_before", "supports_overlap",
        "missing")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    timeline_path = args.timeline.expanduser().resolve()
    timeline = json.loads(timeline_path.read_text())
    records = []
    for film in timeline["films"]:
        install_observed_occupation(film)
        endpoint = endpoint_features(film)
        early20 = early_features(film)
        records.append({
            "pair_id": film["pair_id"], "run_id": film["run_id"],
            "role": film["role"], "arm": film["arm"],
            "health60": film["health60"], "outcome60": film["outcome60"],
            "endpoint": endpoint, "early20": early20,
            "events": {
                "Q_joint_flat": channel_first(film, "joint_flat"),
                "Q_occupation": channel_first(film, "occupation"),
                "Q_occupation_observed": channel_first(film, "occupation_observed"),
                "S1": film["summary"]["first_S1"],
                "S2": film["summary"]["first_S2"],
                "primary": film["summary"]["first_primary_close"],
            },
            "release_counts": {
                "Q_predicted_occupation": sum(
                    episode["last_window_end_ut"] < FINAL_END_MIN
                    for episode in channel_episodes(film, "occupation")),
                "Q_joint_flat": sum(
                    episode["last_window_end_ut"] < FINAL_END_MIN
                    for episode in channel_episodes(film, "joint_flat")),
                "S1": sum(episode["last_window_end_ut"] < FINAL_END_MIN
                          for episode in film["layers"]["S1"]["events"]["episodes"]),
                "S2": sum(episode["last_window_end_ut"] < FINAL_END_MIN
                          for episode in film["layers"]["S2"]["events"]["episodes"]),
            },
        })

    features = (
        "predicted_occupation", "observed_occupation", "complex_capture_flat",
        "joint_flat", "Q_layer_capture", "S1_capture", "S2_capture",
        "primary_close_local", "candidate_dynamic_link")
    endpoint_tables = {
        feature: count_table(records, lambda record, name=feature:
                             record["endpoint"][name]) for feature in features}
    early_names = ("predicted_occupation", "observed_occupation",
                   "complex_capture_flat", "joint_flat", "S1", "S2")
    early_tables = {
        feature: count_table(records, lambda record, name=feature:
                             record["early20"][name]) for feature in early_names}
    routes = {}
    for record in records:
        route = record["endpoint"]["route"]
        routes.setdefault(route, {"n": 0, "health60": 0, "run_ids": []})
        routes[route]["n"] += 1
        routes[route]["health60"] += int(record["health60"])
        routes[route]["run_ids"].append(record["run_id"])

    transported_targets = [record for record in records
                           if record["role"] == "target" and record["arm"] == "t"]
    q_to_s2 = [order_relation(record["events"]["Q_joint_flat"], record["events"]["S2"])
               for record in transported_targets]
    s2_to_primary = [order_relation(record["events"]["S2"], record["events"]["primary"])
                     for record in transported_targets]
    deltas_q_s2 = [record["events"]["S2"]["confirmation_end_ut"]
                   - record["events"]["Q_joint_flat"]["confirmation_end_ut"]
                   for record in transported_targets
                   if record["events"]["S2"] is not None
                   and record["events"]["Q_joint_flat"] is not None]
    deltas_s2_primary = [record["events"]["S2"]["confirmation_end_ut"]
                         - record["events"]["primary"]["confirmation_end_ut"]
                         for record in transported_targets
                         if record["events"]["S2"] is not None
                         and record["events"]["primary"] is not None]

    by_pair = {}
    for record in records:
        by_pair.setdefault(record["pair_id"], {})[record["role"]] = record
    paired_discordant = []
    for pair_id, pair in by_pair.items():
        if pair["target"]["health60"] == pair["control"]["health60"]:
            continue
        paired_discordant.append({
            "pair_id": pair_id,
            "target_run_id": pair["target"]["run_id"],
            "control_run_id": pair["control"]["run_id"],
            "target_endpoint": pair["target"]["endpoint"],
            "control_endpoint": pair["control"]["endpoint"],
        })

    boundary = [record for record in records
                if not record["health60"] and record["outcome60"]["firme_60"]]
    result = {
        "_meta": {
            "timeline": str(timeline_path), "timeline_sha256": sha256(timeline_path),
            "policy": "sólo deriva señales ya extraídas; no relee worldlines",
        },
        "method": {
            "endpoint_active": f"episodio sostenido alcanza t_end>={FINAL_END_MIN}",
            "early": f"confirmación de episodio <= {EARLY_CONFIRM_MAX} u.t.",
            "observed_occupation": "A_line_follower/A_competitor>1 sostenido 2 u.t.",
            "candidate_dynamic_link": ("ocupación predicha persistente AND S1 persistente; "
                                       "candidato POST HOC, no umbral preregistrado"),
            "definite_order": "confirmación de A anterior al inicio de soporte de B",
        },
        "summary": {
            "n": len(records), "n_health60": sum(record["health60"] for record in records),
            "endpoint_tables": endpoint_tables, "early20_tables": early_tables,
            "routes": routes,
            "transported_target_chronology": {
                "n": len(transported_targets),
                "Q_joint_to_S2": relation_counts(q_to_s2),
                "S2_to_primary": relation_counts(s2_to_primary),
                "median_confirmation_delta_S2_minus_Qjoint_ut": (
                    float(np.median(deltas_q_s2)) if deltas_q_s2 else None),
                "median_confirmation_delta_S2_minus_primary_ut": (
                    float(np.median(deltas_s2_primary)) if deltas_s2_primary else None),
            },
            "paired_discordant": {
                "n": len(paired_discordant),
                "target_predicted_occupation_final": sum(
                    pair["target_endpoint"]["predicted_occupation"]
                    for pair in paired_discordant),
                "control_predicted_occupation_final": sum(
                    pair["control_endpoint"]["predicted_occupation"]
                    for pair in paired_discordant),
                "target_S1_final": sum(pair["target_endpoint"]["S1_capture"]
                                       for pair in paired_discordant),
                "control_S1_final": sum(pair["control_endpoint"]["S1_capture"]
                                        for pair in paired_discordant),
            },
            "phase_firm_but_health_false": [record["run_id"] for record in boundary],
        },
        "warnings": [
            "Banco pequeño, elegido por los positivos Gate E: no estima prevalencia ni p citable.",
            "candidate_dynamic_link fue visto y formulado en este mismo banco.",
            "Persistir hasta 60 u.t. sigue sin equivaler a supervivencia asintótica.",
            "S1/S2 son locks de capa, no intervenciones causales.",
            "El outcome Gate E promedia dw en [50,60]; puede castigar una captura dentro de esa ventana.",
        ],
        "paired_discordant": paired_discordant,
        "records": records,
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"[link-grumo] Gate F2: {len(records)} films, {len(routes)} rutas descriptivas")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
