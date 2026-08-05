"""Tests del núcleo del caldo τ: historia (paso 2), interacción (paso 3) y la
CERTIFICACIÓN elementwise del kernel apilado (paso 4, gate (a) — diff == 0 EXACTO)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

from study07.physics.historia_tau import HistoriaCaldo
from study07.physics.interaccion_tau import evaluar_pares, indice_pares, s_proyeccion
from study07.physics.rhs_apilado import derivatives_apilado
from study07.physics.rhs import derivatives
from study07.physics.state import Layer, NodeState


def _spec_canonico():
    from study07.compat.study06_v4 import parse_theta_v2
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    u = [x for x in spec_j["unidades"] if x["run_id"].startswith("s120_par134")][0]
    theta = u["constituyentes"][0]["theta"]
    spec, _ = parse_theta_v2(theta, emission_scale=1.0 / len(theta["modes"]))
    return spec


# ───────────────────────────── historia (paso 2) ─────────────────────────────

def test_historia_hermite_orden4():
    """Muestras de sin(ωt) con v exacta ⇒ error de consulta O(dt⁴)."""
    w = 44.57
    tq = np.array([0.3117, 0.4523, 0.5581, 0.6237, 0.7099])   # tiempos ABSOLUTOS fijos
    errs = []
    for dt in (8e-4, 4e-4):
        h = HistoriaCaldo(1, 1, dt, w_ticks_ini=4096)
        for t in np.arange(0, 2000) * dt:
            h.push(np.array([[np.sin(w * t)]]), np.array([[w * np.cos(w * t)]]))
        x, v = h.consulta(np.zeros(len(tq), dtype=int), tq)
        errs.append(np.abs(x[:, 0] - np.sin(w * tq)).max())
    orden = np.log2(errs[0] / errs[1])
    assert orden > 3.5, f"orden Hermite {orden:.2f} < 3.5 (errs {errs})"


def test_historia_sin_prellenado_y_fail_loud():
    h = HistoriaCaldo(2, 3, 8e-5, w_ticks_ini=8, w_ticks_max=8)
    with pytest.raises(RuntimeError, match="vacía"):
        h.consulta(np.array([0]), np.array([0.0]))
    for k in range(12):                       # 8 de capacidad al tope ⇒ ring desde k=8
        h.push(np.full((2, 3), float(k)), np.zeros((2, 3)))
    assert h.tick_min == 4 and h.high_water == 8
    with pytest.raises(RuntimeError, match="pre-ventana"):
        h.consulta(np.array([0]), np.array([2 * 8e-5]))   # tick 2 < tick_min 4


def test_historia_crecimiento_amortizado():
    h = HistoriaCaldo(1, 1, 1.0, w_ticks_ini=4, w_ticks_max=16)
    for k in range(10):
        h.push(np.array([[float(k)]]), np.array([[0.0]]))
    assert h.capacidad >= 8 and h.tick_min == 0          # creció sin descartar
    x, _ = h.consulta(np.array([0]), np.array([3.0]))
    assert x[0, 0] == 3.0                                 # nodo exacto


# ──────────────────────────── interacción (paso 3) ────────────────────────────

def test_s_proyeccion_dominio_completo():
    tau = np.array([-0.5, 0.0, 4e-4, 8e-4, 1.0])
    B_neg = np.full(5, -1.0)
    s = s_proyeccion(tau, B_neg, 8e-4)
    assert s[0] == 0.0 and s[1] == 0.0                    # τ≤0 con ℬ<0 ⇒ 0 (sin runaway)
    assert 0 < s[2] < 1 and s[3] == 1.0 and s[4] == 1.0
    assert np.all(s_proyeccion(tau, np.ones(5), 8e-4) == 1.0)   # ℬ≥0 ⇒ 1 siempre


def test_evaluar_pares_cero_causal_completo():
    n, n_s = 3, 2
    pares = indice_pares(n)
    x_S = np.random.default_rng(1).normal(size=(n, n_s))
    S_act = x_S.sum(axis=1)
    S_ret = np.ones((len(pares), 2))
    activo = np.array([True, False, True])
    f_S, dtau, B = evaluar_pares(x_S, S_act, S_ret, np.ones(n_s),
                                 np.full(len(pares), 0.01), activo, pares,
                                 K=0.1, lam=1.0, tau_s=8e-4)
    assert B[1] == 0.0 and dtau[1] == 0.0                 # ℬ≡0 del par inactivo
    # el par (0,2) inactivo: onion 1 solo participa del par (1,2)=p2... verificar
    # reacción: par inactivo NO aporta ni siquiera el término −n_S·x (J≡0 COMPLETA):
    f_solo, _, _ = evaluar_pares(x_S, S_act, S_ret, np.ones(n_s),
                                 np.full(len(pares), 0.01),
                                 np.array([True, False, False]), pares,
                                 K=0.1, lam=1.0, tau_s=8e-4)
    assert np.all(f_solo[2] == 0.0)                       # onion 2 sin pares activos ⇒ 0


def test_evaluar_pares_reciprocidad_y_forma():
    """Par único: f sobre i usa S_ret_j y la reacción n_S·x_iμ (colapso §1.1)."""
    n, n_s = 2, 3
    pares = indice_pares(n)
    x_S = np.array([[0.1, 0.2, 0.3], [1.0, 2.0, 3.0]])
    S_act = x_S.sum(axis=1)
    S_ret = np.array([[5.0, 7.0]])                        # [S_j^ret→i, S_i^ret→j]
    K = 0.4
    f_S, dtau, B = evaluar_pares(x_S, S_act, S_ret, np.ones(n_s),
                                 np.array([0.02]), np.array([True]), pares,
                                 K=K, lam=2.0, tau_s=8e-4)
    esperado_i = K * (5.0 - 3 * x_S[0])
    esperado_j = K * (7.0 - 3 * x_S[1])
    assert np.allclose(f_S[0], esperado_i) and np.allclose(f_S[1], esperado_j)
    assert np.isclose(B[0], 2.0 * (S_act[0] * 5.0 + S_act[1] * 7.0))


# ──────────────── certificación kernel apilado (paso 4, gate a) ────────────────

def test_certificacion_elementwise_diff_cero():
    """Apilado vs referencia por-onion: igualdad EXACTA (diff == 0) con f_ext=0,
    estados aleatorios cubriendo todas las ramas (x,v,z,b,e ≠ 0)."""
    spec = _spec_canonico()
    rng = np.random.default_rng(20260805)
    N = 7
    x = rng.normal(size=(N, spec.n_modes))
    v = rng.normal(size=(N, spec.n_modes))
    z = rng.normal(size=(N, spec.n_z)) * 0.5
    b = rng.normal(size=(N, spec.n_layers)) * 2.0
    e = np.abs(rng.normal(size=(N, spec.n_layers))) * 3.0
    f0 = np.zeros((N, spec.n_modes))
    dx, dv, dz, db, de = derivatives_apilado(spec, x, v, z, b, e, f0)
    for i in range(N):
        st = NodeState(x=x[i].copy(), v=v[i].copy(), z=z[i].copy(),
                       b=b[i].copy(), e=e[i].copy())
        ref = derivatives(spec, st, 0.0)
        for mio, suyo, nombre in ((dx[i], ref.x, "x"), (dv[i], ref.v, "v"),
                                  (dz[i], ref.z, "z"), (db[i], ref.b, "b"),
                                  (de[i], ref.e, "e")):
            diff = np.abs(mio - suyo)
            assert diff.max() == 0.0, \
                f"onion {i} canal {nombre}: diff max {diff.max():.3e} ≠ 0 EXACTO"


def test_f_ext_por_modo():
    """La ley nueva: f_ext entra POR MODO dividido por su masa (no escalar uniforme)."""
    spec = _spec_canonico()
    x = np.zeros((1, spec.n_modes)); v = np.zeros_like(x)
    z = np.zeros((1, spec.n_z)); b = np.zeros((1, spec.n_layers))
    e = np.zeros((1, spec.n_layers))
    f = np.zeros((1, spec.n_modes)); f[0, 4] = 2.5
    _, dv, _, _, _ = derivatives_apilado(spec, x, v, z, b, e, f)
    esperado = 2.5 / spec.modes[4].mass
    assert dv[0, 4] == esperado and np.all(np.delete(dv[0], 4) == 0.0)
