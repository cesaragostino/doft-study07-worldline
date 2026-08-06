"""Guardas 9 y 10a del caldo τ [SPEC_MOTOR_TAU_V1 §2.3, §12.5, §12.14a — paso 10].

Guarda 9: ORDEN GLOBAL MEDIDO (no asumido) en génesis SUAVE — determinista (sin
remanente ni kicks: la comparación por trayectoria exige ruido idéntico, y el gate
con ruido es estadístico — §14 bitácora 2026-08-05), onions IDÉNTICOS (S_i=S_j ⇒
ℬ = 2λS² ≥ 0 siempre: s nunca conmuta, sin cruces de frontera causal). Se declara
en el manifiesto: orden ≥ 3 garantizado, ~4 esperado (Hermite O(dt⁴) + RK4).

Guarda 10a: paridad de MATRIZ del Jacobiano frío — FD central del RHS de referencia
(physics/rhs.py, intocado) vs derivatives_apilado (transcripción certificada), sin
integrar. Doble gate de §12.16 extendido a la matriz.
"""
import json
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

from study07.engine.caldo import RedCaldo
from study07.physics.rhs import derivatives
from study07.physics.rhs_apilado import derivatives_apilado
from study07.physics.state import NodeState


def _spec():
    from study07.compat.study06_v4 import parse_theta_v2
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    u = [x for x in spec_j["unidades"] if x["run_id"].startswith("s120_par134")][0]
    spec, _ = parse_theta_v2(u["constituyentes"][0]["theta"], emission_scale=0.1)
    return spec


DT = 8e-5


def _caldo_det(spec, dt):
    """Génesis suave determinista: sin remanente, sin pulso; IC fija idéntica en
    ambos onions puesta ANTES de que la fila 0 de la historia quede sellada."""
    c = RedCaldo(spec, 2, dt=dt, seed=1, K=0.3, lam=100.0, tau_s=8e-4,
                 T_pulso=0.0, ticks_pulso=0, T_rem=0.0, ticks_rem=0)
    rng = np.random.default_rng(20260806)          # patrón FIJO, no ruido de proceso
    patron = 0.02 * rng.standard_normal(len(c.S_idx))
    c.x[:, c.S_idx] = patron[None, :]
    c.historia.buf[0, :, :, 0] = c.x[:, c.S_idx]   # re-sellar la fila t=0 con la IC
    c.historia.buf[0, :, :, 1] = c.v[:, c.S_idx]
    return c


def test_guarda9_orden_global_medido():
    T = 0.08                                        # 1000 pasos a dt — génesis suave
    fin = {}
    for div in (1, 2, 4):
        c = _caldo_det(_spec(), DT / div)
        for _ in range(int(round(T / (DT / div)))):
            c.step()
        fin[div] = (c.x.copy(), c.tau.copy())
    e1x = float(np.max(np.abs(fin[1][0] - fin[4][0])))
    e2x = float(np.max(np.abs(fin[2][0] - fin[4][0])))
    e1t = float(np.max(np.abs(fin[1][1] - fin[4][1])))
    e2t = float(np.max(np.abs(fin[2][1] - fin[4][1])))
    # con referencia dt/4: ratio ≈ (1−4^−p)/(2^−p−4^−p); p=4 ⇒ log2(ratio) ≈ 4.09
    orden_x = float(np.log2(e1x / e2x))
    orden_t = float(np.log2(e1t / e2t))
    assert e1x > 0 and e1t > 0, "trayectoria degenerada: el acople no actuó"
    assert orden_x >= 3.0, f"guarda 9: orden en x = {orden_x:.2f} < 3 (garantizado)"
    assert orden_t >= 3.0, f"guarda 9: orden en τ = {orden_t:.2f} < 3 (garantizado)"
    print(f"[guarda 9] orden medido: x={orden_x:.2f}  τ={orden_t:.2f} "
          f"(e_x(dt)={e1x:.3e}, e_τ(dt)={e1t:.3e})")


def test_guarda10a_jacobiano_frio_paridad():
    spec = _spec()
    nm = len(spec.modes)
    rng = np.random.default_rng(7)
    st = NodeState(x=0.05 * rng.standard_normal(nm),
                   v=0.05 * rng.standard_normal(nm),
                   z=0.05 * rng.standard_normal(spec.n_z),
                   b=0.05 * rng.standard_normal(spec.n_layers),
                   e=np.abs(0.05 * rng.standard_normal(spec.n_layers)))
    campos = [("x", st.x), ("v", st.v), ("z", st.z), ("b", st.b), ("e", st.e)]
    h = 1e-6

    def rhs_ref(vec):
        partes = np.split(vec, np.cumsum([len(a) for _, a in campos])[:-1])
        s = NodeState(x=partes[0], v=partes[1], z=partes[2], b=partes[3], e=partes[4])
        d = derivatives(spec, s, 0.0)
        return np.concatenate([d.x, d.v, d.z, d.b, d.e])

    def rhs_api(vec):
        partes = np.split(vec, np.cumsum([len(a) for _, a in campos])[:-1])
        d = derivatives_apilado(spec, partes[0][None], partes[1][None],
                                partes[2][None], partes[3][None], partes[4][None],
                                np.zeros((1, nm)))
        return np.concatenate([a[0] for a in d])

    v0 = np.concatenate([a for _, a in campos])
    dim = len(v0)
    J_ref = np.empty((dim, dim))
    J_api = np.empty((dim, dim))
    for k in range(dim):
        d = np.zeros(dim); d[k] = h
        J_ref[:, k] = (rhs_ref(v0 + d) - rhs_ref(v0 - d)) / (2 * h)
        J_api[:, k] = (rhs_api(v0 + d) - rhs_api(v0 - d)) / (2 * h)
    assert np.array_equal(J_ref, J_api), \
        "guarda 10a: el Jacobiano frío difiere entre rhs.py y derivatives_apilado"
