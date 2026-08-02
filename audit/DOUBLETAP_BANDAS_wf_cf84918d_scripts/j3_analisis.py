"""JUEZ — analisis uniforme de films (deteccion de capturas, barrido, cruces de banda).

Detectores propios (independientes de t2/t3):
  A) STFT dominancia: rho_j(t) = pico|FFT| en w_L(t)+-1.0 / pico|FFT| en w_self+-1.5
     (Hann W=2 u.t., hop 0.5, zeropad 4x, interpolacion parabolica).
  B) DEMOD (familia independiente, sin FFT): A_movil = |<x_j e^{-i phi_L(t)}>_{1 u.t.}|
     con phi_L = integral de w_L(t) dt (formula, canal b del film);
     A_propia = |<x_j e^{-i w_self t}>_{1 u.t.}|. rho_d = A_movil/A_propia.
  C) detector DEGENERADO (para el chequeo del VOLTEA): w_dom(t) = argmax banda completa
     [2,45]; episodio = |w_dom - w_L| < delta sostenido >= 1 u.t.
Capturas: CONSOLIDADO = rho>1 sostenido >=2 u.t. y persistente hasta fin-1.
          EPISODIO = intervalo maximal rho>1 (>=2 u.t.) no persistente.
Barrido del lider: w_L(t) = C*sqrt(1+0.1*b_Q_lider(t)) con C ajustado contra la
frecuencia espectral del lider (STFT propia) — residuo reportado.
"""
import json
from pathlib import Path
import numpy as np

OUT = Path(__file__).parent
J2 = json.load(open(OUT / "j2_resultados.json"))

BLOCK_BY_PAR = {  # nodo0=lider, nodo1=receptor (manifiestos)
    "par126": ("108114f666e3", "401ff8728f63"), "par127": ("108114f666e3", "74b23f765604"),
    "par128": ("108114f666e3", "956fba96c70c"), "par129": ("108114f666e3", "9c2256bc8e73"),
    "par130": ("108114f666e3", "b053ff4d163b"), "par131": ("108114f666e3", "e58e88925b4d"),
    "par132": ("1bc9dcccf3bd", "34b5ab50a85c"), "par133": ("1bc9dcccf3bd", "46b339f16f33"),
    "par134": ("1bc9dcccf3bd", "61b484288817"),
}

W, HOP, PAD = 2.0, 0.5, 4

def stft_peaks(sig, dt, t_grid, lo, hi):
    """pico (freq, amp) por ventana centrada en t_grid, buscando en [lo,hi] rad/u.t."""
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
        # interpolacion parabolica en ln|S|
        if 0 < k < len(S) - 1 and S[k - 1] > 0 and S[k + 1] > 0:
            la, lb, lc = np.log(S[k - 1]), np.log(S[k]), np.log(S[k + 1])
            d = 0.5 * (la - lc) / (la - 2 * lb + lc + 1e-300)
            d = float(np.clip(d, -0.5, 0.5))
        else:
            d = 0.0
        out_f.append(freqs[k] + d * (freqs[1] - freqs[0]))
        out_a.append(float(S[k]))
    return np.array(out_f), np.array(out_a)

def amp_at(sig, dt, t_grid, w_centers, half):
    """amp pico |FFT| en w_centers(t)+-half por ventana."""
    n_w = int(round(W / dt)); n_fft = n_w * PAD
    win = np.hanning(n_w)
    freqs = 2 * np.pi * np.fft.rfftfreq(n_fft, d=dt)
    out = []
    for tc, wc in zip(t_grid, w_centers):
        i0 = int(round((tc - W / 2) / dt))
        seg = sig[i0:i0 + n_w]
        S = np.abs(np.fft.rfft(seg * win, n_fft))
        m = (freqs >= wc - half) & (freqs <= wc + half)
        out.append(float(S[m].max()) if m.any() else 0.0)
    return np.array(out)

def runs_true(mask, t_grid, min_dur):
    """intervalos maximales True con duracion >= min_dur."""
    out = []
    i = 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]:
                j += 1
            if t_grid[j] - t_grid[i] >= min_dur:
                out.append((float(t_grid[i]), float(t_grid[j])))
            i = j + 1
        else:
            i += 1
    return out

