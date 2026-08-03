from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


TOOLS = Path(__file__).resolve().parents[1] / "tools" / "link_grumo"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from gate_k_power_health import (average_ranks, energetic_support_audit,
                                 fit_logistic_ridge, paired_ranking, power_features,
                                 predict_logistic)


def _arrays(p: np.ndarray, force: np.ndarray | None = None) -> dict:
    n = len(p)
    return {
        "t_force_ut": np.arange(n, dtype=float),
        "window_complete": np.ones(n, dtype=bool),
        "p_node_mean": np.asarray(p, dtype=float),
        "p_node_instant": np.asarray(p, dtype=float),
        "force_rms": np.ones_like(p, dtype=float) if force is None else force,
    }


def test_power_features_are_symmetric_and_preserve_energy_signs():
    p = np.array([[3.0, -2.0], [-4.0, 1.0], [2.0, 1.0]])
    left = power_features(_arrays(p), 0.0, 2.0)
    right = power_features(_arrays(p[:, ::-1]), 0.0, 2.0)
    assert left == right
    assert left["exchange_rate"] == 1.0
    assert left["opposed_fraction"] == 2.0 / 3.0
    assert left["net_power"] == 1.0 / 3.0
    assert left["dissipation_rate"] == 1.0
    assert left["injection_rate"] == 4.0 / 3.0
    assert left["force2"] == 2.0
    assert left["exchange_efficiency"] == 0.5


def test_power_features_require_complete_causal_boxes():
    arrays = _arrays(np.array([[1.0, -1.0], [2.0, -2.0]]))
    arrays["window_complete"][:] = False
    try:
        power_features(arrays, 0.0, 1.0)
    except ValueError as exc:
        assert "sin cajas completas" in str(exc)
    else:
        raise AssertionError("debió rechazar una ventana sin soporte completo")


def test_support_audit_does_not_confuse_instant_return_with_box_injection():
    arrays = _arrays(np.array([[3.0, -1.0], [-3.0, 1.0]]))
    arrays["p_node_mean"] = np.array([[-2.0, -1.0], [-1.0, -1.0]])
    result = energetic_support_audit(arrays)
    assert result["n_instant_net_positive"] == 1
    assert result["n_smoothed_net_positive"] == 0


def test_average_ranks_ties_are_deterministic():
    np.testing.assert_allclose(average_ranks(np.array([3.0, 1.0, 3.0, 2.0])),
                               [3.5, 1.0, 3.5, 2.0])


def test_logistic_ridge_learns_declared_direction():
    x = np.array([[-2.0], [-1.0], [1.0], [2.0]])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    beta = fit_logistic_ridge(x, y, ridge=1.0)
    prediction = predict_logistic(beta, x)
    assert np.all(np.diff(prediction) > 0.0)
    assert prediction[:2].max() < 0.5
    assert prediction[2:].min() > 0.5


def test_paired_ranking_exposes_route_inversion():
    def row(pair, arm, health, value):
        return {"pair": pair, "arm": arm, "coordinate_health": health,
                "run_id": f"{pair}_{arm}",
                "power": {"early_2_20": {"exchange_rate": value}}}

    records = [
        row("a", "t", True, 3.0), row("a", "f", False, 1.0),
        row("b", "t", False, 4.0), row("b", "f", True, 2.0),
    ]
    result = paired_ranking(records, "exchange_rate", "coordinate_health")
    assert result["healthy_better"] == 1
    assert result["unhealthy_better"] == 1
    assert result["by_healthy_arm"]["t"]["healthy_better"] == 1
    assert result["by_healthy_arm"]["f"]["unhealthy_better"] == 1
