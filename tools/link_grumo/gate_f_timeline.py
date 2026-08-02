#!/usr/bin/env python3
"""Gate F1: cronología de elegibilidad, captura y maduración en el banco salud60.

Lee hasta 60 u.t. de los 16 films congelados por Gate F0. En una sola pasada extrae:

* transferencia dirigida Q: ocupación espectral predicha y compatibilidad compleja Q/F;
* lock local por capa Q/S1/S2, con fase corregida usando sólo cada ventana;
* cierre primario Q local, separado del endpoint salud60.

No simula. Verifica hashes de manifiestos/chunks y nunca escribe en el disco externo.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np

from baseline_census import safe_output
from gate_b_dominance import spectrum
from gate_d_phase_transfer import complex_coefficient
from linear_response import chi_layer_sum, jacobian_fd, load_blocks, parse_block
from study07.artifacts.checkpoint import spec_fingerprint


HORIZON_UT = 60.0
STRIDE = 100
Q_WINDOW_UT = 8.0
LAYER_WINDOW_UT = 4.0
HOP_UT = 1.0
Q_SUSTAIN_UT = 2.0
LAYER_SUSTAIN_UT = 4.0
OMEGA_MIN = 2.0
OMEGA_MAX = 50.0
PHASE_MAX_RAD = math.radians(15.0)
R_AMP_MIN = 0.5
R_AMP_MAX = 2.0
RHO_MIN = 1.0
LAYER_RW_MIN = 0.90
PRIMARY_RW_MIN = 0.95
PRIMARY_DW_MAX = 1.1 / 8.0
PISO_AMP_ABS = 1e-12
PISO_AMP_REL = 1e-3
LAYERS = ("Q", "S1", "S2")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_film(run_dir: Path) -> tuple[dict, dict, dict[str, np.ndarray]]:
    manifest_path = run_dir / "manifest.json"
    complete_path = run_dir / "COMPLETE"
    manifest = json.loads(manifest_path.read_text())
    complete = json.loads(complete_path.read_text())
    manifest_hash = sha256(manifest_path)
    if manifest_hash != complete["manifest_sha"]:
        raise RuntimeError(f"manifest SHA inválido: {run_dir.name}")

    ticks_parts: list[np.ndarray] = []
    drive_parts: list[np.ndarray] = []
    x_parts: list[np.ndarray] = []
    v_parts: list[np.ndarray] = []
    verified: list[dict] = []
    for chunk_index, expected_hash in enumerate(complete["chunk_shas"]):
        path = run_dir / "worldline" / f"chunk_{chunk_index:05d}.npz"
        raw = path.read_bytes()
        observed_hash = hashlib.sha256(raw).hexdigest()
        if observed_hash != expected_hash:
            raise RuntimeError(f"chunk SHA inválido: {run_dir.name}/{path.name}")
        verified.append({"file": path.name, "sha256": observed_hash})
        with np.load(io.BytesIO(raw), allow_pickle=False) as npz:
            ticks_all = np.asarray(npz["ticks"])
            select = ((ticks_all % STRIDE == 0)
                      & (ticks_all * float(manifest["dt"]) <= HORIZON_UT))
            if np.any(select):
                ticks_parts.append(ticks_all[select])
                drive_parts.append(np.asarray(npz["drive"])[select])
                x_nodes = []
                v_nodes = []
                for node, info in enumerate(manifest["por_nodo"]):
                    state = np.asarray(npz[f"estados_nodo{node}"])[select]
                    n_modes = int(info["n_modes"])
                    layer_names = np.asarray(info["capas_por_modo"])
                    x_layer = []
                    v_layer = []
                    for layer in LAYERS:
                        indices = np.flatnonzero(layer_names == layer)
                        if not len(indices):
                            x_layer.append(np.zeros(len(state)))
                            v_layer.append(np.zeros(len(state)))
                        else:
                            x_layer.append(np.sum(state[:, indices], axis=1))
                            v_layer.append(np.sum(state[:, n_modes + indices], axis=1))
                    x_nodes.append(np.stack(x_layer, axis=1))
                    v_nodes.append(np.stack(v_layer, axis=1))
                x_parts.append(np.stack(x_nodes, axis=1))
                v_parts.append(np.stack(v_nodes, axis=1))
            if ticks_all[-1] * float(manifest["dt"]) >= HORIZON_UT:
                break
    if not ticks_parts:
        raise RuntimeError(f"film sin muestras: {run_dir.name}")
    ticks = np.concatenate(ticks_parts)
    if ticks[-1] * float(manifest["dt"]) < HORIZON_UT - 2 * STRIDE * float(manifest["dt"]):
        raise RuntimeError(f"film no alcanza 60 u.t.: {run_dir.name}")
    arrays = {
        "ticks": ticks,
        "drive": np.concatenate(drive_parts),
        "X": np.concatenate(x_parts),
        "V": np.concatenate(v_parts),
    }
    provenance = {
        "run_dir": str(run_dir), "manifest_sha256": manifest_hash,
        "n_chunks_verified": len(verified), "chunks_verified": verified,
        "stride": STRIDE, "dt_effective": float(manifest["dt"]) * STRIDE,
        "last_t_ut": float(ticks[-1] * float(manifest["dt"])),
    }
    return manifest, provenance, arrays


def local_phase_metrics(x0: np.ndarray, v0: np.ndarray, x1: np.ndarray,
                        v1: np.ndarray, dt: float) -> tuple[float, float, float, float]:
    phases = []
    omegas = []
    for x, v in ((x0, v0), (x1, v1)):
        theta = np.arctan2(v, x)
        unwrapped = np.unwrap(theta)
        omega = abs(float(np.mean(np.gradient(unwrapped, dt))))
        phi = np.unwrap(np.arctan2(
            np.sin(theta) / max(omega, 1e-9), np.cos(theta)))
        phases.append(phi)
        omegas.append(omega)
    rw = float(abs(np.mean(np.exp(1j * (phases[0] - phases[1])))))
    return rw, abs(omegas[0] - omegas[1]), omegas[0], omegas[1]


def runs(records: list[dict], key: str, sustain_ut: float,
         continuity: bool = False) -> list[dict]:
    min_len = max(int(math.ceil(sustain_ut / HOP_UT)), 1)
    rayleigh = 2.0 * math.pi / Q_WINDOW_UT
    episodes: list[dict] = []
    start = None
    previous = None

    def finish(index: int) -> None:
        nonlocal start
        if start is not None and index - start >= min_len:
            confirm = start + min_len - 1
            episodes.append({
                "start_index": start, "end_index_exclusive": index,
                "support_start_ut": float(records[start]["t_start_ut"]),
                "first_window_end_ut": float(records[start]["t_end_ut"]),
                "confirmation_end_ut": float(records[confirm]["t_end_ut"]),
                "last_window_end_ut": float(records[index - 1]["t_end_ut"]),
                "duration_grid_ut": float((index - start) * HOP_UT),
            })
        start = None

    for index, record in enumerate(records):
        active = bool(record[key])
        discontinuity = bool(
            active and continuity and previous is not None
            and abs(float(record["omega_line"]) - previous) > 2.0 * rayleigh)
        if not active:
            finish(index)
            previous = None
            continue
        if discontinuity:
            finish(index)
            start = index
        elif start is None:
            start = index
        previous = float(record["omega_line"]) if continuity else None
    finish(len(records))
    return episodes


def first_episode(episodes: list[dict]) -> dict | None:
    return episodes[0] if episodes else None


def chi_cached(block_id: str, omega: float, models: dict, cache: dict) -> tuple[complex, float]:
    key = (block_id, round(float(omega), 12))
    if key not in cache:
        spec, matrix, drive = models[block_id]
        rayleigh = 2.0 * math.pi / Q_WINDOW_UT
        samples = np.asarray(chi_layer_sum(
            spec, matrix, drive,
            np.array([max(omega - rayleigh / 2.0, 1e-6), omega,
                      omega + rayleigh / 2.0]), "Q"), dtype=complex)
        variation = float(np.max(np.abs(samples))
                          / max(float(np.min(np.abs(samples))), 1e-300))
        cache[key] = (complex(samples[1]), variation)
    return cache[key]


def q_timeline(arrays: dict[str, np.ndarray], dt: float, block_ids: list[str],
               models: dict, chi_cache: dict) -> tuple[dict, list[dict]]:
    q = arrays["X"][:, :, 0]
    qv = arrays["V"][:, :, 0]
    drive = arrays["drive"]
    times = arrays["ticks"] * (dt / STRIDE)
    n_window = int(round(Q_WINDOW_UT / dt))
    n_hop = int(round(HOP_UT / dt))
    starts = np.arange(0, len(q) - n_window + 1, n_hop, dtype=int)
    directed = {"0_to_1": [], "1_to_0": []}
    primary: list[dict] = []
    for start in starts:
        stop = start + n_window
        spectra = [spectrum(q[start:stop, node], dt) for node in (0, 1)]
        omega = spectra[0][0]
        q_amp = [entry[1] for entry in spectra]
        drive_amp = [spectrum(drive[start:stop, node], dt)[1] for node in (0, 1)]
        valid = (omega >= OMEGA_MIN) & (omega <= OMEGA_MAX)
        candidates = np.flatnonzero(valid)
        rw_q, dw_q, omega0, omega1 = local_phase_metrics(
            q[start:stop, 0], qv[start:stop, 0],
            q[start:stop, 1], qv[start:stop, 1], dt)
        primary.append({
            "t_start_ut": float(times[start]), "t_end_ut": float(times[stop - 1]),
            "rw_Q_local_W8": rw_q, "dw_Q_local_W8": dw_q,
            "omega_Q_node0": omega0, "omega_Q_node1": omega1,
            "primary_close": bool(rw_q >= PRIMARY_RW_MIN and dw_q < PRIMARY_DW_MAX),
        })
        for source in (0, 1):
            follower = 1 - source
            line_index = int(candidates[np.argmax(q_amp[source][candidates])])
            line = float(omega[line_index])
            rayleigh = 2.0 * math.pi / Q_WINDOW_UT
            competitor_candidates = np.flatnonzero(
                valid & (np.abs(omega - line) >= rayleigh))
            competitor_index = int(competitor_candidates[
                np.argmax(q_amp[follower][competitor_candidates])])
            competitor = float(q_amp[follower][competitor_index])
            force_amp = float(drive_amp[follower][line_index])
            rho_observed = float(q_amp[follower][line_index]
                                 / max(competitor, 1e-300))
            chi, chi_variation = chi_cached(
                block_ids[follower], line, models, chi_cache)
            q_hat = complex_coefficient(q[start:stop, follower], times[start:stop], line)
            f_hat = complex_coefficient(drive[start:stop, follower], times[start:stop], line)
            alive = abs(q_hat) > PISO_AMP_ABS and abs(f_hat) > PISO_AMP_ABS
            if alive and abs(chi) > 1e-300:
                residual = (q_hat / f_hat) / chi
                r_amp = float(abs(residual))
                phase_error = float(abs(np.angle(residual)))
                complex_error = float(abs(residual - 1.0))
            else:
                r_amp = None
                phase_error = math.pi
                complex_error = None
            rho_pred = float(abs(chi) * force_amp / max(competitor, 1e-300))
            complex_capture = bool(
                alive and phase_error <= PHASE_MAX_RAD and R_AMP_MIN <= r_amp <= R_AMP_MAX)
            directed[f"{source}_to_{follower}"].append({
                "t_start_ut": float(times[start]), "t_end_ut": float(times[stop - 1]),
                "source": source, "follower": follower,
                "omega_line": line,
                "omega_competitor": float(omega[competitor_index]),
                "A_line_source": float(q_amp[source][line_index]),
                "A_line_follower": float(q_amp[follower][line_index]),
                "A_competitor_follower": competitor, "A_force": force_amp,
                "chi_abs": float(abs(chi)), "chi_phase": float(np.angle(chi)),
                "chi_variation_half_rayleigh": chi_variation,
                "chi_flat": bool(chi_variation <= 2.0),
                "rho_pred": rho_pred, "occupation": bool(rho_pred > RHO_MIN),
                "rho_observed": rho_observed,
                "occupation_observed": bool(rho_observed > RHO_MIN),
                "R_amp": r_amp, "R_phase_error_rad": phase_error,
                "R_phase_error_deg": float(math.degrees(phase_error)),
                "R_complex_error": complex_error,
                "complex_capture": complex_capture,
                "complex_capture_flat": bool(complex_capture and chi_variation <= 2.0),
                "joint": bool(complex_capture and rho_pred > RHO_MIN),
                "joint_flat": bool(complex_capture and rho_pred > RHO_MIN
                                   and chi_variation <= 2.0),
            })
    channel_summary = {}
    for direction, records in directed.items():
        channel_summary[direction] = {"events": {}}
        for key in ("occupation", "occupation_observed",
                    "complex_capture", "complex_capture_flat",
                    "joint", "joint_flat"):
            episodes = runs(records, key, Q_SUSTAIN_UT, continuity=True)
            channel_summary[direction]["events"][key] = {
                "first": first_episode(episodes), "episodes": episodes,
            }
        channel_summary[direction]["n_line_jumps_gt_2rayleigh"] = sum(
            abs(records[index]["omega_line"] - records[index - 1]["omega_line"])
            > 2.0 * 2.0 * math.pi / Q_WINDOW_UT
            for index in range(1, len(records)))
        channel_summary[direction]["series"] = records
    primary_episodes = runs(primary, "primary_close", Q_SUSTAIN_UT)
    return channel_summary, [{"events": {"first": first_episode(primary_episodes),
                                          "episodes": primary_episodes},
                              "series": primary}]


def layer_timeline(arrays: dict[str, np.ndarray], dt: float) -> dict:
    x = arrays["X"]
    v = arrays["V"]
    times = arrays["ticks"] * (dt / STRIDE)
    n_window = int(round(LAYER_WINDOW_UT / dt))
    n_hop = int(round(HOP_UT / dt))
    starts = np.arange(0, len(x) - n_window + 1, n_hop, dtype=int)
    result = {}
    for layer_index, layer in enumerate(LAYERS):
        records = []
        causal_peak = np.zeros(2)
        for start in starts:
            stop = start + n_window
            std = np.std(x[start:stop, :, layer_index], axis=0)
            causal_peak = np.maximum(causal_peak, std)
            mute = bool(any(std[node] < max(PISO_AMP_ABS,
                                             PISO_AMP_REL * causal_peak[node])
                            for node in (0, 1)))
            rw, dw, omega0, omega1 = local_phase_metrics(
                x[start:stop, 0, layer_index], v[start:stop, 0, layer_index],
                x[start:stop, 1, layer_index], v[start:stop, 1, layer_index], dt)
            records.append({
                "t_start_ut": float(times[start]), "t_end_ut": float(times[stop - 1]),
                "rw_local_W4": rw, "dw_local_W4": dw,
                "omega_node0": omega0, "omega_node1": omega1,
                "std_node0": float(std[0]), "std_node1": float(std[1]),
                "mute_causal": mute,
                "capture": bool(not mute and rw >= LAYER_RW_MIN),
            })
        episodes = runs(records, "capture", LAYER_SUSTAIN_UT)
        result[layer] = {"events": {"first": first_episode(episodes),
                                     "episodes": episodes},
                         "series": records}
    return result


def earliest_channel(channels: dict, event_key: str) -> dict | None:
    candidates = []
    for direction, channel in channels.items():
        event = channel["events"][event_key]["first"]
        if event is not None:
            candidates.append({"direction": direction, **event})
    return min(candidates, key=lambda item: item["confirmation_end_ut"]) if candidates else None


def film_summary(channels: dict, primary: list[dict], layers: dict) -> dict:
    return {
        "first_Q_occupation": earliest_channel(channels, "occupation"),
        "first_Q_complex": earliest_channel(channels, "complex_capture"),
        "first_Q_complex_flat": earliest_channel(channels, "complex_capture_flat"),
        "first_Q_joint": earliest_channel(channels, "joint"),
        "first_Q_joint_flat": earliest_channel(channels, "joint_flat"),
        "first_primary_close": primary[0]["events"]["first"],
        "first_layer_Q": layers["Q"]["events"]["first"],
        "first_S1": layers["S1"]["events"]["first"],
        "first_S2": layers["S2"]["events"]["first"],
    }


def event_count(films: list[dict], key: str) -> int:
    return sum(film["summary"][key] is not None for film in films)


def median_time(films: list[dict], key: str) -> float | None:
    values = [film["summary"][key]["confirmation_end_ut"]
              for film in films if film["summary"][key] is not None]
    return float(np.median(values)) if values else None


def summarize_group(films: list[dict]) -> dict:
    keys = ("first_Q_occupation", "first_Q_complex", "first_Q_complex_flat",
            "first_Q_joint", "first_Q_joint_flat", "first_primary_close",
            "first_layer_Q", "first_S1", "first_S2")
    return {
        "n": len(films), "n_health60": sum(film["health60"] for film in films),
        "events": {key: {"n": event_count(films, key),
                         "median_confirmation_end_ut": median_time(films, key)}
                   for key in keys},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    bank_path = args.bank.expanduser().resolve()
    blocks_path = args.blocks.expanduser().resolve()
    bank = json.loads(bank_path.read_text())
    blocks = load_blocks(blocks_path)
    models: dict[str, tuple] = {}
    chi_cache: dict[tuple, tuple] = {}
    films: list[dict] = []

    for pair_index, pair in enumerate(bank["pairs"], 1):
        transported = pair["target"] if pair["target"]["arm"] == "t" else pair["control"]
        transported_manifest = json.loads(
            (Path(transported["run_dir"]) / "manifest.json").read_text())
        block_ids = [str(node["block_id"])
                     for node in transported_manifest["composicion"]["por_nodo"]]
        for block_id in block_ids:
            if block_id not in models:
                spec = parse_block(blocks[block_id])
                matrix, drive_vector = jacobian_fd(spec)
                models[block_id] = (spec, matrix, drive_vector)
        for role in ("target", "control"):
            side = pair[role]
            manifest, provenance, arrays = load_film(Path(side["run_dir"]))
            for node, block_id in enumerate(block_ids):
                if spec_fingerprint(models[block_id][0]) != manifest["spec_fingerprints"][node]:
                    raise RuntimeError(f"constitución no coincide: {side['run_id']} nodo {node}")
            dt_effective = float(manifest["dt"]) * STRIDE
            channels, primary = q_timeline(
                arrays, dt_effective, block_ids, models, chi_cache)
            layers = layer_timeline(arrays, dt_effective)
            summary = film_summary(channels, primary, layers)
            films.append({
                "pair_id": pair["pair_id"], "role": role,
                "run_id": side["run_id"], "arm": side["arm"],
                "health60": bool(side["outcome"]["salud_60"]),
                "outcome60": side["outcome"], "block_ids": block_ids,
                "summary": summary, "Q_channels": channels,
                "primary_Q": primary[0], "layers": layers,
                "provenance": provenance,
            })
            print(f"[link-grumo] F1 {len(films)}/16 {side['run_id']}", flush=True)

    healthy = [film for film in films if film["health60"]]
    unhealthy = [film for film in films if not film["health60"]]
    targets = [film for film in films if film["role"] == "target"]
    controls = [film for film in films if film["role"] == "control"]
    paired = []
    by_run = {film["run_id"]: film for film in films}
    for pair in bank["pairs"]:
        target = by_run[pair["target"]["run_id"]]
        control = by_run[pair["control"]["run_id"]]
        paired.append({
            "pair_id": pair["pair_id"], "relation": pair["outcome_relation"],
            "target": target["summary"], "control": control["summary"],
        })
    result = {
        "_meta": {
            "bank": str(bank_path), "bank_sha256": sha256(bank_path),
            "blocks": str(blocks_path), "blocks_sha256": sha256(blocks_path),
            "policy": "worldlines externas read-only; salida sólo logs/link_grumo",
        },
        "method": bank["gate_f_timeline_contract"],
        "summary": {
            "all": summarize_group(films), "healthy60": summarize_group(healthy),
            "unhealthy60": summarize_group(unhealthy),
            "targets": summarize_group(targets), "controls": summarize_group(controls),
            "n_chi_cache_points": len(chi_cache),
        },
        "warnings": [
            "Banco de descubrimiento: 8 targets seleccionados por salud60; resultados descriptivos.",
            "Las ventanas W4/W8 dan intervalos de soporte, no instantes causales puntuales.",
            "R≈1 prueba compatibilidad con respuesta forzada lineal, no origen causal de la línea.",
            "La línea Q se sigue por dirección y puede chirpear; saltos >2 Rayleigh cortan episodios.",
            "La corrección de fase por capa usa sólo la ventana corriente; no filtra futuro.",
            "Salud60 sigue siendo horizonte finito, no supervivencia asintótica.",
        ],
        "paired": paired,
        "films": films,
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"[link-grumo] Gate F1 completo: {len(films)} films")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
