"""CIRUGÍA DE LÍNEA FIJA [M1] — emisor PROGRAMADO sobre un receptor único.

Prereg: bitácora 2026-08-02 §12 (diseño post-§8 de COA; medición decisiva del tap
wf_f2afea35 con las tres correcciones). DOS EXPERIMENTOS DECLARADOS — no se mezclan:
  · CLAMP: la fuerza programada F0·cos φ(t) se SUMA como fuerza externa al nodo (sin
    términos de reacción). F̂ = F0 POR CONSTRUCCIÓN — la nula sin parámetro libre
    (captura ⇔ F0 > A_S^OFF(t)/|χ_m(ω)|, c=1) vive acá.
  · LINK_REAL: arista KV virtual contra una fuente programada X(t), V(t) — la MISMA ley
    del contrato §3 con w=1: F = k_c·(X−x_i) + γ_c·(V−v_i). La reacción del receptor
    está INCLUIDA (F̂ depende del receptor — se mide del canal drive, declarado). El
    retardo τ queda ABSORBIDO en la fase del programa (declarado: el programa ES la
    emisión que LLEGA; para una fuente sintética τ es re-parametrización de fase).
Programas (φ y ω analíticos, evaluados al t EXACTO de cada sub-paso RK4):
  · estacion: ω(t) = w0 (frecuencia constante — drive estacionario por construcción)
  · barrido:  ω(t) = w0 + rate·t, φ(t) = w0·t + rate·t²/2 (amplitud constante; rate ±)
X(t) = F0·cos φ(t); V(t) = Ẋ(t) = −F0·ω(t)·sin φ(t).
El canal drive de la worldline registra la fuerza TOTAL aplicada en el sub-paso 0
(semántica verificada bit-exacta en el tap wf_f2afea35/jc0 — se preserva).
El paso replica el RK4 del contrato §5 (mismo orden de operaciones; la única adición es
la fuerza del programa en los mismos 4 puntos donde Network evalúa _f_inter). Con
F0=0 en CLAMP el paso es BIT-EXACTO al de Network (batería K1).
"""
from __future__ import annotations

import math
from typing import List

import numpy as np

from ..engine.network import Network
from ..physics.state import NodeState, rk4_combine, state_add

_MODOS = ("clamp", "link_real")
_FORMAS = ("estacion", "barrido")


class ProgramaDrive:
    """Programa del emisor sintético — validación fail-loud, evaluación analítica."""

    def __init__(self, cfg: dict) -> None:
        claves = {"modo", "forma", "F0", "w0", "rate"}
        extra = set(cfg) - claves
        if extra:
            raise ValueError(f"programa con claves desconocidas {sorted(extra)}")
        faltan = claves - set(cfg)
        if faltan:
            raise ValueError(f"programa sin claves {sorted(faltan)} (todas explícitas)")
        self.modo = str(cfg["modo"])
        self.forma = str(cfg["forma"])
        self.F0 = float(cfg["F0"])
        self.w0 = float(cfg["w0"])
        self.rate = float(cfg["rate"])
        if self.modo not in _MODOS:
            raise ValueError(f"programa.modo={self.modo!r}: debe ser {_MODOS}")
        if self.forma not in _FORMAS:
            raise ValueError(f"programa.forma={self.forma!r}: debe ser {_FORMAS}")
        if not (math.isfinite(self.F0) and self.F0 >= 0):
            raise ValueError("programa.F0 debe ser finito y >= 0")
        if not (math.isfinite(self.w0) and self.w0 > 0):
            raise ValueError("programa.w0 debe ser finito y > 0")
        if not math.isfinite(self.rate):
            raise ValueError("programa.rate debe ser finito")
        if self.forma == "estacion" and self.rate != 0.0:
            raise ValueError("estacion exige rate=0 (declarado, sin defaults mágicos)")

    def fase_w(self, t: float) -> tuple:
        w = self.w0 + self.rate * t
        if w <= 0:
            raise ValueError(f"programa: ω({t})={w} <= 0 — el barrido salió del rango físico")
        return self.w0 * t + 0.5 * self.rate * t * t, w

    def xv(self, t: float) -> tuple:
        fase, w = self.fase_w(t)
        return self.F0 * math.cos(fase), -self.F0 * w * math.sin(fase)

    def fuerza_clamp(self, t: float) -> float:
        fase, _ = self.fase_w(t)
        return self.F0 * math.cos(fase)


