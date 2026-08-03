#!/usr/bin/env python3
"""Gate B2: trayectoria de dominancia espectral en remotos resolubles.

Usa W=8 u.t. y hop=1 u.t. Sólo analiza transported con dw temprano mayor que la
resolución Rayleigh 2pi/W, junto con su fresh apareado hasta el mismo horizonte. Lee y
verifica los chunks necesarios del archivo externo; no integra ni modifica films.
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


WINDOW_UT = 8.0
HOP_UT = 1.0
STRIDE = 100
SUSTAIN_UT = 2.0
OMEGA_RANGE = (2.0, 50.0)


def index_runs(root: Path) -> dict[str, Path]:
    return {p.name: p for p in root.glob("*/unidades/*")
            if p.is_dir() and (p / "manifest.json").is_file()}


def read_series(run_dir: Path, limit_ut: float) -> tuple[dict, dict]:
    manifest_path = run_dir / "manifest.json"
    complete_path = run_dir / "COMPLETE"
    manifest = json.loads(manifest_path.read_text())
    complete = json.loads(complete_path.read_text())
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if manifest_sha != complete["manifest_sha"]:
        raise RuntimeError(f"manifest SHA inválido: {run_dir.name}")

    ticks_parts: list[np.ndarray] = []
    q_parts: list[list[np.ndarray]] = [[] for _ in manifest["por_nodo"]]
    drive_parts: list[np.ndarray] = []
    verified = []
    for chunk_index, expected_sha in enumerate(complete["chunk_shas"]):
        path = run_dir / "worldline" / f"chunk_{chunk_index:05d}.npz"
        raw = path.read_bytes()
        observed_sha = hashlib.sha256(raw).hexdigest()
        if observed_sha != expected_sha:
            raise RuntimeError(f"chunk SHA inválido: {run_dir.name}/{path.name}")
        verified.append({"file": path.name, "sha256": observed_sha})
        with np.load(io.BytesIO(raw), allow_pickle=False) as npz:
            ticks = np.asarray(npz["ticks"])
            select = (ticks % STRIDE == 0) & (ticks * float(manifest["dt"]) <= limit_ut)
            ticks_parts.append(ticks[select])
            drive_parts.append(np.asarray(npz["drive"])[select])
            for j, info in enumerate(manifest["por_nodo"]):
                state = np.asarray(npz[f"estados_nodo{j}"])
                n_modes = int(info["n_modes"])
                q_idx = np.array([i for i, layer in enumerate(info["capas_por_modo"])
                                  if layer == "Q"], dtype=int)
                if q_idx.size == 0:
                    q_idx = np.arange(n_modes)
                q_parts[j].append(np.sum(state[select, :n_modes][:, q_idx], axis=1))
            if ticks[-1] * float(manifest["dt"]) >= limit_ut:
                break
    ticks = np.concatenate(ticks_parts)
    q = np.stack([np.concatenate(parts) for parts in q_parts], axis=1)
    drive = np.concatenate(drive_parts, axis=0)
    if len(ticks) < int(WINDOW_UT / (float(manifest["dt"]) * STRIDE)):
        raise RuntimeError(f"serie insuficiente para W8: {run_dir.name}")
    provenance = {"run_dir": str(run_dir), "manifest_sha256": manifest_sha,
                  "chunks_verificados": verified}
    return {"ticks": ticks, "Q": q, "drive": drive,
            "dt": float(manifest["dt"]) * STRIDE}, provenance


def spectrum(values: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(values, dtype=float)
    y = y - float(np.mean(y))
    window = np.hanning(len(y))
    n_fft = 1 << int(math.ceil(math.log2(max(4 * len(y), 2))))
    coefficients = np.fft.rfft(y * window, n=n_fft)
    omega = 2.0 * np.pi * np.fft.rfftfreq(n_fft, d=dt)
    amplitude = 2.0 * np.abs(coefficients) / max(float(np.sum(window)), 1e-300)
    return omega, amplitude


def runs_true(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    result = []
    start = None
    for i, value in enumerate(mask.tolist() + [False]):
        if value and start is None:
            start = i
        elif not value and start is not None:
            if i - start >= min_len:
                result.append((start, i))
            start = None
    return result


def dominance_series(series: dict, source: int) -> dict:
    dt = float(series["dt"])
    q = np.asarray(series["Q"])
    drive = np.asarray(series["drive"])
    n_window = int(round(WINDOW_UT / dt))
    n_hop = int(round(HOP_UT / dt))
    starts = np.arange(0, len(q) - n_window + 1, n_hop, dtype=int)
    follower = 1 - source
    rayleigh = 2.0 * np.pi / WINDOW_UT
    records = []
    previous_line = None
    jumps = 0
    for start in starts:
        stop = start + n_window
        omega, src_amp = spectrum(q[start:stop, source], dt)
        _, fol_amp = spectrum(q[start:stop, follower], dt)
        _, force_amp = spectrum(drive[start:stop, follower], dt)
        valid = (omega >= OMEGA_RANGE[0]) & (omega <= OMEGA_RANGE[1])
        candidates = np.flatnonzero(valid)
        line_index = int(candidates[np.argmax(src_amp[candidates])])
        line = float(omega[line_index])
        if previous_line is not None and abs(line - previous_line) > 2.0 * rayleigh:
            jumps += 1
        previous_line = line
        outside_line = valid & (np.abs(omega - line) >= rayleigh)
        competitor_indices = np.flatnonzero(outside_line)
        competitor_index = int(competitor_indices[np.argmax(fol_amp[competitor_indices])])
        a_line = float(fol_amp[line_index])
        a_comp = float(fol_amp[competitor_index])
        records.append({
            "t_fin_ut": float((stop - 1) * dt),
            "omega_linea": line,
            "A_linea_source": float(src_amp[line_index]),
            "A_linea_seguidor": a_line,
            "A_force_linea_sobre_seguidor": float(force_amp[line_index]),
            "ganancia_empirica_seguidor": float(
                a_line / max(float(force_amp[line_index]), 1e-300)),
            "omega_competidor": float(omega[competitor_index]),
            "A_competidor": a_comp,
            "rho_dominancia": float(a_line / max(a_comp, 1e-300)),
        })
    rho = np.array([r["rho_dominancia"] for r in records])
    episodes = runs_true(rho > 1.0, max(int(math.ceil(SUSTAIN_UT / HOP_UT)), 1))
    first = records[episodes[0][0]]["t_fin_ut"] if episodes else None
    return {
        "W_ut": WINDOW_UT, "hop_ut": HOP_UT,
        "resolucion_rayleigh_omega": rayleigh,
        "source_candidate": source, "follower_candidate": follower,
        "primer_rho_gt_1_sostenido_fin_ventana_ut": first,
        "episodios_indices": [list(x) for x in episodes],
        "rho_final": float(rho[-1]), "rho_max": float(np.max(rho)),
        "n_saltos_linea_mayor_2Rayleigh": jumps,
        "serie": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worldlines-root", required=True, type=Path)
    parser.add_argument("--gate-a", required=True, type=Path)
    parser.add_argument("--gate-b-arrival", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    root = args.worldlines_root.expanduser().resolve()
    gate_a = json.loads(args.gate_a.expanduser().resolve().read_text())
    arrival = json.loads(args.gate_b_arrival.expanduser().resolve().read_text())
    run_index = index_runs(root)
    a_by_id = {p["transported"]["run_id"]: p for p in gate_a["pairs"]}
    rayleigh = 2.0 * np.pi / WINDOW_UT

    result_pairs = []
    for pair_b in arrival["pairs"]:
        t_id = pair_b["transported"]["run_id"]
        pair_a = a_by_id[t_id]
        if float(pair_a["transported"]["dw_temprana"]) < rayleigh:
            continue
        phase_close = pair_a["transported"]["fase_cinematica"][
            "primer_cierre_robusto_fin_ventana_ut"]
        limit_ut = min(max(float(phase_close) + WINDOW_UT, 2.0 * WINDOW_UT), 60.0)
        arms = {}
        for arm in ("transported", "fresh"):
            record_b = pair_b[arm]
            run_id = record_b["run_id"]
            source = int(record_b["linea_compartida_llegada"]["nodo_dominante_Q"])
            raw_series, provenance = read_series(run_index[run_id], limit_ut)
            dom = dominance_series(raw_series, source)
            arms[arm] = {"run_id": run_id, "procedencia": provenance,
                         "dominancia": dom,
                         "dw_temprana_gate_A": float(pair_a[arm]["dw_temprana"]),
                         "separacion_resoluble_W8": bool(
                             float(pair_a[arm]["dw_temprana"]) >= rayleigh)}
        t_dom = arms["transported"]["dominancia"][
            "primer_rho_gt_1_sostenido_fin_ventana_ut"]
        f_dom = arms["fresh"]["dominancia"][
            "primer_rho_gt_1_sostenido_fin_ventana_ut"]
        result_pairs.append({
            **arms,
            "fase_transportada": {
                "primer_cierre_robusto_fin_ventana_ut": phase_close,
                "delta_dominancia_menos_fase_ut": (
                    float(t_dom - phase_close) if t_dom is not None else None),
            },
            "horizonte_leido_ut": limit_ut,
            "fresh_tiene_dominancia_sostenida": f_dom is not None,
        })

    t_first = [p["transported"]["dominancia"][
        "primer_rho_gt_1_sostenido_fin_ventana_ut"] for p in result_pairs]
    f_first_resolvable = [p["fresh"]["dominancia"][
        "primer_rho_gt_1_sostenido_fin_ventana_ut"] for p in result_pairs
        if p["fresh"]["separacion_resoluble_W8"]]
    deltas = [p["fase_transportada"]["delta_dominancia_menos_fase_ut"]
              for p in result_pairs
              if p["fase_transportada"]["delta_dominancia_menos_fase_ut"] is not None]
    result = {
        "_meta": {
            "pregunta": "Gate B2: la linea domina antes, junto o despues del cierre de fase",
            "worldlines_root": str(root),
            "policy": "read-only; chunks verificados; salida sólo logs/link_grumo",
        },
        "metodo": {
            "W_ut": WINDOW_UT, "hop_ut": HOP_UT,
            "resolucion_rayleigh_omega": rayleigh,
            "linea": "pico Q móvil del nodo dominante Q fijado en llegada",
            "competidor": "máximo Q del seguidor fuera de ±1 Rayleigh",
            "dominancia": "rho=A_linea/A_competidor >1 sostenido 2 u.t.",
            "timestamp": "fin de ventana; no es instante causal",
        },
        "summary": {
            "n_pares_transportados_resolubles": len(result_pairs),
            "n_t_con_dominancia_sostenida": sum(x is not None for x in t_first),
            "n_f_resolubles": len(f_first_resolvable),
            "n_f_resolubles_con_dominancia_sostenida": sum(
                x is not None for x in f_first_resolvable),
            "n_dominancia_antes_fase": sum(x < 0.0 for x in deltas),
            "n_dominancia_junto_fase_2ut": sum(abs(x) <= 2.0 for x in deltas),
            "n_dominancia_despues_fase": sum(x > 2.0 for x in deltas),
            "mediana_delta_dominancia_menos_fase_ut": (
                float(np.median(deltas)) if deltas else None),
        },
        "advertencias": [
            "banco seleccionado por éxito transported; no estima prevalencia",
            "rho es dominancia espectral, no prueba autonomía ni energía",
            "la línea móvil puede saltar; se publica el conteo de saltos",
            "W8 impide precedencias más finas que su soporte temporal",
        ],
        "pairs": result_pairs,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate B2: {len(result_pairs)} pares resolubles W8")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
