#!/usr/bin/env python3
"""Gate H: aplica la máquina de estados preregistrada a los cuatro films s600.

No relee worldlines. Consume el lector v2 y las series pequeñas ya derivadas por el tap
de transferencia. Sólo escribe bajo ``logs/link_grumo`` del worktree actual.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from baseline_census import safe_output
from link_state_machine import LinkStateMachine, MachineConfig, Observation


PARS = ("par129", "par131", "par132", "par134")
SLOPE_WINDOW_UT = 30.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def in_intervals(t: float, intervals: list[list[float]]) -> bool:
    return any(float(start) <= t <= float(end) for start, end in intervals)


def causal_log_slope(t: np.ndarray, values: np.ndarray, index: int,
                     width_ut: float = SLOPE_WINDOW_UT) -> float | None:
    selected = (t >= t[index] - width_ut) & (t <= t[index])
    if int(np.sum(selected)) < 5:
        return None
    return float(np.polyfit(
        t[selected], np.log(np.maximum(values[selected], 1e-300)), 1,
    )[0])


def state_runs(snapshots: list, hop: float) -> list[dict]:
    if not snapshots:
        return []
    result = []
    start = 0

    def signature(snapshot) -> tuple:
        return (snapshot.connection, snapshot.vitality, snapshot.power,
                snapshot.confirmed_modes)

    for index in range(1, len(snapshots) + 1):
        if index < len(snapshots) and signature(snapshots[index]) == signature(snapshots[start]):
            continue
        first, last = snapshots[start], snapshots[index - 1]
        result.append({
            "start_ut": first.t_ut,
            "end_ut": last.t_ut,
            "duration_grid_ut": float(last.t_ut - first.t_ut + hop),
            "connection": first.connection,
            "vitality": first.vitality,
            "power": first.power,
            "confirmed_modes": list(first.confirmed_modes),
        })
        start = index
    return result


def nearest_snapshot(snapshots: list, target: float) -> dict:
    item = min(snapshots, key=lambda snapshot: abs(snapshot.t_ut - target))
    return {
        "requested_ut": target, "observed_ut": item.t_ut,
        "connection": item.connection, "vitality": item.vitality,
        "power": item.power, "confirmed_modes": list(item.confirmed_modes),
        "source_ratio_to_causal_peak": item.source_ratio_to_causal_peak,
        "receiver_ratio_to_causal_peak": item.receiver_ratio_to_causal_peak,
        "receiver_log_slope": item.receiver_log_slope,
    }


def evaluate_par(par: str, reading: dict, series_path: Path,
                 config: MachineConfig) -> dict:
    with np.load(series_path, allow_pickle=False) as data:
        t = np.asarray(data["t_grid"], dtype=float)
        source = np.asarray(data["F_hat"], dtype=float)
        received_by_mode = np.asarray(data["A_L"], dtype=float)
    if received_by_mode.ndim != 2 or received_by_mode.shape[1] != len(t):
        raise RuntimeError(f"forma A_L inválida en {series_path}")
    if len(source) != len(t):
        raise RuntimeError(f"forma F_hat inválida en {series_path}")

    modes = {
        name: value for name, value in reading["modos"].items()
        if not value["mudo"]
    }
    line_valid = not reading["linea"]["bandera_linea"]
    received = np.max(received_by_mode, axis=0)
    source_peak = np.maximum.accumulate(source)
    receiver_peak = np.maximum.accumulate(received)
    machine = LinkStateMachine(config)
    snapshots = []
    for index, time in enumerate(t):
        dominant = tuple(sorted(
            mode for mode, value in modes.items()
            if in_intervals(float(time), value["citable"]["eps_u1.0"])
        ))
        approach = tuple(sorted(
            mode for mode, value in modes.items()
            if mode not in dominant
            and in_intervals(float(time), value["citable"]["eps_u0.8"])
        ))
        snapshots.append(machine.update(Observation(
            t_ut=float(time), dominant_modes=dominant, approach_modes=approach,
            observable=line_valid,
            source_ratio_to_causal_peak=float(source[index] / max(source_peak[index], 1e-300)),
            receiver_ratio_to_causal_peak=float(
                received[index] / max(receiver_peak[index], 1e-300)),
            receiver_log_slope=causal_log_slope(t, received, index),
        )))

    hop = float(np.median(np.diff(t)))
    events = [
        {"kind": event.kind, "t_ut": event.t_ut, "modes": list(event.modes),
         "detail": event.detail}
        for snapshot in snapshots for event in snapshot.events
    ]
    final = snapshots[-1]
    source_faded = [snapshot.t_ut for snapshot in snapshots
                    if snapshot.vitality == "SOURCE_FADED"]
    connection_counts = {
        state: sum(snapshot.connection == state for snapshot in snapshots)
        for state in ("UNOBSERVABLE", "ABSENT", "APPROACH", "DOMINANT",
                      "GRACE", "RELEASED")
    }
    return {
        "par": par,
        "input_series": str(series_path),
        "input_series_sha256": sha256(series_path),
        "n_samples": len(snapshots), "hop_ut": hop,
        "state_runs": state_runs(snapshots, hop),
        "events": events,
        "summary": {
            "connection_fraction": {
                key: float(value / len(snapshots))
                for key, value in connection_counts.items()
            },
            "channel_present_fraction": float(sum(
                snapshot.connection in ("DOMINANT", "GRACE")
                for snapshot in snapshots) / len(snapshots)),
            "n_capture": sum(event["kind"] == "capture" for event in events),
            "n_release": sum(event["kind"] == "release" for event in events),
            "n_recapture": sum(event["kind"] == "recapture" for event in events),
            "n_mode_recapture": sum(event["kind"] == "mode_recapture" for event in events),
            "n_recover_short_gap": sum(event["kind"] == "recover" for event in events),
            "n_relay_overlap": sum(event["kind"] == "relay_overlap" for event in events),
            "first_source_faded_ut": source_faded[0] if source_faded else None,
            "final": {
                "t_ut": final.t_ut, "connection": final.connection,
                "vitality": final.vitality, "power": final.power,
                "confirmed_modes": list(final.confirmed_modes),
                "source_ratio_to_causal_peak": final.source_ratio_to_causal_peak,
                "receiver_ratio_to_causal_peak": final.receiver_ratio_to_causal_peak,
                "receiver_log_slope": final.receiver_log_slope,
            },
            "checkpoints": [nearest_snapshot(snapshots, target)
                            for target in (60, 120, 200, 300, 450, 590)],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--long-reader", required=True, type=Path)
    parser.add_argument("--series-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    reader_path = args.long_reader.expanduser().resolve()
    series_root = args.series_root.expanduser().resolve()
    reader = json.loads(reader_path.read_text())
    config = MachineConfig()
    records = []
    for par in PARS:
        series_path = series_root / f"jz_series_{par}.npz"
        if not series_path.is_file():
            raise SystemExit(f"falta serie derivada: {series_path}")
        records.append(evaluate_par(par, reader[par], series_path, config))
        print(f"[link-grumo] Gate H {par} evaluado", flush=True)

    by_par = {record["par"]: record for record in records}
    checks = {
        "par132_final_released": (
            by_par["par132"]["summary"]["final"]["connection"] == "RELEASED"),
        "par134_final_released": (
            by_par["par134"]["summary"]["final"]["connection"] == "RELEASED"),
        "par129_final_dominant_but_source_faded": (
            by_par["par129"]["summary"]["final"]["connection"] == "DOMINANT"
            and by_par["par129"]["summary"]["final"]["vitality"] == "SOURCE_FADED"),
        "par131_final_dominant_but_source_faded": (
            by_par["par131"]["summary"]["final"]["connection"] == "DOMINANT"
            and by_par["par131"]["summary"]["final"]["vitality"] == "SOURCE_FADED"),
        "par129_has_link_recapture": by_par["par129"]["summary"]["n_recapture"] >= 1,
    }
    scale_arbitration = {
        "par129_has_modal_recapture": (
            by_par["par129"]["summary"]["n_mode_recapture"] >= 1),
        "interpretation": (
            "La predicción preregistrada 'par129 recaptura' era ambigua de escala: "
            "Q0 recaptura bajo cobertura continua de Q2; no hay release/recapture del link."
        ),
    }

    # Sensibilidad descriptiva agregada después de la corrida primaria. No redefine el
    # preregistro: comprueba si las conclusiones cualitativas dependen de h=8 o piso=1e-4.
    sensitivity_grace = {}
    for grace in (4.0, 8.0, 12.0):
        cfg = MachineConfig(grace_ut=grace)
        variant = {
            par: evaluate_par(par, reader[par], series_root / f"jz_series_{par}.npz", cfg)
            for par in PARS
        }
        sensitivity_grace[str(grace)] = {
            par: {
                "final_connection": variant[par]["summary"]["final"]["connection"],
                "n_release": variant[par]["summary"]["n_release"],
                "channel_present_fraction": variant[par]["summary"]["channel_present_fraction"],
            } for par in PARS
        }
    sensitivity_floor = {}
    for floor in (1e-3, 1e-4, 1e-5):
        cfg = MachineConfig(relative_floor=floor)
        variant = {
            par: evaluate_par(par, reader[par], series_root / f"jz_series_{par}.npz", cfg)
            for par in PARS
        }
        sensitivity_floor[str(floor)] = {
            par: {
                "final_vitality": variant[par]["summary"]["final"]["vitality"],
                "first_source_faded_ut": variant[par]["summary"]["first_source_faded_ut"],
            } for par in PARS
        }
    result = {
        "_meta": {
            "long_reader": str(reader_path),
            "long_reader_sha256": sha256(reader_path),
            "series_root": str(series_root),
            "policy": "sólo lee derivados existentes; salida local bajo logs/link_grumo",
            "config": {
                "capture_confirm_ut": config.capture_confirm_ut,
                "grace_ut": config.grace_ut,
                "relative_floor": config.relative_floor,
                "activity_slope_deadband": config.activity_slope_deadband,
                "slope_window_ut": SLOPE_WINDOW_UT,
            },
        },
        "method": {
            "channel": "episodios citables rho STFT AND demod; u=1, confirmación causal 2 u.t.",
            "approach": "episodios citables u=0.8 que todavía no dominan",
            "vitality": "F_hat y max_m A_L relativos a máximo causal; pendiente trailing 30 u.t.",
            "power": "UNKNOWN en esta corrida: el spot-check energético no tiene serie temporal completa",
        },
        "preregistered_checks": checks,
        "all_preregistered_checks_hold": all(checks.values()),
        "scale_arbitration": scale_arbitration,
        "posthoc_sensitivity": {
            "grace_ut": sensitivity_grace,
            "relative_floor": sensitivity_floor,
        },
        "warnings": [
            "Cuatro casos elegidos: consistencia mecánica, no validación poblacional.",
            "Los episodios del lector ya pasaron concordancia de familias; Gate H agrega causalidad online.",
            "SOURCE_FADED usa un piso heredado, no una constante física universal.",
            "Sin P(t) continuo, la dirección energética queda UNKNOWN y no se imputa.",
        ],
        "records": records,
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"[link-grumo] Gate H salida: {output}")
    print(f"[link-grumo] predicciones preregistradas: {sum(checks.values())}/{len(checks)}")


if __name__ == "__main__":
    main()
