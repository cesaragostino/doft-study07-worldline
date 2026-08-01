"""EXPRIMIR C1 — pasada 2 [M1-recolección, SIN conclusiones] (COA 2026-07-30).

Junta lo que la pasada 1 no midió; produce datos, no veredictos:
  1. Δω EFECTIVO: frecuencia instantánea por nodo (dθ/dt, mediana robusta) en ventana
     temprana [0.5, 5.5] u.t. y tardía (última ventana) — la constitucional (omega_ref)
     puede no ser la que baila.
  2. FRICCIÓN POR ARISTA (proxy declarado): P_edge(t) ∝ w_γ·(v_em_i(t) − v_em_j(t−τ))²
     con v_em = Σv_modos del nodo (raw float32, submuestreado; retardo por interpolación
     lineal en muestras). Guardo perfiles (percentiles) + medias por tramo.
  3. COQUETEO: episodios de R_w≥0.90 (número, duración máxima, fracción total) por arista.
  4. ENFRIAMIENTO: percentiles de E(t) por nodo (curva del apagado, no sólo t_mitad).
Salida: data/c1_exprimido/v2_<eval_id>.json. READ-ONLY del respaldo.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
DISK = Path("/Volumes/ExternalDisk/doft-study06-fundamental-lock-dynamics")
SWEEP = DISK / "data/processed/ola1_v4_c1/ola2/sweep"
OUT = STUDY07 / "data/c1_exprimido"

SUB = 100
DT_SUB = SUB * 8e-5            # 8e-3 u.t. por muestra
W_VENT = 125                   # 1 u.t.


def _freq_efectiva(theta_col, lo_ut, hi_ut):
    """Mediana robusta de dθ/dt (rad/u.t.) en [lo, hi] u.t. — unwrap + gradiente."""
    a, b = int(lo_ut / DT_SUB), int(hi_ut / DT_SUB)
    th = np.unwrap(theta_col[a:b])
    if th.size < 10:
        return None
    return float(np.median(np.gradient(th, DT_SUB)))


def _episodios(rw, umbral=0.90):
    sobre = rw >= umbral
    n_ep, dur_max, corr = 0, 0, 0
    for s in sobre:
        if s:
            corr += 1
            dur_max = max(dur_max, corr)
        else:
            if corr >= W_VENT:      # episodio = sostuvo al menos 1 ventana
                n_ep += 1
            corr = 0
    if corr >= W_VENT:
        n_ep += 1
    return {"n_episodios": n_ep, "dur_max_ut": float(dur_max * DT_SUB),
            "frac_total": float(np.mean(sobre))}


def _rw_serie(theta, i, j):
    z = np.exp(1j * (theta[:, i] - theta[:, j]))
    kern = np.ones(W_VENT) / W_VENT
    return np.abs(np.convolve(z, kern, mode="valid"))


def exprimir_v2(ev):
    m = ev["metrics_raw"]
    film = SWEEP / "lock_band_series" / Path(m["lock_band_series_path"]).name
    with np.load(film, allow_pickle=False) as f:
        edges = f["meta_edges"][:]
        offs = f["meta_node_mode_offsets"][:]
        w_g = f["meta_edge_w_gamma"][:]
        tau_e = f["meta_edge_tau"][:]
        theta = f["theta_nodes"][::SUB]
        E = f["E_nodes"][::SUB]
        raw_v = f["raw_v"][::SUB].astype(np.float64)
        th_f = f["control_formation_fresh_theta_nodes"][::SUB]

    n_nodos = theta.shape[1]
    # 1 · frecuencia efectiva por nodo (temprana y tardía) + fresh temprana
    frecs = []
    for j in range(n_nodos):
        frecs.append({"temprana": _freq_efectiva(theta[:, j], 0.5, 5.5),
                      "tardia": _freq_efectiva(theta[:, j], 55.0, 59.5),
                      "fresh_temprana": _freq_efectiva(th_f[:, j], 0.5, 5.5)})
    # 2 · fricción por arista: v de emisión por nodo (Σ v modos; escala irrelevante)
    v_em = np.stack([raw_v[:, a:b].sum(axis=1) for a, b in zip(offs[:-1], offs[1:])], axis=1)
    t_idx = np.arange(v_em.shape[0], dtype=np.float64)
    friccion = []
    for e, (i, j) in enumerate(edges):
        d_samp = float(tau_e[e]) / DT_SUB
        atras = t_idx - d_samp
        v_j_ret = np.interp(atras, t_idx, v_em[:, j])
        v_i_ret = np.interp(atras, t_idx, v_em[:, i])
        # potencia del damper en ambos sentidos del vínculo (proxy simétrico)
        p_ij = float(w_g[e]) * (v_em[:, i] - v_j_ret) ** 2
        p_ji = float(w_g[e]) * (v_em[:, j] - v_i_ret) ** 2
        p = 0.5 * (p_ij + p_ji)
        recorte = slice(int(np.ceil(d_samp)) + 1, None)   # sin el borde sin historia
        pv = p[recorte]
        friccion.append({
            "i": int(i), "j": int(j), "tau": float(tau_e[e]),
            "p_edge_percentiles": [float(np.percentile(pv, q))
                                   for q in (5, 25, 50, 75, 95)],
            "p_edge_primeras_10ut": float(np.mean(pv[:int(10 / DT_SUB)])),
            "p_edge_ultimas_10ut": float(np.mean(pv[-int(10 / DT_SUB):])),
        })
    # 3 · coqueteo por arista (transported y fresh)
    coqueteo = []
    for (i, j) in edges:
        rw = _rw_serie(theta, i, j)
        rw_f = _rw_serie(th_f, i, j)
        reg = {"i": int(i), "j": int(j)}
        reg.update(_episodios(rw))
        reg["fresh"] = _episodios(rw_f)
        # fricción por arista pre/post primer episodio firme (si existe)
        coqueteo.append(reg)
    # 4 · curva de enfriamiento por nodo (percentiles temporales de E)
    enfriamiento = []
    marcas = [0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 59.0]
    for j in range(n_nodos):
        e = E[:, j]
        enfriamiento.append({
            "muestras_ut": marcas,
            "E_en_marcas": [float(e[min(int(t / DT_SUB), len(e) - 1)]) for t in marcas]})
    return {"eval_id": ev["eval_id"], "frecuencias": frecs, "friccion_arista": friccion,
            "coqueteo": coqueteo, "enfriamiento": enfriamiento}


def main():
    evs = [json.loads(l) for l in open(SWEEP / "evaluations.jsonl")]
    listos = {p.stem.replace("v2_", "") for p in OUT.glob("v2_*.json")}
    t0 = time.time()
    for k, ev in enumerate(evs):
        if ev["eval_id"] in listos:
            continue
        reg = exprimir_v2(ev)
        (OUT / f"v2_{ev['eval_id']}.json").write_text(json.dumps(reg, indent=1))
        print(f"[{k+1}/{len(evs)}] v2 {ev['eval_id'][:12]} ({time.time()-t0:.0f}s)", flush=True)
    print(f"[fin v2] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
