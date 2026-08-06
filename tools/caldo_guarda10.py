"""Guarda 10b [SPEC_MOTOR_TAU_V1 §12.14b — paso 10]: invariantes internos del motor
nuevo con el ESTIMADOR DE BANDA EXISTENTE (núcleo j3 verbatim de leer_suelto120).

Corrida (i): N=1, K=λ=0, calendario de pulso del caldo 1 → el reloj C√(1+0.1b_Q)
debe sostener resid ≤ 1.5% (sellado) sobre 120 u.t.; R² de los picos reportado.
Corrida (ii): N=2 con (K,λ) declarados por la ronda 2b (argv) — mismo estimador
con el acople vivo: el reloj es propiedad del onion, no del aislamiento.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
OUT = STUDY07 / "data/caldo"

W, HOP, PAD = 2.0, 0.5, 4                     # j3 verbatim
DT = 8e-5
T_PULSO, TICKS_PULSO = 13.0, 1250             # calendario caldo 1 (prereg piloto i)
T_REM, TICKS_REM = 0.05, 2500


def _spec():
    from study07.compat.study06_v4 import parse_theta_v2
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    u = [x for x in spec_j["unidades"] if x["run_id"].startswith("s120_par134")][0]
    spec, _ = parse_theta_v2(u["constituyentes"][0]["theta"], emission_scale=0.1)
    return spec


def stft_peaks(sig, dt, t_grid, lo, hi):      # j3 verbatim (leer_suelto120.py)
    n_w = int(round(W / dt)); n_fft = n_w * PAD
    win = np.hanning(n_w)
    freqs = 2 * np.pi * np.fft.rfftfreq(n_fft, d=dt)
    sel = (freqs >= lo) & (freqs <= hi)
    idx_sel = np.where(sel)[0]
    out_f, out_a = [], []
    for tc in t_grid:
        i0 = int(round((tc - W / 2) / dt))
        seg = sig[i0:i0 + n_w]
        S = np.abs(np.fft.rfft(seg * win, n_fft))
        k_rel = int(np.argmax(S[idx_sel])); k = idx_sel[k_rel]
        if 0 < k < len(S) - 1 and S[k - 1] > 0 and S[k + 1] > 0:
            la, lb, lc = np.log(S[k - 1]), np.log(S[k]), np.log(S[k + 1])
            d = 0.5 * (la - lc) / (la - 2 * lb + lc + 1e-300)
            d = float(np.clip(d, -0.5, 0.5))
        else:
            d = 0.0
        out_f.append(freqs[k] + d * (freqs[1] - freqs[0]))
        out_a.append(float(S[k]))
    return np.array(out_f), np.array(out_a)


def correr(n, K, lam, etiqueta):
    from study07.engine.caldo import RedCaldo
    from study07.physics.state import Layer
    spec = _spec()
    c = RedCaldo(spec, n, dt=DT, seed=20260805, K=K, lam=lam, tau_s=8e-4,
                 T_pulso=T_PULSO, ticks_pulso=TICKS_PULSO,
                 T_rem=T_REM, ticks_rem=TICKS_REM)
    iQ = [i for i, m in enumerate(spec.modes) if m.layer == Layer.Q][:3]
    idxQ = [i for i, cap in enumerate(spec.layers_present) if cap == Layer.Q][0]
    ticks = int(round(120.0 / DT))
    lider = np.empty((ticks, n)); bq = np.empty((ticks, n))
    t0 = time.time()
    for k in range(ticks):
        c.step()
        lider[k] = c.x[:, iQ].sum(axis=1)
        bq[k] = c.b[:, idxQ]
    t = np.arange(ticks) * DT
    t_grid = np.arange(W / 2 + 0.25, 120.0 - W / 2 - 0.25, HOP)
    res = {"etiqueta": etiqueta, "n": n, "K": K, "lam": lam, "ut": 120.0,
           "calendario": {"T_pulso": T_PULSO, "ticks_pulso": TICKS_PULSO,
                          "T_rem": T_REM, "ticks_rem": TICKS_REM},
           "min_por_corrida": (time.time() - t0) / 60, "onions": []}
    for i in range(n):
        w_spec, _ = stft_peaks(lider[:, i], DT, t_grid, 2.0, 60.0)
        raiz = np.sqrt(1 + 0.1 * np.interp(t_grid, t, bq[:, i]))
        C = float(np.sum(w_spec * raiz) / np.sum(raiz ** 2))
        resid = float(np.max(np.abs(w_spec - C * raiz) / (C * raiz)))
        ss_res = float(np.sum((w_spec - C * raiz) ** 2))
        ss_tot = float(np.sum((w_spec - w_spec.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        res["onions"].append({"C": C, "resid_max": resid, "R2_picos": r2,
                              "pasa_1p5": bool(resid <= 0.015),
                              "b_q_rango": [float(bq[:, i].min()), float(bq[:, i].max())]})
        print(f"  [{etiqueta}] onion {i}: C={C:.4f} resid={resid*100:.2f}% "
              f"R²={r2:.4f} {'PASA' if resid <= 0.015 else 'FALLA'}", flush=True)
    res["tau_final"] = [float(x) for x in c.tau] if c.n_pairs else []
    (OUT / f"GUARDA10B_{etiqueta}.json").write_text(json.dumps(res, indent=1))
    print(f"[guarda10b] {etiqueta} → GUARDA10B_{etiqueta}.json "
          f"({res['min_por_corrida']:.1f} min)", flush=True)


if __name__ == "__main__":
    modo = sys.argv[1]
    if modo == "i":
        correr(1, 0.0, 0.0, "i")
    elif modo == "ii":
        correr(2, float(sys.argv[2]), float(sys.argv[3]), "ii")
