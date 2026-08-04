from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from study07.instruments import link_bond_trend  # noqa: E402


DT = 0.01


def synthetic_series(duration: float = 20.0, release: bool = False):
    ticks = np.arange(int(round(duration / DT)) + 1, dtype=np.int64)
    t = ticks * DT
    x = np.empty((len(t), 2, 3), dtype=float)
    v = np.empty_like(x)
    for layer, omega in enumerate((2.0, 3.0, 4.0)):
        phase0 = omega * t + 0.2 * layer
        phase1 = phase0 - 0.4
        if release and layer == 2:
            middle = (t >= 7.0) & (t < 13.0)
            phase1 = phase1.copy()
            phase1[middle] += 2.0 * (t[middle] - 7.0)
            phase1[t >= 13.0] += 12.0
        # Coordenadas mecánicas consistentes: v=dx/dt. La corrección heredada
        # atan2(sin(theta)/omega,cos(theta)) debe recuperar la fase geométrica.
        x[:, 0, layer] = np.cos(phase0)
        x[:, 1, layer] = np.cos(phase1)
        v[:, 0, layer] = -np.gradient(phase0, DT) * np.sin(phase0)
        v[:, 1, layer] = -np.gradient(phase1, DT) * np.sin(phase1)
    drive = np.empty((len(t), 2), dtype=float)
    drive[:, 0] = 2.0 + 0.1 * np.sin(0.7 * t)
    drive[:, 1] = -1.5 + 0.2 * np.cos(0.4 * t)
    drive[0] = 0.0
    manifest = {
        "run_id": "synthetic",
        "dt": DT,
        "n_nodes": 2,
        "por_nodo": [
            {"n_modes": 3, "capas_por_modo": ["Q", "S1", "S2"]},
            {"n_modes": 3, "capas_por_modo": ["Q", "S1", "S2"]},
        ],
        "topologia": {"edges_ij": [[0, 1]]},
    }
    return manifest, ticks, drive, x, v


def make_view(**overrides):
    manifest, ticks, drive, x, v = synthetic_series(release=overrides.pop("release", False))
    cfg, ratios = link_bond_trend._validated_config({
        "lock_window_ut": 2.0,
        "power_window_ut": 1.0,
        "hop_ut": 0.25,
        "retain_dt": True,
        **overrides,
    })
    return link_bond_trend._view_from_series(
        manifest, "a" * 64, ticks, drive, x, v, cfg, ratios
    )


def test_power_is_full_dt_aligned_and_closes_by_layer() -> None:
    manifest, ticks, drive, x, v = synthetic_series()
    view = make_view()
    power = view.arrays["power_layer_instant_dt"]
    np.testing.assert_allclose(power[1], drive[1, :, None] * v[0])
    np.testing.assert_allclose(
        np.sum(power[1:], axis=2), drive[1:] * np.sum(v[:-1], axis=2)
    )
    assert view.manifest["stride_input"] == 1
    assert view.manifest["power_layer_closure_max_abs"] <= view.manifest[
        "power_layer_closure_tolerance"
    ]
    assert view.arrays["power_valid_dt"][0] == np.False_
    assert np.all(view.arrays["power_valid_dt"][1:])


def test_lock_trend_sees_stable_release_and_recapture() -> None:
    stable = make_view()
    # La corrección elíptica heredada no deja L=1 con un desfase fijo arbitrario,
    # pero las tres capas permanecen por encima del umbral declarado.
    assert np.min(stable.arrays["lock_corrected_fixed"][:, 0, :]) > 0.90
    assert np.all(stable.arrays["locked"][:, 0, :])

    released = make_view(release=True)
    times = released.arrays["t_end_ut"]
    s2 = released.arrays["lock_corrected_fixed"][:, 0, 2]
    assert np.median(s2[(times >= 3.0) & (times < 7.0)]) > 0.90
    assert np.min(s2[(times >= 8.0) & (times < 13.0)]) < 0.50
    assert np.median(s2[times >= 16.0]) > 0.90
    assert len(released.arrays["ticks_lock_dt"]) > len(released.arrays["ticks_end"])
    assert np.all(np.diff(released.arrays["ticks_lock_dt"]) == 1)


