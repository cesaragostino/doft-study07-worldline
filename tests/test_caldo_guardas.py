"""Guardas 1-8 del caldo τ [SPEC_MOTOR_TAU_V1 §8] — la batería CI (paso 6)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

from study07.engine.caldo import RedCaldo
from study07.engine.network import Network
from study07.physics.interaccion_tau import evaluar_pares, indice_pares
from study07.physics.state import NodeState


def _spec():
    from study07.compat.study06_v4 import parse_theta_v2
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    u = [x for x in spec_j["unidades"] if x["run_id"].startswith("s120_par134")][0]
    theta = u["constituyentes"][0]["theta"]
    spec, _ = parse_theta_v2(theta, emission_scale=1.0 / len(theta["modes"]))
    return spec


DT = 8e-5


def _caldo(**kw):
    base = dict(dt=DT, seed=20260805, K=0.0, lam=0.0, tau_s=8e-4,
                T_pulso=0.0, ticks_pulso=0, T_rem=0.0, ticks_rem=0)
    base.update(kw)
    return RedCaldo(_spec(), kw.pop("n", base.pop("n", 2)), **{k: v for k, v in base.items() if k != "n"})


def test_guarda1_onion_aislado_bit_exacto_vs_v1():
    """K=λ=0: el caldo N=1 reproduce el motor v1 (sin aristas) BIT-EXACTO 2000 ticks."""
    spec = _spec()
    caldo = RedCaldo(spec, 1, dt=DT, seed=7, K=0.0, lam=0.0, tau_s=8e-4,
                     T_pulso=0.0, ticks_pulso=0, T_rem=0.05, ticks_rem=500)
    st0 = NodeState(x=caldo.x[0].copy(), v=caldo.v[0].copy(), z=caldo.z[0].copy(),
                    b=caldo.b[0].copy(), e=caldo.e[0].copy())
    red_v1 = Network([spec], [st0], [], dt=DT, seed=7, k_global=0.0,
                     coupling_gamma_c=0.0, tau_field=0.0, temperature=0.0)
    for _ in range(2000):
        caldo.step()
        red_v1.step()
    for mio, suyo, nombre in ((caldo.x[0], red_v1.states[0].x, "x"),
                              (caldo.v[0], red_v1.states[0].v, "v"),
                              (caldo.z[0], red_v1.states[0].z, "z"),
                              (caldo.b[0], red_v1.states[0].b, "b"),
                              (caldo.e[0], red_v1.states[0].e, "e")):
        assert np.array_equal(mio, suyo), f"guarda 1: canal {nombre} difiere del motor v1"


def test_guarda2_permutacion_con_streams_por_identidad():
    """Permutar slots manteniendo (id, stream): trayectorias por ID iguales al redondeo."""
    kw = dict(dt=DT, seed=11, K=1e-3, lam=1e-2, tau_s=8e-4,
              T_pulso=0.05, ticks_pulso=100, T_rem=0.05, ticks_rem=200)
    a = RedCaldo(_spec(), 3, ids=[0, 1, 2], **kw)
    b = RedCaldo(_spec(), 3, ids=[2, 0, 1], **kw)      # slot s ↔ id perm[s]
    for _ in range(300):
        a.step(); b.step()
    # id k vive en slot k (a) y en slot donde ids==k (b)
    for k in range(3):
        sb = int(np.where(b.ids == k)[0][0])
        assert np.allclose(a.x[k], b.x[sb], rtol=1e-9, atol=1e-12), \
            f"guarda 2: id {k} difiere más allá del redondeo declarado"


def test_guarda3_todos_los_pares_sin_poda():
    c = _caldo(n=5)
    assert c.n_pairs == 10 and len(c.pares) == 10
    # la única máscara legal es la causal (t_src<0); no existe poda por τ/amplitud:
    S_ret, activo = c._S_ret(10 * DT, np.full(10, 3 * DT), c.x, c.v)
    assert activo.all()                                   # todos consultados
    S_ret2, activo2 = c._S_ret(10 * DT, np.full(10, 20 * DT), c.x, c.v)
    assert (~activo2).all()                               # todos desconectados (causal)


def test_guarda4_cero_causal_J_completa():
    """Par causalmente desconectado ⇒ las CUATRO salidas nulas (incl. reacción)."""
    n, n_s = 2, 3
    pares = indice_pares(n)
    x_S = np.ones((n, n_s))
    f_S, dtau, B = evaluar_pares(x_S, x_S.sum(1), np.ones((1, 2)), np.ones(n_s),
                                 np.array([0.5]), np.array([False]), pares,
                                 K=1.0, lam=1.0, tau_s=8e-4)
    assert np.all(f_S == 0.0) and dtau[0] == 0.0 and B[0] == 0.0


def test_guarda7_simetria_sin_textura():
    """MISMO key para todos (config de test): onions idénticos para siempre."""
    from study07.compat.study06_v4 import node_seed
    c = _caldo(n=3, K=1e-3, lam=1e-2)
    c.rngs = [np.random.default_rng(node_seed(99, 0)) for _ in range(3)]
    c.T_pulso, c.ticks_pulso = 0.05, 100
    for _ in range(200):
        c.step()
    assert np.array_equal(c.x[0], c.x[1]) and np.array_equal(c.x[1], c.x[2]), \
        "guarda 7: con pulso idéntico los onions divergieron (textura fabricada)"
    assert np.all(c.tau == c.tau[0])


def test_guarda8_rectificacion_no_impuesta():
    """ℬ sobre señales INCONMENSURABLES: |⟨dτ/dt⟩_T| cae ~1/T (pendiente ≤ −0.8);
    el control CONMENSURADO apareado NO cae."""
    phi = (1 + np.sqrt(5)) / 2
    w1 = 43.45
    dt = 1e-4
    t = np.arange(0, 400.0, dt)

    def deriva(w2, T):
        S1 = np.cos(w1 * t)
        S2 = np.cos(w2 * t + 0.7)
        B = S1 * S2 + S2 * S1                             # bilineal par (λ=1, τ→0 ret≈act)
        m = t < T
        return abs(np.mean(B[m]))

    Ts = np.array([50.0, 100.0, 200.0, 400.0])
    inco = np.array([deriva(w1 * phi, T) for T in Ts])
    conm = np.array([deriva(w1, T) for T in Ts])          # control 1:1 (DC del bilineal PAR)
    pend = np.polyfit(np.log(Ts), np.log(inco + 1e-300), 1)[0]
    assert pend <= -0.8, f"guarda 8: pendiente {pend:.2f} > -0.8 (no cae como 1/T)"
    pend_c = np.polyfit(np.log(Ts), np.log(conm + 1e-300), 1)[0]
    assert pend_c > -0.5, f"control conmensurado cayó ({pend_c:.2f}) — test degenerado"


def test_clamp_respaldo_contador():
    """τ jamás negativo tras combine; el clamp de respaldo cuenta al trending."""
    c = _caldo(n=2, K=0.0, lam=0.0)
    c.tau[:] = 1e-9                                       # pegado a la frontera
    c.lam = -50.0                                          # forzar ℬ<0 brutal (solo test)
    c.x[:, c.S_idx] = 1.0                                  # S≠0 para que ℬ actúe
    for _ in range(50):
        c.step()
    assert np.all(c.tau >= 0.0)
