"""Lecturas del caldo como FUNCIONES PURAS con custodia [M2-build 4; §35 contrato].

Formaliza los estimadores usados en M1 (§27-§33, ad-hoc verificados) como librería:
misma matemática, entradas/salidas declaradas, sin I/O. La probeta GOLD (M2-build 2)
los certifica contra fixtures sellados; el harness censal los consume.
Conceptos SEPARADOS (escalera §30): afinidad (ω(b) en lengua) ≠ lock de fase
(|dΔφ/dt| acotada por caja) ≠ link causal (contrafáctico — NO es una función de acá).
"""
from __future__ import annotations

import numpy as np

LENGUA = 0.275                 # lengua de Arnold (census study07; H2)
C_RELOJ = 10.240               # reloj universal medido (§19; genoma canónico)


def omega_reloj(b_q: np.ndarray, C: float = C_RELOJ) -> np.ndarray:
    """ω(b) — la coordenada de afinidad biográfica (§30): C·√(1+0.1·b_Q)."""
    return C * np.sqrt(1.0 + 0.1 * np.asarray(b_q))


def grafo_afinidad(b_q: np.ndarray, C: float = C_RELOJ,
                   lengua: float = LENGUA):
    """Adyacencia predicha SOLO desde b (grafo de intervalos 1-D, §30).
    Devuelve (adyacencia (N,N) bool, |Δω| (P,) en orden lexicográfico p)."""
    w = omega_reloj(b_q, C)
    n = len(w)
    iu = np.triu_indices(n, 1)
    dw = np.abs(w[:, None] - w[None, :])
    A = dw < lengua
    np.fill_diagonal(A, False)
    return A, dw[iu]


def fases_banda(sig: np.ndarray, dt: float, lo: float = 7.0,
                hi: float = 22.0) -> np.ndarray:
    """Fase analítica por señal (columnas = onions) en banda [lo, hi] rad/u.t.
    (señal analítica por FFT, banda positiva, desenrollada)."""
    n = sig.shape[0]
    F = np.fft.fft(sig, axis=0)
    fr = 2.0 * np.pi * np.fft.fftfreq(n, d=dt)
    F[(np.abs(fr) < lo) | (np.abs(fr) > hi)] = 0
    F[fr < 0] = 0
    return np.unwrap(np.angle(np.fft.ifft(2.0 * F, axis=0)), axis=0)


def grafo_lock(ph: np.ndarray, dt: float, caja_ut: float = 1.0,
               umbral: float = LENGUA, frac_min: float = 0.5):
    """Grafo de phase-lock observado (§26-§27): cajas de caja_ut; caja locked si
    |Δ pendiente de fase| < umbral; par locked si fracción ≥ frac_min.
    Devuelve (adyacencia (N,N) bool, frac (P,) orden p, grado (N,))."""
    n_t, n = ph.shape
    caja = int(round(caja_ut / dt))
    ncaja = n_t // caja
    if ncaja < 1:
        raise ValueError("grafo_lock: ventana menor que una caja")
    iu = np.triu_indices(n, 1)
    frac = np.zeros(len(iu[0]))
    t_loc = np.arange(caja) * dt
    for a in range(ncaja):
        pend = np.polyfit(t_loc, ph[a * caja:(a + 1) * caja], 1)[0]
        frac += ((np.abs(pend[:, None] - pend[None, :]) < umbral)[iu]).astype(float)
    frac /= ncaja
    A = np.zeros((n, n), dtype=bool)
    A[iu] = frac >= frac_min
    A = A | A.T
    return A, frac, A.sum(1)


def slips_en_lock(ph: np.ndarray, dt: float, caja_ut: float = 1.0,
                  umbral: float = LENGUA) -> tuple:
    """Peldaño 3 (§32): saltos de Δφ > π dentro de cajas locked.
    Devuelve (n_slips, n_cajas_locked)."""
    n_t, n = ph.shape
    caja = int(round(caja_ut / dt))
    ncaja = n_t // caja
    iu = np.triu_indices(n, 1)
    pares_cols = [j * n + k for j, k in zip(*iu)]
    t_loc = np.arange(caja) * dt
    slips = 0
    locked_tot = 0
    for a in range(ncaja):
        seg = ph[a * caja:(a + 1) * caja]
        pend = np.polyfit(t_loc, seg, 1)[0]
        in_lock = (np.abs(pend[:, None] - pend[None, :]) < umbral)[iu]
        dphi = (seg[:, :, None] - seg[:, None, :]).reshape(caja, -1)[:, pares_cols]
        exc = (np.abs(dphi - np.median(dphi, 0)) > np.pi).any(0)
        slips += int((exc & in_lock).sum())
        locked_tot += int(in_lock.sum())
    return slips, locked_tot


