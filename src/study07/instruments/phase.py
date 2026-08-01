"""Instrumento de FASE — la primera vista offline del programa (F4).

Reproduce, LEYENDO SÓLO LA WORLDLINE, lo que el motor de Study06 calculaba online:
  theta_Q[t, nodo] = atan2(Σ v_Q, Σ x_Q)      [oráculo differential_engine.py:366-375]
  Z[t] = mean_nodos(exp(i·theta))              [oráculo :996]
  R = |Z| · J = Im(conj(Z)·dZ/dt) · omega_c = J/max(R², eps_den) si R ≥ r_min
                                               [oráculo atlas/observables.py:93-109]
Constantes transcriptas: eps_den=1e-12, r_min=0.08 (R_MIN_DEFAULT) — en la config, declaradas.
El film es auto-suficiente para esta vista: el layout por nodo viaja en el manifiesto.
Taxonomía de canales (INSTRUMENT_CONTRACT): theta/z son DATO transformado del film; r/j/omega
son INFERENCIA (estimador dZ/dt dependiente de la ventana); omega_valid es VEREDICTO (umbral
r_min declarado). Con stride>1, J/omega usan dt efectivo = dt·stride: es OTRO estimador, no
una decimación del de stride=1 — declarado en el manifiesto de la vista.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from .api import View, armar_config, exigir_canales, exigir_completo, ventana

INSTRUMENT_ID = "phase_lock"
VERSION = "1.1"
DEFAULTS = {"eps_den": 1e-12, "r_min": 0.08, "t0_tick": 0, "t1_tick": None, "stride": 1,
            "permitir_incompleto": False}

CANALES = {"ticks": "dato", "theta": "dato", "z": "dato",
           "r": "inferencia", "j": "inferencia (estimador dZ/dt, dt_ef=dt*stride)",
           "omega": "inferencia (J/max(R^2,eps_den), umbral r_min)",
           "omega_valid": "veredicto (r >= r_min)"}


def theta_por_nodo(wl: Dict, man: Dict, sel: np.ndarray) -> np.ndarray:
    """Extracción de la fase Q por nodo — LA MISMA para fase y para par (par_link la
    importa: un solo camino de extracción, cero divergencia entre instrumentos)."""
    thetas = []
    for j, info in enumerate(man["por_nodo"]):
        capas = info.get("capas_por_modo")
        if capas is None:
            raise RuntimeError("worldline sin layout por nodo (capas_por_modo): film "
                               "pre-esquema — el instrumento no adivina")
        n = int(info["n_modes"])
        qi = np.array([k for k, c in enumerate(capas) if c == "Q"], dtype=int)
        if qi.size == 0:
            qi = np.arange(n)     # fallback del oráculo: sin capa Q, todos los modos
        est = wl["estados"][j][sel]
        X = est[:, qi].sum(axis=1)
        V = est[:, n + qi].sum(axis=1)
        thetas.append(np.arctan2(V, X))
    return np.stack(thetas, axis=1)                         # (t, nodo)


def run(wl: Dict, observation_config: Dict | None = None) -> View:
    cfg = armar_config(DEFAULTS, observation_config)
    exigir_canales(wl, ["estados", "manifest", "worldline_hash", "ticks"])
    exigir_completo(wl, cfg["permitir_incompleto"])
    man = wl["manifest"]
    dt = float(man["dt"])
    sel = ventana(wl, cfg)
    theta = theta_por_nodo(wl, man, sel)

    # ESPEJO ESCALAR del oráculo (atlas/observables.py:93-109 + differential_engine.py:996):
    # z_val es un complex de PYTHON por tick y las operaciones son escalares — la versión
    # vectorizada difiere en el último ulp (hypot/asociación) y el gate de dos niveles exige
    # 0.0 exacto en el entorno del generador. La aritmética se espeja, no se "mejora".
    dt_ef = dt * int(cfg["stride"])
    n_t = theta.shape[0]
    z = np.empty(n_t, dtype=complex)
    for k in range(n_t):
        z[k] = complex(np.mean(np.exp(1j * theta[k])))       # el mismo z del oráculo (:996)
    r = np.empty(n_t); j_val = np.empty(n_t)
    omega = np.empty(n_t); valido = np.empty(n_t, dtype=bool)
    for k in range(n_t):
        # escalares NUMPY indexados del array — el generador de la referencia le pasó
        # exactamente estos a lock_band_observables; python-complex difiere en el último ulp
        z_val = z[k]
        last_z = z[k - 1] if k > 0 else 0j
        dz = (z_val - last_z) / max(float(dt_ef), cfg["eps_den"]) if k > 0 else 0.0 + 0.0j
        jv = float(np.imag(np.conj(z_val) * dz))
        rv = float(abs(z_val))
        ok = bool(np.isfinite(rv) and rv >= float(cfg["r_min"]))
        r[k], j_val[k], valido[k] = rv, jv, ok
        omega[k] = (jv / max(rv * rv, cfg["eps_den"])) if ok else float("nan")

    return View(INSTRUMENT_ID, VERSION, cfg, wl["worldline_hash"],
                {"ticks": wl["ticks"][sel], "theta": theta, "z": z, "r": r,
                 "j": j_val, "omega": omega, "omega_valid": valido},
                {"canales": dict(CANALES),
                 # la vista NO calla la procedencia del film (double tap F6 c4-S6)
                 "film_intervenida": bool(man.get("intervenida", False)),
                 "film_linaje_intervenido": bool(man.get("linaje_intervenido",
                                                         man.get("intervenida", False))),
                 "nota": ("J[0]=0, omega[0] segun validez; el primer tick de TODA ventana "
                          "tiene J=0 por construccion; stride>1 => dZ/dt con dt efectivo "
                          "(OTRO estimador, no decimacion)")})
