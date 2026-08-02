from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from study07.instruments import link_power  # noqa: E402


def synthetic_worldline(n_nodes: int = 2, edges=None) -> dict:
    ticks = np.arange(6, dtype=np.int64)
    states = []
    for node in range(n_nodes):
        state = np.zeros((len(ticks), 4), dtype=float)  # dos x, dos v
        if node == 0:
            state[:, 2] = np.arange(1.0, 7.0)
            state[:, 3] = np.arange(2.0, 8.0)
        else:
            state[:, 2] = np.arange(1.0, 7.0)
            state[:, 3] = 0.0
        states.append(state)
    drive = np.zeros((len(ticks), n_nodes), dtype=float)
    drive[1:, 0] = np.arange(2.0, 12.0, 2.0)
    if n_nodes > 1:
        drive[1:, 1] = -2.0
    if edges is None:
        edges = [[0, 1]] if n_nodes == 2 else []
    return {
        "ticks": ticks,
        "drive": drive,
        "estados": states,
        "complete": True,
        "worldline_hash": "a" * 64,
        "manifest": {
            "dt": 1.0,
            "n_nodes": n_nodes,
            "por_nodo": [
                {"n_modes": 2, "capas_por_modo": ["Q", "Q"]}
                for _ in range(n_nodes)
            ],
            "topologia": {"edges_ij": edges},
        },
    }


def config(**overrides) -> dict:
    return {"box_ut": 2.0, "hop_ut": 1.0, **overrides}


def test_power_uses_drive_k_with_velocity_k_minus_one() -> None:
    view = link_power.run(synthetic_worldline(), config())
    np.testing.assert_array_equal(view.arrays["ticks_step"], np.arange(1, 6))
    np.testing.assert_array_equal(view.arrays["t_force_ut"], np.arange(0.0, 5.0))
    # v_sum_pre nodo0 = 3,5,7,9,11; usar v[k] daría otra serie.
    np.testing.assert_allclose(
        view.arrays["p_node_instant"][:, 0], [6.0, 20.0, 42.0, 72.0, 110.0]
    )
    np.testing.assert_allclose(
        view.arrays["p_node_instant"][:, 1], [-2.0, -4.0, -6.0, -8.0, -10.0]
    )
    assert view.manifest["single_edge_pair_identifiable"] is True


def test_trailing_box_is_causal_and_sign_preserving() -> None:
    view = link_power.run(synthetic_worldline(), config())
    p = view.arrays["p_node_mean"]
    assert np.isnan(p[0]).all()
    np.testing.assert_allclose(p[1:, 0], [13.0, 31.0, 57.0, 91.0])
    np.testing.assert_allclose(p[1:, 1], [-3.0, -5.0, -7.0, -9.0])
    np.testing.assert_allclose(view.arrays["fraction_negative"][1:, 0], 0.0)
    np.testing.assert_allclose(view.arrays["fraction_negative"][1:, 1], 1.0)
    np.testing.assert_allclose(
        view.arrays["work_node"][:, 0], [6.0, 26.0, 68.0, 140.0, 250.0]
    )
    np.testing.assert_array_equal(
        view.arrays["window_complete"], [False, True, True, True, True]
    )


def test_subwindow_does_not_leak_power_from_before_t0() -> None:
    view = link_power.run(
        synthetic_worldline(), config(t0_tick=2, t1_tick=4)
    )
    np.testing.assert_array_equal(view.arrays["ticks_step"], [2, 3, 4])
    assert np.isnan(view.arrays["p_node_mean"][0]).all()
    np.testing.assert_allclose(view.arrays["p_node_mean"][1:, 0], [31.0, 57.0])
    np.testing.assert_allclose(view.arrays["work_node"][:, 0], [20.0, 62.0, 134.0])


def test_box_result_does_not_depend_on_publication_hop() -> None:
    wl = synthetic_worldline()
    dense = link_power.run(wl, config(hop_ut=1.0))
    sparse = link_power.run(wl, config(hop_ut=2.0))
    by_tick = {
        int(tick): row for tick, row in
        zip(dense.arrays["ticks_step"], dense.arrays["p_node_mean"])
    }
    for tick, row in zip(sparse.arrays["ticks_step"], sparse.arrays["p_node_mean"]):
        np.testing.assert_allclose(row, by_tick[int(tick)], equal_nan=True)


def test_multiedge_film_is_only_identifiable_as_node_port() -> None:
    wl = synthetic_worldline(3, edges=[[0, 1], [0, 2]])
    view = link_power.run(wl, config())
    assert view.manifest["node_degree"] == [2, 1, 1]
    assert view.manifest["n_edges"] == 2
    assert view.manifest["single_edge_pair_identifiable"] is False


def test_missing_or_invalid_causal_channels_fail_loud() -> None:
    no_drive = synthetic_worldline()
    del no_drive["drive"]
    with pytest.raises(RuntimeError, match="drive"):
        link_power.run(no_drive, config())

    nonfinite = synthetic_worldline()
    nonfinite["drive"][2, 0] = np.nan
    with pytest.raises(RuntimeError, match="no finitos"):
        link_power.run(nonfinite, config())

    with pytest.raises(RuntimeError, match="t0_tick>=1"):
        link_power.run(synthetic_worldline(), config(t0_tick=0))
    with pytest.raises(RuntimeError, match="stride=1"):
        link_power.run(synthetic_worldline(), config(stride=2))


def test_streaming_path_matches_in_memory_view_across_chunk_boundary(tmp_path) -> None:
    wl = synthetic_worldline()
    run_dir = tmp_path / "run"
    chunks_dir = run_dir / "worldline"
    chunks_dir.mkdir(parents=True)
    chunk_shas = []
    for index, sl in enumerate((slice(0, 3), slice(3, 6))):
        path = chunks_dir / f"chunk_{index:05d}.npz"
        np.savez_compressed(
            path,
            ticks=wl["ticks"][sl],
            drive=wl["drive"][sl],
            **{f"estados_nodo{j}": state[sl]
               for j, state in enumerate(wl["estados"])},
        )
        chunk_shas.append(hashlib.sha256(path.read_bytes()).hexdigest())
    man_text = json.dumps(wl["manifest"], indent=1)
    (run_dir / "manifest.json").write_text(man_text)
    manifest_sha = hashlib.sha256(man_text.encode("utf-8")).hexdigest()
    complete = {
        "chunks": 2,
        "chunk_shas": chunk_shas,
        "sha_total": "b" * 64,
        "manifest_sha": manifest_sha,
    }
    (run_dir / "COMPLETE").write_text(json.dumps(complete))
    wl["worldline_hash"] = hashlib.sha256(
        (complete["sha_total"] + manifest_sha).encode("utf-8")
    ).hexdigest()

    in_memory = link_power.run(wl, config())
    streaming = link_power.run_path(run_dir, config())
    assert streaming.manifest == in_memory.manifest
    assert streaming.view_hash() == in_memory.view_hash()
    for key in in_memory.arrays:
        np.testing.assert_allclose(
            streaming.arrays[key], in_memory.arrays[key], equal_nan=True,
            err_msg=f"streaming difiere en {key}",
        )
