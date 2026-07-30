"""Acople Kelvin-Voigt retardado por arista — PHYSICS_CONTRACT §3
(transcripción de differential_engine.py:82-138 del oráculo).

Acumulación SECUENCIAL en orden de aristas (cláusula de conformidad: bit-exacto sólo grado ≤ 7;
con grado ≥ 8 se acepta ≤ 1 ulp o se replica la suma secuencial — esto ES la suma secuencial).
"""
from __future__ import annotations

import numpy as np


def kv_force(xv_now: np.ndarray, del_ep: np.ndarray, edge_ij: np.ndarray,
             w_k: np.ndarray, w_g: np.ndarray, wsum_k: np.ndarray, wsum_g: np.ndarray,
             k_spring: float, k_damp: float, n_nodes: int) -> np.ndarray:
    """F_i = k_spring·Σ w_k·(x_other(t−τ)−x_i)/Σw_k + k_damp·Σ w_g·(v_other(t−τ)−v_i)/Σw_g.

    del_ep: (E, 4) = [x_i(t−τ_e), v_i(t−τ_e), x_j(t−τ_e), v_j(t−τ_e)].
    """
    x_now, v_now = xv_now[:, 0], xv_now[:, 1]
    f_spr = np.zeros(n_nodes, dtype=float)
    f_dmp = np.zeros(n_nodes, dtype=float)
    for e in range(int(edge_ij.shape[0])):
        i, j = int(edge_ij[e, 0]), int(edge_ij[e, 1])
        f_spr[i] += w_k[e] * (del_ep[e, 2] - x_now[i])
        f_spr[j] += w_k[e] * (del_ep[e, 0] - x_now[j])
        f_dmp[i] += w_g[e] * (del_ep[e, 3] - v_now[i])
        f_dmp[j] += w_g[e] * (del_ep[e, 1] - v_now[j])
    f_inter = np.zeros(n_nodes, dtype=float)
    for i in range(n_nodes):
        spring = k_spring * f_spr[i] / wsum_k[i] if wsum_k[i] > 0 else 0.0
        damp = k_damp * f_dmp[i] / wsum_g[i] if wsum_g[i] > 0 else 0.0
        f_inter[i] = spring + damp
    return f_inter


def parse_edges(edges, n_nodes: int, tau_default: float):
    """Aristas: dicts {i, j, w_k?, w_gamma?, tau?} o tuplas (i, j) legacy — fail-loud
    (transcripción de differential_engine.py:45-79)."""
    ij, w_k, w_g, tau = [], [], [], []
    allowed = {"i", "j", "w_k", "w_gamma", "tau"}
    for edge in edges:
        if isinstance(edge, dict):
            unknown = set(edge.keys()) - allowed
            if unknown:
                raise ValueError(f"edge con claves desconocidas {sorted(unknown)}")
            i, j = int(edge["i"]), int(edge["j"])
            wk = float(edge.get("w_k", 1.0))
            wg = float(edge.get("w_gamma", wk))
            tv = float(edge.get("tau", tau_default))
        elif isinstance(edge, (list, tuple)) and len(edge) == 2:
            i, j = int(edge[0]), int(edge[1])
            wk, wg, tv = 1.0, 1.0, float(tau_default)
        else:
            raise ValueError(f"edge inválido: {edge!r}")
        if not (0 <= i < n_nodes and 0 <= j < n_nodes) or i == j:
            raise ValueError(f"edge ({i},{j}) fuera de rango o i==j")
        if not (np.isfinite(wk) and np.isfinite(wg) and np.isfinite(tv)) or wk < 0 or wg < 0 or tv < 0:
            raise ValueError(f"edge ({i},{j}): w/tau deben ser finitos y >= 0")
        ij.append((i, j)); w_k.append(wk); w_g.append(wg); tau.append(tv)
    return (np.array(ij, dtype=int).reshape(-1, 2), np.array(w_k, dtype=float),
            np.array(w_g, dtype=float), np.array(tau, dtype=float))
