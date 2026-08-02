#!/usr/bin/env python3
"""Gate B1: cosecha del estado de llegada sin integrar films nuevos.

Lee únicamente chunk_00000 de los nueve remotos transported y sus fresh apareados. Verifica
COMPLETE, manifiesto y SHA del chunk antes de medir. La ventana [0.5, 5.0] u.t. es fija y no
usa el outcome. Sólo puede escribir debajo de logs/link_grumo.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from baseline_census import safe_output


T0_UT = 0.5
T1_UT = 5.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rms(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(values, dtype=float) ** 2)))


def spectral_peak(values: np.ndarray, dt: float,
                  lo_omega: float = 2.0, hi_omega: float = 50.0) -> dict:
    y = np.asarray(values, dtype=float)
    y = y - float(np.mean(y))
    window = np.hanning(len(y))
    n_fft = 1 << int(math.ceil(math.log2(max(4 * len(y), 2))))
    spectrum = np.fft.rfft(y * window, n=n_fft)
    omega = 2.0 * np.pi * np.fft.rfftfreq(n_fft, d=dt)
    mask = (omega >= lo_omega) & (omega <= hi_omega)
    if not np.any(mask):
        return {"omega": None, "amplitud": 0.0}
    candidates = np.flatnonzero(mask)
    index = int(candidates[np.argmax(np.abs(spectrum[candidates]))])
    amplitude = 2.0 * float(abs(spectrum[index])) / max(float(np.sum(window)), 1e-300)
    return {"omega": float(omega[index]), "amplitud": amplitude,
            "resolucion_grid_omega": float(omega[1] - omega[0]),
            "resolucion_rayleigh_omega": float(2.0 * np.pi / (len(y) * dt))}


def spectral_amplitude(values: np.ndarray, dt: float, omega: float) -> float:
    """Amplitud Hann en una frecuencia declarada; no convierte zero-padding en resolución."""
    y = np.asarray(values, dtype=float)
    y = y - float(np.mean(y))
    window = np.hanning(len(y))
    times = np.arange(len(y), dtype=float) * dt
    coefficient = np.sum(y * window * np.exp(-1j * float(omega) * times))
    return 2.0 * float(abs(coefficient)) / max(float(np.sum(window)), 1e-300)


def index_runs(root: Path) -> dict[str, Path]:
    out = {}
    for unit in root.glob("*/unidades/*"):
        if unit.is_dir() and (unit / "manifest.json").is_file():
            out[unit.name] = unit
    return out


def verify_and_load_chunk0(run_dir: Path) -> tuple[dict, dict, dict[str, np.ndarray]]:
    manifest_path = run_dir / "manifest.json"
    complete_path = run_dir / "COMPLETE"
    chunk_path = run_dir / "worldline" / "chunk_00000.npz"
    if not all(p.is_file() for p in (manifest_path, complete_path, chunk_path)):
        raise RuntimeError(f"artefacto incompleto: {run_dir}")
    manifest = json.loads(manifest_path.read_text())
    complete = json.loads(complete_path.read_text())
    manifest_sha = sha256(manifest_path)
    chunk_sha = sha256(chunk_path)
    if manifest_sha != complete["manifest_sha"]:
        raise RuntimeError(f"manifest SHA inválido: {run_dir.name}")
    if chunk_sha != complete["chunk_shas"][0]:
        raise RuntimeError(f"chunk_00000 SHA inválido: {run_dir.name}")
    with np.load(chunk_path, allow_pickle=False) as npz:
        arrays = {key: np.asarray(npz[key]) for key in npz.files
                  if key != "rng_state_json" and not key.startswith("kicks_")}
    provenance = {"run_dir": str(run_dir), "manifest_sha256": manifest_sha,
                  "chunk_00000_sha256": chunk_sha}
    return manifest, provenance, arrays


def node_metrics(state: np.ndarray, drive: np.ndarray, mask: np.ndarray,
                 dt: float, info: dict) -> dict:
    n_modes = int(info["n_modes"])
    n_z = int(info["n_z"])
    n_layers = int(info["n_layers"])
    layers = list(info["layers_present"])
    q_indices = np.array([i for i, layer in enumerate(info["capas_por_modo"])
                          if layer == "Q"], dtype=int)
    if q_indices.size == 0:
        q_indices = np.arange(n_modes)

    x = state[mask, :n_modes]
    v = state[mask, n_modes:2 * n_modes]
    force = drive[mask]
    x_sum = np.sum(x, axis=1)
    v_sum = np.sum(v, axis=1)
    q_x = np.sum(x[:, q_indices], axis=1)
    q_v = np.sum(v[:, q_indices], axis=1)
    power = force * v_sum  # drive se aplica como fuerza idéntica a cada modo
    start = 2 * n_modes + n_z
    b0 = state[0, start:start + n_layers]
    e0 = state[0, start + n_layers:start + 2 * n_layers]
    last_index = int(np.flatnonzero(mask)[-1])
    b1 = state[last_index, start:start + n_layers]
    e1 = state[last_index, start + n_layers:start + 2 * n_layers]
    f_rms = rms(force)
    v_rms = rms(v_sum)
    p_mean = float(np.mean(power))
    drive_peak = spectral_peak(force, dt)
    q_peak = spectral_peak(q_x, dt)

    return {
        "drive": {"rms": f_rms, "mean_abs": float(np.mean(np.abs(force))),
                  "p95_abs": float(np.percentile(np.abs(force), 95)),
                  "pico_espectral": drive_peak},
        "respuesta": {
            "emision_x_rms": rms(float(info["emission_scale"]) * x_sum),
            "emision_v_rms": rms(float(info["emission_scale"]) * v_sum),
            "Q_x_rms": rms(q_x), "Q_v_rms": rms(q_v),
            "pico_Q": q_peak,
        },
        "trabajo_link": {
            "potencia_media_entrada": p_mean,
            "trabajo_neto": float(np.sum(power) * dt),
            "fraccion_potencia_positiva": float(np.mean(power > 0.0)),
            "factor_potencia": float(p_mean / max(f_rms * v_rms, 1e-300)),
            "convencion": "P_i = drive_i * suma(v_modos_i); P>0 inyecta al nodo",
        },
        "estado_lento": {
            "capas": layers,
            "b_inicio": b0.tolist(), "e_inicio": e0.tolist(),
            "b_fin_ventana": b1.tolist(), "e_fin_ventana": e1.tolist(),
            "norma_b_inicio": float(np.linalg.norm(b0)),
            "norma_e_inicio": float(np.linalg.norm(e0)),
        },
    }


def run_metrics(run_id: str, run_dir: Path, gate_a_record: dict) -> dict:
    manifest, provenance, arrays = verify_and_load_chunk0(run_dir)
    ticks = arrays["ticks"]
    dt = float(manifest["dt"])
    times = ticks * dt
    mask = (times >= T0_UT) & (times < T1_UT)
    if int(np.sum(mask)) < 100:
        raise RuntimeError(f"ventana de llegada ausente: {run_id}")
    nodes = []
    for j, info in enumerate(manifest["por_nodo"]):
        nodes.append(node_metrics(arrays[f"estados_nodo{j}"], arrays["drive"][:, j],
                                  mask, dt, info))

    # Referencia compartida descriptiva: línea Q del nodo de mayor amplitud Q en llegada.
    # Evita llamar "drive" al pico global de la fuerza, que puede vivir en otra capa.
    source_candidate = int(np.argmax([node["respuesta"]["Q_x_rms"] for node in nodes]))
    line_omega = float(nodes[source_candidate]["respuesta"]["pico_Q"]["omega"])
    line_by_node = []
    for j, info in enumerate(manifest["por_nodo"]):
        state = arrays[f"estados_nodo{j}"]
        n_modes = int(info["n_modes"])
        q_indices = np.array([i for i, layer in enumerate(info["capas_por_modo"])
                              if layer == "Q"], dtype=int)
        if q_indices.size == 0:
            q_indices = np.arange(n_modes)
        q_x = np.sum(state[mask, :n_modes][:, q_indices], axis=1)
        force = arrays["drive"][mask, j]
        self_omega = float(gate_a_record["omega_temprana"][j])
        q_at_line = spectral_amplitude(q_x, dt, line_omega)
        q_at_self = spectral_amplitude(q_x, dt, self_omega)
        force_at_line = spectral_amplitude(force, dt, line_omega)
        rayleigh = float(2.0 * np.pi / (int(np.sum(mask)) * dt))
        separation = abs(line_omega - self_omega)
        resolvable = bool(separation >= rayleigh)
        line_by_node.append({
            "node": j,
            "omega_self_gate_A": self_omega,
            "separacion_omega": separation,
            "resoluble_rayleigh": resolvable,
            "A_Q_en_linea": q_at_line,
            "A_Q_en_self": q_at_self,
            "A_force_en_linea": force_at_line,
            "dominancia_linea_sobre_self": (float(q_at_line / max(q_at_self, 1e-300))
                                              if resolvable else None),
            "ganancia_empirica_AQ_sobre_AF": float(
                q_at_line / max(force_at_line, 1e-300)),
        })
    follower = 1 - source_candidate

    drive_sum = sum(node["drive"]["rms"] for node in nodes)
    q_sum = sum(node["respuesta"]["Q_x_rms"] for node in nodes)
    work = [node["trabajo_link"]["trabajo_neto"] for node in nodes]
    b_values = [x for node in nodes for x in node["estado_lento"]["b_inicio"]]
    e_values = [x for node in nodes for x in node["estado_lento"]["e_inicio"]]
    return {
        "run_id": run_id,
        "brazo": gate_a_record["brazo"],
        "categoria_cinematica": gate_a_record["categoria_cinematica"],
        "E0_reporte": float(gate_a_record["E0"]),
        "omega_temprana_gate_A": gate_a_record["omega_temprana"],
        "procedencia": provenance,
        "ventana_ut": [T0_UT, T1_UT],
        "n_muestras": int(np.sum(mask)),
        "nodos": nodes,
        "linea_compartida_llegada": {
            "criterio": "pico Q del nodo con mayor Q_x_rms en [0.5,5.0]",
            "nodo_dominante_Q": source_candidate,
            "nodo_seguidor_candidato": follower,
            "omega_linea": line_omega,
            "resolucion_rayleigh_omega": float(
                2.0 * np.pi / (int(np.sum(mask)) * dt)),
            "por_nodo": line_by_node,
            "dominancia_seguidor": line_by_node[follower]["dominancia_linea_sobre_self"],
        },
        "agregado": {
            "drive_rms_suma": float(drive_sum),
            "Q_x_rms_suma": float(q_sum),
            "trabajo_neto_link": float(sum(work)),
            "trabajo_entregado_a_nodos": float(sum(max(x, 0.0) for x in work)),
            "trabajo_extraido_de_nodos": float(sum(min(x, 0.0) for x in work)),
            "n_nodos_con_trabajo_positivo": int(sum(x > 0.0 for x in work)),
            "norma_b_inicio": float(np.linalg.norm(b_values)),
            "norma_e_inicio": float(np.linalg.norm(e_values)),
        },
    }


def ratio(a: float, b: float) -> float:
    return float(a / max(abs(b), 1e-300))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worldlines-root", required=True, type=Path)
    parser.add_argument("--gate-a", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = safe_output(args.output)
    root = args.worldlines_root.expanduser().resolve()
    gate_a = json.loads(args.gate_a.expanduser().resolve().read_text())
    run_index = index_runs(root)

    pairs = []
    for pair_a in gate_a["pairs"]:
        records = {}
        for arm in ("transported", "fresh"):
            source = pair_a[arm]
            run_id = source["run_id"]
            if run_id not in run_index:
                raise RuntimeError(f"no se encontró {run_id} bajo {root}")
            records[arm] = run_metrics(run_id, run_index[run_id], source)
        t = records["transported"]["agregado"]
        f = records["fresh"]["agregado"]
        contrast = {
            "E0_t_sobre_f": ratio(records["transported"]["E0_reporte"],
                                   records["fresh"]["E0_reporte"]),
            "drive_rms_t_sobre_f": ratio(t["drive_rms_suma"], f["drive_rms_suma"]),
            "Q_rms_t_sobre_f": ratio(t["Q_x_rms_suma"], f["Q_x_rms_suma"]),
            "norma_b_t_menos_f": float(t["norma_b_inicio"] - f["norma_b_inicio"]),
            "norma_e_t_sobre_f": ratio(t["norma_e_inicio"], f["norma_e_inicio"]),
            "trabajo_neto_t": t["trabajo_neto_link"],
            "trabajo_neto_f": f["trabajo_neto_link"],
            "n_receptores_netos_t": t["n_nodos_con_trabajo_positivo"],
            "n_receptores_netos_f": f["n_nodos_con_trabajo_positivo"],
            "dominancia_seguidor_t": records["transported"][
                "linea_compartida_llegada"]["dominancia_seguidor"],
            "dominancia_seguidor_f": records["fresh"][
                "linea_compartida_llegada"]["dominancia_seguidor"],
        }
        pairs.append({**records, "contraste_apareado": contrast})

    contrasts = [p["contraste_apareado"] for p in pairs]
    low_e = [c for c in contrasts if c["E0_t_sobre_f"] < 1.0]
    dom_t = [c["dominancia_seguidor_t"] for c in contrasts
             if c["dominancia_seguidor_t"] is not None]
    dom_f = [c["dominancia_seguidor_f"] for c in contrasts
             if c["dominancia_seguidor_f"] is not None]
    summary = {
        "n_pares": len(pairs),
        "n_E0_t_mayor": sum(c["E0_t_sobre_f"] > 1.0 for c in contrasts),
        "n_drive_t_mayor": sum(c["drive_rms_t_sobre_f"] > 1.0 for c in contrasts),
        "n_Q_t_mayor": sum(c["Q_rms_t_sobre_f"] > 1.0 for c in contrasts),
        "n_b_t_mayor": sum(c["norma_b_t_menos_f"] > 0.0 for c in contrasts),
        "n_link_neto_disipativo_t": sum(c["trabajo_neto_t"] < 0.0 for c in contrasts),
        "n_link_neto_disipativo_f": sum(c["trabajo_neto_f"] < 0.0 for c in contrasts),
        "n_t_con_receptor_neto": sum(c["n_receptores_netos_t"] > 0 for c in contrasts),
        "n_f_con_receptor_neto": sum(c["n_receptores_netos_f"] > 0 for c in contrasts),
        "linea_seguidor_resoluble": {
            "n_t": len(dom_t), "n_f": len(dom_f),
            "n_domina_t": sum(x > 1.0 for x in dom_t),
            "n_domina_f": sum(x > 1.0 for x in dom_f),
            "mediana_t": float(np.median(dom_t)) if dom_t else None,
            "mediana_f": float(np.median(dom_f)) if dom_f else None,
        },
        "medianas_ratios": {
            "E0_t_sobre_f": float(np.median([c["E0_t_sobre_f"] for c in contrasts])),
            "drive_t_sobre_f": float(np.median(
                [c["drive_rms_t_sobre_f"] for c in contrasts])),
            "Q_t_sobre_f": float(np.median([c["Q_rms_t_sobre_f"] for c in contrasts])),
        },
        "subgrupo_E0_t_menor": {
            "n": len(low_e),
            "n_drive_t_mayor": sum(c["drive_rms_t_sobre_f"] > 1.0 for c in low_e),
            "n_Q_t_mayor": sum(c["Q_rms_t_sobre_f"] > 1.0 for c in low_e),
            "n_b_t_mayor": sum(c["norma_b_t_menos_f"] > 0.0 for c in low_e),
        },
        "categorias": dict(Counter(
            p["transported"]["categoria_cinematica"] for p in pairs)),
    }
    result = {
        "_meta": {
            "pregunta": "Gate B1: qué cambia la biografía en una ventana fija de llegada",
            "worldlines_root": str(root),
            "gate_a": str(args.gate_a.expanduser().resolve()),
            "policy": "worldlines read-only; only chunk_00000; output logs/link_grumo",
        },
        "ventana_prereg": [T0_UT, T1_UT],
        "advertencias": [
            "b!=0 identifica transported por construcción; no prueba causalidad ni salud",
            "P=drive*suma(v) es trabajo externo exacto sobre modos, no energía total del nodo",
            "el banco fue seleccionado por éxito transported; los conteos no son prevalencias",
            "el pico espectral de 4.5 u.t. describe llegada y tiene resolución limitada",
            "dominancia drive/self sólo se publica si la separación supera Rayleigh=2pi/T",
        ],
        "summary": summary,
        "pairs": pairs,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate B1: {len(pairs)} pares, 18 chunk_00000 verificados")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