def matriz_tau(tau_p: np.ndarray, n: int) -> np.ndarray:
    """(P,) orden lexicográfico p → matriz simétrica (N,N), diagonal 0."""
    M = np.zeros((n, n))
    iu = np.triu_indices(n, 1)
    M[iu] = tau_p
    return M + M.T


def mds_espectro(D: np.ndarray):
    """Embedding espectral del mapa τ (§20-§21): B = −½·J·D²·J, autovalores
    descendentes. Devuelve (autovalores (N,), d* = #{λ_k > |λ_min|},
    fracción no-euclídea Σ|λ⁻|/Σ|λ|)."""
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    ev = np.sort(np.linalg.eigvalsh(-0.5 * J @ (D ** 2) @ J))[::-1]
    tot = np.abs(ev).sum()
    piso = abs(ev.min()) if (ev < 0).any() else 0.0
    dstar = int((ev > piso).sum())
    no_eucl = float(np.abs(ev[ev < 0]).sum() / tot) if tot > 0 else 0.0
    return ev, dstar, no_eucl


def componentes(A: np.ndarray):
    """Componentes conexas de una adyacencia bool (N,N) — etiquetas (N,) int
    por BFS determinista en orden de índice (0 = primera componente)."""
    n = A.shape[0]
    etiqueta = np.full(n, -1, dtype=np.int64)
    actual = 0
    for s in range(n):
        if etiqueta[s] >= 0:
            continue
        cola = [s]
        etiqueta[s] = actual
        while cola:
            u = cola.pop(0)
            for vtx in np.where(A[u] & (etiqueta < 0))[0]:
                etiqueta[vtx] = actual
                cola.append(int(vtx))
        actual += 1
    return etiqueta


def tracker_componentes(lista_A, jaccard_min: float = 0.5):
    """Medición 5 del contrato M2 (§35): persistencia/relevos/fragmentación.

    lista_A: adyacencias bool (N,N) por ventana consecutiva. Componentes de ≥2
    onions; matching entre ventanas por Jaccard ≥ jaccard_min (mejor primero,
    determinista). Devuelve dict con:
      episodios: [{id, nace, muere (exclusivo; None=vivo al final), miembros_ini,
                   miembros_fin, relevos (nº de cambios de membresía)}]
      eventos:   [{t, tipo: nace|muere|fusion|fision|relevo, ids}]
      fragmentacion: [nº componentes por ventana]
    """
    episodios, eventos, frag = [], [], []
    vivos = {}                                   # id → set de miembros
    prox_id = 0
    for t, A in enumerate(lista_A):
        et = componentes(A)
        comps = []
        for c in np.unique(et):
            m = set(np.where(et == c)[0].tolist())
            if len(m) >= 2:
                comps.append(m)
        frag.append(len(comps))
        usados_prev, usados_new = set(), set()
        matches = []
        for vid, vm in vivos.items():
            for k, cm in enumerate(comps):
                inter = len(vm & cm); union = len(vm | cm)
                if union and inter / union >= jaccard_min:
                    matches.append((inter / union, vid, k))
        matches.sort(key=lambda x: (-x[0], x[1], x[2]))
        for jac, vid, k in matches:
            if vid in usados_prev or k in usados_new:
                continue
            usados_prev.add(vid); usados_new.add(k)
            if vivos[vid] != comps[k]:
                ep = next(e for e in episodios if e["id"] == vid)
                ep["relevos"] += 1
                ep["miembros_fin"] = sorted(comps[k])
                eventos.append({"t": t, "tipo": "relevo", "ids": [vid]})
            vivos[vid] = comps[k]
        for vid in [v for v in list(vivos) if v not in usados_prev]:
            next(e for e in episodios if e["id"] == vid)["muere"] = t
            eventos.append({"t": t, "tipo": "muere", "ids": [vid]})
            del vivos[vid]
        for k, cm in enumerate(comps):
            if k in usados_new:
                continue
            episodios.append({"id": prox_id, "nace": t, "muere": None,
                              "miembros_ini": sorted(cm),
                              "miembros_fin": sorted(cm), "relevos": 0})
            eventos.append({"t": t, "tipo": "nace", "ids": [prox_id]})
            vivos[prox_id] = cm
            prox_id += 1
    return {"episodios": episodios, "eventos": eventos, "fragmentacion": frag}