class RedConDrivePrograma(Network):
    """Red de UN nodo (el receptor) + emisor programado. No toca el núcleo: hereda todo
    y re-implementa step() con la adición del programa en los 4 sub-pasos."""

    @classmethod
    def desde_red(cls, net: Network, programa_cfg: dict, k_c: float, g_c: float):
        if len(net.specs) != 1:
            raise ValueError("cirugía: la red debe tener EXACTAMENTE 1 nodo (el receptor)")
        if net.edge_ij.shape[0] != 0:
            raise ValueError("cirugía: la red no debe tener aristas reales (el emisor es "
                             "el programa)")
        if net.temperature != 0.0:
            raise ValueError("cirugía v1: T=0 declarado (el kick FDT no está en la batería)")
        obj = cls.__new__(cls)
        obj.__dict__ = net.__dict__            # transplante: mismos specs/estado/buffers
        obj.programa = ProgramaDrive(programa_cfg)
        obj.k_c = float(k_c)
        obj.g_c = float(g_c)
        obj.t_abs = 0.0                        # tiempo absoluto en u.t. (ticks·dt)
        return obj

    def _fuerza_programa(self, states: List[NodeState], t: float) -> float:
        if self.programa.modo == "clamp":
            return self.programa.fuerza_clamp(t)
        X, V = self.programa.xv(t)
        xv = self._xv(states)                  # emisión actual del receptor (§3)
        return self.k_c * (X - xv[0, 0]) + self.g_c * (V - xv[0, 1])

    def step(self) -> None:
        # RK4 del contrato §5 — MISMO orden; f_prog evaluada a t exacto de cada sub-paso
        dt = self.dt
        t0 = self.t_abs
        s0 = self.states
        f0 = self._f_inter(s0, 0.0)
        f0 = f0 + np.array([self._fuerza_programa(s0, t0)])
        self.last_drive0 = f0.copy()           # canal drive = fuerza TOTAL del sub-paso 0
        from ..physics.rhs import derivatives
        k1 = [derivatives(sp, st, f0[i]) for i, (sp, st) in enumerate(zip(self.specs, s0))]
        s1 = [state_add(st, k, dt * 0.5) for st, k in zip(s0, k1)]

        f1 = self._f_inter(s1, 0.5) + np.array([self._fuerza_programa(s1, t0 + 0.5 * dt)])
        k2 = [derivatives(sp, st, f1[i]) for i, (sp, st) in enumerate(zip(self.specs, s1))]
        s2 = [state_add(st, k, dt * 0.5) for st, k in zip(s0, k2)]

        f2 = self._f_inter(s2, 0.5) + np.array([self._fuerza_programa(s2, t0 + 0.5 * dt)])
        k3 = [derivatives(sp, st, f2[i]) for i, (sp, st) in enumerate(zip(self.specs, s2))]
        s3 = [state_add(st, k, dt) for st, k in zip(s0, k3)]

        f3 = self._f_inter(s3, 1.0) + np.array([self._fuerza_programa(s3, t0 + dt)])
        k4 = [derivatives(sp, st, f3[i]) for i, (sp, st) in enumerate(zip(self.specs, s3))]

        nuevos: List[NodeState] = []
        for i, sp in enumerate(self.specs):
            ns = rk4_combine(s0[i], k1[i], k2[i], k3[i], k4[i], dt)
            self.last_noise_kicks[i] = np.zeros(sp.n_modes)     # T=0 validado en desde_red
            nuevos.append(ns)
        self.states = nuevos
        self.history.push(self._xv(nuevos))
        self.t_abs = t0 + dt