def test_retained_dt_lock_is_the_source_of_published_trend() -> None:
    view = make_view(release=True)
    dt_ticks = view.arrays["ticks_lock_dt"]
    rows = np.searchsorted(dt_ticks, view.arrays["ticks_end"])
    np.testing.assert_allclose(
        view.arrays["lock_raw"], view.arrays["lock_raw_dt"][rows],
        atol=0.0, rtol=0.0,
    )
    np.testing.assert_allclose(
        view.arrays["lock_corrected_fixed"],
        view.arrays["lock_corrected_fixed_dt"][rows],
        atol=0.0, rtol=0.0,
    )


def test_hop_only_changes_publication_grid() -> None:
    dense = make_view(hop_ut=0.25)
    sparse = make_view(hop_ut=0.50)
    by_tick = {
        int(tick): row for tick, row in
        zip(dense.arrays["ticks_end"], dense.arrays["lock_corrected_fixed"])
    }
    for tick, row in zip(sparse.arrays["ticks_end"],
                         sparse.arrays["lock_corrected_fixed"]):
        np.testing.assert_allclose(row, by_tick[int(tick)], atol=1e-14, rtol=0.0)
    assert dense.manifest["lock_window_ticks"] == sparse.manifest["lock_window_ticks"]
    assert dense.manifest["power_window_ticks"] == sparse.manifest["power_window_ticks"]


def test_mute_layer_never_becomes_locked() -> None:
    manifest, ticks, drive, x, v = synthetic_series()
    x[:, :, 2] = 0.0
    v[:, :, 2] = 0.0
    cfg, ratios = link_bond_trend._validated_config({
        "lock_window_ut": 2.0,
        "power_window_ut": 1.0,
        "hop_ut": 0.25,
    })
    view = link_bond_trend._view_from_series(
        manifest, "b" * 64, ticks, drive, x, v, cfg, ratios
    )
    assert np.all(view.arrays["mute"][:, :, 2])
    assert not np.any(view.arrays["locked"][:, :, 2])


def test_ratio_contract_and_multiedge_fail_loud() -> None:
    cfg, ratios = link_bond_trend._validated_config({"ratios": ["1:1", "5:4"]})
    assert cfg["ratios"] == ["1:1", "5:4"]
    assert ratios == ((1, 1), (5, 4))
    with pytest.raises(RuntimeError, match="coprimos"):
        link_bond_trend._validated_config({"ratios": ["2:2"]})

    manifest, ticks, drive, x, v = synthetic_series()
    manifest["topologia"]["edges_ij"] = [[0, 1], [0, 1]]
    with pytest.raises(RuntimeError, match="una sola arista"):
        link_bond_trend._view_from_series(
            manifest, "c" * 64, ticks, drive, x, v, cfg, ratios
        )


def test_run_path_verifies_and_view_roundtrips(tmp_path: Path) -> None:
    manifest, ticks, drive, x, v = synthetic_series(duration=6.0)
    run_dir = tmp_path / "run"
    worldline = run_dir / "worldline"
    worldline.mkdir(parents=True)
    chunk_shas = []
    slices = (slice(0, 301), slice(301, len(ticks)))
    for index, sl in enumerate(slices):
        arrays = {"ticks": ticks[sl], "drive": drive[sl]}
        for node in range(2):
            arrays[f"estados_nodo{node}"] = np.concatenate(
                [x[sl, node], v[sl, node]], axis=1
            )
        path = worldline / f"chunk_{index:05d}.npz"
        np.savez_compressed(path, **arrays)
        chunk_shas.append(hashlib.sha256(path.read_bytes()).hexdigest())
    man_text = json.dumps(manifest, indent=1)
    (run_dir / "manifest.json").write_text(man_text)
    manifest_sha = hashlib.sha256(man_text.encode("utf-8")).hexdigest()
    complete = {
        "chunks": len(slices), "chunk_shas": chunk_shas,
        "sha_total": "d" * 64, "manifest_sha": manifest_sha,
    }
    (run_dir / "COMPLETE").write_text(json.dumps(complete))

    view = link_bond_trend.run_path(run_dir, {
        "lock_window_ut": 2.0,
        "power_window_ut": 1.0,
        "hop_ut": 0.25,
    })
    out = view.write(tmp_path / "views")
    from study07.instruments.api import load_view
    loaded = load_view(out)
    assert loaded["view_hash"] == view.view_hash()
    np.testing.assert_array_equal(loaded["arrays"]["ticks_end"], view.arrays["ticks_end"])
