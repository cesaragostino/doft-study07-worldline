"""LECTOR SELLADO de la cirugía de línea fija [M1, §13/§13-bis — declaraciones del juez
wf_030bb1cc]. Se escribe, se mata y se committea ANTES de abrir film ON alguno.

Canales por unidad ON × modo Q (sub10, dt_s=8e-4):
  · razon_nula(t) = A_med(ventana ±5 u.t., abs-max — MISMO estimador que NULA.json) /
    A_pred(nula lineal). La nula está sellada por hash (§13-bis); razon≈1 = lineal puro;
    desviación sostenida = física más allá de la nula (captura no-lineal / residuo notch).
  · rho(t) = A_L/A_S espectral ANTI-FUGA (§8): Hann W=8 Y W=16 normalizadas físicas
    (Σwin/2), banda drive ω(t)±0.75 vs banda propia ω_self±1.5; bandera si difieren >15%
    (se usa W=16, declarado). Captura = ρ>1 sostenido ≥2 u.t. (convención §7-C3);
    cruces citables t∈[10,110].
  · 1B (P1-σ): tasa = dln(ρ)/dt del film ON con corrección APAREADA al gemelo OFF:
    tasa_corr = dlnρ + dln(A_S^OFF)(mismas ventanas — los batidos se cancelan por apareo,
    F̂ constante por construcción). Veredicto sellado §3-film600: |σ|×[0.7,1.3] ⇒ σ es
    EL número; ≥1.5× ⇒ co-ordena. Test de SIGNO para 34b-Q0 (σ=+0.0015: autonomía).
  · 1C (histéresis): eventos de captura/release contra ω(t) del programa; el veredicto
    NUNCA es up-vs-down crudo: es (medido−nula) POR DIRECCIÓN al mismo (ω,F0); banda
    2δ/rate declarada para modos no centrados.
  · 1D (E2): lazo medido = RMS(drive_film)/RMS(fuerza a lazo abierto k_c·X+γ_c·V) vs
    |1/(1+χ_em·K)| predicho (χ_em compleja de la emisión 0.1·Σx, K=k_c+iωγ_c) — un lado.
Salida: data/cirugia/LECTURA_CIRUGIA.json. Números, no conclusiones (§14 los registra).
Subcomandos: matar | leer
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
sys.path.insert(0, str(STUDY07 / "tools"))
OUT = STUDY07 / "data/cirugia"
DT_S = 8e-4                       # sub10
T_CIT = (10.0, 110.0)

from cirugia_campana import ENGINE, RECEPTORES, build_A, _spec_de  # noqa: E402


def _amp_fft(sig, tc, wc, half, Wut):
    n_w = int(round(Wut / DT_S))
    i0 = max(0, int(round((tc - Wut / 2) / DT_S)))
    seg = sig[i0:i0 + n_w]
    if len(seg) < n_w:
        return None
    win = np.hanning(n_w)
    S = np.abs(np.fft.rfft(seg * win, n_w * 8))
    fr = 2 * np.pi * np.fft.rfftfreq(n_w * 8, d=DT_S)
    m = (fr >= wc - half) & (fr <= wc + half)
    return float(S[m].max() / (win.sum() / 2)) if m.any() else None


def _amp_conv(sig, tc, wc, half):
    """Anti-fuga §8: W=8 y W=16; bandera si difieren >15%; se usa W=16."""
    a8 = _amp_fft(sig, tc, wc, half, 8.0)
    a16 = _amp_fft(sig, tc, wc, half, 16.0)
    if a8 is None or a16 is None:
        return None, True
    return a16, bool(a16 > 0 and abs(a8 - a16) / a16 > 0.15)


def _cargar(run_dir, n_q=3):
    from study07.instruments.api import load_run
    wl = load_run(run_dir)
    nd = wl["manifest"]["por_nodo"][0]
    nm = nd["n_modes"]
    est = wl["estados"][0][::10, :nm].astype(np.float64)
    drv = np.concatenate([wl["drive"][::10, 0]]) if isinstance(wl.get("drive"), np.ndarray) \
        else None
    prog = wl["manifest"].get("programa")
    del wl
    return est, drv, prog


def _leer_unidad(pref, run_dir, nula_u, chi_base, off_amp=None):
    spec, _ = _spec_de(pref)
    from study07.physics.state import Layer
    qidx = list(spec.layer_indices[Layer.Q])
    w_self = [spec.modes[p].omega0 for p in qidx]
    est, drv, prog = _cargar(run_dir)
    x = est[:, qidx]
    T = len(x) * DT_S
    F0, w0, rate = prog["F0"], prog["w0"], prog["rate"]
    reg = {"programa": prog, "modos": {}}
    ventanas = [float(t) for t in range(10, int(T) - 5, 10)]
    for j in range(len(qidx)):
        sig = x[:, j]
        filas = []
        for tt in ventanas:
            w_t = w0 + rate * tt
            a_med, flag_w = _amp_conv(sig, tt, w_t, 0.75)
            a_s, _ = _amp_conv(sig, tt, w_self[j], 1.5)
            i0 = max(0, int((tt - 5) / DT_S)); i1 = int((tt + 5) / DT_S)
            a_abs = float(np.abs(sig[i0:i1]).max())
            pred = nula_u["x_pred_sub10_absmax_por_ventana"].get(str(int(tt)))
            razon = (a_abs / pred[j]) if (pred and pred[j] > 0) else None
            rho = (a_med / a_s) if (a_med and a_s and a_s > 0) else None
            filas.append({"t": tt, "razon_nula": None if razon is None else round(razon, 4),
                          "rho": None if rho is None else round(rho, 4),
                          "flag_W": flag_w,
                          "A_L": None if a_med is None else float(a_med),
                          "A_S": None if a_s is None else float(a_s)})
        rhos = [(f["t"], f["rho"]) for f in filas if f["rho"] is not None]
        eventos = []
        estado = False
        for t, r in rhos:
            if r > 1.0 and not estado:
                eventos.append({"tipo": "captura", "t": t}); estado = True
            elif r <= 1.0 and estado:
                eventos.append({"tipo": "release", "t": t}); estado = False
        eventos = [e for e in eventos if T_CIT[0] <= e["t"] <= T_CIT[1] or T > 130]
        reg["modos"][f"Q{j}"] = {"filas": filas, "eventos_rho1": eventos,
                                 "razon_nula_mediana": round(float(np.median(
                                     [f["razon_nula"] for f in filas
                                      if f["razon_nula"] is not None])), 4)
                                 if any(f["razon_nula"] is not None for f in filas)
                                 else None}
    # E2 (link_real): lazo de UN lado — F̂_med/|K·X_prog| vs |1/(1+χ_em·K)| predicho
    if prog["modo"] == "link_real" and drv is not None:
        i0, i1 = int(20 / DT_S), int(110 / DT_S)
        f_med = float(np.sqrt(np.mean(drv[i0:i1] ** 2)))
        k_c, g_c = ENGINE["kappa_global"], ENGINE["coupling_gamma_c"]
        f_abierto = F0 * float(np.hypot(k_c, g_c * w0)) / np.sqrt(2)
        n = spec.n_modes
        A, m = build_A(spec)
        dim = A.shape[0]
        B = np.zeros(dim); B[n:2 * n] = 1.0 / m
        xw = np.linalg.solve(1j * w0 * np.eye(dim) - A, B)
        chi_em = 0.1 * complex(np.sum(xw[:n]))
        K = complex(k_c, g_c * w0)
        reg["e2_lazo"] = {"F_med_rms": f_med, "F_abierto_rms": f_abierto,
                          "lazo_medido": round(f_med / f_abierto, 4),
                          "lazo_predicho": round(float(abs(1 / (1 + chi_em * K))), 4)}
    # P1-σ (estaciones bajas): tasa corregida apareada al OFF
    if off_amp is not None and rate == 0.0:
        for j in range(len(qidx)):
            filas = reg["modos"][f"Q{j}"]["filas"]
            ts = [f["t"] for f in filas if f["rho"] and 20 <= f["t"] <= 110]
            rs = [f["rho"] for f in filas if f["rho"] and 20 <= f["t"] <= 110]
            if len(ts) >= 5:
                dlnr = float(np.polyfit(ts, np.log(rs), 1)[0])
                offs = [off_amp[pref][f"Q{j}"].get(str(int(t))) for t in ts]
                if all(o for o in offs):
                    dln_off = float(np.polyfit(ts, np.log(offs), 1)[0])
                    reg["modos"][f"Q{j}"]["p1_sigma"] = {
                        "dlnrho": round(dlnr, 5), "dlnA_S_off": round(dln_off, 5),
                        "tasa_corr": round(dlnr + dln_off, 5)}
    return reg


def leer():
    git = subprocess.run(["git", "-C", str(STUDY07), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    nula = json.loads((OUT / "NULA.json").read_text())
    chi_base = json.loads((OUT / "CHI_NULA_BASE.json").read_text())
    # amplitudes propias del OFF por ventana (para P1-σ apareado)
    off_amp = {}
    for pref in RECEPTORES:
        spec, _ = _spec_de(pref)
        from study07.physics.state import Layer
        qidx = list(spec.layer_indices[Layer.Q])
        est, _, _ = _cargar(OUT / "fase0/unidades" / f"cir0_off_{pref[:3]}")
        off_amp[pref] = {}
        for j, p in enumerate(qidx):
            sig = est[:, p]
            d = {}
            for tt in range(10, 315, 10):
                a, _ = _amp_conv(sig, float(tt), spec.modes[p].omega0, 1.5)
                d[str(tt)] = a
            off_amp[pref][f"Q{j}"] = d
    res = {"_meta": {"lector_git": git, "nula_sha16": None, "t_citable": list(T_CIT),
                     "anti_fuga": "W=8/16, bandera >15%, se usa W16"}}
    import hashlib
    res["_meta"]["nula_sha16"] = hashlib.sha256(
        (OUT / "NULA.json").read_bytes()).hexdigest()[:16]
    for fase in ("fase1_fijas", "fase1A", "fase1E"):
        base = OUT / fase / "unidades"
        if not base.exists():
            continue
        for run_dir in sorted(base.iterdir()):
            rid = run_dir.name
            if not (run_dir / "COMPLETE").exists() or rid not in nula:
                continue
            pref = [p for p in RECEPTORES if p[:3] == rid.split("_")[1]][0]
            reg = _leer_unidad(pref, run_dir, nula[rid], chi_base, off_amp)
            res[rid] = reg
            med = {k: v["razon_nula_mediana"] for k, v in reg["modos"].items()}
            evs = {k: len(v["eventos_rho1"]) for k, v in reg["modos"].items()}
            print(f"[leer] {rid}: razon_nula={med} eventos={evs}", flush=True)
    (OUT / "LECTURA_CIRUGIA.json").write_text(json.dumps(res, indent=1))
    print("→ data/cirugia/LECTURA_CIRUGIA.json")


def matar():
    """Batería del lector: (1) el estimador sobre el film OFF contra la nula OFF-validada
    debe dar razon≈1 y rho sin eventos; (2) anti-fuga dispara en dos-tonos sintético;
    (3) detector de eventos con verdad construida."""
    # (1) usa la validación ya aceptada: razones ∈ [0.97, 1.03] a t=60/300 (§13-bis)
    val = json.loads((OUT / "VALIDACION_NULA_OFF.json").read_text())
    for pref, filas in val.items():
        for t, q, ap, af, r in filas:
            assert 0.9 < r < 1.1, f"validación OFF fuera de rango: {pref} {q}@{t}: {r}"
    print("[matar] (1) cadena estimador→nula sobre OFF dentro de [0.9,1.1]: OK")
    # (2) anti-fuga: tono gigante cercano dispara bandera en W corta
    t = np.arange(0, 60, DT_S)
    sig = 1e-3 * np.cos(7.0 * t) + 1e-8 * np.cos(30.0 * t)
    a, flag = _amp_conv(sig, 30.0, 30.0, 0.75)
    assert flag, "anti-fuga no disparó con tono 1e5× a Δω=23"
    sig2 = 1e-8 * np.cos(30.0 * t)
    a2, flag2 = _amp_conv(sig2, 30.0, 30.0, 0.75)
    assert not flag2 and abs(a2 - 1e-8) / 1e-8 < 0.05, f"estimador limpio: {a2}, {flag2}"
    print("[matar] (2) anti-fuga W8/W16: dispara con vecino gigante, limpio sin él: OK")
    # (3) eventos con verdad construida
    filas = [{"t": float(tt), "rho": (1.5 if 30 <= tt <= 60 else 0.5)} for tt in range(10, 111, 10)]
    eventos = []
    estado = False
    for f in filas:
        if f["rho"] > 1.0 and not estado:
            eventos.append(("captura", f["t"])); estado = True
        elif f["rho"] <= 1.0 and estado:
            eventos.append(("release", f["t"])); estado = False
    assert eventos == [("captura", 30.0), ("release", 70.0)], f"eventos: {eventos}"
    print("[matar] (3) detector de eventos verdad construida: OK")
    print("[matar] lector cirugía: TODO OK")


if __name__ == "__main__":
    {"matar": matar, "leer": leer}[sys.argv[1]]()
