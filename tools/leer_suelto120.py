"""LECTOR SELLADO del lote suelto 120 u.t. [M1, prereg §15 + declaraciones §16].

PORT del detector del juez del tap wf_cf84918d (j0_extraer.py + j3_analisis.py,
archivados en audit/DOUBLETAP_BANDAS_wf_cf84918d_scripts/) — el núcleo `analizar` es
verbatim salvo parametrización de paths y un reordenamiento inocuo (cruce_S1 se computa
antes del loop de modos); regresión 4/4 con números idénticos contra j3_resultados.json.
Las AMPLIACIONES pasaron su propio kill (wf_122a505c, BLOQUEA→arreglos 1-9 aplicados;
audit/DOUBLETAP_LECTOR_S120_*). Decisiones DECLARADAS ANTES de abrir film alguno (§16):

  · t_salida = primer t con ω_L(fórmula) ≥ techo de banda S1 ESTÁTICA del receptor
    (bandas_x_solo de j2, número de MÁQUINA: par134→33.6054, no el «33.61» de prosa;
    Δt≈0.06 u.t.). Si nunca: None ⇒ sellado no aplicable (banda no alcanzada, declarado).
  · fin operativo de ρ = t_grid[-1] = T−W/2−0.25 (~118.75 para T=120), margen STFT del
    núcleo; ψ/slips válidos hasta T−0.5 (media móvil 1 u.t.) ⇒ slips se miden a T−0.5.
  · slips: ψ_j = unwrap(angle(⟨x_j·e^{−iφ_L}⟩_{1 u.t.})). TRES conteos publicados SIEMPRE:
    neto=|Δψ|/2π, tv=Σ|dψ|/2π, disc=cruces de múltiplos de 2π de ψ−ψ(a) (robusto a
    cancelación ida-vuelta y a deriva lenta). El SELLADO (a)/(b) usa DISC (recomendación
    del juez del kill, declarada acá antes de leer); discrepancia de veredicto entre
    conteos ⇒ bandera degenerado_no_coherente (punto 3: bandera, no promedio).
  · (a) SOBREVIVE (por modo): en [t_salida+2, fin]: ρ>1 SOSTENIDO (fracción>0.9 y sin
    hueco ρ≤1 de ≥1 u.t. — implementación declarada) y slip_rate_disc<0.1/u.t. medido
    en [t_salida+2, T−0.5]. Por UNIDAD: a_sobrevive_3Q = AND sobre los modos Q («para
    los 3 Q» del sello); si algún modo es mudo/no-evaluable ⇒ None.
  · (b) RELEASE tipo par132 (por modo): corrida ρ<1 (≥2 u.t.) con SOLAPAMIENTO ≥2 u.t.
    con [t_salida, t_salida+8] (interpretación declarada de «dentro de»: solape, no
    inicio-en-ventana) y sl5_disc≥2 en alguna ventana de 5 u.t. CONTENIDA en el rango
    (a∈[t_salida, t_salida+3] paso 0.5, b=min(a+5, t_salida+8, T−0.5); ventana truncada
    ⇒ umbral absoluto 2 sobre ventana corta = conservador). Por unidad: OR sobre modos
    (regla declarada; None si ningún True y hay no-evaluables).
  · CENSURA: si t_salida no es None y fin−t_salida < 10 u.t. (margen declarado), el
    sellado publica los números pero NO afirma (a)/(b)/tercero (precedente: la CENSURA
    REAL de par132 a 60 u.t. en el veredicto del juez).
  · ni (a) ni (b) (y sin censura) ⇒ TERCER DESENLACE (se describe, no se fuerza).
  · PISO DE MUDEZ por modo (punto 8): amp_mediana(film) y amp_temprana([0,t_salida])
    ambas < 1e-4 × mediana(|x|) del modo Q más activo del mismo film ⇒ MUDO: sellado
    no evaluable, w_self no citable.
  · secundarios (d): pico S1 (RMS móvil 1 u.t., pico/mediana-mismo-film, t_pico−t_entra);
    t_cap(u) global (punto 4) Y t_recap(u) post-t_salida (§15(d), el dato nuevo), ambas
    familias, u∈{0.8,1.0,1.5}; b_Q del seguidor max Y FINAL (todas las capas de b1);
    banda dinámica punto 7: ω_techo(t)=ω_techo(0)·√(1+0.1·b_S1_receptor(t)).
  · banderas (punto 3 extendido a los outcomes nuevos): bandera_cruzada por modo
    (consolidado_desde stft vs demod, conjunto y onset ±3 u.t.), bandera_ab por modo
    (stft vs demod discrepan en a/b), bandera_orden_familias por unidad (secuencia de
    onsets de consolidación entre familias, ±3 u.t., episodios en una sola familia).
  · LIMITACIÓN DEL SELLO (medida en el kill, t5c): (a) solo, tal como está escrito, no
    distingue tono fijo cercano a ω_L final de captura real (fuga Hann W=2 + conteo).
    Un a_sobrevive=True SOLO se cita como SOBREVIVE si además t_cap(u) cierra, w_final
    está sobre la línea y no hay banderas — los secundarios son parte del veredicto.
Notas de herencia declaradas: ω_self del juez = STFT W=2 centrada en t=3 (ventana [2,4];
la prosa del veredicto dice «[1,6]»; materialidad medida ≤0.05 rad/u.t. — se porta el
CÓDIGO ejecutado). PROHIBICIONES (punto 8, los 4 ítems): sin detector restringido-a-banda;
extremos de ω_L siempre por fórmula; amplificación S1 solo pico/mediana-mismo-film;
piso de mudez por modo (implementado en este arreglo).

Subcomandos: extraer | prefijo | matar | leer  (en ese orden de protocolo; leer exige
CONTROL_PREFIJO con bit_exacto=true para las 4 unidades — §15: si difiere, se frena TODO).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
AUD = STUDY07 / "audit/DOUBLETAP_BANDAS_wf_cf84918d_scripts"
LOTE = STUDY07 / "data/lote_suelto_120/lote/unidades"
VIEJO = Path("/Volumes/ExternalDisk/study07_census_arnold/lote1/unidades")
SCRATCH = Path("/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-"
               "lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad")
NPZ_NUEVO = SCRATCH / "suelto120"
NPZ_JUEZ = SCRATCH / "juez_dtap"
OUT = STUDY07 / "data/lote_suelto_120"

STRIDE = 10
UNITS = ["par134", "par132", "par129", "par131"]
TICKS_VIEJO = 750000

MARGEN_CENSURA = 10.0     # u.t. mínimas post-salida para afirmar (a)/(b)/tercero (§16)
PISO_MUDEZ_REL = 1e-4     # × mediana(|x|) del modo Q más activo del mismo film (§16)
U_CAP = (0.8, 1.0, 1.5)

BLOCK_BY_PAR = {  # nodo0=lider, nodo1=receptor (j3, manifiestos)
    "par126": ("108114f666e3", "401ff8728f63"), "par127": ("108114f666e3", "74b23f765604"),
    "par128": ("108114f666e3", "956fba96c70c"), "par129": ("108114f666e3", "9c2256bc8e73"),
    "par130": ("108114f666e3", "b053ff4d163b"), "par131": ("108114f666e3", "e58e88925b4d"),
    "par132": ("1bc9dcccf3bd", "34b5ab50a85c"), "par133": ("1bc9dcccf3bd", "46b339f16f33"),
    "par134": ("1bc9dcccf3bd", "61b484288817"),
}

W, HOP, PAD = 2.0, 0.5, 4          # j3 verbatim


# ------------------------------ núcleo j3 (verbatim) ------------------------------

def stft_peaks(sig, dt, t_grid, lo, hi):
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


def amp_at(sig, dt, t_grid, w_centers, half):
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


# --------------------------- ampliaciones selladas §15/§16 ---------------------------

def _slips_psi(sig, phi_L, dt):
    """ψ demodulada contra φ_L, promediada 1 u.t. (misma media móvil que j3-demod)."""
    n_1ut = int(round(1.0 / dt))
    k = np.ones(n_1ut) / n_1ut
    zm = np.convolve(sig * np.exp(-1j * phi_L), k, mode="same")
    return np.unwrap(np.angle(zm))


def _ventana(psi, t, a, b):
    ia, ib = np.searchsorted(t, a), min(np.searchsorted(t, b), len(psi) - 1)
    return (psi[ia:ib + 1] if ib > ia else psi[ia:ia + 1])


def _slips3(psi, t, a, b):
    """(neto, tv, disc) en [a,b]. disc = cruces de múltiplos de 2π de ψ−ψ(a)."""
    w = _ventana(psi, t, a, b)
    if len(w) < 2:
        return 0.0, 0.0, 0
    y = (w - w[0]) / (2 * np.pi)
    neto = float(abs(y[-1]))
    tv = float(np.sum(np.abs(np.diff(y))))
    disc = int(np.sum(np.abs(np.diff(np.floor(y))) >= 1))
    return neto, tv, disc


def _sostenido(mask, t_grid, a, b, hueco_max=1.0, frac_min=0.9):
    """«ρ>1 sostenido en [a,b]»: fracción>frac_min y sin hueco ρ≤1 de ≥hueco_max u.t."""
    sel = (t_grid >= a) & (t_grid <= b)
    if not sel.any():
        return False, 0.0
    frac = float(np.mean(mask[sel]))
    huecos = runs_true(~mask[sel], t_grid[sel], hueco_max)
    return (frac > frac_min and not huecos), frac


def _t_caps(r, t_grid, inicio_min=None):
    """t_cap(u): inicio de la primera corrida ρ>u de ≥2 u.t. (global o post-inicio_min)."""
    out = {}
    for u in U_CAP:
        rr = runs_true(r > u, t_grid, 2.0)
        if inicio_min is not None:
            rr = [e for e in rr if e[0] > inicio_min]
        out[str(u)] = rr[0][0] if rr else None
    return out


def analizar(par, npz_path, ampliado=True):
    """Núcleo j3 verbatim + ampliaciones §15/§16 (campos nuevos, sin tocar los del juez)."""
    J2 = json.load(open(AUD / "j2_resultados.json"))
    f = np.load(npz_path)
    dt = float(f["dt_s"]); x0, x1 = f["x0"], f["x1"]
    b0, b1 = f["b0"], f["b1"]
    capas = [str(c) for c in f["capas1"]]
    iQ = [i for i, c in enumerate(capas) if c == "Q"]
    iS1 = [i for i, c in enumerate(capas) if c == "S1"]
    n = x0.shape[0]; T = n * dt
    t = np.arange(n) * dt
    t_grid = np.arange(W / 2 + 0.25, T - W / 2 - 0.25, HOP)
    lider_sig = x0[:, :3].sum(axis=1)
    bq0 = b0[:, 0]
    bq1_max = float(np.abs(b1).max(axis=0)[0])

    wl_spec, _ = stft_peaks(lider_sig, dt, t_grid, 2.0, 60.0)
    raiz = np.sqrt(1 + 0.1 * np.interp(t_grid, t, bq0))
    C = float(np.sum(wl_spec * raiz) / np.sum(raiz ** 2))
    resid = float(np.max(np.abs(wl_spec - C * raiz) / (C * raiz)))
    w_L = C * np.sqrt(1 + 0.1 * np.interp(t_grid, t, bq0))
    w_L_full = C * np.sqrt(1 + 0.1 * bq0)
    phi_L = np.cumsum(w_L_full) * dt
    n_1ut = int(round(1.0 / dt))

    # cruce de banda S1 (movido antes del loop de modos — inocuo, regresión lo verifica)
    bandas = J2[[k for k in J2 if k.startswith(BLOCK_BY_PAR[par][1])][0]]["bandas_x_solo"]
    lo, hi = bandas["S1"]

    def t_cruce(w_obj):
        m = w_L_full >= w_obj
        return float(t[np.argmax(m)]) if m.any() else None

    cruce = {"banda_S1": [lo, hi], "t_entra": t_cruce(lo), "t_sale": t_cruce(hi),
             "w_L_max": float(w_L_full.max()), "w_L_ini": float(w_L_full[0])}
    t_salida = cruce["t_sale"]

    res_modos = {}
    for j in iQ:
        sig = x1[:, j]
        early_grid = np.array([3.0])
        wself = float(stft_peaks(sig, dt, early_grid, 2.0, 25.0)[0][0])
        A_L = amp_at(sig, dt, t_grid, w_L, 1.0)
        A_S = amp_at(sig, dt, t_grid, np.full_like(t_grid, wself), 1.5)
        rho = A_L / np.maximum(A_S, 1e-300)
        dm = sig * np.exp(-1j * phi_L)
        ds = sig * np.exp(-1j * wself * t)
        k = np.ones(n_1ut) / n_1ut
        Am = np.abs(np.convolve(dm, k, mode="same"))
        As = np.abs(np.convolve(ds, k, mode="same"))
        rho_d = np.interp(t_grid, t, Am / np.maximum(As, 1e-300))

        def veredicto(r):
            eps = runs_true(r > 1.0, t_grid, 2.0)
            consolidado = None
            if eps and eps[-1][1] >= t_grid[-1] - 1.0:
                consolidado = eps[-1][0]
            return {"episodios_rho>1": eps, "consolidado_desde": consolidado,
                    "rho_max": float(r.max()), "rho_fin": float(r[-1])}

        w_ini = float(stft_peaks(sig, dt, np.array([3.0]), 2.0, 45.0)[0][0])
        w_fin = float(stft_peaks(sig, dt, np.array([T - 3.0]), 2.0, 45.0)[0][0])
        reg = {"w_self": round(wself, 3), "w_llegada": round(w_ini, 3),
               "w_final": round(w_fin, 3),
               "stft": veredicto(rho), "demod": veredicto(rho_d)}
        if ampliado:
            abs_sig = np.abs(sig)
            reg["amp_mediana"] = float(np.median(abs_sig))
            fin_tem = t_salida if t_salida is not None else T
            reg["amp_temprana"] = float(np.median(abs_sig[t <= fin_tem]))
            reg["t_cap_u"] = {"stft": _t_caps(rho, t_grid),
                              "demod": _t_caps(rho_d, t_grid)}
            reg["t_recap_u"] = {
                fam: (_t_caps(r, t_grid, inicio_min=t_salida)
                      if t_salida is not None else {str(u): None for u in U_CAP})
                for fam, r in (("stft", rho), ("demod", rho_d))}
            reg["_rho"] = rho; reg["_rho_d"] = rho_d
            reg["_psi"] = _slips_psi(sig, phi_L, dt)
        res_modos[f"Q{j}"] = reg

    out = {"par": par, "C_fit": round(C, 4), "resid_max": round(resid, 4),
           "bq_lider": [float(bq0[0]), float(bq0[-1])], "bq_receptor_max_Q": bq1_max,
           "cruce_S1": cruce, "modos": res_modos}
    if not ampliado:
        return out

    # ---- piso de mudez (punto 8): relativo al modo Q más activo del mismo film ----
    piso = PISO_MUDEZ_REL * max(mv["amp_mediana"] for mv in res_modos.values())
    out["piso_mudez"] = piso
    for mv in res_modos.values():
        mv["mudo"] = bool(mv["amp_mediana"] < piso and mv["amp_temprana"] < piso)

    # ---- veredictos sellados (a)/(b)/tercero, por modo Q y familia ----
    out["t_salida"] = t_salida
    fin = float(t_grid[-1])                 # fin operativo de ρ (declarado: ≈T−1.25)
    fin_ps = T - 0.5                        # ψ válida hasta acá (media móvil 1 u.t.)
    censurado = (t_salida is not None and fin - t_salida < MARGEN_CENSURA)
    out["censurado_post_salida"] = censurado
    for mk, mv in res_modos.items():
        sellado = {}
        for fam, r in (("stft", mv["_rho"]), ("demod", mv["_rho_d"])):
            if mv["mudo"]:
                sellado[fam] = {"aplicable": False, "nota": "MUDO: no evaluable",
                                "a_sobrevive": None, "b_release": None}
                continue
            v = {"aplicable": t_salida is not None}
            if t_salida is None:
                v["nota"] = "banda no alcanzada: outcome = consolidación al horizonte"
                v["a_sobrevive"] = None; v["b_release"] = None
                sellado[fam] = v
                continue
            sost, frac = _sostenido(r > 1.0, t_grid, t_salida + 2.0, fin)
            neto, tv, disc = _slips3(mv["_psi"], t, t_salida + 2.0, fin_ps)
            dur = max(fin_ps - t_salida - 2.0, 1e-9)
            rates = {"neto": neto / dur, "tv": tv / dur, "disc": disc / dur}
            v["frac_rho>1_post"] = round(frac, 3)
            v["slip_rate_post"] = {kk: round(vv, 4) for kk, vv in rates.items()}
            # (b): corridas ρ<1 con SOLAPE ≥2 u.t. con [t_salida, t_salida+8] (§16)
            rel_runs = [e for e in runs_true(r < 1.0, t_grid, 2.0)
                        if min(e[1], t_salida + 8.0) - max(e[0], t_salida) >= 2.0]
            # sl5: SOLO ventanas de 5 u.t. CONTENIDAS en el rango (arreglo 1 del kill)
            sl5 = {"neto": 0.0, "tv": 0.0, "disc": 0}
            for a in np.arange(t_salida, t_salida + 3.0 + 1e-9, 0.5):
                b_v = min(a + 5.0, t_salida + 8.0, fin_ps)
                if b_v - a < 0.5:
                    continue
                n3, t3, d3 = _slips3(mv["_psi"], t, a, b_v)
                sl5 = {"neto": max(sl5["neto"], n3), "tv": max(sl5["tv"], t3),
                       "disc": max(sl5["disc"], d3)}
            v["slips_max_5ut_ventana_salida"] = {
                "neto": round(sl5["neto"], 2), "tv": round(sl5["tv"], 2),
                "disc": sl5["disc"]}
            a_por = {kk: bool(sost and rates[kk] < 0.1) for kk in rates}
            b_por = {"neto": bool(rel_runs and sl5["neto"] >= 2.0),
                     "tv": bool(rel_runs and sl5["tv"] >= 2.0),
                     "disc": bool(rel_runs and sl5["disc"] >= 2)}
            v["degenerado_no_coherente"] = bool(
                len(set(a_por.values())) > 1 or len(set(b_por.values())) > 1
                or (tv >= 0.5 and tv / max(neto, 1e-9) > 2.0))
            if censurado:
                v["censurado"] = True
                v["a_sobrevive"] = None; v["b_release"] = None
            else:
                v["a_sobrevive"] = a_por["disc"]        # conteo SELLADO = disc (§16)
                v["b_release"] = b_por["disc"]
                if not v["a_sobrevive"] and not v["b_release"]:
                    v["tercer_desenlace"] = True
            sellado[fam] = v
        mv["sellado"] = sellado
        mv["bandera_ab"] = bool(
            sellado["stft"]["a_sobrevive"] != sellado["demod"]["a_sobrevive"]
            or sellado["stft"]["b_release"] != sellado["demod"]["b_release"])
        cs, cd = mv["stft"]["consolidado_desde"], mv["demod"]["consolidado_desde"]
        mv["bandera_cruzada"] = not (
            (cs is None) == (cd is None)
            and (cs is None or abs(cs - cd) <= 3.0))
        for k_ in ("_rho", "_rho_d", "_psi"):
            del mv[k_]

    # ---- agregación por UNIDAD (regla del sello (a): «para los 3 Q») ----
    out["sellado_unidad"] = {}
    for fam in ("stft", "demod"):
        avs = [res_modos[mk]["sellado"][fam]["a_sobrevive"] for mk in sorted(res_modos)]
        bvs = [res_modos[mk]["sellado"][fam]["b_release"] for mk in sorted(res_modos)]
        a_u = None if any(v is None for v in avs) else all(avs)
        b_u = True if any(v is True for v in bvs) else (
            None if any(v is None for v in bvs) else False)
        out["sellado_unidad"][fam] = {"a_sobrevive_3Q": a_u, "b_release_algun_Q": b_u}

    # ---- bandera de ORDEN entre familias (punto 3: conjunto y orden ±3 u.t.) ----
    sec = {}
    for fam in ("stft", "demod"):
        sec[fam] = sorted([(mk, res_modos[mk][fam]["consolidado_desde"])
                           for mk in res_modos if res_modos[mk][fam]["consolidado_desde"]
                           is not None], key=lambda p: p[1])
    out["bandera_orden_familias"] = bool(
        [p[0] for p in sec["stft"]] != [p[0] for p in sec["demod"]]
        or any(abs(a[1] - b[1]) > 3.0 for a, b in zip(sec["stft"], sec["demod"])))

    # ---- secundarios (d): pico S1, banda dinámica, multiplete, b final ----
    if iS1:
        sS1 = x1[:, iS1].sum(axis=1)
        rms = np.sqrt(np.convolve(sS1 ** 2, np.ones(n_1ut) / n_1ut, mode="same"))
        i_pk = int(np.argmax(rms))
        out["s1_receptor"] = {
            "pico_sobre_mediana": float(rms[i_pk] / max(np.median(rms), 1e-300)),
            "t_pico": float(t[i_pk]),
            "t_pico_menos_t_entra": (None if cruce["t_entra"] is None
                                     else float(t[i_pk] - cruce["t_entra"]))}
    assert b1.shape[1] >= 2, f"b1 con {b1.shape[1]} capas: se esperan Q,S1[,S2]"
    b_s1_r = b1[:, 1]
    techo_din = hi * np.sqrt(1 + 0.1 * b_s1_r)
    m_din = w_L_full >= techo_din
    out["banda_dinamica"] = {"b_S1_receptor_final": float(b_s1_r[-1]),
                             "techo_din_final": float(techo_din[-1]),
                             "t_salida_dinamica": (float(t[np.argmax(m_din)])
                                                   if m_din.any() else None)}
    out["bq_receptor_final"] = [float(abs(b1[-1, kk])) for kk in range(b1.shape[1])]
    ws = [res_modos[k]["w_final"] for k in sorted(res_modos)]
    out["multiplete_Q"] = {"w_final_por_modo": ws,
                           "split": float(max(ws) - min(ws)) if len(ws) > 1 else 0.0}
    return out


# ----------------------------------- comandos -----------------------------------

def extraer():
    from study07.instruments.api import load_run
    NPZ_NUEVO.mkdir(parents=True, exist_ok=True)
    for u in UNITS:
        dest = NPZ_NUEVO / f"s120_{u}_t_jz.npz"
        if dest.exists():
            print(u, "ya extraido", flush=True); continue
        wl = load_run(LOTE / f"s120_{u}_t_k03_tau02")
        man = wl["manifest"]
        arrays = {"dt_s": np.array(float(man["dt"]) * STRIDE)}
        for j, nd in enumerate(man["por_nodo"]):
            nm, nz, nl = nd["n_modes"], nd["n_z"], nd["n_layers"]
            est = wl["estados"][j]
            arrays[f"x{j}"] = est[::STRIDE, :nm].astype(np.float64)
            arrays[f"b{j}"] = est[::STRIDE, 2 * nm + nz: 2 * nm + nz + nl].astype(np.float64)
            arrays[f"capas{j}"] = np.array(nd["capas_por_modo"])
        np.savez_compressed(dest, **arrays)
        print(u, "ok", wl["worldline_hash"][:12], len(wl["ticks"]), "ticks", flush=True)
        del wl


def prefijo():
    """Control (i) §15: prefijo de 750k ticks BIT-EXACTO vs film archivado de tanda 1.
    Chunks completos por sha de archivo; chunk de borde por igualdad de arrays, con
    `borde` = largo REAL del chunk viejo (incluye la fila de cierre del tick 750000)."""
    import hashlib
    res = {}
    for u in UNITS:
        d_new = LOTE / f"s120_{u}_t_k03_tau02/worldline"
        d_old = VIEJO / f"{u}_t_k03_tau02/worldline"
        chunk_ticks = 65536
        n_full = TICKS_VIEJO // chunk_ticks
        ok = True
        for c in range(n_full):
            nom = f"chunk_{c:05d}.npz"
            sa = hashlib.sha256((d_new / nom).read_bytes()).hexdigest()
            sb = hashlib.sha256((d_old / nom).read_bytes()).hexdigest()
            if sa != sb:
                ok = False
                print(f"[prefijo] {u} {nom}: SHA DIFIERE — SE FRENA TODO", flush=True)
        fa = np.load(d_new / f"chunk_{n_full:05d}.npz")
        fb = np.load(d_old / f"chunk_{n_full:05d}.npz")
        borde = len(fb["ticks"])            # largo real del chunk viejo
        m_por_key = {}
        for key in fb.files:
            if key == "rng_state_json":     # estado al FIN del chunk: ticks distintos
                continue
            a, b = fa[key], fb[key]
            if len(a) < borde:
                ok = False
                print(f"[prefijo] {u} borde {key}: chunk nuevo más corto que el viejo",
                      flush=True)
                continue
            m_por_key[key] = int(min(len(b), borde))
            if not np.array_equal(a[:m_por_key[key]], b[:m_por_key[key]]):
                ok = False
                print(f"[prefijo] {u} chunk borde {key}: ARRAYS DIFIEREN", flush=True)
        res[u] = {"chunks_sha_identicos": n_full, "ticks_borde_verificados": int(borde),
                  "filas_comparadas_por_key": m_por_key, "bit_exacto": ok}
        print(f"[prefijo] {u}: {'BIT-EXACTO' if ok else 'FALLA'} "
              f"({n_full} chunks + {borde} filas de borde)", flush=True)
    (OUT / "CONTROL_PREFIJO.json").write_text(json.dumps(res, indent=1))
    if not all(r["bit_exacto"] for r in res.values()):
        raise SystemExit("[prefijo] FALLA DE DETERMINISMO — no se lee nada (§15)")


def matar():
    """Regresión: núcleo portado vs j3_resultados.json en los 4 films YA VISTOS de
    tanda 1 (declarados §7; mismo dato + mismo detector ⇒ números IDÉNTICOS)."""
    ref = json.load(open(AUD / "j3_resultados.json"))
    fallas = []
    for u in UNITS:
        mio = analizar(u, NPZ_JUEZ / f"{u}_t_jz.npz", ampliado=False)
        suyo = ref[f"{u}_t"]
        for k in ("C_fit", "resid_max"):
            if abs(mio[k] - suyo[k]) > 1e-9:
                fallas.append(f"{u}.{k}: {mio[k]} vs {suyo[k]}")
        for ck in ("t_entra", "t_sale", "w_L_max"):
            a, b = mio["cruce_S1"][ck], suyo["cruce_S1"][ck]
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9):
                fallas.append(f"{u}.cruce.{ck}: {a} vs {b}")
        for mk, mv in mio["modos"].items():
            sv = suyo["modos"][mk]
            for k in ("w_self", "w_llegada", "w_final"):
                if abs(mv[k] - sv[k]) > 1e-9:
                    fallas.append(f"{u}.{mk}.{k}: {mv[k]} vs {sv[k]}")
            for fam in ("stft", "demod"):
                a, b = mv[fam]["consolidado_desde"], sv[fam]["consolidado_desde"]
                if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9):
                    fallas.append(f"{u}.{mk}.{fam}.cons: {a} vs {b}")
                if abs(mv[fam]["rho_max"] - sv[fam]["rho_max"]) > 1e-6:
                    fallas.append(f"{u}.{mk}.{fam}.rho_max")
                if [tuple(e) for e in mv[fam]["episodios_rho>1"]] != \
                   [tuple(e) for e in sv[fam]["episodios_rho>1"]]:
                    fallas.append(f"{u}.{mk}.{fam}.episodios")
        print(f"[matar] {u}: {'OK' if not any(f.startswith(u) for f in fallas) else 'FALLA'}",
              flush=True)
    if fallas:
        print("\n".join(fallas))
        raise SystemExit(f"[matar] {len(fallas)} discrepancias — el port NO es fiel")
    print("[matar] regresión 4/4: port fiel al juez (números idénticos)")


def leer():
    ctl_p = OUT / "CONTROL_PREFIJO.json"
    if not ctl_p.exists():
        raise SystemExit("[leer] falta CONTROL_PREFIJO (orden §15: prefijo antes de leer)")
    ctl = json.loads(ctl_p.read_text())
    if not (set(UNITS) <= set(ctl) and all(ctl[u]["bit_exacto"] for u in UNITS)):
        raise SystemExit("[leer] CONTROL_PREFIJO con falla — §15: se frena TODO")
    git = subprocess.run(["git", "-C", str(STUDY07), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    res = {"_meta": {"lector_git": git,
                     "umbrales_declarados": {
                         "conteo_sellado_slips": "disc",
                         "piso_mudez_rel": PISO_MUDEZ_REL,
                         "margen_censura_ut": MARGEN_CENSURA,
                         "slips_hasta": "T-0.5",
                         "sl5": "ventanas de 5 u.t. contenidas en [t_salida, t_salida+8]",
                         "rel_runs": "solape >= 2 u.t. con la ventana"}}}
    for u in UNITS:
        r = analizar(u, NPZ_NUEVO / f"s120_{u}_t_jz.npz", ampliado=True)
        res[u] = r
        c = r["cruce_S1"]
        print(f"\n== s120_{u} == C={r['C_fit']} resid={r['resid_max']} "
              f"bqL {r['bq_lider'][0]:.2f}->{r['bq_lider'][1]:.2f} "
              f"| banda {c['banda_S1']} t_entra={c['t_entra']} t_sale={c['t_sale']} "
              f"wLmax={c['w_L_max']:.2f} | censurado={r['censurado_post_salida']}",
              flush=True)
        print(f"  UNIDAD: {r['sellado_unidad']} | orden_familias="
              f"{r['bandera_orden_familias']} | bq_final={r['bq_receptor_final']}")
        for mk, mv in sorted(r["modos"].items()):
            s = mv["sellado"]["stft"]
            print(f"  {mk} self={mv['w_self']} fin={mv['w_final']} mudo={mv['mudo']} "
                  f"| cons stft={mv['stft']['consolidado_desde']} "
                  f"demod={mv['demod']['consolidado_desde']} "
                  f"| a={s.get('a_sobrevive')} b={s.get('b_release')} "
                  f"3er={s.get('tercer_desenlace', False)} "
                  f"| recap={mv['t_recap_u']['stft']} "
                  f"| flags ab={mv['bandera_ab']} cz={mv['bandera_cruzada']} "
                  f"dg={s.get('degenerado_no_coherente')}")
    (OUT / "LECTURA.json").write_text(json.dumps(res, indent=1, default=str))
    print("\n[leer] → data/lote_suelto_120/LECTURA.json")


if __name__ == "__main__":
    {"extraer": extraer, "prefijo": prefijo, "matar": matar, "leer": leer}[sys.argv[1]]()
