"""EXPRIMIR C1 — pasada 3 [M1-recolección]: la EVOLUCIÓN (cómo cambia la lengua en el tiempo).

  1. FRECUENCIA VENTANEADA por nodo: 12 ventanas de 5 u.t. → Δω_film(t) por arista — el
     PULLING (convergencia de frecuencias) es la firma de interacción aun sin lock.
  2. PARES SIN ARISTA (cadenas: el par (0,2) no conectado) — el NULO del lock por par:
     rw y episodios de un par que sólo se ve a través del medio.
  3. Canales ep_* restantes (E_coh, E_mem, Lambda, Lambda_coup, N_eff, S_E): percentiles
     + tramos (primeras/últimas 10 u.t.), transported y fresh.
Salida: data/c1_exprimido/v3_<eval_id>.json. READ-ONLY del respaldo.
"""
import json
import time
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
DISK = Path("/Volumes/ExternalDisk/doft-study06-fundamental-lock-dynamics")
SWEEP = DISK / "data/processed/ola1_v4_c1/ola2/sweep"
OUT = STUDY07 / "data/c1_exprimido"

SUB = 100
DT_SUB = SUB * 8e-5
W_VENT = 125
N_VENTANAS, ANCHO_UT = 12, 5.0
CANALES_EP = ("ep_E_coh", "ep_E_mem", "ep_Lambda", "ep_Lambda_coup", "ep_N_eff", "ep_S_E")


def _freq_ventaneada(theta_col):
    filas = []
    for v in range(N_VENTANAS):
        a = int(v * ANCHO_UT / DT_SUB)
        b = int((v + 1) * ANCHO_UT / DT_SUB)
        th = np.unwrap(theta_col[a:b])
        filas.append(float(np.median(np.gradient(th, DT_SUB))) if th.size > 10 else None)
    return filas


def _rw_stats(theta, i, j):
    z = np.exp(1j * (theta[:, i] - theta[:, j]))
    kern = np.ones(W_VENT) / W_VENT
    rw = np.abs(np.convolve(z, kern, mode="valid"))
    return {"rw_final": float(np.mean(rw[-1250:])), "rw_max": float(np.max(rw)),
            "frac_090": float(np.mean(rw >= 0.90)), "frac_095": float(np.mean(rw >= 0.95))}


def exprimir_v3(ev):
    m = ev["metrics_raw"]
    film = SWEEP / "lock_band_series" / Path(m["lock_band_series_path"]).name
    with np.load(film, allow_pickle=False) as f:
        edges = f["meta_edges"][:]
        theta = f["theta_nodes"][::SUB]
        th_f = f["control_formation_fresh_theta_nodes"][::SUB]
        ep = {c: f[c][::SUB] for c in CANALES_EP}
        ep_f = {c: f["control_formation_fresh_" + c][::SUB] for c in CANALES_EP}

    n = theta.shape[1]
    frecs = [_freq_ventaneada(theta[:, j]) for j in range(n)]
    # pulling por arista: |Δω_film| en cada ventana
    pulling = []
    for (i, j) in edges:
        serie = [abs(a - b) if a is not None and b is not None else None
                 for a, b in zip(frecs[i], frecs[j])]
        pulling.append({"i": int(i), "j": int(j), "dw_ventanas": serie})
    # pares SIN arista (el nulo): todo par de nodos no conectado
    con_arista = {frozenset((int(i), int(j))) for i, j in edges}
    nulos = []
    for i in range(n):
        for j in range(i + 1, n):
            if frozenset((i, j)) not in con_arista:
                reg = {"i": i, "j": j}
                reg.update(_rw_stats(theta, i, j))
                reg["dw_ventanas"] = [abs(a - b) if a is not None and b is not None else None
                                      for a, b in zip(frecs[i], frecs[j])]
                nulos.append(reg)
    canales = {}
    for c in CANALES_EP:
        for etiqueta, serie in ((c, ep[c]), (c + "_fresh", ep_f[c])):
            canales[etiqueta] = {
                "percentiles": [float(np.percentile(serie, q)) for q in (5, 50, 95)],
                "ini10": float(np.mean(serie[:int(10 / DT_SUB)])),
                "fin10": float(np.mean(serie[-int(10 / DT_SUB):]))}
    return {"eval_id": ev["eval_id"], "freq_ventaneada": frecs, "pulling": pulling,
            "pares_sin_arista": nulos, "canales_ep": canales,
            "ventanas": {"n": N_VENTANAS, "ancho_ut": ANCHO_UT}}


def main():
    evs = [json.loads(l) for l in open(SWEEP / "evaluations.jsonl")]
    listos = {p.stem.replace("v3_", "") for p in OUT.glob("v3_*.json")}
    t0 = time.time()
    for k, ev in enumerate(evs):
        if ev["eval_id"] in listos:
            continue
        reg = exprimir_v3(ev)
        (OUT / f"v3_{ev['eval_id']}.json").write_text(json.dumps(reg, indent=1))
        print(f"[{k+1}/{len(evs)}] v3 {ev['eval_id'][:12]} ({time.time()-t0:.0f}s)", flush=True)
    print(f"[fin v3] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
