from __future__ import annotations

import sys
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1] / "tools" / "link_grumo"
sys.path.insert(0, str(TOOLS))

from gate_i_residual_phenotypes import FALSE_DRIFT_W8, residual_kind  # noqa: E402


def record(*, active: bool, health: bool, joint: bool = False,
           observed: bool = False, episodes: int = 1,
           slope: float = 0.0) -> dict:
    return {
        "coordinate_health": health,
        "early": {"active20": {
            "Q": active,
            "joint_flat": joint,
            "rho_observed_occupation": observed,
        }},
        "full_Q": {"episodes": [{} for _ in range(episodes)]},
        "outcome60": {"corrected_slope_50_60": slope},
    }


def test_in_pattern_case_has_no_residual_label() -> None:
    assert residual_kind(record(active=True, health=True)) is None
    assert residual_kind(record(active=False, health=False)) is None


def test_early_failure_separates_sliding_from_intermittent() -> None:
    sliding = record(active=True, health=False, slope=FALSE_DRIFT_W8)
    intermittent = record(active=True, health=False, episodes=2)
    assert residual_kind(sliding) == "SLIDING_WINDOW_COHERENCE"
    assert residual_kind(intermittent) == "INTERMITTENT_PHASE_CAPTURE"


def test_late_health_separates_three_precursor_routes() -> None:
    flat = record(active=False, health=True, joint=True, observed=True)
    provisional = record(active=False, health=True, observed=True)
    nucleation = record(active=False, health=True)
    assert residual_kind(flat) == "SELECTED_FLAT_BEFORE_PHASE"
    assert residual_kind(provisional) == "NONFLAT_PROVISIONAL_BEFORE_PHASE"
    assert residual_kind(nucleation) == "LATE_NUCLEATION"
