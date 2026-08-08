"""RedCaldo — el motor τ [SPEC_MOTOR_TAU_V1 §2 (pseudocódigo normativo) + §12].

Estado: X apilado (x,v,z,b,e con eje N) + τ (n_pairs,) float64 en U.T.
Paso: RK4 clásico con τ VARIABLE DE ETAPA; consultas retardadas por HISTORIA (Hermite,
§3) y rama solapada por HERMITE DE ETAPA (§12.4 — cada etapa con su propio extremo
derecho); cero causal J≡0 COMPLETA (t_pulso ≡ 0); clamp duro post-combine τ←max(τ,0)
como RESPALDO con contador; kicks FDT por STREAM DE IDENTIDAD (node_seed(seed, id));
push de historia POST-kick, UNO por paso. Combine transcrito de state.rk4_combine
(mismo orden de operaciones — guarda 1 bit-exacta contra el motor v1 con K=λ=0).
Génesis (§12.6): burn-in del remanente FUERA del calendario (trayectoria descartada,
stream propio); t_pulso ≡ 0 = origen; la historia arranca con la ÚNICA fila del
remanente en tick 0. Sin eventos, sin poda, sin lecturas aguas arriba.
"""
from __future__ import annotations

import numpy as np

from ..compat.study06_v4 import node_seed
from ..physics.historia_tau import HistoriaCaldo
from ..physics.interaccion_tau import evaluar_pares, indice_pares
from ..physics.rhs_apilado import derivatives_apilado
from ..physics.rhs_apilado_het import derivatives_apilado_het
from ..physics.spec_lote import SpecLote
from ..physics.state import Layer, NodeSpec

_C_RK4 = (0.0, 0.5, 0.5, 1.0)


