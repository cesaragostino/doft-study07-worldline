"""Interacción del caldo τ — la ley J por par [SPEC_MOTOR_TAU_V1 §1 + §12].

Función PURA sobre arrays apilados: una evaluación por par produce las cuatro salidas
(f^S ambas direcciones, ℬ) desde el MISMO estado de etapa y las MISMAS historias
retardadas. Cero causal J≡0 COMPLETA (spec §1.3). Proyección s(τ) con dominio completo
(§1.2: s=0 en τ≤0 si ℬ<0; smoothstep en (0,τ_s); 1 después — τ_s FÍSICO en u.t.).
Orden de reducción CANÓNICO (§12.12): acumulación sobre receptores en orden del índice
lexicográfico p vía np.add.at (secuencial por índice, documentado); la forma canónica
del término por par sobre el receptor i es (S_ret_j − n_S^(j)·x_iμ), acumulada como
suma escalar de S_ret en orden p + conteo (equivalente determinista declarado).
"""
from __future__ import annotations

import numpy as np


def indice_pares(n: int) -> np.ndarray:
    """(n_pairs, 2) int64 en orden lexicográfico: p = i·N − i·(i+1)/2 + (j−i−1)."""
    pares = [(i, j) for i in range(n) for j in range(i + 1, n)]
    return np.array(pares, dtype=np.int64).reshape(-1, 2)


def s_proyeccion(tau: np.ndarray, B: np.ndarray, tau_s: float) -> np.ndarray:
    """s(τ) del spec §1.2: 1 si ℬ≥0; si ℬ<0: 0 en τ≤0, smoothstep(τ/τ_s) en (0,τ_s),
    1 en τ≥τ_s. Dominio COMPLETO (el smoothstep literal en τ<0 crece sin cota — tap)."""
    u = np.clip(tau / float(tau_s), 0.0, 1.0)
    smooth = 3.0 * u ** 2 - 2.0 * u ** 3
    return np.where(B >= 0.0, 1.0, smooth)


def evaluar_pares(x_S: np.ndarray, S_act: np.ndarray, S_ret: np.ndarray,
                  masa_S: np.ndarray, tau: np.ndarray, activo: np.ndarray,
                  pares: np.ndarray, K: float, lam: float, tau_s: float):
    """Una evaluación de TODOS los pares (spec §1).

    x_S    (N, n_S)  : coordenadas S del estado de etapa
    S_act  (N,)      : Σ_ν x_Sν del estado de etapa (la MISMA suma que consume ℬ)
    S_ret  (P, 2)    : sumas retardadas [S_j(t_src), S_i(t_src)] por par (orden p)
    masa_S (n_S,)    : masas de los modos S (genoma canónico: 1.0)
    tau    (P,)      : τ de etapa por par
    activo (P,) bool : cero causal — False ⇒ J≡0 COMPLETA (las cuatro salidas)
    pares  (P, 2)    : índices (i, j) lexicográficos
    Devuelve: f_S (N, n_S) fuerza por modo receptor; dtau (P,); B (P,) sin proyección
    (para el registro); S_ret ya es el canal fS_sub0 del schema.
    """
    n, n_s = x_S.shape
    i_idx, j_idx = pares[:, 0], pares[:, 1]
    act = activo.astype(np.float64)

    # ℬ simetrizado (§1.2), nulo si el par está causalmente desconectado
    B = lam * (S_act[i_idx] * S_ret[:, 0] + S_act[j_idx] * S_ret[:, 1]) * act
    dtau = B * s_proyeccion(tau, B, tau_s)

    # f^S: acumulación canónica en orden p (np.add.at = secuencial por índice)
    acc = np.zeros(n, dtype=np.float64)       # Σ_pares S_ret del emisor, por receptor
    cnt = np.zeros(n, dtype=np.float64)       # pares activos por receptor
    np.add.at(acc, i_idx, S_ret[:, 0] * act)
    np.add.at(acc, j_idx, S_ret[:, 1] * act)
    np.add.at(cnt, i_idx, act)
    np.add.at(cnt, j_idx, act)
    # término por modo receptor: (K/m_μ)·(acc_i − cnt_i·n_S·x_iμ)  [colapso §1.1,
    # n_S del EMISOR = n_S común (todos-iguales); forma factorizada canónica declarada]
    f_S = (K / masa_S[None, :]) * (acc[:, None] - cnt[:, None] * float(n_s) * x_S)
    return f_S, dtau, B
