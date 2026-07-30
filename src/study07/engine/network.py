"""Integrador de red — PHYSICS_CONTRACT §5 (transcripción de differential_engine.py:647-719).

El motor es agnóstico de nivel (cláusula 1 de COA): integra N nodos completos con aristas KV
retardadas. No mide, no clasifica, no escribe a disco — el recorder y los instrumentos viven
afuera. Cero instrumentos horneados (la lección estructural de Study06).
"""
from __future__ import annotations

import math
from typing import List, Sequence

import numpy as np

from ..physics.coupling import kv_force, parse_edges
from ..physics.delay import HistoryBuffer
from ..physics.rhs import derivatives, emitted_xv
from ..physics.state import NodeSpec, NodeState, rk4_combine, state_add


class Network:
    def __init__(self, specs: Sequence[NodeSpec], states: Sequence[NodeState], edges,
                 dt: float, seed: int, k_global: float = 0.0,
                 coupling_damp_ratio: float = 0.0, coupling_gamma_c: float | None = None,
                 tau_field: float = 0.0, temperature: float = 0.0) -> None:
        if dt <= 0 or not math.isfinite(dt):
            raise ValueError("dt debe ser finito y > 0 (configurado EXPLÍCITO — contrato §5)")
        self.specs = list(specs)
        self.states = [s.copy() for s in states]
        self.dt = float(dt)
        self.seed = int(seed)
        n = len(self.specs)
        if len(self.states) != n:
            raise ValueError("specs y states desalineados")

        self.k_global = float(k_global)
        self.gamma_c = (float(coupling_gamma_c) if coupling_gamma_c is not None
                        else float(coupling_damp_ratio) * self.k_global)
        self.edge_ij, self.edge_w_k, self.edge_w_g, self.edge_tau = parse_edges(
            edges, n, tau_field)
        self.edge_tau_steps = self.edge_tau / self.dt
        self._wsum_k = np.zeros(n); self._wsum_g = np.zeros(n)
        for e in range(self.edge_ij.shape[0]):
            a, b = int(self.edge_ij[e, 0]), int(self.edge_ij[e, 1])
            self._wsum_k[a] += self.edge_w_k[e]; self._wsum_k[b] += self.edge_w_k[e]
            self._wsum_g[a] += self.edge_w_g[e]; self._wsum_g[b] += self.edge_w_g[e]
        # grupos por tau único — una lectura del buffer por tau por sub-paso (oráculo :473-478)
        self._tau_groups = []
        for val in sorted(set(float(t) for t in self.edge_tau_steps)):
            idxs = np.where(self.edge_tau_steps == val)[0]
            self._tau_groups.append((val, idxs))
        tau_steps_max = (float(np.max(self.edge_tau_steps)) if self.edge_tau_steps.size
                         else (tau_field / self.dt if self.dt > 0 else 0.0))
        delay_steps = int(math.ceil(tau_steps_max)) if tau_steps_max > 0 else 0

        # termostato FDT — contrato §6: UN Generator de red, semilla derivada declarada
        self.temperature = float(temperature)
        self.noise_rng = np.random.default_rng((self.seed * 1000003 + 99991) & 0xFFFFFFFF)

        xv_init = np.array([emitted_xv(sp, st) for sp, st in zip(self.specs, self.states)])
        self.history = HistoryBuffer(delay_steps, xv_init)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _xv(self, states: List[NodeState]) -> np.ndarray:
        return np.array([emitted_xv(sp, st) for sp, st in zip(self.specs, states)])

    def _delayed_endpoints(self, xv_sub: np.ndarray, offset: float) -> np.ndarray:
        """(E,4) = [x_i, v_i, x_j, v_j] a τ_e − offset; τ_e − offset ≤ 0 ⇒ xv del sub-paso
        ACTUAL (contrato §5, semántica RK4 del oráculo :564-577)."""
        out = np.empty((self.edge_ij.shape[0], 4), dtype=float)
        for val, idxs in self._tau_groups:
            sa = val - offset
            src = xv_sub if sa <= 0.0 else self.history.get_delayed_steps(sa)
            ii = self.edge_ij[idxs, 0]; jj = self.edge_ij[idxs, 1]
            out[idxs, 0] = src[ii, 0]; out[idxs, 1] = src[ii, 1]
            out[idxs, 2] = src[jj, 0]; out[idxs, 3] = src[jj, 1]
        return out

    def _f_inter(self, states: List[NodeState], offset: float) -> np.ndarray:
        xv = self._xv(states)
        del_ep = self._delayed_endpoints(xv, offset)
        return kv_force(xv, del_ep, self.edge_ij, self.edge_w_k, self.edge_w_g,
                        self._wsum_k, self._wsum_g, self.k_global, self.gamma_c,
                        len(self.specs))

    # ── el paso — contrato §5, orden EXACTO del oráculo ─────────────────────
    def step(self) -> None:
        s0 = self.states
        f0 = self._f_inter(s0, 0.0)
        k1 = [derivatives(sp, st, f0[i]) for i, (sp, st) in enumerate(zip(self.specs, s0))]
        s1 = [state_add(st, k, self.dt * 0.5) for st, k in zip(s0, k1)]

        f1 = self._f_inter(s1, 0.5)
        k2 = [derivatives(sp, st, f1[i]) for i, (sp, st) in enumerate(zip(self.specs, s1))]
        s2 = [state_add(st, k, self.dt * 0.5) for st, k in zip(s0, k2)]

        f2 = self._f_inter(s2, 0.5)
        k3 = [derivatives(sp, st, f2[i]) for i, (sp, st) in enumerate(zip(self.specs, s2))]
        s3 = [state_add(st, k, self.dt) for st, k in zip(s0, k3)]

        f3 = self._f_inter(s3, 1.0)
        k4 = [derivatives(sp, st, f3[i]) for i, (sp, st) in enumerate(zip(self.specs, s3))]

        nuevos: List[NodeState] = []
        for i, sp in enumerate(self.specs):
            ns = rk4_combine(s0[i], k1[i], k2[i], k3[i], k4[i], self.dt)
            if self.temperature > 0.0:
                # kick FDT post-RK4 (split de operador) — POR MODO, orden de consumo del RNG:
                # nodos en orden de índice, modos en orden del vector (contrato §5/§6)
                gamma = np.array([m.gamma for m in sp.modes])
                mass = np.array([max(m.mass, 1e-12) for m in sp.modes])
                sigma_v = np.sqrt(2.0 * gamma * self.temperature * self.dt / mass)
                ns.v = ns.v + sigma_v * self.noise_rng.standard_normal(ns.v.shape)
            nuevos.append(ns)
        self.states = nuevos
        self.history.push(self._xv(nuevos))   # UNA vez por paso, al final (contrato §5)
