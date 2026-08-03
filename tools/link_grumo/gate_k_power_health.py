#!/usr/bin/env python3
"""Gate K: contrasta potencia temprana con salud tardía ya sellada.

Sólo lee las views locales de Gate J y los resultados locales de Gates F/G. No relee
worldlines, no redefine salud y no modifica fitness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from baseline_census import auc, safe_output
from study07.instruments import api


PRIMARY_INTERVAL = (2.0, 20.0)
INTERVALS = {
    "early_2_10": (2.0, 10.0),
    "early_2_20": PRIMARY_INTERVAL,
    "early_10_20": (10.0, 20.0),
    "maturation_20_40": (20.0, 40.0),
}
PRIMARY_METRICS = (
    "exchange_rate", "exchange_efficiency", "opposed_fraction", "force2",
)
DIAGNOSTIC_METRICS = (
    "net_power", "dissipation_rate", "injection_rate",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def power_features(arrays: dict, lo: float, hi: float) -> dict:
    """Resume potencia sobre cajas completas cuyo extremo causal cae en [lo, hi]."""
    t = np.asarray(arrays["t_force_ut"], dtype=float)
    complete = np.asarray(arrays["window_complete"], dtype=bool)
    select = complete & (t >= lo - 1e-10) & (t <= hi + 1e-10)
    if not np.any(select):
        raise ValueError(f"sin cajas completas en [{lo},{hi}]")
    p = np.asarray(arrays["p_node_mean"], dtype=float)[select]
    force = np.asarray(arrays["force_rms"], dtype=float)[select]
    if p.ndim != 2 or p.shape[1] != 2 or force.shape != p.shape:
        raise ValueError("Gate K exige exactamente dos extremos identificables")
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(force)):
        raise ValueError("potencia/fuerza no finita")
    incoming = np.maximum(p, 0.0).sum(axis=1)
    outgoing = np.maximum(-p, 0.0).sum(axis=1)
    exchange = np.minimum(incoming, outgoing)
    net = p.sum(axis=1)
    force2 = float(np.mean(np.square(force).sum(axis=1)))
    exchange_rate = float(np.mean(exchange))
    return {
        "interval_ut": [float(lo), float(hi)],
        "n_windows": int(np.sum(select)),
        "first_box_end_ut": float(t[select][0]),
        "last_box_end_ut": float(t[select][-1]),
        "exchange_rate": exchange_rate,
        "exchange_efficiency": (
            float(exchange_rate / force2) if force2 > 0.0 else None),
        "opposed_fraction": float(np.mean((p[:, 0] * p[:, 1]) < 0.0)),
        "net_power": float(np.mean(net)),
        "dissipation_rate": float(np.mean(np.maximum(-net, 0.0))),
        "injection_rate": float(np.mean(np.maximum(net, 0.0))),
        "force2": force2,
    }


def energetic_support_audit(arrays: dict) -> dict:
    """Separa devolución instantánea de energía y balance de caja suavizado."""
    instant = np.asarray(arrays["p_node_instant"], dtype=float).sum(axis=1)
    complete = np.asarray(arrays["window_complete"], dtype=bool)
    smoothed = np.asarray(arrays["p_node_mean"], dtype=float)[complete].sum(axis=1)
    return {
        "n_instant_samples": int(instant.size),
        "n_instant_net_positive": int(np.sum(instant > 0.0)),
        "instant_net_min": float(np.min(instant)),
        "instant_net_max": float(np.max(instant)),
        "n_complete_boxes": int(smoothed.size),
        "n_smoothed_net_positive": int(np.sum(smoothed > 0.0)),
        "smoothed_net_min": float(np.min(smoothed)),
        "smoothed_net_max": float(np.max(smoothed)),
    }


def index_power_views(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in root.rglob("manifest.json"):
        try:
            manifest = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("instrument_id") != "link_power":
            continue
        view_hash = manifest.get("view_hash")
        if not view_hash:
            continue
        if view_hash in result and result[view_hash] != path.parent:
            raise RuntimeError(f"view_hash duplicado: {view_hash}")
        result[str(view_hash)] = path.parent
    return result


def average_ranks(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        stop = start + 1
        while stop < len(values) and values[order[stop]] == values[order[start]]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * (start + stop - 1) + 1.0
        start = stop
    return ranks


def metric_summary(records: list[dict], metric: str, outcome: str) -> dict:
    positive = [float(row["power"]["early_2_20"][metric]) for row in records
                if row[outcome] and row["power"]["early_2_20"][metric] is not None]
    negative = [float(row["power"]["early_2_20"][metric]) for row in records
                if not row[outcome] and row["power"]["early_2_20"][metric] is not None]
    return {
        "n_positive": len(positive), "n_negative": len(negative),
        "median_positive": float(np.median(positive)) if positive else None,
        "median_negative": float(np.median(negative)) if negative else None,
        "auc_larger": auc(positive, negative),
    }


def paired_ranking(records: list[dict], metric: str, outcome: str,
                   interval: str = "early_2_20") -> dict:
    pairs: dict[str, dict[str, dict]] = {}
    for row in records:
        pairs.setdefault(row["pair"], {})[row["arm"]] = row
    wins = losses = ties = skipped = 0
    differences = []
    details = []
    by_healthy_arm = {arm: {"n": 0, "healthy_better": 0,
                            "unhealthy_better": 0, "ties": 0,
                            "differences": []}
                      for arm in ("t", "f")}
    for pair_id, pair in sorted(pairs.items()):
        if set(pair) != {"t", "f"} or pair["t"][outcome] == pair["f"][outcome]:
            continue
        healthy = pair["t"] if pair["t"][outcome] else pair["f"]
        unhealthy = pair["f"] if healthy is pair["t"] else pair["t"]
        a = healthy["power"][interval][metric]
        b = unhealthy["power"][interval][metric]
        if a is None or b is None:
            skipped += 1
            continue
        difference = float(a - b)
        differences.append(difference)
        arm_summary = by_healthy_arm[healthy["arm"]]
        arm_summary["n"] += 1
        arm_summary["differences"].append(difference)
        if difference > 0:
            wins += 1
            arm_summary["healthy_better"] += 1
        elif difference < 0:
            losses += 1
            arm_summary["unhealthy_better"] += 1
        else:
            ties += 1
            arm_summary["ties"] += 1
        details.append({
            "pair": pair_id, "healthy_run_id": healthy["run_id"],
            "unhealthy_run_id": unhealthy["run_id"],
            "healthy_value": float(a), "unhealthy_value": float(b),
            "difference": difference,
        })
    by_arm_public = {}
    for arm, summary in by_healthy_arm.items():
        arm_differences = summary.pop("differences")
        by_arm_public[arm] = {
            **summary,
            "median_healthy_minus_unhealthy": (
                float(np.median(arm_differences)) if arm_differences else None),
        }
    return {
        "n": wins + losses + ties, "healthy_better": wins,
        "unhealthy_better": losses, "ties": ties, "skipped": skipped,
        "median_healthy_minus_unhealthy": (
            float(np.median(differences)) if differences else None),
        "by_healthy_arm": by_arm_public,
        "details": details,
    }


def residualized_exchange(records: list[dict], outcome: str) -> dict:
    exchange = np.array([row["power"]["early_2_20"]["exchange_rate"]
                         for row in records], dtype=float)
    force2 = np.array([row["power"]["early_2_20"]["force2"]
                       for row in records], dtype=float)
    arm = np.array([row["arm"] == "t" for row in records], dtype=float)
    log_dw = np.log1p([row["isolated_dw"] for row in records])
    y = average_ranks(exchange)
    y = (y - y.mean()) / max(y.std(), 1e-12)
    force_rank = average_ranks(force2)
    force_rank = (force_rank - force_rank.mean()) / max(force_rank.std(), 1e-12)
    log_dw = (log_dw - log_dw.mean()) / max(log_dw.std(), 1e-12)
    x = np.column_stack([np.ones(len(records)), arm, log_dw, force_rank])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ beta
    residual = y - fitted
    positive = [float(residual[i]) for i, row in enumerate(records) if row[outcome]]
    negative = [float(residual[i]) for i, row in enumerate(records) if not row[outcome]]
    return {
        "formula": "rank(exchange) ~ arm + log1p(dw) + rank(force2)",
        "coefficients": [float(value) for value in beta],
        "r2_without_outcome": float(1.0 - np.sum(np.square(residual))
                                    / max(np.sum(np.square(y - y.mean())), 1e-300)),
        "auc_residual_larger": auc(positive, negative),
        "median_residual_positive": float(np.median(positive)) if positive else None,
        "median_residual_negative": float(np.median(negative)) if negative else None,
    }


def _positive_scale(train: np.ndarray) -> float:
    positive = train[train > 0.0]
    return float(np.median(positive)) if positive.size else 1.0


def prepare_fold(train_rows: list[dict], test_rows: list[dict], fields: list[str]
                 ) -> tuple[np.ndarray, np.ndarray]:
    def raw(row: dict, field: str) -> float:
        early = row["early"]
        power = row["power"]["early_2_20"]
        values = {
            "arm": float(row["arm"] == "t"),
            "log_dw": float(np.log1p(row["isolated_dw"])),
            "primary_rw": float(early["primary_rw_end20"]),
            "log_rho": float(np.log1p(early["rho_observed_end20"])),
            "force2": float(power["force2"]),
            "exchange_rate": float(power["exchange_rate"]),
            "exchange_efficiency": float(power["exchange_efficiency"]),
            "opposed_fraction": float(power["opposed_fraction"]),
        }
        return values[field]

    train = np.array([[raw(row, field) for field in fields] for row in train_rows])
    test = np.array([[raw(row, field) for field in fields] for row in test_rows])
    open_scale = {"force2", "exchange_rate", "exchange_efficiency"}
    continuous = set(fields) - {"arm"}
    for index, field in enumerate(fields):
        if field in open_scale:
            scale = _positive_scale(train[:, index])
            train[:, index] = np.arcsinh(train[:, index] / scale)
            test[:, index] = np.arcsinh(test[:, index] / scale)
        if field in continuous:
            mean = float(train[:, index].mean())
            std = max(float(train[:, index].std()), 1e-12)
            train[:, index] = (train[:, index] - mean) / std
            test[:, index] = (test[:, index] - mean) / std
    return train, test


def fit_logistic_ridge(x: np.ndarray, y: np.ndarray, ridge: float = 1.0) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.zeros(design.shape[1], dtype=float)
    penalty = np.diag([0.0] + [ridge] * x.shape[1])
    for _ in range(100):
        eta = np.clip(design @ beta, -35.0, 35.0)
        prob = 1.0 / (1.0 + np.exp(-eta))
        weight = np.maximum(prob * (1.0 - prob), 1e-9)
        gradient = design.T @ (prob - y) + penalty @ beta
        hessian = design.T @ (weight[:, None] * design) + penalty
        step = np.linalg.solve(hessian, gradient)
        beta -= step
        if float(np.max(np.abs(step))) < 1e-10:
            break
    return beta


def predict_logistic(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    eta = np.clip(design @ beta, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-eta))


def lopo_models(records: list[dict]) -> dict:
    model_fields = {
        "M0_dynamic": ["arm", "log_dw", "primary_rw", "log_rho"],
        "M1_drive": ["arm", "log_dw", "primary_rw", "log_rho", "force2"],
        "M2_power": ["arm", "log_dw", "primary_rw", "log_rho", "force2",
                     "exchange_rate", "exchange_efficiency", "opposed_fraction"],
    }
    pairs = sorted({row["pair"] for row in records})
    output = {}
    predictions_by_model = {}
    for model, fields in model_fields.items():
        predictions: dict[str, float] = {}
        for pair in pairs:
            train_rows = [row for row in records if row["pair"] != pair]
            test_rows = [row for row in records if row["pair"] == pair]
            x_train, x_test = prepare_fold(train_rows, test_rows, fields)
            y_train = np.array([row["coordinate_health"] for row in train_rows],
                               dtype=float)
            beta = fit_logistic_ridge(x_train, y_train, ridge=1.0)
            probability = predict_logistic(beta, x_test)
            predictions.update({row["run_id"]: float(value)
                                for row, value in zip(test_rows, probability)})
        ordered = np.array([predictions[row["run_id"]] for row in records])
        truth = np.array([row["coordinate_health"] for row in records], dtype=bool)
        positive = ordered[truth].tolist()
        negative = ordered[~truth].tolist()
        clipped = np.clip(ordered, 1e-12, 1.0 - 1e-12)
        y = truth.astype(float)
        output[model] = {
            "fields": fields, "auc": auc(positive, negative),
            "log_loss": float(-np.mean(y * np.log(clipped)
                                       + (1.0 - y) * np.log(1.0 - clipped))),
        }
        predictions_by_model[model] = predictions
    output["increments"] = {
        "M1_minus_M0_auc": output["M1_drive"]["auc"] - output["M0_dynamic"]["auc"],
        "M1_vs_M0_log_loss_reduction": (output["M0_dynamic"]["log_loss"]
                                         - output["M1_drive"]["log_loss"]),
        "M2_minus_M1_auc": output["M2_power"]["auc"] - output["M1_drive"]["auc"],
        "M2_vs_M1_log_loss_reduction": (output["M1_drive"]["log_loss"]
                                         - output["M2_power"]["log_loss"]),
    }
    individual = []
    for row in records:
        truth = bool(row["coordinate_health"])
        p1 = predictions_by_model["M1_drive"][row["run_id"]]
        p2 = predictions_by_model["M2_power"][row["run_id"]]
        loss1 = -np.log(np.clip(p1 if truth else 1.0 - p1, 1e-12, 1.0))
        loss2 = -np.log(np.clip(p2 if truth else 1.0 - p2, 1e-12, 1.0))
        individual.append({
            "run_id": row["run_id"], "pair": row["pair"], "arm": row["arm"],
            "coordinate_health": truth, "p_M1": float(p1), "p_M2": float(p2),
            "log_loss_improvement_M2": float(loss1 - loss2),
            "classification_corrected": bool((p1 >= 0.5) != truth
                                               and (p2 >= 0.5) == truth),
            "classification_worsened": bool((p1 >= 0.5) == truth
                                              and (p2 >= 0.5) != truth),
        })
    individual.sort(key=lambda row: abs(row["log_loss_improvement_M2"]), reverse=True)
    output["individual"] = individual
    return output


def outliers(records: list[dict]) -> dict:
    exchange = np.array([row["power"]["early_2_20"]["exchange_rate"]
                         for row in records], dtype=float)
    force2 = np.array([row["power"]["early_2_20"]["force2"]
                       for row in records], dtype=float)
    q_exchange = np.quantile(exchange, [0.25, 0.75])
    q_force = np.quantile(force2, [0.25, 0.75])

    def compact(row: dict) -> dict:
        p = row["power"]["early_2_20"]
        return {
            "run_id": row["run_id"], "pair": row["pair"], "arm": row["arm"],
            "coordinate_health": row["coordinate_health"],
            "isolated_dw": row["isolated_dw"], "flagged": row["flagged"],
            "exchange_rate": p["exchange_rate"],
            "exchange_efficiency": p["exchange_efficiency"],
            "opposed_fraction": p["opposed_fraction"], "force2": p["force2"],
        }

    return {
        "quartiles": {"exchange": q_exchange.tolist(), "force2": q_force.tolist()},
        "healthy_low_exchange": [compact(row) for row in records
            if row["coordinate_health"]
            and row["power"]["early_2_20"]["exchange_rate"] <= q_exchange[0]],
        "unhealthy_high_exchange": [compact(row) for row in records
            if not row["coordinate_health"]
            and row["power"]["early_2_20"]["exchange_rate"] >= q_exchange[1]],
        "high_force_low_exchange": [compact(row) for row in records
            if row["power"]["early_2_20"]["force2"] >= q_force[1]
            and row["power"]["early_2_20"]["exchange_rate"] <= q_exchange[0]],
        "low_force_high_exchange": [compact(row) for row in records
            if row["power"]["early_2_20"]["force2"] <= q_force[0]
            and row["power"]["early_2_20"]["exchange_rate"] >= q_exchange[1]],
    }


def aggregate_support_audit(records: list[dict]) -> dict:
    audits = [row["energetic_support_audit"] for row in records]
    return {
        "n_films": len(audits),
        "films_with_instant_net_positive": sum(
            audit["n_instant_net_positive"] > 0 for audit in audits),
        "instant_samples": sum(audit["n_instant_samples"] for audit in audits),
        "instant_net_positive_samples": sum(
            audit["n_instant_net_positive"] for audit in audits),
        "instant_net_min": min(audit["instant_net_min"] for audit in audits),
        "instant_net_max": max(audit["instant_net_max"] for audit in audits),
        "complete_boxes": sum(audit["n_complete_boxes"] for audit in audits),
        "smoothed_net_positive_boxes": sum(
            audit["n_smoothed_net_positive"] for audit in audits),
        "smoothed_net_min": min(audit["smoothed_net_min"] for audit in audits),
        "smoothed_net_max": max(audit["smoothed_net_max"] for audit in audits),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--power-ledger", required=True, type=Path)
    parser.add_argument("--health", required=True, type=Path)
    parser.add_argument("--gate-g", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    power_path = args.power_ledger.expanduser().resolve()
    health_path = args.health.expanduser().resolve()
    gate_g_path = args.gate_g.expanduser().resolve()
    power_data = json.loads(power_path.read_text())
    health_data = json.loads(health_path.read_text())
    gate_g_data = json.loads(gate_g_path.read_text())

    views_root = Path(power_data["_meta"]["views_root"]).resolve()
    view_index = index_power_views(views_root)
    ledger = {row["run_id"]: row for row in power_data["records"]}
    if len(ledger) != len(power_data["records"]):
        raise RuntimeError("run_id duplicado en ledger de potencia")
    records = []
    for index, health in enumerate(health_data["records"], 1):
        source = ledger.get(health["run_id"])
        if source is None or source["status"] == "failed":
            raise RuntimeError(f"falta potencia para {health['run_id']}")
        if source["worldline_hash"] != health["worldline_hash"]:
            raise RuntimeError(f"worldline_hash no coincide: {health['run_id']}")
        if not source["single_edge_pair_identifiable"]:
            raise RuntimeError(f"film no identificable por edge: {health['run_id']}")
        view_path = view_index.get(source["view_hash_power"])
        if view_path is None:
            raise RuntimeError(f"view local no encontrada: {source['view_hash_power']}")
        view = api.load_view(view_path)
        if view["view_hash"] != source["view_hash_power"]:
            raise RuntimeError(f"view_hash no coincide: {health['run_id']}")
        manifest = view["manifest"]
        if manifest["worldline_hash"] != health["worldline_hash"]:
            raise RuntimeError(f"manifest/worldline no coincide: {health['run_id']}")
        power = {name: power_features(view["arrays"], *interval)
                 for name, interval in INTERVALS.items()}
        records.append({
            "run_id": health["run_id"], "pair": health["pair"],
            "arm": health["arm"], "isolated_dw": health["isolated_dw"],
            "coordinate_health": health["coordinate_health"],
            "raw_health": health["raw_health"], "firm": health["firm"],
            "flagged": health["flagged"],
            "worldline_hash": health["worldline_hash"],
            "view_hash_power": source["view_hash_power"], "power": power,
            "energetic_support_audit": energetic_support_audit(view["arrays"]),
        })
        if index % 50 == 0 or index == len(health_data["records"]):
            print(f"[link-grumo] Gate K {index}/{len(health_data['records'])}", flush=True)

    clean = [row for row in records if not row["flagged"]]
    by_run = {row["run_id"]: row for row in records}
    gate_g_records = []
    for source in gate_g_data["records"]:
        row = by_run[source["run_id"]]
        if row["coordinate_health"] != source["coordinate_health"]:
            raise RuntimeError(f"outcome Gate G no coincide: {source['run_id']}")
        gate_g_records.append({**row, "early": source["early"]})

    def outcome_block(selected: list[dict], outcome: str) -> dict:
        return {
            "n": len(selected), "n_positive": sum(row[outcome] for row in selected),
            "metrics": {metric: metric_summary(selected, metric, outcome)
                        for metric in PRIMARY_METRICS + DIAGNOSTIC_METRICS},
            "by_arm": {
                arm: {metric: metric_summary(
                    [row for row in selected if row["arm"] == arm], metric, outcome)
                      for metric in PRIMARY_METRICS}
                for arm in ("t", "f")
            },
            "paired": {metric: paired_ranking(selected, metric, outcome)
                       for metric in PRIMARY_METRICS},
            "residualized_exchange": residualized_exchange(selected, outcome),
        }

    interval_pairing = {
        name: {metric: paired_ranking(clean, metric, "coordinate_health", name)
               for metric in PRIMARY_METRICS}
        for name in INTERVALS
    }
    result = {
        "_meta": {
            "power_ledger": str(power_path), "power_ledger_sha256": sha256(power_path),
            "health": str(health_path), "health_sha256": sha256(health_path),
            "gate_g": str(gate_g_path), "gate_g_sha256": sha256(gate_g_path),
            "views_root": str(views_root),
            "policy": "sólo views/resultados locales; no relee worldlines ni cambia fitness",
        },
        "method": {
            "primary_predictor_interval_ut": list(PRIMARY_INTERVAL),
            "outcome_interval_ut": [50.0, 60.0],
            "intervals": {key: list(value) for key, value in INTERVALS.items()},
            "power_role_policy": "simétrica; no se elige emisor/receptor por outcome",
            "primary_coordinate": "exchange_rate",
            "paired_unit": "mismo par y semilla; transported vs fresh",
            "gate_g_model": "leave-one-pair-out logistic ridge lambda=1",
        },
        "summary": {
            "all_coordinate": outcome_block(records, "coordinate_health"),
            "clean_coordinate": outcome_block(clean, "coordinate_health"),
            "clean_raw": outcome_block(clean, "raw_health"),
            "clean_firm": outcome_block(clean, "firm"),
            "interval_pairing_clean_coordinate": interval_pairing,
            "gate_g_incremental": lopo_models(gate_g_records),
            "outliers_clean_coordinate": outliers(clean),
            "energetic_support_audit": aggregate_support_audit(records),
        },
        "warnings": [
            "Los AUC poblacionales son descriptivos: hay reutilización de nodos.",
            "Gate G es case-control seleccionado por outcome; sólo compara mecanismos.",
            "Potencia temprana asociada no implica causalidad ni autoriza meterla en fitness.",
            "exchange_efficiency siempre debe leerse junto con force2.",
        ],
        "records": records,
    }
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    tmp.replace(output)
    print(f"[link-grumo] salida: {output}", flush=True)


if __name__ == "__main__":
    main()
