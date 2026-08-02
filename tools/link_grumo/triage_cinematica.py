#!/usr/bin/env python3
"""Gate A: cinemática read-only de remotos transported y sus fresh apareados.

No intenta identificar un mecanismo. Describe quién se desplaza, si la frecuencia final
queda dentro o fuera del intervalo de llegada y cuándo la pendiente de diferencia de fase
se vuelve pequeña de forma sostenida. Sólo escribe bajo logs/link_grumo.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np

from baseline_census import (FALSE_ZONE, cargar_filas, enriquecer_remotos,
                             indexar_reportes, indexar_views_w8, lock60,
                             safe_output)


FIT_WINDOWS_UT = (4.0, 8.0)
HOP_UT = 0.5
SUSTAIN_UT = 2.0


def runs_true(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    """Intervalos [inicio, fin) que sostienen True al menos min_len muestras."""
    out: list[tuple[int, int]] = []
    start: int | None = None
    for i, value in enumerate(mask.tolist() + [False]):
        if value and start is None:
            start = i
        elif not value and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    return out


def rolling_slopes(dphi: np.ndarray, dt: float, window_ut: float,
                   hop_ut: float) -> tuple[np.ndarray, np.ndarray]:
    """Pendiente LS en ventanas móviles, sin derivar tick a tick."""
    stride = max(int(round(0.008 / dt)), 1)
    y = dphi[::stride]
    dt_sub = dt * stride
    n_per = max(int(round(window_ut / dt_sub)), 4)
    hop = max(int(round(hop_ut / dt_sub)), 1)
    starts = np.arange(0, len(y) - n_per + 1, hop, dtype=int)
    x = (np.arange(n_per, dtype=float) - (n_per - 1) / 2.0) * dt_sub
    slopes = np.array([(y[start:start + n_per] @ x) / float(x @ x)
                       for start in starts])
    centers = (starts + (n_per - 1) / 2.0) * dt_sub
    return centers, slopes


def ruta_frecuencias(early: np.ndarray, late: np.ndarray, zone: float) -> dict:
    target = float(np.mean(late))
    lo, hi = float(np.min(early)), float(np.max(early))
    span = max(hi - lo, 1e-12)
    outside = max(lo - target, target - hi, 0.0)
    distance_to_arrivals = np.abs(early - target)
    travel = np.abs(late - early)
    late_dw = float(abs(late[0] - late[1]))

    if late_dw >= zone:
        category = "sin_cierre_tardio"
    elif outside > zone:
        category = "linea_fuera_intervalo_llegada"
    elif float(np.min(distance_to_arrivals)) <= 0.20 * span:
        category = "ancla_y_seguidor"
    else:
        category = "convergencia_compartida"

    return {
        "categoria_cinematica": category,
        "omega_temprana": early.tolist(),
        "omega_tardia": late.tolist(),
        "linea_tardia_media": target,
        "dw_temprana": float(abs(early[0] - early[1])),
        "dw_tardia": late_dw,
        "cierre_relativo": float(late_dw / span),
        "desplazamiento_por_nodo": travel.tolist(),
        "fraccion_movimiento_nodo0": float(travel[0] / max(float(np.sum(travel)), 1e-12)),
        "distancia_linea_a_llegada_mas_cercana_sobre_dw":
            float(np.min(distance_to_arrivals) / span),
        "distancia_fuera_intervalo": float(outside),
    }


def analizar_fila(fila: dict, reports: dict[str, dict], views: dict[str, Path]) -> dict:
    report = reports.get(fila["run_id"])
    if report is None:
        raise RuntimeError(f"sin REPORTE para {fila['run_id']}")
    wl_hash = str(report["worldline_hash"])
    data_path = views.get(wl_hash[:16])
    if data_path is None:
        raise RuntimeError(f"sin vista W8 para {fila['run_id']} ({wl_hash[:16]})")
    manifest_path = data_path.with_name("manifest.json")
    manifest = json.loads(manifest_path.read_text())
    dt = float(manifest["dt"])

    with np.load(data_path) as npz:
        theta = np.asarray(npz["theta"], dtype=float)
        omega = np.asarray(npz["omega_nodo"], dtype=float)

    # Reproduce la corrección elíptica usada por par_link, pero conserva la trayectoria.
    phases = []
    for node in range(2):
        w_full = max(float(omega[node, 0]), 1e-9)
        phase = np.arctan2(np.sin(theta[:, node]) / w_full,
                           np.cos(theta[:, node]))
        phases.append(np.unwrap(phase))
    dphi = phases[0] - phases[1]
    scales = {}
    first_by_scale = []
    for window_ut in FIT_WINDOWS_UT:
        times, slopes = rolling_slopes(dphi, dt, window_ut, HOP_UT)
        zone_scale = 1.1 / window_ut
        closed = np.abs(slopes) < zone_scale
        min_bins = max(int(math.ceil(SUSTAIN_UT / HOP_UT)), 1)
        episodes = runs_true(closed, min_bins)
        # Timestamp conservador: fin de la primera ventana que inicia el sostén.
        first_close = (float(times[episodes[0][0]] + window_ut / 2.0)
                       if episodes else None)
        if first_close is not None:
            first_by_scale.append(first_close)
        scales[f"W{int(window_ut)}"] = {
            "window_ut": window_ut,
            "hop_ut": HOP_UT,
            "umbral_abs_pendiente": zone_scale,
            "primer_cierre_sostenido_fin_ventana_ut": first_close,
            "episodios_centros_ut": [[float(times[a]), float(times[b - 1])]
                                      for a, b in episodes],
            "n_releases": max(len(episodes) - int(bool(episodes and episodes[-1][1]
                                                       == len(slopes))), 0),
            "fraccion_ventanas_cerradas": float(np.mean(closed)),
            "pendiente_mediana_temprana": float(np.median(slopes[times <= 10.0])),
            "pendiente_mediana_ult10": float(np.median(
                slopes[times >= times[-1] - 10.0])),
            "serie": {"t_centro_ut": times.tolist(), "d_dphi_dt": slopes.tolist()},
        }
    robust_first = max(first_by_scale) if len(first_by_scale) == len(FIT_WINDOWS_UT) else None
    phase_idx = min(int((robust_first or (len(dphi) * dt)) / dt), len(dphi) - 1)
    phase_winding_pre = float(abs(dphi[phase_idx] - dphi[0]) / (2.0 * np.pi))
    zone = FALSE_ZONE["W8"]

    record = {
        "run_id": fila["run_id"],
        "brazo": fila["brazo"],
        "par": fila["_par"],
        "worldline_hash": wl_hash,
        "block_i": fila["block_i"],
        "block_j": fila["block_j"],
        "dw_aislado": float(fila["_dw"]),
        "E0": float(report.get("metricas", {}).get("E0_nodo0", 0.0)
                    + report.get("metricas", {}).get("E0_nodo1", 0.0)),
        "detector": {
            "lock60_W8": lock60(fila, "W8"),
            "t_lock_W8": fila["W8"]["t_lock_ut"],
            "estado_W8": int(fila["W8"]["estado"]),
        },
        "fase_cinematica": {
            "sosten_ut": SUSTAIN_UT,
            "primer_cierre_robusto_fin_ventana_ut": robust_first,
            "vueltas_fase_antes_primer_cierre": phase_winding_pre,
            "escalas": scales,
        },
        "banderas": {
            "nodos_armonico": manifest.get("nodos_armonico", []),
            "nodos_mudos": manifest.get("nodos_mudos", []),
        },
    }
    record.update(ruta_frecuencias(omega[:, 1], omega[:, 2], zone))
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = args.source_root.expanduser().resolve()
    output = safe_output(args.output)

    filas, hashes = cargar_filas(source)
    reports = indexar_reportes(source)
    views = indexar_views_w8(source)
    remotos = enriquecer_remotos(filas, reports, views)
    strict_ids = {r["run_id"] for r in remotos if r["strict_remote"]}
    by_pair_arm = {(f["_par"], f["brazo"]): f for f in filas if not f["_self"]}
    t_rows = sorted((f for f in filas if f["run_id"] in strict_ids),
                    key=lambda f: f["run_id"])

    pairs = []
    for transported in t_rows:
        fresh = by_pair_arm.get((transported["_par"], "f"))
        if fresh is None:
            raise RuntimeError(f"sin fresh apareado para {transported['run_id']}")
        t_record = analizar_fila(transported, reports, views)
        f_record = analizar_fila(fresh, reports, views)
        arrival_delta = float(np.mean(np.abs(np.asarray(t_record["omega_temprana"])
                                             - np.asarray(f_record["omega_temprana"]))))
        pairs.append({
            "transported": t_record,
            "fresh": f_record,
            "contraste_apareado": {
                "E0_t_sobre_f": float(t_record["E0"] / max(f_record["E0"], 1e-300)),
                "transported_tiene_mas_E0": bool(t_record["E0"] > f_record["E0"]),
                "distancia_media_omega_temprana_t_vs_f": arrival_delta,
                "categorias_iguales": (t_record["categoria_cinematica"]
                                        == f_record["categoria_cinematica"]),
            },
        })

    def summarize(arm: str) -> dict:
        records = [p[arm] for p in pairs]
        return {
            "categorias": dict(Counter(r["categoria_cinematica"] for r in records)),
            "n_cierre_tardio": sum(r["dw_tardia"] < FALSE_ZONE["W8"] for r in records),
            "n_cierre_sostenido_por_pendiente": sum(
                r["fase_cinematica"]["primer_cierre_robusto_fin_ventana_ut"] is not None
                for r in records),
            "mediana_cierre_relativo": float(np.median(
                [r["cierre_relativo"] for r in records])),
            "mediana_E0": float(np.median([r["E0"] for r in records])),
        }

    e_ratios = [p["contraste_apareado"]["E0_t_sobre_f"] for p in pairs]
    arrival_deltas = [p["contraste_apareado"]["distancia_media_omega_temprana_t_vs_f"]
                      for p in pairs]
    result = {
        "_meta": {
            "pregunta": "Gate A: descripcion cinematica; no identifica mecanismo",
            "source_root": str(source),
            "input_sha256": hashes,
            "policy": "source read-only; output restricted to logs/link_grumo",
        },
        "criterios": {
            "cierre": ("pendiente LS en W4 y W8 por debajo de 1.1/W durante "
                       f"{SUSTAIN_UT} u.t.; timestamp = fin de ventana"),
            "ancla": "linea final dentro de 20% del dw inicial respecto de una llegada",
            "fuera_intervalo": ("linea final mas de la zona de falso-firme W8 fuera del "
                                 "intervalo de frecuencias tempranas"),
            "advertencia": "categorias descriptivas; no son nombres de mecanismos",
        },
        "summary": {"n_pares": len(pairs),
                    "transported": summarize("transported"),
                    "fresh": summarize("fresh"),
                    "apareado": {
                        "n_transportado_con_mas_E0": sum(
                            p["contraste_apareado"]["transported_tiene_mas_E0"]
                            for p in pairs),
                        "mediana_E0_t_sobre_f": float(np.median(e_ratios)),
                        "mediana_distancia_omega_temprana_t_vs_f":
                            float(np.median(arrival_deltas)),
                    }},
        "pairs": pairs,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] Gate A: {len(pairs)} transported + {len(pairs)} fresh")
    print(f"[link-grumo] salida: {output}")


if __name__ == "__main__":
    main()