class RedCaldo:
    """spec: NodeSpec (población homogénea — camino SELLADO, ops intactas) o
    lista de N NodeSpecs (heterogénea, M2-build 1 — kernel het certificado;
    genoma_ids OBLIGATORIO en ese caso, fail-loud)."""

    def __init__(self, spec, n_onions: int, *, dt: float, seed: int,
                 K: float, lam: float, tau_s: float,
                 T_pulso: float, ticks_pulso: int,
                 T_rem: float, ticks_rem: int,
                 w_ticks_max: int = 1 << 21, ids=None, genoma_ids=None,
                 T_fondo: float = 0.0) -> None:
        self.het = isinstance(spec, (list, tuple))
        if self.het:
            if len(spec) != int(n_onions):
                raise ValueError("RedCaldo het: len(specs) != n_onions")
            if genoma_ids is None:
                raise ValueError("RedCaldo het: genoma_ids es OBLIGATORIO (custodia)")
            self.lote = SpecLote(spec, genoma_ids)
            self.spec = self.lote.ref            # arquitectura (índices, capas)
            self.genoma_ids = list(self.lote.genoma_ids)
        else:
            self.spec = spec
            self.lote = None
            self.genoma_ids = None if genoma_ids is None else list(genoma_ids)
        self.n = int(n_onions)
        self.dt = float(dt)
        self.K = float(K)
        self.lam = float(lam)
        self.tau_s = float(tau_s)
        self.T_pulso = float(T_pulso)
        self.T_fondo = float(T_fondo)   # §53 A1: baño FDT post-pulso (calendario, no ley; 0 = sellado)
        self.ticks_pulso = int(ticks_pulso)
        self.ids = (np.arange(self.n, dtype=np.int64) if ids is None
                    else np.asarray(ids, dtype=np.int64))   # identidad estable del génesis
        self.rngs = [np.random.default_rng(node_seed(int(seed), int(i)))
                     for i in self.ids]
        self.S_idx = np.array([i for i, m in enumerate(self.spec.modes)
                               if m.layer in (Layer.S1, Layer.S2)], dtype=np.int64)
        self.n_s = len(self.S_idx)
        if self.het:
            self.masa = self.lote.mass           # (N, nm) — por onion
            self.gamma = self.lote.gamma
            self.masa_S = self.masa[:, self.S_idx]     # (N, n_S)
        else:
            self.masa = np.array([m.mass for m in self.spec.modes])
            self.gamma = np.array([m.gamma for m in self.spec.modes])
            self.masa_S = self.masa[self.S_idx]
        self.pares = indice_pares(self.n)
        self.n_pairs = len(self.pares)
        nm, nz, nl = self.spec.n_modes, self.spec.n_z, self.spec.n_layers
        self.x = np.zeros((self.n, nm)); self.v = np.zeros((self.n, nm))
        self.z = np.zeros((self.n, nz)); self.b = np.zeros((self.n, nl))
        self.e = np.zeros((self.n, nl))
        self.tau = np.zeros(self.n_pairs)
        self.tick = 0                                    # t ≡ tick·dt DERIVADO
        # trending causal + respaldo
        self.clamp_count = 0
        self.max_abs_dtau = 0.0
        self.min_margen_causal = np.inf
        # canales del sub-paso 0 (registro — convención drive[n])
        self.last_fS_sub0 = np.zeros((self.n_pairs, 2))
        self.last_B_sub0 = np.zeros(self.n_pairs)
        self.last_kicks = np.zeros((self.n, nm))
        # ── génesis: burn-in FUERA del calendario (trayectoria descartada) ──
        if ticks_rem > 0 and T_rem > 0.0:
            self._burn_in(float(T_rem), int(ticks_rem))
        self.historia = HistoriaCaldo(self.n, self.n_s, self.dt,
                                      w_ticks_max=int(w_ticks_max))
        self.historia.push(self.x[:, self.S_idx], self.v[:, self.S_idx])  # fila t=0

    # ── burn-in aislado (K=λ=0, FDT a T_rem, streams propios) ──
    def _kernel(self, x, v, z, b, e, f_ext):
        """Despacho: kernel het certificado (población heterogénea) o el homogéneo
        SELLADO (bit-igualdad probada en N-idénticos — doble gate M2-build 1)."""
        if self.het:
            return derivatives_apilado_het(self.lote, x, v, z, b, e, f_ext)
        return derivatives_apilado(self.spec, x, v, z, b, e, f_ext)

    def _burn_in(self, T_rem: float, ticks_rem: int) -> None:
        f0 = np.zeros_like(self.x)
        sigma_v = np.sqrt(2.0 * self.gamma * T_rem * self.dt / np.maximum(self.masa, 1e-12))
        for _ in range(ticks_rem):
            self._rk4_interno(f0)
            for i in range(self.n):
                sv = sigma_v if sigma_v.ndim == 1 else sigma_v[i]   # het: fila del onion
                kick = sv * self.rngs[i].standard_normal(self.x.shape[1])
                self.v[i] = self.v[i] + kick

    def _rk4_interno(self, f_ext) -> None:
        """RK4 SOLO interno (burn-in): sin pares, sin τ."""
        est = (self.x, self.v, self.z, self.b, self.e)
        k1 = self._kernel(*est, f_ext)
        e2 = tuple(s + 0.5 * self.dt * k for s, k in zip(est, k1))
        k2 = self._kernel(*e2, f_ext)
        e3 = tuple(s + 0.5 * self.dt * k for s, k in zip(est, k2))
        k3 = self._kernel(*e3, f_ext)
        e4 = tuple(s + self.dt * k for s, k in zip(est, k3))
        k4 = self._kernel(*e4, f_ext)
        c = self.dt / 6.0
        self.x, self.v, self.z, self.b, self.e = tuple(
            s + c * (a + 2 * b_ + 2 * c_ + d) for s, a, b_, c_, d in
            zip(est, k1, k2, k3, k4))

    # ── consultas retardadas de una etapa ──
    def _S_ret(self, t_stage: float, tau_stage: np.ndarray,
               x_stage: np.ndarray, v_stage: np.ndarray):
        """S_ret (P,2) = [S_j(t_src), S_i(t_src)] por par + máscara causal."""
        t_src = t_stage - tau_stage
        activo = t_src >= 0.0                             # cero causal (t_pulso ≡ 0)
        t_hist = (self.tick) * self.dt                    # última fila de historia = tick
        S_ret = np.zeros((self.n_pairs, 2))
        if not activo.any():
            return S_ret, activo
        i_idx, j_idx = self.pares[:, 0], self.pares[:, 1]
        # partición: historia (t_src ≤ t_hist) vs rama solapada (t_src > t_hist)
        en_hist = activo & (t_src <= t_hist)
        solapada = activo & (t_src > t_hist)
        if en_hist.any():
            ons = np.concatenate([j_idx[en_hist], i_idx[en_hist]])
            ts = np.concatenate([t_src[en_hist], t_src[en_hist]])
            x_ret, _ = self.historia.consulta(ons, ts)
            m = en_hist.sum()
            S_ret[en_hist, 0] = x_ret[:m].sum(axis=1)
            S_ret[en_hist, 1] = x_ret[m:].sum(axis=1)
        if solapada.any():
            # HERMITE DE ETAPA en [t_hist, t_stage]: nodo izq = fila de historia (tick),
            # nodo der = estado de ETAPA (§12.4 — cada etapa su propio extremo derecho)
            span = t_stage - t_hist
            th = ((t_src[solapada] - t_hist) / span)[:, None]
            fila = self.historia.buf[self.tick % self.historia.capacidad]  # (N,n_S,2)
            x0a, v0a = fila[:, :, 0], fila[:, :, 1]
            x1a = x_stage[:, self.S_idx]; v1a = v_stage[:, self.S_idx]
            h00 = 2 * th ** 3 - 3 * th ** 2 + 1
            h10 = th ** 3 - 2 * th ** 2 + th
            h01 = -2 * th ** 3 + 3 * th ** 2
            h11 = th ** 3 - th ** 2
            for col, quien in ((0, j_idx[solapada]), (1, i_idx[solapada])):
                xq = (h00 * x0a[quien] + h10 * span * v0a[quien]
                      + h01 * x1a[quien] + h11 * span * v1a[quien])
                S_ret[solapada, col] = xq.sum(axis=1)
        return S_ret, activo

    def _rhs_caldo(self, t_stage, x, v, z, b, e, tau):
        """Evaluación de una etapa completa: interno + pares + dτ."""
        S_ret, activo = self._S_ret(t_stage, tau, x, v)
        x_S = x[:, self.S_idx]
        S_act = x_S.sum(axis=1)
        f_S, dtau, B = evaluar_pares(x_S, S_act, S_ret, self.masa_S, tau, activo,
                                     self.pares, K=self.K, lam=self.lam,
                                     tau_s=self.tau_s)
        f_ext = np.zeros_like(x)
        f_ext[:, self.S_idx] = f_S
        dx, dv, dz, db, de = self._kernel(x, v, z, b, e, f_ext)
        return (dx, dv, dz, db, de, dtau), (S_ret, B)

    def step(self) -> None:
        t0 = self.tick * self.dt
        est0 = (self.x, self.v, self.z, self.b, self.e, self.tau)
        ks = []
        registro0 = None
        for s_i, c in enumerate(_C_RK4):
            if s_i == 0:
                etapa = est0
            else:
                coef = c * self.dt
                k_prev = ks[-1]
                etapa = tuple(s + coef * k for s, k in zip(est0, k_prev))
                etapa = etapa[:5] + (etapa[5],)
            k, reg = self._rhs_caldo(t0 + c * self.dt, *etapa)
            if s_i == 0:
                registro0 = reg
            ks.append(k)
        c6 = self.dt / 6.0
        nuevos = tuple(s + c6 * (k1 + 2 * k2 + 2 * k3 + k4)
                       for s, k1, k2, k3, k4 in zip(est0, *ks))
        self.x, self.v, self.z, self.b, self.e, tau_nuevo = nuevos
        # clamp de RESPALDO post-combine (spec §1.2) con contador al trending
        negativos = tau_nuevo < 0.0
        if negativos.any():
            self.clamp_count += int(negativos.sum())
            tau_nuevo = np.maximum(tau_nuevo, 0.0)
        # trending causal (con n_pairs=0 no hay pares que medir)
        if self.n_pairs > 0:
            dtau_efectivo = np.abs(tau_nuevo - self.tau) / self.dt
            self.max_abs_dtau = max(self.max_abs_dtau, float(dtau_efectivo.max()))
        self.tau = tau_nuevo
        self.tick += 1
        if self.n_pairs > 0:
            margen = (self.tick * self.dt) - self.tau
            self.min_margen_causal = min(self.min_margen_causal, float(margen.min()))
        # kicks FDT del PULSO (calendario: T(t)=T_pulso en [0, ticks_pulso))
        T_ahora = (self.T_pulso if (self.tick <= self.ticks_pulso and self.T_pulso > 0.0)
                   else self.T_fondo)
        if T_ahora > 0.0:
            sigma_v = np.sqrt(2.0 * self.gamma * T_ahora * self.dt
                              / np.maximum(self.masa, 1e-12))
            for i in range(self.n):
                sv = sigma_v if sigma_v.ndim == 1 else sigma_v[i]   # het: fila del onion
                kick = sv * self.rngs[i].standard_normal(self.x.shape[1])
                self.v[i] = self.v[i] + kick
                self.last_kicks[i] = kick
        else:
            self.last_kicks[:] = 0.0
        # push POST-kick, uno por paso
        self.historia.push(self.x[:, self.S_idx], self.v[:, self.S_idx])
        self.last_fS_sub0, self.last_B_sub0 = registro0
