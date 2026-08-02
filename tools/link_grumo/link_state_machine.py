#!/usr/bin/env python3
"""Máquina causal mínima para separar canal y vitalidad de un link.

No extrae observables ni decide fitness. Consume observaciones ya medidas y conserva
dos ejes que los films largos demostraron que no son intercambiables:

* conexión por dominancia modal concordante;
* vitalidad de la actividad transportada.

El contrato está preregistrado en ``audit/LINK_GRUMO_GATE_H_STATE_MACHINE_PREREG.md``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable


CONNECTION_STATES = {
    "UNOBSERVABLE", "ABSENT", "APPROACH", "DOMINANT", "GRACE", "RELEASED",
}
VITALITY_STATES = {
    "UNOBSERVABLE", "SOURCE_FADED", "RECEIVER_FADED",
    "GROWING", "SUSTAINED", "DECAYING",
}
POWER_STATES = {"UNKNOWN", "INTO_RECEIVER", "OUT_OF_RECEIVER", "BALANCED"}


@dataclass(frozen=True)
class MachineConfig:
    capture_confirm_ut: float = 2.0
    grace_ut: float = 8.0
    relative_floor: float = 1e-4
    activity_slope_deadband: float = 0.005
    power_zero_tolerance: float = 0.0


@dataclass(frozen=True)
class Observation:
    t_ut: float
    dominant_modes: tuple[str, ...] = ()
    approach_modes: tuple[str, ...] = ()
    observable: bool = True
    source_ratio_to_causal_peak: float | None = None
    receiver_ratio_to_causal_peak: float | None = None
    receiver_log_slope: float | None = None
    power_receiver: float | None = None
    power_source: float | None = None


@dataclass(frozen=True)
class Event:
    kind: str
    t_ut: float
    modes: tuple[str, ...] = ()
    detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Snapshot:
    t_ut: float
    connection: str
    vitality: str
    power: str
    confirmed_modes: tuple[str, ...]
    observed_dominant_modes: tuple[str, ...]
    approach_modes: tuple[str, ...]
    ever_captured: bool
    gap_age_ut: float | None
    source_ratio_to_causal_peak: float | None
    receiver_ratio_to_causal_peak: float | None
    receiver_log_slope: float | None
    events: tuple[Event, ...]

    def to_dict(self) -> dict:
        out = asdict(self)
        out["events"] = [asdict(event) for event in self.events]
        return out


def _vitality(observation: Observation, config: MachineConfig) -> str:
    if not observation.observable:
        return "UNOBSERVABLE"
    source = observation.source_ratio_to_causal_peak
    receiver = observation.receiver_ratio_to_causal_peak
    slope = observation.receiver_log_slope
    if source is None or receiver is None:
        return "UNOBSERVABLE"
    if source < config.relative_floor:
        return "SOURCE_FADED"
    if receiver < config.relative_floor:
        return "RECEIVER_FADED"
    if slope is None:
        return "UNOBSERVABLE"
    if slope > config.activity_slope_deadband:
        return "GROWING"
    if slope < -config.activity_slope_deadband:
        return "DECAYING"
    return "SUSTAINED"


def _power(observation: Observation, config: MachineConfig) -> str:
    value = observation.power_receiver
    if value is None:
        return "UNKNOWN"
    eps = config.power_zero_tolerance
    if value > eps:
        return "INTO_RECEIVER"
    if value < -eps:
        return "OUT_OF_RECEIVER"
    return "BALANCED"


class LinkStateMachine:
    """Observador online sin fuga de información futura.

    ``dominant_modes`` ya debe incorporar la concordancia de estimadores y las guardias
    de línea/mudez. La clase sólo aplica persistencia, gracia y memoria de releases.
    """

    def __init__(self, config: MachineConfig | None = None) -> None:
        self.config = config or MachineConfig()
        self._last_t: float | None = None
        self._support_since: dict[str, float] = {}
        self._confirmed_modes: set[str] = set()
        self._ever_confirmed_modes: set[str] = set()
        self._connection = "ABSENT"
        self._ever_captured = False
        self._ever_released = False
        self._gap_since: float | None = None
        self._unknown = False
        self._unknown_absent_since: float | None = None

    def _update_support(self, observation: Observation) -> set[str]:
        present = set(observation.dominant_modes)
        for mode in list(self._support_since):
            if mode not in present:
                del self._support_since[mode]
        for mode in present:
            self._support_since.setdefault(mode, observation.t_ut)
        return {
            mode for mode, start in self._support_since.items()
            if observation.t_ut - start + 1e-12 >= self.config.capture_confirm_ut
        }

    def update(self, observation: Observation) -> Snapshot:
        t = float(observation.t_ut)
        if self._last_t is not None and t <= self._last_t:
            raise ValueError("las observaciones deben tener tiempos estrictamente crecientes")
        self._last_t = t
        events: list[Event] = []

        if not observation.observable:
            self._support_since.clear()
            self._unknown = True
            self._unknown_absent_since = None
            return Snapshot(
                t_ut=t, connection="UNOBSERVABLE",
                vitality=_vitality(observation, self.config),
                power=_power(observation, self.config),
                confirmed_modes=tuple(sorted(self._confirmed_modes)),
                observed_dominant_modes=tuple(sorted(observation.dominant_modes)),
                approach_modes=tuple(sorted(observation.approach_modes)),
                ever_captured=self._ever_captured,
                gap_age_ut=None if self._gap_since is None else t - self._gap_since,
                source_ratio_to_causal_peak=observation.source_ratio_to_causal_peak,
                receiver_ratio_to_causal_peak=observation.receiver_ratio_to_causal_peak,
                receiver_log_slope=observation.receiver_log_slope,
                events=(),
            )

        confirmed = self._update_support(observation)
        raw_present = bool(observation.dominant_modes)
        near = bool(observation.approach_modes) or raw_present

        # Tras un tramo no observable no se infiere continuidad ni release. Se exige
        # confirmación nueva; hasta entonces el estado físico sigue desconocido.
        if self._unknown and not confirmed:
            if near:
                self._unknown_absent_since = None
                connection = "UNOBSERVABLE"
            else:
                self._unknown_absent_since = (
                    t if self._unknown_absent_since is None
                    else self._unknown_absent_since
                )
                absence_age = t - self._unknown_absent_since
                if absence_age + 1e-12 < self.config.grace_ut:
                    connection = "UNOBSERVABLE"
                else:
                    self._unknown = False
                    if self._ever_captured:
                        self._connection = "RELEASED"
                        self._ever_released = True
                        events.append(Event(
                            "release_after_unknown", t, detail={
                                "valid_absence_since_ut": self._unknown_absent_since,
                                "release_time_censored": True,
                            },
                        ))
                        connection = "RELEASED"
                    else:
                        self._connection = "ABSENT"
                        connection = "ABSENT"
        else:
            if self._unknown and confirmed:
                events.append(Event("reobserved", t, tuple(sorted(confirmed))))
                self._unknown = False
                self._unknown_absent_since = None

            if confirmed:
                previous = set(self._confirmed_modes)
                if self._connection == "GRACE":
                    events.append(Event("recover", t, tuple(sorted(confirmed))))
                elif self._connection == "RELEASED" or self._ever_released:
                    events.append(Event("recapture", t, tuple(sorted(confirmed))))
                    self._ever_released = False
                elif not self._ever_captured:
                    events.append(Event("capture", t, tuple(sorted(confirmed))))

                added = confirmed - previous
                recaptured_modes = added & self._ever_confirmed_modes
                if recaptured_modes:
                    events.append(Event(
                        "mode_recapture", t, tuple(sorted(recaptured_modes)),
                    ))
                if previous and added and previous & confirmed:
                    events.append(Event(
                        "relay_overlap", t, tuple(sorted(added)),
                        {"covered_by": sorted(previous & confirmed)},
                    ))
                removed = previous - confirmed
                if removed:
                    events.append(Event("mode_exit", t, tuple(sorted(removed))))

                self._confirmed_modes = confirmed
                self._ever_confirmed_modes.update(confirmed)
                self._connection = "DOMINANT"
                self._gap_since = None
                self._ever_captured = True
                connection = "DOMINANT"
            elif self._connection == "DOMINANT":
                self._confirmed_modes.clear()
                self._gap_since = t
                self._connection = "GRACE"
                events.append(Event("gap_start", t))
                connection = "GRACE"
            elif self._connection == "GRACE":
                assert self._gap_since is not None
                support_in_time = any(
                    start - self._gap_since <= self.config.grace_ut
                    for start in self._support_since.values()
                )
                expired = t - self._gap_since >= self.config.grace_ut
                if expired and not support_in_time:
                    release_t = self._gap_since + self.config.grace_ut
                    self._connection = "RELEASED"
                    self._ever_released = True
                    events.append(Event("release", release_t))
                    connection = "RELEASED"
                else:
                    connection = "GRACE"
            elif self._connection == "RELEASED":
                connection = "APPROACH" if near else "RELEASED"
            else:
                connection = "APPROACH" if near else "ABSENT"
                self._connection = connection

        assert connection in CONNECTION_STATES
        vitality = _vitality(observation, self.config)
        power = _power(observation, self.config)
        assert vitality in VITALITY_STATES and power in POWER_STATES
        return Snapshot(
            t_ut=t, connection=connection, vitality=vitality, power=power,
            confirmed_modes=tuple(sorted(self._confirmed_modes)),
            observed_dominant_modes=tuple(sorted(observation.dominant_modes)),
            approach_modes=tuple(sorted(observation.approach_modes)),
            ever_captured=self._ever_captured,
            gap_age_ut=None if self._gap_since is None else t - self._gap_since,
            source_ratio_to_causal_peak=observation.source_ratio_to_causal_peak,
            receiver_ratio_to_causal_peak=observation.receiver_ratio_to_causal_peak,
            receiver_log_slope=observation.receiver_log_slope,
            events=tuple(events),
        )

    def scan(self, observations: Iterable[Observation]) -> list[Snapshot]:
        return [self.update(observation) for observation in observations]
