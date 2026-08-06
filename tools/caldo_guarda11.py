"""Guarda 11 [SPEC_MOTOR_TAU_V1 §8 fila 11; contrato §11]: calibrador χ^S.

Port del clamp M1 (cirugía de línea fija, artifacts/cirugia.py: fuerza programada
F0·cos(ωt) SUMADA como externa, sin reacción) a la ENTRADA S POR MODO del motor nuevo:
se maneja el kernel CERTIFICADO derivatives_apilado (sin tocar el motor) con
f_ext[μ] = F0·cos(ω_d·t) evaluado al t EXACTO de cada sub-paso RK4 (semántica cirugía),
onion frío (origen: punto fijo exacto sin ruido), F0 chico (régimen lineal).

χ^S_μ(ω_d) medido = A_lockin/F0 (lock-in sobre ventana declarada tras el transitorio —
estimador DE BANDA, lección §14 de la cirugía). χ^S predicho = |e_μᵀ(iωI−J)⁻¹B e_μ| del
Jacobiano FD en el origen (paridad certificada por guarda 10a). IDENTIDAD r ≡
χ_med/χ_pred = 1 (c=1): la NULA sin parámetro libre de toda lectura del caldo — las
desviaciones se REPORTAN, no se ajustan.
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
OUT = STUDY07 / "data/caldo"

DT = 8e-5
F0 = 1e-4                      # régimen lineal (respuesta ~χ·F0 ≪ 1)
T_TRANS, T_MED = 3.0, 5.0      # transitorio descartado + ventana lock-in declarada
FRACS = (0.95, 0.98, 1.0, 1.02, 1.05)


def _spec():
    from study07.compat.study06_v4 import parse_theta_v2
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    u = [x for x in spec_j["unidades"] if x["run_id"].startswith("s120_par134")][0]
    spec, _ = parse_theta_v2(u["constituyentes"][0]["theta"], emission_scale=0.1)
    return spec


def _dims(spec):
    return [spec.n_modes, spec.n_modes, spec.n_z, spec.n_layers, spec.n_layers]


def jacobiano_origen(spec):
    """J del RHS certificado en el origen (FD central) — como guarda 10a."""
    from study07.physics.rhs_apilado import derivatives_apilado
    dims = _dims(spec)
    dim = sum(dims)
    corte = np.cumsum(dims)[:-1]
    nm = spec.n_modes

    def rhs(vec):
        p = np.split(vec, corte)
        d = derivatives_apilado(spec, p[0][None], p[1][None], p[2][None],
                                p[3][None], p[4][None], np.zeros((1, nm)))
        return np.concatenate([a[0] for a in d])

    h = 1e-7
    J = np.empty((dim, dim))
    for k in range(dim):
        d = np.zeros(dim); d[k] = h
        J[:, k] = (rhs(d) - rhs(-d)) / (2 * h)
    return J


def chi_pred(spec, J, mu, w):
    """|x_μ/F_μ| de la respuesta lineal vestida: y = (iωI − J)⁻¹ B, B = e_{v_μ}/m_μ."""
    dim = J.shape[0]
    B = np.zeros(dim)
    B[spec.n_modes + mu] = 1.0 / spec.modes[mu].mass     # la fuerza entra por v̇_μ
    y = np.linalg.solve(1j * w * np.eye(dim) - J, B)
    return float(np.abs(y[mu]))


def _medir(args):
    """Una corrida clamp: drive en modo μ a ω_d, lock-in de x_μ → χ medido."""
    mu, w_d = args
    from study07.physics.rhs_apilado import derivatives_apilado
    spec = _spec()
    dims = _dims(spec)
    nm = spec.n_modes
    x = np.zeros((1, nm)); v = np.zeros((1, nm))
    z = np.zeros((1, dims[2])); b = np.zeros((1, dims[3])); e = np.zeros((1, dims[4]))
    ticks = int(round((T_TRANS + T_MED) / DT))
    k_ini = int(round(T_TRANS / DT))
    acc = 0.0 + 0.0j
    n_acc = 0

    def f_ext(t):
        f = np.zeros((1, nm))
        f[0, mu] = F0 * np.cos(w_d * t)
        return f

    for k in range(ticks):
        t = k * DT
        est = (x, v, z, b, e)
        k1 = derivatives_apilado(spec, *est, f_ext(t))
        e2 = tuple(s + 0.5 * DT * q for s, q in zip(est, k1))
        k2 = derivatives_apilado(spec, *e2, f_ext(t + 0.5 * DT))
        e3 = tuple(s + 0.5 * DT * q for s, q in zip(est, k2))
        k3 = derivatives_apilado(spec, *e3, f_ext(t + 0.5 * DT))
        e4 = tuple(s + DT * q for s, q in zip(est, k3))
        k4 = derivatives_apilado(spec, *e4, f_ext(t + DT))
        c6 = DT / 6.0
        x, v, z, b, e = tuple(s + c6 * (a + 2 * b_ + 2 * c_ + d)
                              for s, a, b_, c_, d in zip(est, k1, k2, k3, k4))
        if k >= k_ini:
            acc += x[0, mu] * np.exp(-1j * w_d * (k + 1) * DT)
            n_acc += 1
    A = 2.0 * abs(acc) / n_acc
    return {"mu": mu, "w_d": w_d, "chi_med": A / F0}


def main():
    from study07.physics.state import Layer
    spec = _spec()
    iS = [i for i, m in enumerate(spec.modes) if m.layer in (Layer.S1, Layer.S2)]
    J = jacobiano_origen(spec)
    ev = np.linalg.eigvals(J)
    print(f"[guarda11] dim={J.shape[0]}  Re(λ)_max={ev.real.max():.4f} "
          f"(origen {'INESTABLE' if ev.real.max() > 0 else 'estable'} — §40)", flush=True)
    trabajos = [(mu, spec.modes[mu].omega0 * f) for mu in iS for f in FRACS]
    t0 = time.time()
    res = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for r in ex.map(_medir, trabajos):
            r["chi_pred"] = chi_pred(spec, J, r["mu"], r["w_d"])
            r["r"] = r["chi_med"] / r["chi_pred"]
            res.append(r)
            m = spec.modes[r["mu"]]
            print(f"  μ={r['mu']:2d} ({m.layer.name}) ω_d={r['w_d']:7.2f}: "
                  f"χ_med={r['chi_med']:.4e} χ_pred={r['chi_pred']:.4e} "
                  f"r={r['r']:.4f}", flush=True)
    rs = np.array([r["r"] for r in res])
    veredicto = {"r_mediana": float(np.median(rs)), "r_min": float(rs.min()),
                 "r_max": float(rs.max()),
                 "desviacion_max_pct": float(np.abs(rs - 1).max() * 100)}
    print(f"[guarda11] r: mediana={veredicto['r_mediana']:.4f} "
          f"rango=[{veredicto['r_min']:.4f}, {veredicto['r_max']:.4f}] "
          f"|r−1|_max={veredicto['desviacion_max_pct']:.2f}%  "
          f"({(time.time()-t0)/60:.1f} min)", flush=True)
    (OUT / "GUARDA11_CHI_S.json").write_text(json.dumps(
        {"genoma": "61b48428", "F0": F0, "dt": DT,
         "ventanas": {"transitorio": T_TRANS, "lockin": T_MED},
         "Re_lambda_max_origen": float(ev.real.max()),
         "resultados": res, "veredicto": veredicto}, indent=1))
    print("[guarda11] → GUARDA11_CHI_S.json", flush=True)


if __name__ == "__main__":
    main()
