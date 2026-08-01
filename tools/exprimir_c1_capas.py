"""EXPRIMIR C1 — pasada 5 [M1-prereg §5]: CAPTURAS SECUNDARIAS POR CAPA (hipótesis COA).

«La portadora acerca; la secundaria decide.» Por film, del raw por-modo:
  · θ_capa por nodo (atan2(Σv_capa, Σx_capa), capas Q/S1/S2 por meta_mode_layer)
  · amplitud por capa (piso de MUDEZ por capa — advertencia DD: sin señal no hay lock)
  · por arista × capa: rw de fase corregida §16, W=4 u.t. (punto ciego 0.275 DECLARADO —
    verdad sintética validada: captura/release construidos detectados a ±W, control limpio),
    episodios (umbral 0.90, sostén 1W), frac, dur_max, releases (fines de episodio).
Sólo transported (el fresh no trae raw — declarado). Salida: v5_<eval_id>.json.
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
W = 500                    # 4 u.t.
UMBRAL = 0.90
CAPAS = {0: "Q", 1: "S1", 2: "S2"}


def _rw_corr(th_i, th_j):
    fases = []
    for th in (th_i, th_j):
        unw = np.unwrap(th)
        w_full = abs(float(np.mean(np.gradient(unw, DT_SUB))))
        phi = np.arctan2(np.sin(th) / max(w_full, 1e-9), np.cos(th))
        fases.append(np.unwrap(phi))
    z = np.exp(1j * (fases[0] - fases[1]))
    cz = np.concatenate([[0j], np.cumsum(z)])
    return np.abs((cz[W:] - cz[:-W]) / W)


def _episodios(rw):
    sobre = rw >= UMBRAL
    eps, ini = [], None
    for k, s in enumerate(sobre):
        if s and ini is None:
            ini = k
        if not s and ini is not None:
            if k - ini >= W:
                eps.append((float(ini * DT_SUB), float(k * DT_SUB)))
            ini = None
    if ini is not None and len(sobre) - ini >= W:
        eps.append((float(ini * DT_SUB), float(len(sobre) * DT_SUB)))
    return eps


def exprimir_capas(ev):
    m = ev["metrics_raw"]
    film = SWEEP / "lock_band_series" / Path(m["lock_band_series_path"]).name
    with np.load(film, allow_pickle=False) as f:
        offs = f["meta_node_mode_offsets"][:]
        capa_modo = f["meta_mode_layer"][:]
        edges = f["meta_edges"][:]
        rx = f["raw_x"][::SUB].astype(np.float64)
        rv = f["raw_v"][::SUB].astype(np.float64)
    n_nodos = len(offs) - 1
    th = {}      # (nodo, capa) -> theta serie
    mudo = {}    # (nodo, capa) -> bool
    for nd in range(n_nodos):
        a, b = offs[nd], offs[nd + 1]
        for cod, nombre in CAPAS.items():
            idx = np.where(capa_modo[a:b] == cod)[0] + a
            if idx.size == 0:
                continue
            X = rx[:, idx].sum(axis=1)
            V = rv[:, idx].sum(axis=1)
            th[(nd, nombre)] = np.arctan2(V, X)
            s_full = float(X.std())
            s_fin = float(X[-W:].std())
            mudo[(nd, nombre)] = s_fin < max(1e-12, 1e-3 * s_full)
    filas = []
    for (i, j) in edges:
        reg = {"i": int(i), "j": int(j)}
        for nombre in CAPAS.values():
            if (i, nombre) not in th or (j, nombre) not in th:
                continue
            if mudo[(i, nombre)] or mudo[(j, nombre)]:
                reg[nombre] = {"mudo": True}
                continue
            rw = _rw_corr(th[(i, nombre)], th[(j, nombre)])
            eps = _episodios(rw)
            reg[nombre] = {"mudo": False,
                           "frac_090": float(np.mean(rw >= UMBRAL)),
                           "rw_final": float(np.mean(rw[-W:])),
                           "n_eps": len(eps),
                           "dur_max": (max(e[1] - e[0] for e in eps) if eps else 0.0),
                           "episodios": eps}
        filas.append(reg)
    return {"eval_id": ev["eval_id"],
            "mudos": sorted(f"{nd}:{c}" for (nd, c), v in mudo.items() if v),
            "aristas_capas": filas}


def main():
    evs = [json.loads(l) for l in open(SWEEP / "evaluations.jsonl")]
    listos = {p.stem.replace("v5_", "") for p in OUT.glob("v5_*.json")}
    t0 = time.time()
    for k, ev in enumerate(evs):
        if ev["eval_id"] in listos:
            continue
        reg = exprimir_capas(ev)
        (OUT / f"v5_{ev['eval_id']}.json").write_text(json.dumps(reg, indent=1))
        print(f"[{k+1}/{len(evs)}] v5 {ev['eval_id'][:12]} ({time.time()-t0:.0f}s)",
              flush=True)
    print(f"[fin v5] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
