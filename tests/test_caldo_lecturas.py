"""Instrumentos formales del caldo (M2-build 4a): tests sintéticos HERMÉTICOS
(respuesta conocida por construcción; la paridad contra M1 sellado va en
tools/paridad_lecturas.py porque depende del disco externo)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from study07.instruments.caldo_lecturas import (componentes, fases_banda,
                                                grafo_afinidad, grafo_lock,
                                                matriz_tau, mds_espectro,
                                                omega_reloj, slips_en_lock)

DT = 1e-3


def _tres_osciladores():
    """0 y 1 a ω=10.0 (lockeados por construcción); 2 a ω=12.0 (fuera de lengua)."""
    t = np.arange(0, 20.0, DT)
    sig = np.stack([np.cos(10.0 * t), np.cos(10.0 * t + 0.6),
                    np.cos(12.0 * t)], axis=1)
    return sig


def test_grafo_lock_conocido():
    ph = fases_banda(_tres_osciladores(), DT, lo=7.0, hi=15.0)
    A, frac, grado = grafo_lock(ph, DT, caja_ut=1.0)
    assert A[0, 1] and not A[0, 2] and not A[1, 2]
    assert list(grado) == [1, 1, 0]


def test_slips_cero_en_señal_limpia():
    ph = fases_banda(_tres_osciladores(), DT, lo=7.0, hi=15.0)
    slips, locked = slips_en_lock(ph, DT)
    assert locked > 0 and slips == 0


def test_afinidad_reconstruye_lengua():
    b = np.array([0.0, 0.001, 5.0])          # 0,1 pegados; 2 lejos en el eje ω(b)
    A, dw = grafo_afinidad(b)
    assert A[0, 1] and not A[0, 2] and not A[1, 2]
    assert np.isclose(omega_reloj(0.0), 10.240)


def test_mds_linea_es_1d():
    """Puntos EN UNA LÍNEA: d*=1 y fracción no-euclídea ~0 (métrica exacta)."""
    pos = np.array([0.0, 1.0, 2.0, 3.5, 5.0])
    D = np.abs(pos[:, None] - pos[None, :])
    ev, dstar, no_eucl = mds_espectro(D)
    assert dstar == 1
    assert ev[0] > 100 * abs(ev[1:]).max()
    assert no_eucl < 1e-10


def test_matriz_tau_y_componentes():
    tau_p = np.array([0.1, 0.0, 0.0])        # N=3: pares (0,1),(0,2),(1,2)
    M = matriz_tau(tau_p, 3)
    assert M[0, 1] == 0.1 and M[1, 0] == 0.1 and M.trace() == 0.0
    A = np.zeros((4, 4), dtype=bool)
    A[0, 1] = A[1, 0] = A[2, 3] = A[3, 2] = True
    et = componentes(A)
    assert et[0] == et[1] and et[2] == et[3] and et[0] != et[2]
