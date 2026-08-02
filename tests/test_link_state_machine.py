from __future__ import annotations

import sys
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1] / "tools" / "link_grumo"
sys.path.insert(0, str(TOOLS))

from link_state_machine import LinkStateMachine, MachineConfig, Observation  # noqa: E402


def obs(t: float, dominant=(), approach=(), **kwargs) -> Observation:
    defaults = {
        "source_ratio_to_causal_peak": 1.0,
        "receiver_ratio_to_causal_peak": 1.0,
        "receiver_log_slope": 0.0,
    }
    defaults.update(kwargs)
    return Observation(t, tuple(dominant), tuple(approach), **defaults)


def event_kinds(snapshot) -> list[str]:
    return [event.kind for event in snapshot.events]


def test_capture_is_causal_and_requires_two_units() -> None:
    machine = LinkStateMachine()
    snapshots = machine.scan([
        obs(0.0), obs(1.0, dominant=("Q0",)),
        obs(2.0, dominant=("Q0",)), obs(3.0, dominant=("Q0",)),
    ])
    assert [item.connection for item in snapshots] == [
        "ABSENT", "APPROACH", "APPROACH", "DOMINANT",
    ]
    assert event_kinds(snapshots[-1]) == ["capture"]


def test_short_gap_recovers_without_release() -> None:
    machine = LinkStateMachine()
    snapshots = machine.scan([
        obs(0.0, dominant=("Q0",)), obs(2.0, dominant=("Q0",)),
        obs(3.0), obs(7.0, dominant=("Q0",)),
        obs(9.0, dominant=("Q0",)),
    ])
    assert snapshots[2].connection == "GRACE"
    assert snapshots[3].connection == "GRACE"
    assert snapshots[4].connection == "DOMINANT"
    assert "recover" in event_kinds(snapshots[4])
    assert all("release" not in event_kinds(item) for item in snapshots)


def test_long_gap_releases_and_later_recaptures() -> None:
    machine = LinkStateMachine()
    snapshots = machine.scan([
        obs(0.0, dominant=("Q0",)), obs(2.0, dominant=("Q0",)),
        obs(3.0), obs(11.0),
        obs(20.0, dominant=("Q1",)), obs(22.0, dominant=("Q1",)),
    ])
    assert snapshots[3].connection == "RELEASED"
    assert event_kinds(snapshots[3]) == ["release"]
    assert snapshots[-1].connection == "DOMINANT"
    assert "recapture" in event_kinds(snapshots[-1])


def test_overlap_is_relay_not_link_death() -> None:
    machine = LinkStateMachine()
    snapshots = machine.scan([
        obs(0.0, dominant=("Q0",)), obs(2.0, dominant=("Q0",)),
        obs(3.0, dominant=("Q0", "Q2")),
        obs(5.0, dominant=("Q0", "Q2")), obs(6.0, dominant=("Q2",)),
    ])
    assert snapshots[-1].connection == "DOMINANT"
    assert "relay_overlap" in event_kinds(snapshots[3])
    assert "mode_exit" in event_kinds(snapshots[4])
    assert all("release" not in event_kinds(item) for item in snapshots)


def test_mode_can_recapture_without_link_recapture() -> None:
    machine = LinkStateMachine()
    snapshots = machine.scan([
        obs(0.0, dominant=("Q0",)), obs(2.0, dominant=("Q0",)),
        obs(3.0, dominant=("Q0", "Q2")), obs(5.0, dominant=("Q0", "Q2")),
        obs(6.0, dominant=("Q2",)),
        obs(20.0, dominant=("Q0", "Q2")), obs(22.0, dominant=("Q0", "Q2")),
    ])
    assert snapshots[-1].connection == "DOMINANT"
    assert "mode_recapture" in event_kinds(snapshots[-1])
    assert "recapture" not in event_kinds(snapshots[-1])


def test_unobservable_does_not_fabricate_release() -> None:
    machine = LinkStateMachine()
    snapshots = machine.scan([
        obs(0.0, dominant=("Q0",)), obs(2.0, dominant=("Q0",)),
        obs(20.0, observable=False), obs(21.0), obs(29.0),
    ])
    assert snapshots[2].connection == "UNOBSERVABLE"
    assert snapshots[3].connection == "UNOBSERVABLE"
    assert snapshots[4].connection == "RELEASED"
    assert event_kinds(snapshots[4]) == ["release_after_unknown"]


def test_connection_and_vitality_are_independent_axes() -> None:
    machine = LinkStateMachine(MachineConfig(relative_floor=1e-4))
    snapshots = machine.scan([
        obs(0.0, dominant=("Q0",)),
        obs(2.0, dominant=("Q0",), receiver_log_slope=-0.02),
        obs(3.0, dominant=("Q0",), source_ratio_to_causal_peak=1e-6,
            receiver_ratio_to_causal_peak=2e-6, receiver_log_slope=-0.02),
    ])
    assert snapshots[1].connection == "DOMINANT"
    assert snapshots[1].vitality == "DECAYING"
    assert snapshots[2].connection == "DOMINANT"
    assert snapshots[2].vitality == "SOURCE_FADED"


def test_power_sign_is_reported_but_does_not_create_channel() -> None:
    machine = LinkStateMachine()
    snapshot = machine.update(obs(0.0, power_receiver=0.2, power_source=-0.2))
    assert snapshot.connection == "ABSENT"
    assert snapshot.power == "INTO_RECEIVER"