def analizar(par, brazo):
    f = np.load(OUT / f"{par}_{brazo}_jz.npz")
    dt = float(f["dt_s"]); x0, x1 = f["x0"], f["x1"]
    b0, b1 = f["b0"], f["b1"]
    capas = [str(c) for c in f["capas1"]]
    iQ = [i for i, c in enumerate(capas) if c == "Q"]
    n = x0.shape[0]; T = n * dt
    t = np.arange(n) * dt
    t_grid = np.arange(W / 2 + 0.25, T - W / 2 - 0.25, HOP)
    lider_sig = x0[:, :3].sum(axis=1)  # suma modos Q del lider
    bq0 = b0[:, 0]  # capa Q = indice 0 (orden canonico Q,S1,S2)
    bq1_max = float(np.abs(b1).max(axis=0)[0])

    # --- barrido del lider: fit C en w = C*sqrt(1+0.1*b_Q) ---
    wl_spec, _ = stft_peaks(lider_sig, dt, t_grid, 2.0, 60.0)
    raiz = np.sqrt(1 + 0.1 * np.interp(t_grid, t, bq0))
    C = float(np.sum(wl_spec * raiz) / np.sum(raiz ** 2))
    resid = float(np.max(np.abs(wl_spec - C * raiz) / (C * raiz)))
    w_L = C * np.sqrt(1 + 0.1 * np.interp(t_grid, t, bq0))
    w_L_full = C * np.sqrt(1 + 0.1 * bq0)

    # --- receptor por modo Q ---
    res_modos = {}
    phi_L = np.cumsum(w_L_full) * dt  # fase integrada de la linea (demod B)
    n_1ut = int(round(1.0 / dt))
    for j in iQ:
        sig = x1[:, j]
        # w_self temprana: [1,6]
        early_grid = np.array([3.0])
        wself = float(stft_peaks(sig, dt, early_grid, 2.0, 25.0)[0][0])
        A_L = amp_at(sig, dt, t_grid, w_L, 1.0)
        A_S = amp_at(sig, dt, t_grid, np.full_like(t_grid, wself), 1.5)
        rho = A_L / np.maximum(A_S, 1e-300)
        # demod (familia B)
        dm = sig * np.exp(-1j * phi_L)
        ds = sig * np.exp(-1j * wself * t)
        k = np.ones(n_1ut) / n_1ut
        Am = np.abs(np.convolve(dm, k, mode="same"))
        As = np.abs(np.convolve(ds, k, mode="same"))
        rho_d = np.interp(t_grid, t, Am / np.maximum(As, 1e-300))
        # veredictos
        def veredicto(r):
            eps = runs_true(r > 1.0, t_grid, 2.0)
            consolidado = None
            if eps and eps[-1][1] >= t_grid[-1] - 1.0:
                consolidado = eps[-1][0]
            return {"episodios_rho>1": eps, "consolidado_desde": consolidado,
                    "rho_max": float(r.max()), "rho_fin": float(r[-1])}
        # frecuencia llegada/final del modo
        w_ini = float(stft_peaks(sig, dt, np.array([3.0]), 2.0, 45.0)[0][0])
        w_fin = float(stft_peaks(sig, dt, np.array([T - 3.0]), 2.0, 45.0)[0][0])
        res_modos[f"Q{j}"] = {"w_self": round(wself, 3), "w_llegada": round(w_ini, 3),
                              "w_final": round(w_fin, 3),
                              "stft": veredicto(rho), "demod": veredicto(rho_d)}

    # --- detector DEGENERADO banda completa (chequeo VOLTEA, solo informativo) ---
    degen = {}
    for j in iQ:
        w_dom, _ = stft_peaks(x1[:, j], dt, t_grid, 2.0, 45.0)
        for delta in (0.5, 1.0):
            eps = runs_true(np.abs(w_dom - w_L) < delta, t_grid, 1.0)
            degen[f"Q{j}_delta{delta}"] = eps

    # --- cruces de banda S1 del receptor (formula, canal b del film) ---
    bandas = J2[[k for k in J2 if k.startswith(BLOCK_BY_PAR[par][1])][0]]["bandas_x_solo"]
    lo, hi = bandas["S1"]
    def t_cruce(w_obj):
        m = w_L_full >= w_obj
        return float(t[np.argmax(m)]) if m.any() else None
    cruce = {"banda_S1": [lo, hi], "t_entra": t_cruce(lo), "t_sale": t_cruce(hi),
             "w_L_max": float(w_L_full.max()), "w_L_ini": float(w_L_full[0])}

    return {"par": par, "brazo": brazo, "C_fit": round(C, 4), "resid_max": round(resid, 4),
            "bq_lider": [float(bq0[0]), float(bq0[-1])], "bq_receptor_max_Q": bq1_max,
            "cruce_S1": cruce, "modos": res_modos, "degenerado_par132": degen if par == "par132" else None}

FILMS = [("par132", "t"), ("par133", "t"), ("par134", "t"),
         ("par126", "t"), ("par127", "t"), ("par128", "t"),
         ("par129", "t"), ("par130", "t"), ("par131", "t"),
         ("par133", "f"), ("par134", "f")]

res = {}
for par, brazo in FILMS:
    if not (OUT / f"{par}_{brazo}_jz.npz").exists():
        print(par, brazo, "PENDIENTE"); continue
    r = analizar(par, brazo)
    res[f"{par}_{brazo}"] = r
    print(f"\n== {par}_{brazo} == C={r['C_fit']} resid={r['resid_max']} "
          f"bqL {r['bq_lider'][0]:.2f}->{r['bq_lider'][1]:.2f} bqR_max {r['bq_receptor_max_Q']:.2e}")
    print(f"   cruce S1 {r['cruce_S1']}")
    for mk, mv in r["modos"].items():
        print(f"   {mk} self={mv['w_self']} llegada={mv['w_llegada']} final={mv['w_final']}"
              f" | STFT cons={mv['stft']['consolidado_desde']} eps={mv['stft']['episodios_rho>1']}"
              f" rho_max={mv['stft']['rho_max']:.2f}"
              f" | DEMOD cons={mv['demod']['consolidado_desde']} rho_max={mv['demod']['rho_max']:.2f}")
    if r["degenerado_par132"]:
        print("   DEGEN:", r["degenerado_par132"])

json.dump(res, open(OUT / "j3_resultados.json", "w"), indent=1, default=str)
print("\nOK")
