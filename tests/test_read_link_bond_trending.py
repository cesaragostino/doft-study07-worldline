from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest


TOOLS = Path(__file__).resolve().parents[1] / "tools" / "link_grumo"
sys.path.insert(0, str(TOOLS))

import read_link_bond_trending as reader  # noqa: E402


def _summary() -> dict:
    phase_layers = []
    power_layers = []
    for layer in reader.LAYERS:
        phase_layers.append({
            "layer": layer,
            "lock_median": 0.95,
            "lock_q10": 0.80,
            "lock_q90": 0.99,
            "drift_median": 0.1,
            "raw_corrected_median_abs_delta": 0.2,
            "locked_fraction": 2.0 / 3.0,
            "locked_state_changes": 2,
        })
        power_layers.append({"layer": layer, "net_power_median": -0.1})
    return {
        "t_range_ut": [4.0, 60.0],
        "phase": [{"ratio": "1:1", "layers": phase_layers}],
        "power": power_layers,
    }


def test_reader_exposes_correction_and_positive_energy_exception(tmp_path: Path) -> None:
    view = tmp_path / "view"
    view.mkdir()
    raw = np.full((3, 1, 3), 0.50)
    corrected = np.array([
        [[0.95, 0.95, 0.95]],
        [[0.50, 0.50, 0.50]],
        [[0.95, 0.95, 0.95]],
    ])
    np.savez_compressed(
        view / "data.npz",
        lock_raw=raw,
        lock_corrected_fixed=corrected,
        mute=np.zeros((3, 2, 3), dtype=bool),
        ticks_end=np.array([10, 20, 30]),
        t_end_ut=np.array([1.0, 2.0, 3.0]),
        net_power_layer_mean=np.array([
            [-1.0, 0.1, 0.2],
            [-0.1, 0.2, 0.3],
            [-1.0, 0.1, 0.2],
        ]),
    )
    (view / "manifest.json").write_text(json.dumps({"view_hash": "v" * 64}))
    ledger = {
        "summary": {"n": 1},
        "records": [{
            "run_id": "case_t_k03_tau02",
            "status": "computed",
            "view_dir": str(view),
            "view_hash_trending": "v" * 64,
            "summary": _summary(),
        }],
    }
    ledger_path = tmp_path / "population.json"
    ledger_path.write_text(json.dumps(ledger))

    panel = reader.read_panel(ledger_path)
    assert panel["custody"]["n_records"] == 1
    assert panel["phase_correction_sensitivity"] == {
        "n_layer_films": 3,
        "n_temporal_categories_changed": 3,
        "definition": (
            "categoría raw vs corrected_fixed sobre la misma grilla, umbral y "
            "guard de mudez"
        ),
    }
    energy = panel["energy_support"]
    assert energy["n_positive_total_net_power_boxes"] == 1
    assert energy["positive_exceptions"][0]["t_ut"] == 2.0
    assert panel["groups"][0]["raw_category_counts"] == {"never": 1}
    assert panel["groups"][0]["corrected_category_counts"] == {
        "intermittent": 1
    }


def test_reader_helpers_fail_on_ambiguous_arm_and_nonfinite_group() -> None:
    with pytest.raises(RuntimeError, match="brazo inequívoco"):
        reader._arm("case_without_arm")
    with pytest.raises(RuntimeError, match="no finito"):
        reader._quantiles([float("nan")])
