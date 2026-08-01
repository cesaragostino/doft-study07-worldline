"""Instrumento de PAR — el descubridor de LINKS (etapa 0 del norte «descubriendo el link
corremos el universo», COA 2026-07-30, bitácora §17-§18).

Mide, LEYENDO SÓLO LA WORLDLINE, el estado de salud de cada par de nodos:
  · fase por nodo θ (la misma extracción Q del instrumento de fase) + CORRECCIÓN de fase
    (panel §16: la fase atan2 cruda es elíptica y castiga locks con desfase —
    φ = atan2(sin θ / max(ω̂,eps), cos θ) con ω̂ = |⟨dθ_unwrap/dt⟩| propio del nodo)
  · rw(t) = |⟨e^{iΔφ}⟩|_W por ventana deslizante (media móvil por cumsum, O(n))
  · PORTADORA por nodo (ω̂ completa/temprana/tardía) y PULLING del par (Δω̂ temprana→tardía)
  · VEREDICTO por par: FIRME (rw_final ≥ umbral_firme) · COQUETEO (episodios sostenidos
    sobre umbral_coqueteo sin firmeza) · MUERTO — con t_lock (primer sostén) y episodios.
Umbrales por DEFAULTS con procedencia MEDIDA (C1, §13-§16), jamás elegidos a ojo.
Punto ciego DECLARADO: con ventana W, lock y deriva son indistinguibles bajo Δω ≈ 2π/W
(§16) — por eso el default es W=4 u.t. (punto ciego ~1.6 rad/u.t. → usar W mayor para
detuning fino). La resolución de detección de episodios/t_lock es stride_det ticks.

portadora_fft(y, dt): estimador de portadora del panel (§16: FFT con Hann + zeropad ×8,
pico en rad/u.t.) — el que reemplazó al estimador saturado; sirve para rings de cápsula
y para emisiones de film.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from .api import View, armar_config, exigir_canales, exigir_completo, ventana
from .phase import theta_por_nodo

INSTRUMENT_ID = "par_link"
VERSION = "1.0"
DEFAULTS = {
    "w_ut": 4.0,               # ventana de rw en u.t. (§16: 4-8 baja el punto ciego)
    "umbral_firme": 0.95,      # medido en C1: separa los 7 links firmes (§13)
    "umbral_coqueteo": 0.80,   # medido en C1: el hombro intermitente (§13)
    "sosten_ventanas": 2.0,    # sostén exigido para t_lock, en ventanas W (patrón §12)
    "temprana_ut": 5.5,        # fin de la ventana temprana de portadora (arranca en 0.5)
    "tardia_ut": 10.0,         # largo de la ventana tardía
    "stride_det": 100,         # resolución (ticks) de la detección de episodios/t_lock
    "t0_tick": 0, "t1_tick": None, "stride": 1,
    "permitir_incompleto": False,
}
ESTADOS = ("firme", "coqueteo", "muerto")

CANALES = {
    "ticks": "dato", "theta": "dato (fase Q por nodo, la del instrumento de fase)",
    "omega_nodo": "inferencia (portadora ω̂ por nodo: completa/temprana/tardía)",
    "pares_ij": "dato (índices i,j de cada par, TODOS los pares i<j)",
    "rw_final": "inferencia (|⟨e^{iΔφ}⟩| ventana final, fase corregida §16)",
    "rw_max": "inferencia", "dphi_final": "inferencia",
    "dw_temprana": "inferencia (pulling: |Δω̂| temprana)",
    "dw_tardia": "inferencia (pulling: |Δω̂| tardía)",
    "t_lock_ut": "inferencia (primer sostén sobre umbral_firme; NaN si no hubo)",
    "episodios": "inferencia (n de sostenes sobre umbral_coqueteo)",
    "dur_max_ut": "inferencia", "frac_coqueteo": "inferencia",
    "estado": "VEREDICTO (0=muerto, 1=coqueteo, 2=firme — umbrales declarados)",
}


def portadora_fft(y: np.ndarray, dt: float) -> float:
    """Portadora dominante en rad/u.t. — estimador del panel §16 (Hann + zeropad ×8).
    Reemplaza al estimador saturado de §15 (mediana de atan2 sin normalizar = punto fijo)."""
    y = np.asarray(y, dtype=np.float64)
    y = y - y.mean()
    n = y.size
    if n < 16:
        raise RuntimeError("portadora_fft: serie demasiado corta")
    espectro = np.abs(np.fft.rfft(y * np.hanning(n), n=8 * n))
    om = np.fft.rfftfreq(8 * n, float(dt)) * 2.0 * np.pi
    return float(om[np.argmax(espectro)])


def _rw_movil(dphi: np.ndarray, w_ticks: int) -> np.ndarray:
    """|media móvil de e^{iΔφ}| con ventana w_ticks — cumsum, O(n)."""
    z = np.exp(1j * dphi)
    cz = np.concatenate([[0.0 + 0.0j], np.cumsum(z)])
    return np.abs((cz[w_ticks:] - cz[:-w_ticks]) / w_ticks)


def _episodios(rw_det: np.ndarray, umbral: float, min_muestras: int):
    """Episodios = rachas sobre umbral con largo >= min_muestras (en muestras de detección)."""
    sobre = rw_det >= umbral
    n_ep, dur_max, corr, primer_sosten = 0, 0, 0, None
    for k, s in enumerate(sobre):
        if s:
            corr += 1
            dur_max = max(dur_max, corr)
            if corr >= min_muestras and primer_sosten is None:
                primer_sosten = k - min_muestras + 1
        else:
            if corr >= min_muestras:
                n_ep += 1
            corr = 0
    if corr >= min_muestras:
        n_ep += 1
    return n_ep, dur_max, primer_sosten


def run(wl: Dict, observation_config: Dict | None = None) -> View:
    cfg = armar_config(DEFAULTS, observation_config)
    if int(cfg["stride"]) != 1:
        raise RuntimeError("par_link v1 exige stride=1: la ventana W y la detección de "
                           "episodios están definidas sobre el film a tasa completa "
                           "(decimar redefine el estimador — INSTRUMENT_CONTRACT)")
    exigir_canales(wl, ["estados", "manifest", "worldline_hash", "ticks"])
    exigir_completo(wl, cfg["permitir_incompleto"])
    man = wl["manifest"]
    dt = float(man["dt"])
    sel = ventana(wl, cfg)
    theta = theta_por_nodo(wl, man, sel)                      # (t, nodo) — el de fase
    n_t, n_nodos = theta.shape
    w_ticks = max(int(round(float(cfg["w_ut"]) / dt)), 4)
    if n_t < 3 * w_ticks:
        raise RuntimeError(f"film de {n_t} ticks: se exigen >= 3 ventanas W "
                           f"({3 * w_ticks} ticks) para un veredicto de par honesto")

    # portadora y fase corregida por nodo (§16)
    unw = np.unwrap(theta, axis=0)
    grad = np.gradient(unw, dt, axis=0)
    a_temp = int(round(0.5 / dt)); b_temp = int(round(float(cfg["temprana_ut"]) / dt))
    n_tard = int(round(float(cfg["tardia_ut"]) / dt))
    omega_nodo = np.empty((n_nodos, 3))
    fases = []
    for k in range(n_nodos):
        w_full = abs(float(np.mean(grad[:, k])))
        omega_nodo[k] = (w_full,
                         abs(float(np.mean(grad[a_temp:b_temp, k]))),
                         abs(float(np.mean(grad[-n_tard:, k]))))
        phi = np.arctan2(np.sin(theta[:, k]) / max(w_full, 1e-9), np.cos(theta[:, k]))
        fases.append(np.unwrap(phi))

    stride_det = int(cfg["stride_det"])
    # sostén de EPISODIO = 1 ventana W (semántica §12); sostén de FIRMEZA (t_lock) =
    # sosten_ventanas × W (default 2, patrón §12/§16)
    min_ep = max(int(round(w_ticks / stride_det)), 1)
    min_firme = max(int(round(float(cfg["sosten_ventanas"]) * w_ticks / stride_det)), 1)
    pares, filas = [], []
    for i in range(n_nodos):
        for j in range(i + 1, n_nodos):
            rw = _rw_movil(fases[i] - fases[j], w_ticks)
            rw_det = rw[::stride_det]
            rw_final = float(np.mean(rw[-w_ticks:]))
            n_ep, dur_max, sost = _episodios(rw_det, float(cfg["umbral_coqueteo"]), min_ep)
            _, _, sost_firme = _episodios(rw_det, float(cfg["umbral_firme"]), min_firme)
            t_lock = (float(sost_firme * stride_det * dt) if sost_firme is not None
                      else float("nan"))
            if rw_final >= float(cfg["umbral_firme"]):
                estado = 2
            elif n_ep >= 1:
                estado = 1
            else:
                estado = 0
            zf = np.exp(1j * (fases[i] - fases[j]))[-w_ticks:]
            pares.append((i, j))
            filas.append((rw_final, float(np.max(rw)), float(np.angle(np.mean(zf))),
                          abs(omega_nodo[i, 1] - omega_nodo[j, 1]),
                          abs(omega_nodo[i, 2] - omega_nodo[j, 2]),
                          t_lock, float(n_ep), float(dur_max * stride_det * dt),
                          float(np.mean(rw_det >= float(cfg["umbral_coqueteo"]))),
                          float(estado)))
    filas = np.array(filas)
    return View(INSTRUMENT_ID, VERSION, cfg, wl["worldline_hash"],
                {"ticks": wl["ticks"][sel], "theta": theta,
                 "omega_nodo": omega_nodo,
                 "pares_ij": np.array(pares, dtype=np.int64),
                 "rw_final": filas[:, 0], "rw_max": filas[:, 1],
                 "dphi_final": filas[:, 2],
                 "dw_temprana": filas[:, 3], "dw_tardia": filas[:, 4],
                 "t_lock_ut": filas[:, 5], "episodios": filas[:, 6],
                 "dur_max_ut": filas[:, 7], "frac_coqueteo": filas[:, 8],
                 "estado": filas[:, 9]},
                {"canales": dict(CANALES),
                 "film_intervenida": bool(man.get("intervenida", False)),
                 "film_linaje_intervenido": bool(man.get("linaje_intervenido",
                                                         man.get("intervenida", False))),
                 "procedencia_umbrales": ("MEDIDOS en C1 (bitácora §13/§16): firme=0.95 "
                                          "separa los 7 links; coqueteo=0.80 el hombro; "
                                          "correccion de fase y W=4-8 del panel §16"),
                 "punto_ciego_dw": float(2.0 * np.pi / (w_ticks * dt)),
                 "nota": ("estado: 0=muerto 1=coqueteo 2=firme; t_lock=NaN sin sostén; "
                          "deteccion con resolucion stride_det ticks; rw sobre fase "
                          "CORREGIDA (§16) — no comparable con rw de fase cruda")})
