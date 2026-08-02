"""LECTOR v2 del film largo 600 u.t. [M1, prereg 2026-08-02 §3 + §3-bis; prescripciones
del tap wf_cfb44e2e; kill wf_12d753fc BLOQUEA→7 arreglos obligatorios APLICADOS].

Núcleo espectral IMPORTADO de leer_suelto120 (port del juez, regresión 4/4). Sello v2:
  · CANAL CITABLE = episodio de dominancia en AMBAS familias (presc. 1-2, arreglo 4):
    episodios_citables(u) = corridas de (ρ_stft>u ∧ ρ_demod>u) ≥2 u.t.; las listas por
    familia quedan como diagnóstico; bandera_familias si conjunto/onset difieren (±3 u.t.).
  · LÍNEA MEDIDA con guardia (arreglo 3): búsqueda con PRIOR de banda fórmula±2 (la
    fórmula está sellada para extremos — usarla de prior no viola presc. 5) + bandera de
    continuidad: salto>1 rad/u.t. por paso o resid>0.05 ⇒ bandera_linea y NO-CITABLE lo
    posterior al primer salto. Medido en s120: los 4 films limpios (salto max 0.137).
  · COBERTURA por unidad sobre citables (u=1.0): fraccion_del_film Y
    fraccion_desde_primer_canal (ambos denominadores explícitos), huecos vs h_max=8
    (incluido el TERMINAL), relevos con solape>0 en ambas familias citado como RANGO
    sobre u∈{0.8,1.0,1.5}, releases v2 (fin de episodio ≥2 u.t. preexistente).
  · P1 (arreglos 1-2-7): elegibilidad por SOLAPE (una ventana se excluye solo si un
    episodio la solapa; las post-release SÍ son elegibles, etiquetadas), hovering PREVIO
    (corrida ρ≥0.95 de ≥2 u.t. en el tramo desde el fin del último episodio —o inicio—
    hasta el fin de la ventana ⇒ excluido; se publica rho_max_pre), AMBAS familias con
    bandera si el veredicto difiere, y PERFIL MÓVIL 10 u.t. publicado (min/max/mediana +
    mitades + bandera_perfil si difieren >2×) — presc. 4 textual.
  · P4 (arreglo 6): pico sobre serie SUAVIZADA 5 u.t. (declarado; el suavizado baja el
    pico ~0.9% y corre picos asimétricos ~+2 u.t.), con SOPORTE del máximo (ε=1e-3):
    si el soporte cruza el borde de [230,340] ⇒ OTRO «meseta/borde» (nunca decidido por
    polvo numérico). veredicto_sellado SOLO para par132; par134 = réplica de FORMA
    (~0.007 @ ~347±2); par129/131 descriptivos. Films <550 u.t. ⇒ no_aplicable_film_corto.
  · GUARDIAS de largo (arreglo 5): extraer exige COMPLETE + n_ticks del manifiesto;
    picos reales en t<5 o t>T−5 son invisibles por diseño (bordes del suavizado).
Umbrales declarados (§3 + §3-bis, TODOS en _meta): u_cap {0.8,1.0,1.5}; h_max=8;
drive_estac 0.005 sostenido ≥30; hover 0.95 (corrida ≥2 u.t.); piso mudez 1e-4 rel
(mediana global AND temprana, como v1); tol sobre_linea 0.5 rad/u.t. (§3-bis); salto
línea 1.0 rad/u.t.; resid línea 0.05; P4 [230,340]/[0.22,0.37]/0.9×pico/T−10/ε=1e-3;
P1 bandas 0.7-1.3 (σ es EL número) / ≥1.5 (co-ordena), veredicto sobre familia stft con
bandera de familia, dirección publicada.

Subcomandos: extraer | prefijo | matar | leer  (orden §3; custodia 60→120→600).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
sys.path.insert(0, str(STUDY07 / "tools"))
from leer_suelto120 import (AUD, BLOCK_BY_PAR, HOP, PAD, PISO_MUDEZ_REL, W,  # noqa: E402
                            amp_at, runs_true, stft_peaks)

LOTE = STUDY07 / "data/film_largo_600/lote/unidades"
S120 = STUDY07 / "data/lote_suelto_120/lote/unidades"
SCRATCH = Path("/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-"
               "lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad")
NPZ_600 = SCRATCH / "largo600"
NPZ_120 = SCRATCH / "suelto120"
OUT = STUDY07 / "data/film_largo_600"

STRIDE = 10
UNITS = ["par134", "par132", "par129", "par131"]
TICKS_120 = 1500000
TICKS_600 = 7500000
U_CAP = (0.8, 1.0, 1.5)
H_MAX = 8.0
DRIVE_ESTAC = 0.005
LARGO_ESTAC = 30.0
HOVER = 0.95
TOL_LINEA = 0.5          # |w_final − línea| para sobre_linea (§3-bis)
SALTO_LINEA = 1.0        # rad/u.t. por paso ⇒ bandera_linea (§3-bis)
RESID_LINEA = 0.05       # resid_max del fit ⇒ bandera_linea (§3-bis)
P4_T = (230.0, 340.0)
P4_V = (0.22, 0.37)
P4_EPS = 1e-3
T_MIN_P4 = 550.0

UMBRALES = {"u_cap": list(U_CAP), "h_max": H_MAX, "drive_estac": DRIVE_ESTAC,
            "largo_estac": LARGO_ESTAC, "hover": HOVER, "hover_min_corrida": 2.0,
            "piso_mudez_rel": PISO_MUDEZ_REL, "tol_sobre_linea": TOL_LINEA,
            "salto_linea": SALTO_LINEA, "resid_linea": RESID_LINEA,
            "p4_t": list(P4_T), "p4_v": list(P4_V), "p4_ratio_fin": 0.9,
            "p4_eps_soporte": P4_EPS, "p4_suavizado_ut": 5.0, "p4_t_min": T_MIN_P4,
            "p1_bandas": [0.7, 1.3, 1.5], "p1_familia_veredicto": "stft",
            "rms_drive_ut": 2.0, "perfil_movil_ut": 10.0, "min_dur_episodio": 2.0,
            "margen_release": 1.0, "linea_prior_banda": 2.0}


# ------------------------- utilitarios (testeables en matar) -------------------------

def _fusionar(intervalos):
    if not intervalos:
        return []
    xs = sorted(intervalos)
    out = [list(xs[0])]
    for a, b in xs[1:]:
        if a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(x) for x in out]


def _perfil_pendiente(tg, y, ancho=10.0):
    ly = np.log(np.maximum(y, 1e-300))
    out = np.full_like(tg, np.nan)
    for i, tc in enumerate(tg):
        m = (tg >= tc - ancho / 2) & (tg <= tc + ancho / 2)
        if m.sum() >= 5:
            out[i] = np.polyfit(tg[m], ly[m], 1)[0]
    return out


def _relevos(eps_por_modo):
    """Relevos entre episodios de modos DISTINTOS con solape>0, excluyendo anidados.
    Letra chica declarada: contacto-en-un-punto (solape==0) NO publica; co-dominancia
    larga cuenta (sello: solape>0); empate exacto de fines no publica."""
    out = []
    for mk_a, eps_a in eps_por_modo.items():
        for mk_b, eps_b in eps_por_modo.items():
            if mk_a >= mk_b:
                continue
            for ea in eps_a:
                for eb in eps_b:
                    sol = min(ea[1], eb[1]) - max(ea[0], eb[0])
                    if sol <= 0:
                        continue
                    if ea[1] == eb[1]:               # empate exacto: no hay saliente
                        continue
                    anidado = (ea[0] >= eb[0] and ea[1] <= eb[1]) or \
                              (eb[0] >= ea[0] and eb[1] <= ea[1])
                    if anidado:
                        continue
                    saliente = mk_a if ea[1] < eb[1] else mk_b
                    entrante = mk_b if saliente == mk_a else mk_a
                    out.append({"sale": saliente, "entra": entrante,
                                "solape": round(sol, 2),
                                "t": round(max(ea[0], eb[0]), 2)})
    return out


def _casos_p1(t_grid, series_fam, F, eps_union, ventanas, sigma):
    """P1 §3 con arreglos 1-2-7: elegibilidad por SOLAPE, hovering PREVIO, ambas
    familias, perfil móvil. series_fam = {'stft': rho, 'demod': rho_d}."""
    casos = []
    rho_v = series_fam["stft"]
    for (a, b) in ventanas:
        if any(e[0] < b and e[1] > a for e in eps_union):
            continue                          # episodio SOLAPA la ventana (entera)
        previos = [e[1] for e in eps_union if e[1] <= a]
        t0_tramo = max(previos) if previos else float(t_grid[0])
        tramo = (t_grid >= t0_tramo) & (t_grid <= b)
        hover_runs = runs_true(rho_v[tramo] >= HOVER, t_grid[tramo], 2.0)
        rho_max_pre = float(rho_v[tramo].max()) if tramo.any() else 0.0
        if hover_runs:
            continue                          # hovering previo sostenido: excluido
        etiqueta = "post_release" if previos else "pre_primera_captura"
        sel = (t_grid >= a) & (t_grid <= b)
        lF = float(np.polyfit(t_grid[sel], np.log(np.maximum(F[sel], 1e-300)), 1)[0])
        caso = {"ventana": [round(a, 1), round(b, 1)], "etiqueta": etiqueta,
                "rho_max_pre_captura": round(rho_max_pre, 3),
                "dlnF": round(lF, 5), "familias": {}}
        for fam, r in series_fam.items():
            lr = float(np.polyfit(t_grid[sel], np.log(np.maximum(r[sel], 1e-300)), 1)[0])
            corr = lr - lF
            razon = abs(corr) / max(abs(sigma), 1e-9)
            pend = _perfil_pendiente(t_grid[sel], r[sel])
            pend = pend[~np.isnan(pend)]
            mid = 0.5 * (a + b)
            m1 = float(np.polyfit(t_grid[sel & (t_grid <= mid)],
                                  np.log(np.maximum(r[sel & (t_grid <= mid)], 1e-300)),
                                  1)[0])
            m2 = float(np.polyfit(t_grid[sel & (t_grid > mid)],
                                  np.log(np.maximum(r[sel & (t_grid > mid)], 1e-300)),
                                  1)[0])
            caso["familias"][fam] = {
                "dlnrho": round(lr, 5), "tasa_corr": round(corr, 5),
                "direccion": ("+" if corr > 0 else "-"),
                "razon_vs_sigma": round(razon, 4),
                "veredicto": ("sigma_es_EL_numero" if 0.7 <= razon <= 1.3
                              else ("co-ordena" if razon >= 1.5 else "zona_gris")),
                "perfil10": {"min": round(float(pend.min()), 5) if len(pend) else None,
                             "max": round(float(pend.max()), 5) if len(pend) else None,
                             "mediana": (round(float(np.median(pend)), 5)
                                         if len(pend) else None)},
                "mitades": [round(m1, 5), round(m2, 5)],
                "bandera_perfil": bool(abs(m1 - m2) >
                                       2.0 * max(min(abs(m1), abs(m2)), 1e-5))}
        vs = {fam: c["veredicto"] for fam, c in caso["familias"].items()}
        caso["veredicto_sellado"] = caso["familias"]["stft"]["veredicto"]
        caso["bandera_familia_p1"] = bool(len(set(vs.values())) > 1)
        casos.append(caso)
    return casos


def _p4(bs1, t, dt, T, par):
    """P4 §3 con arreglo 6: soporte del máximo, guardia de largo, veredicto por par.
    Números sobre la serie SUAVIZADA 5 u.t. (declarado)."""
    assert len(bs1) == len(t), f"_p4: b_S1 ({len(bs1)}) y t ({len(t)}) de largos distintos"
    n5 = int(round(5.0 / dt))
    bs = np.convolve(bs1, np.ones(n5) / n5, mode="same")
    lo_r, hi_r = n5, len(bs) - n5
    i_pk = int(np.argmax(bs[lo_r:hi_r])) + lo_r
    t_pk, v_pk = float(t[i_pk]), float(bs[i_pk])
    b_fin = float(bs[hi_r - 1])
    mask = np.zeros(len(bs), dtype=bool)
    mask[lo_r:hi_r] = bs[lo_r:hi_r] >= v_pk * (1.0 - P4_EPS)
    t_sop = [float(t[mask].min()), float(t[mask].max())] if mask.any() else [t_pk, t_pk]
    base = {"t_pico": round(t_pk, 1), "pico": round(v_pk, 4),
            "soporte_maximo": [round(t_sop[0], 1), round(t_sop[1], 1)],
            "b_fin": round(b_fin, 4),
            "ratio_fin_pico": round(b_fin / max(v_pk, 1e-12), 3),
            "b_en_grilla": {str(tt): round(float(bs1[min(int(tt / dt), len(bs1) - 1)]), 4)
                            for tt in (60, 120, 200, 281, 340, 400, 500, 600) if tt <= T},
            "nota": "pico/soporte/b_fin sobre serie SUAVIZADA 5 u.t. (pico −~0.9%, "
                    "corrimiento asimétrico ~+2 u.t.; picos en t<5 o t>T−5 invisibles); "
                    "b_en_grilla sobre serie CRUDA (corrección §5: el suavizado 'same' "
                    "reducía a la mitad el punto de borde t=600 por zero-padding)"}
    if T < T_MIN_P4:
        base["veredicto"] = "no_aplicable_film_corto"
        base["bandera_film_corto"] = True
        return base
    monotono = bool(t_sop[1] >= T - 10.0)
    dentro = bool(P4_T[0] <= t_sop[0] and t_sop[1] <= P4_T[1])
    fuera = bool(t_sop[1] < P4_T[0] or t_sop[0] > P4_T[1])
    if par == "par132":
        if monotono:
            base["veredicto"] = "MUERE"
        elif dentro and P4_V[0] <= v_pk <= P4_V[1] and b_fin < 0.9 * v_pk:
            base["veredicto"] = "SOSTIENE"
        elif not dentro and not fuera:
            base["veredicto"] = "OTRO (meseta/borde de criterio)"
        else:
            base["veredicto"] = "OTRO"
    elif par == "par134":
        base["forma"] = {"tiene_maximo_local": not monotono,
                         "decae": bool(b_fin < 0.9 * v_pk),
                         "esperado": "~0.007 @ ~347±2 (réplica de FORMA, no de valor)"}
        base["veredicto"] = None
    else:
        base["veredicto"] = None              # descriptivo (líder débil)
    return base


def _stft_prior(sig, dt, t_grid, w_prior, half):
    """Pico STFT con PRIOR de banda por ventana: [w_prior−half, w_prior+half]."""
    out = np.empty_like(t_grid)
    for i, (tc, wp) in enumerate(zip(t_grid, w_prior)):
        out[i] = stft_peaks(sig, dt, np.array([tc]), max(wp - half, 1.0), wp + half)[0][0]
    return out


def analizar_v2(par, npz_path):
    J2 = json.load(open(AUD / "j2_resultados.json"))
    f = np.load(npz_path)
    dt = float(f["dt_s"]); x0, x1 = f["x0"], f["x1"]
    b0, b1 = f["b0"], f["b1"]
    capas = [str(c) for c in f["capas1"]]
    iQ = [i for i, c in enumerate(capas) if c == "Q"]
    n = x0.shape[0]; T = n * dt
    t = np.arange(n) * dt
    t_grid = np.arange(W / 2 + 0.25, T - W / 2 - 0.25, HOP)
    lider_sig = x0[:, :3].sum(axis=1)
    bq0 = b0[:, 0]

    # línea MEDIDA con prior fórmula±2 (arreglo 3 complemento) + guardia de continuidad
    raiz_g = np.sqrt(1 + 0.1 * np.interp(t_grid, t, bq0))
    wl_libre, _ = stft_peaks(lider_sig, dt, t_grid, 2.0, 60.0)
    C0 = float(np.sum(wl_libre * raiz_g) / np.sum(raiz_g ** 2))
    wl_med = _stft_prior(lider_sig, dt, t_grid, C0 * raiz_g, UMBRALES["linea_prior_banda"])
    C = float(np.sum(wl_med * raiz_g) / np.sum(raiz_g ** 2))
    resid = float(np.max(np.abs(wl_med - C * raiz_g) / (C * raiz_g)))
    saltos = np.abs(np.diff(wl_med)) / HOP
    bandera_linea = bool(saltos.max() > SALTO_LINEA or resid > RESID_LINEA)
    t_primer_salto = (float(t_grid[int(np.argmax(saltos > SALTO_LINEA))])
                      if (saltos > SALTO_LINEA).any() else None)
    w_L_form_full = C * np.sqrt(1 + 0.1 * bq0)
    wl_med_full = np.interp(t, t_grid, wl_med)
    phi_L_med = np.cumsum(wl_med_full) * dt
    n_1ut = int(round(1.0 / dt))

    n_2ut = int(round(2.0 / dt))
    F_full = np.sqrt(np.convolve(lider_sig ** 2, np.ones(n_2ut) / n_2ut, mode="same"))
    F = np.interp(t_grid, t, F_full)
    dlnF = _perfil_pendiente(t_grid, F)
    ventanas_estac = runs_true(np.nan_to_num(np.abs(dlnF) < DRIVE_ESTAC, nan=False),
                               t_grid, LARGO_ESTAC)

    bkey = [k for k in J2 if k.startswith(BLOCK_BY_PAR[par][1])][0]
    lo, hi = J2[bkey]["bandas_x_solo"]["S1"]
    sigma_rec = float(J2[bkey]["sigma_analitico"])

    def t_cruce(w_obj):
        m = w_L_form_full >= w_obj
        return float(t[np.argmax(m)]) if m.any() else None

    cruce = {"banda_S1": [lo, hi], "t_entra": t_cruce(lo), "t_sale": t_cruce(hi),
             "w_L_form_max": float(w_L_form_full.max()),
             "w_L_med_max": float(wl_med.max())}

    # ---- por modo: ρ ambas familias, episodios por familia + CITABLES (arreglo 4) ----
    modos, series = {}, {}
    fin = float(t_grid[-1])
    for j in iQ:
        sig = x1[:, j]
        wself = float(stft_peaks(sig, dt, np.array([3.0]), 2.0, 25.0)[0][0])
        A_L = amp_at(sig, dt, t_grid, wl_med, 1.0)
        A_S = amp_at(sig, dt, t_grid, np.full_like(t_grid, wself), 1.5)
        rho = A_L / np.maximum(A_S, 1e-300)
        dm = sig * np.exp(-1j * phi_L_med)
        ds = sig * np.exp(-1j * wself * t)
        k = np.ones(n_1ut) / n_1ut
        Am = np.abs(np.convolve(dm, k, mode="same"))
        As = np.abs(np.convolve(ds, k, mode="same"))
        rho_d = np.interp(t_grid, t, Am / np.maximum(As, 1e-300))
        w_fin = float(stft_peaks(sig, dt, np.array([T - 3.0]), 2.0, 60.0)[0][0])
        abs_sig = np.abs(sig)
        reg = {"w_self": round(wself, 3), "w_final": round(w_fin, 3),
               "w_linea_med_final": round(float(wl_med[-1]), 3),
               "sobre_linea": bool(abs(w_fin - wl_med[-1]) < TOL_LINEA),
               "amp_mediana": float(np.median(abs_sig)),
               "amp_temprana": float(np.median(abs_sig[t <= min(60.0, T)]))}
        for fam, r in (("stft", rho), ("demod", rho_d)):
            reg[fam] = {f"eps_u{u}": runs_true(r > u, t_grid, 2.0) for u in U_CAP}
            reg[fam]["rho_max"] = float(r.max())
            reg[fam]["rho_fin"] = float(r[-1])
        reg["citable"] = {f"eps_u{u}": runs_true((rho > u) & (rho_d > u), t_grid, 2.0)
                          for u in U_CAP}
        e_s, e_d = reg["stft"]["eps_u1.0"], reg["demod"]["eps_u1.0"]
        reg["bandera_familias"] = bool(
            len(e_s) != len(e_d)
            or any(abs(a[0] - b[0]) > 3.0 for a, b in zip(e_s, e_d)))
        series[f"Q{j}"] = {"stft": rho, "demod": rho_d, "A_L": A_L, "A_S": A_S}
        modos[f"Q{j}"] = reg

    piso = PISO_MUDEZ_REL * max(mv["amp_mediana"] for mv in modos.values())
    for mv in modos.values():
        mv["mudo"] = bool(mv["amp_mediana"] < piso and mv["amp_temprana"] < piso)

    # ---- cobertura por unidad sobre CITABLES (arreglos 4 + recomendados) ----
    eps_cit = {mk: mv["citable"]["eps_u1.0"] for mk, mv in modos.items()
               if not mv["mudo"]}
    cob = _fusionar([e for eps in eps_cit.values() for e in eps])
    t0 = cob[0][0] if cob else None
    frac_film = (sum(b - a for a, b in cob) / (fin - float(t_grid[0]))) if cob else 0.0
    frac_canal = ((sum(b - a for a, b in cob) / (fin - t0))
                  if cob and fin > t0 else 0.0)
    huecos = [{"de": b1_, "a": a2, "largo": round(a2 - b1_, 2),
               "admisible_h8": bool(a2 - b1_ <= H_MAX)}
              for (a1, b1_), (a2, _) in zip(cob, cob[1:])]
    if cob and cob[-1][1] < fin - 1.0:
        huecos.append({"de": cob[-1][1], "a": fin, "largo": round(fin - cob[-1][1], 2),
                       "admisible_h8": False, "terminal": True})
    relevos = _relevos(eps_cit)
    for rv in relevos:                        # rango de solape sobre u (arreglo 4)
        rango = {}
        for u in U_CAP:
            cand = _relevos({mk: mv["citable"][f"eps_u{u}"]
                             for mk, mv in modos.items() if not mv["mudo"]})
            match = [c["solape"] for c in cand
                     if c["sale"] == rv["sale"] and c["entra"] == rv["entra"]
                     and abs(c["t"] - rv["t"]) < 10.0]
            rango[str(u)] = max(match) if match else None
        rv["solape_rango_u"] = rango
    releases = [{"modo": mk, "t_release": round(b, 2), "episodio_desde": round(a, 2)}
                for mk, eps in eps_cit.items() for a, b in eps if b < fin - 1.0]
    cobertura = {"episodios_citables_por_modo": eps_cit, "cobertura": cob,
                 "primer_canal": t0, "fraccion_del_film": round(frac_film, 4),
                 "fraccion_desde_primer_canal": round(frac_canal, 4),
                 "huecos": huecos, "relevos": relevos, "releases_v2": releases,
                 "diagnostico_por_familia": {
                     fam: {mk: mv[fam]["eps_u1.0"] for mk, mv in modos.items()}
                     for fam in ("stft", "demod")}}

    # ---- P1 (arreglos 1-2-7) ----
    p1 = {"ventanas_estacionarias": ventanas_estac, "sigma_receptor": sigma_rec,
          "casos": []}
    for mk, mv in modos.items():
        if mv["mudo"]:
            continue
        eps_union = _fusionar(mv["stft"]["eps_u1.0"] + mv["demod"]["eps_u1.0"])
        casos = _casos_p1(t_grid, {"stft": series[mk]["stft"],
                                   "demod": series[mk]["demod"]},
                          F, eps_union, ventanas_estac, sigma_rec)
        for c in casos:
            c["modo"] = mk
        p1["casos"].extend(casos)

    # ---- P4 ----
    assert b1.shape[1] >= 2, f"b1 con {b1.shape[1]} capas"
    p4 = _p4(b1[:, 1].astype(np.float64), t, dt, T, par)

    return {"par": par, "T": round(T, 1), "C_fit": round(C, 4),
            "resid_max": round(resid, 4),
            "linea": {"bandera_linea": bandera_linea, "salto_max": round(float(saltos.max()), 3),
                      "t_primer_salto": t_primer_salto,
                      "no_citable_desde": t_primer_salto if bandera_linea else None},
            "bq_lider": [float(bq0[0]), float(bq0[-1])],
            "bq_receptor_max": [float(np.abs(b1).max(axis=0)[k])
                                for k in range(b1.shape[1])],
            "bq_receptor_final": [float(abs(b1[-1, k])) for k in range(b1.shape[1])],
            "cruce_S1": cruce, "piso_mudez": piso, "modos": modos,
            "cobertura": cobertura, "p1_tasas": p1, "p4_biografia": p4}


# ----------------------------------- comandos -----------------------------------

def extraer():
    from study07.instruments.api import load_run
    NPZ_600.mkdir(parents=True, exist_ok=True)
    for u in UNITS:
        dest = NPZ_600 / f"s600_{u}_t_jz.npz"
        if dest.exists():
            print(u, "ya extraido", flush=True); continue
        rd = LOTE / f"s600_{u}_t_k03_tau02"
        if not (rd / "COMPLETE").exists():
            raise SystemExit(f"[extraer] {u}: sin COMPLETE — no se extrae (arreglo 5)")
        wl = load_run(rd)
        man = wl["manifest"]
        n_ticks = len(wl["ticks"])
        if abs(n_ticks - (TICKS_600 + 1)) > 1:
            raise SystemExit(f"[extraer] {u}: {n_ticks} ticks ≠ {TICKS_600}+1 (arreglo 5)")
        arrays = {"dt_s": np.array(float(man["dt"]) * STRIDE)}
        for j, nd in enumerate(man["por_nodo"]):
            nm, nz, nl = nd["n_modes"], nd["n_z"], nd["n_layers"]
            est = wl["estados"][j]
            arrays[f"x{j}"] = est[::STRIDE, :nm].astype(np.float64)
            arrays[f"b{j}"] = est[::STRIDE, 2 * nm + nz: 2 * nm + nz + nl].astype(np.float64)
            arrays[f"capas{j}"] = np.array(nd["capas_por_modo"])
        np.savez_compressed(dest, **arrays)
        print(u, "ok", wl["worldline_hash"][:12], n_ticks, "ticks", flush=True)
        del wl


def prefijo():
    """Custodia 60→120→600: prefijo de 1.5M ticks BIT-EXACTO vs films s120."""
    import hashlib
    res = {}
    for u in UNITS:
        d_new = LOTE / f"s600_{u}_t_k03_tau02/worldline"
        d_old = S120 / f"s120_{u}_t_k03_tau02/worldline"
        chunk_ticks = 65536
        n_full = TICKS_120 // chunk_ticks
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
        borde = len(fb["ticks"])
        m_por_key = {}
        for key in fb.files:
            if key == "rng_state_json":
                continue
            a, b = fa[key], fb[key]
            if len(a) < borde:
                ok = False
                print(f"[prefijo] {u} borde {key}: chunk nuevo más corto", flush=True)
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
        raise SystemExit("[prefijo] FALLA DE DETERMINISMO — no se lee nada (§3)")


def matar():
    """Kill local post-arreglos: (1) regresión de hechos vs LECTURA.json (v1, familia
    stft diagnóstica) en npz s120; (2) trampas sintéticas de los arreglos del kill
    wf_12d753fc (P1 elegibilidad/hovering-previo, P4 soporte/meseta/film-corto,
    relevos, familias, línea)."""
    fallas = []
    v1 = json.load(open(STUDY07 / "data/lote_suelto_120/LECTURA.json"))
    for u in UNITS:
        r2 = analizar_v2(u, NPZ_120 / f"s120_{u}_t_jz.npz")
        if r2["p4_biografia"].get("veredicto") not in (None, "no_aplicable_film_corto"):
            fallas.append(f"{u}: p4 en film de 120 debería ser no_aplicable")
        for mk, mv1 in v1[u]["modos"].items():
            eps1 = mv1["stft"]["episodios_rho>1"]
            eps2 = r2["modos"][mk]["stft"]["eps_u1.0"]
            if len(eps1) != len(eps2):
                fallas.append(f"{u}.{mk}: n_eps {len(eps1)} vs {len(eps2)}")
                continue
            for (a1, b1_), (a2, b2_) in zip(eps1, eps2):
                if abs(a1 - a2) > 1.5 or abs(b1_ - b2_) > 1.5:
                    fallas.append(f"{u}.{mk}: eps [{a1},{b1_}] vs [{a2:.2f},{b2_:.2f}]")
        print(f"[matar] {u}: regresión hechos "
              f"{'OK' if not any(x.startswith(u) for x in fallas) else 'FALLA'}",
              flush=True)

    # --- trampas P1 (arreglos 1-2: la trampa que el kill exigió) ---
    tg = np.arange(1.25, 600.0, 0.5)
    rho = np.full_like(tg, 0.3)
    rho[(tg >= 10) & (tg <= 40)] = 1.2        # episodio temprano
    fam = {"stft": rho, "demod": rho}
    F = np.full_like(tg, 1.0)
    eps_u = _fusionar([(10.0, 40.0)])
    casos = _casos_p1(tg, fam, F, eps_u, [(70.0, 110.0), (200.0, 400.0)], -0.01)
    assert len(casos) == 2 and all(c["etiqueta"] == "post_release" for c in casos), \
        f"P1 post-release: {len(casos)} casos"
    casos = _casos_p1(tg, fam, F, eps_u, [(30.0, 70.0)], -0.01)
    assert len(casos) == 0, "P1: ventana solapada con episodio debió excluirse"
    rho_h = np.full_like(tg, 0.3)
    rho_h[(tg >= 10) & (tg <= 40)] = 0.96     # hovering previo, sin episodio
    casos = _casos_p1(tg, {"stft": rho_h, "demod": rho_h}, F, [], [(50.0, 90.0)], -0.01)
    assert len(casos) == 0, "P1: hovering previo sostenido debió excluir"
    casos = _casos_p1(tg, {"stft": np.full_like(tg, 0.3),
                           "demod": np.full_like(tg, 0.3)}, F, [], [(50.0, 90.0)], -0.01)
    assert len(casos) == 1 and casos[0]["etiqueta"] == "pre_primera_captura"
    # tasa construida exacta: rho=e^{0.015 t}, F cte ⇒ tasa_corr=0.015, razón exacta
    rho_c = np.exp(0.015 * tg) * 1e-6
    casos = _casos_p1(tg, {"stft": rho_c, "demod": rho_c}, F, [], [(50.0, 90.0)], -0.015)
    c0 = casos[0]["familias"]["stft"]
    assert abs(c0["tasa_corr"] - 0.015) < 1e-4 and abs(c0["razon_vs_sigma"] - 1.0) < 0.01
    assert casos[0]["veredicto_sellado"] == "sigma_es_EL_numero"
    print("[matar] trampas P1 (elegibilidad/hovering/etiquetas/tasa exacta): OK",
          flush=True)

    # --- trampas P4 (arreglo 6) ---
    dt_s = 0.008
    ts = np.arange(0, 600, dt_s)
    p = _p4(0.3 * np.exp(-((ts - 280.0) / 30.0) ** 2), ts, dt_s, 600.0, "par132")
    assert p["veredicto"] == "SOSTIENE", f"pico limpio: {p['veredicto']}"
    p = _p4(0.3 * (ts / 600.0) ** 2, ts, dt_s, 600.0, "par132")
    assert p["veredicto"] == "MUERE", f"monótono: {p['veredicto']}"
    meseta = np.where((ts >= 320) & (ts <= 370), 0.3, 0.3 * np.exp(-np.abs(ts - 345) / 60))
    p = _p4(meseta, ts, dt_s, 600.0, "par132")
    assert "meseta" in str(p["veredicto"]), f"meseta cruza 340: {p['veredicto']}"
    p = _p4(0.3 * (ts[:15000] / 600.0) ** 2, ts[:15000], dt_s, 120.0, "par132")
    assert p["veredicto"] == "no_aplicable_film_corto", "film corto sin guardia"
    p = _p4(0.007 * np.exp(-((ts - 347.0) / 40.0) ** 2), ts, dt_s, 600.0, "par134")
    assert p["veredicto"] is None and p["forma"]["tiene_maximo_local"] and p["forma"]["decae"]
    print("[matar] trampas P4 (pico/monótono/meseta-borde/film-corto/forma-134): OK",
          flush=True)

    # --- trampas relevos/cobertura/familias ---
    rv = _relevos({"A": [(10.0, 50.0)], "B": [(45.0, 120.0)]})
    assert len(rv) == 1 and rv[0]["sale"] == "A" and abs(rv[0]["solape"] - 5.0) < 1e-9
    assert _relevos({"A": [(10.0, 100.0)], "B": [(40.0, 60.0)]}) == [], "anidado no es relevo"
    assert _relevos({"A": [(10.0, 50.0), (60.0, 90.0)]}) == [], "mismo modo no es relevo"
    rv = _relevos({"A": [(10.0, 50.0)], "B": [(45.0, 120.0)], "C": [(115.0, 200.0)]})
    assert len(rv) == 2, "cadena A→B→C"
    assert _relevos({"A": [(10.0, 50.0)], "B": [(50.0, 90.0)]}) == [], "contacto no publica"
    # familias: citable = intersección
    r1 = np.where((tg >= 10) & (tg <= 50), 1.2, 0.3)
    r2_ = np.where((tg >= 45) & (tg <= 120), 1.2, 0.3)
    cit = runs_true((r1 > 1.0) & (r2_ > 1.0), tg, 2.0)
    assert len(cit) == 1 and abs(cit[0][0] - 45.25) < 0.6 and abs(cit[0][1] - 49.75) < 0.6
    print("[matar] trampas relevos/contacto/anidado/cadena/intersección familias: OK",
          flush=True)
    if fallas:
        print("\n".join(fallas))
        raise SystemExit(f"[matar] {len(fallas)} discrepancias")
    print("[matar] lector v2 post-arreglos: TODO OK")


def leer():
    ctl_p = OUT / "CONTROL_PREFIJO.json"
    if not ctl_p.exists():
        raise SystemExit("[leer] falta CONTROL_PREFIJO (orden §3)")
    ctl = json.loads(ctl_p.read_text())
    if not (set(UNITS) <= set(ctl) and all(ctl[u]["bit_exacto"] for u in UNITS)):
        raise SystemExit("[leer] CONTROL_PREFIJO con falla — §3: se frena TODO")
    git = subprocess.run(["git", "-C", str(STUDY07), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    res = {"_meta": {"lector_git": git,
                     "sello": "v2 (tap wf_cfb44e2e + kill wf_12d753fc aplicado + §3/§3-bis)",
                     "umbrales": UMBRALES}}
    for u in UNITS:
        r = analizar_v2(u, NPZ_600 / f"s600_{u}_t_jz.npz")
        res[u] = r
        c = r["cruce_S1"]
        print(f"\n== s600_{u} == C={r['C_fit']} resid={r['resid_max']} "
              f"linea_ok={not r['linea']['bandera_linea']} "
              f"bqL {r['bq_lider'][0]:.1f}->{r['bq_lider'][1]:.1f} | banda {c['banda_S1']} "
              f"entra={c['t_entra']} sale={c['t_sale']} wLmax={c['w_L_med_max']:.2f}",
              flush=True)
        p4 = r["p4_biografia"]
        print(f"  P4: pico={p4['pico']} @t={p4['t_pico']} sop={p4['soporte_maximo']} "
              f"fin={p4['b_fin']} -> {p4.get('veredicto')} "
              f"{p4.get('forma', '')}")
        cb = r["cobertura"]
        print(f"  cobertura(citable): film={cb['fraccion_del_film']} "
              f"canal={cb['fraccion_desde_primer_canal']} desde={cb['primer_canal']} | "
              f"huecos={len(cb['huecos'])} relevos={len(cb['relevos'])} "
              f"releases={len(cb['releases_v2'])}")
        for mk, mv in sorted(r["modos"].items()):
            print(f"  {mk} self={mv['w_self']} fin={mv['w_final']} "
                  f"sobre={mv['sobre_linea']} flags fam={mv['bandera_familias']} "
                  f"cit1.0={[(round(a,1),round(b,1)) for a,b in mv['citable']['eps_u1.0']]}")
        for caso in r["p1_tasas"]["casos"]:
            s = caso["familias"]["stft"]
            print(f"  P1 {caso['modo']} {caso['ventana']} [{caso['etiqueta']}]: "
                  f"corr={s['tasa_corr']} razon={s['razon_vs_sigma']} "
                  f"-> {caso['veredicto_sellado']} "
                  f"(flags perfil={s['bandera_perfil']} fam={caso['bandera_familia_p1']})")
    (OUT / "LECTURA_v2.json").write_text(json.dumps(res, indent=1, default=str))
    print("\n[leer] → data/film_largo_600/LECTURA_v2.json")


if __name__ == "__main__":
    {"extraer": extraer, "prefijo": prefijo, "matar": matar, "leer": leer}[sys.argv[1]]()
