"""ANÁLISIS POOLED del census Arnold A∪B [M1 — SELLADO post-tap wf_27523659 (BLOQUEA →
15 arreglos aplicados; audit/DOUBLETAP_POOLED_*)].

Sellos: prereg §1 + adenda §3 + DISENO_OLA_B C1-C9 + semántica §5/§7/§8. JERARQUÍA
CITABLE fijada por el juez (declaraciones §10):
  PRIMARIO: (a) LENGUA = P(primer lock ≤ 60) por bin×brazo (EXACTO en todas las filas:
    t_lock es primer lock; None a 120 ⇒ ninguno a 60 — sin supuesto de persistencia;
    coincide con KM@60) + 1−S(120) por KM censurado donde haya filas a 120; W4; IC
    bootstrap dos vías n_boot=2000. (b) tasa firme ESTRATIFICADA por horizonte propio
    (la MIXTA no se publica como citable). (c) contraste t−f = Δ ponderado por bootstrap
    dos vías (peso del par = cnt[bi]·cnt[bj]), SIN self, por región y horizonte.
    (d) pulling no-firmes en (piso, 0.275): 1 − dw_tardia/dw_temprana (MEDIDO/MEDIDO,
    letra del prereg §1), por brazo y horizonte. (e) monotonía: tendencia (cov de firme60
    con log dw) con PERMUTACIÓN POR NODO (w_fina permutada sobre node-ids, dw'
    recomputado por par; calibra al 5% — la naive llegaba a 49% FP y queda RETIRADA).
  ROBUSTEZ: réplica W8 de TODO; sensibilidad sin-vistazo (24 pares = 15 del estrato
    [0,0.1]-grilla presentes en t1 + 9 tap-abiertos), bin a bin a horizonte común;
    sensibilidad de binning dw±σ_dw (dos corridas extremas; regla pre-declarada: si el
    orden de la lengua no sobrevive, fusionar bins <0.05); interacción tanda×dw citable
    en [0.30,2.0) (ambas a 60) y en [0.05,0.30) SOLO sobre lock60; reponderada a las
    11175 duplas DEL ZOOLÓGICO (cobertura declarada ~94.4%; ≥50 = 5.2% no muestreado →
    ola C) sobre lock60, con IC.
  DESCRIPTIVO: McNemar exacto (regla de poder: discordantes<5 ⇒ sin_poder, p no
    citable); self-pairs; κ/τ (n=25); t_lock mediana condicionada (sesgo declarado);
    censura real = «nunca lockeó a su horizonte» (release observado = EVENTO, no
    censura); distribuciones rw_final/rw_max crudas + umbral re-medido candidato
    (outcome ii; advertencia de circularidad).
  Todo IC publica n_nodos, frac de resamples descartados y bandera de citabilidad
  (n_nodos≥5 y ancho>0); n_eff = Kish (Σm)²/Σm² por análisis. σ_dw por bin (mediana/
  máx); bins con ancho < 2·σ_med = «no resolubles internamente». Bins con n=0 se
  emiten explícitos. _meta con git/sha de insumos/semilla/parámetros (regla §48).
  ESTANDARIZACIÓN DURA pre-registrada (opcional, ANTES de mirar outcomes): re-lectura
  de los 74 films de 120 truncados a 750k — no corrida en esta versión (lock60 exacto
  la vuelve innecesaria para el primario).
Subcomandos: matar (trampas sintéticas) | correr (UNA corrida citable).
"""
import hashlib
import json
import subprocess
import sys
from math import comb, log
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
OUT = STUDY07 / "data/census_arnold"

SEED = 20260802
N_BOOT = 2000
N_PERM = 2000
PISO_EJE = 0.02
PULL_MAX = 0.275
BINS_LENGUA = [("self", None), ("<piso", (0.0, PISO_EJE)), ("0.02-0.05", (PISO_EJE, 0.05)),
               ("0.05-0.15", (0.05, 0.15)), ("0.15-0.30", (0.15, 0.30)),
               ("0.30-0.60", (0.30, 0.60)), ("0.60-1.0", (0.60, 1.0)),
               ("1.0-2.0", (1.0, 2.0)), ("2.0-3.5", (2.0, 3.5)), ("3.5-5.1", (3.5, 5.1)),
               ("5.1-10", (5.1, 10.0)), ("10-50", (10.0, 50.0))]
SOPORTE_COMUN = (0.05, 2.0)
BIN_GRUESO = [("<0.275", (0.0, PULL_MAX)), ("0.275-1", (PULL_MAX, 1.0)),
              ("1-10", (1.0, 10.0)), (">=10", (10.0, 1e9))]


# ------------------------------- carga y básicos -------------------------------

def cargar():
    t1 = json.load(open(OUT / "tabla_tanda1.json"))
    t2 = json.load(open(OUT / "tabla_tanda2.json"))
    filas = []
    for f in t1:
        filas.append({"tanda": 1, "brazo": f["brazo"], "celda": "k03_tau02",
                      "dw": f["dw_fina"], "sdw": None, "self": False,
                      "par": f"t1_{f['par_idx']}", "par_idx": f["par_idx"],
                      "bi": f["block_i"], "bj": f["block_j"],
                      "hor": round(f["ticks"] * 8e-5), "W4": f["W4"], "W8": f["W8"]})
    for f in t2:
        filas.append({"tanda": 2, "brazo": f["brazo"], "celda": f["celda"],
                      "dw": 0.0 if f["self_par"] else f["dw_fina_prereg"],
                      "sdw": f.get("sigma_dw_prereg"), "self": f["self_par"],
                      "par": f"t2_{f['par_idx']}", "par_idx": f["par_idx"],
                      "bi": f["block_i"], "bj": f["block_j"],
                      "hor": round(f["ticks"] * 8e-5), "W4": f["W4"], "W8": f["W8"]})
    return filas


def firme(f, W):
    return 1 if f[W]["estado"] == 2 else 0


def lock60(f, W):
    """P(primer lock ≤ 60) por fila — EXACTO para horizontes 60 y 120 (ver docstring)."""
    tl = f[W]["t_lock_ut"]
    return 1 if (tl is not None and tl <= 60.0) else 0


def bin_de(f, dw=None):
    if f["self"]:
        return "self"
    d = f["dw"] if dw is None else dw
    for nombre, rango in BINS_LENGUA[1:]:
        if rango[0] <= d < rango[1]:
            return nombre
    return None


def km_1mS(eventos, t_q, pesos=None):
    """1−S(t_q) Kaplan-Meier. eventos=[(t, es_evento)]; censura al horizonte propio."""
    if not eventos:
        return None
    if pesos is None:
        pesos = [1.0] * len(eventos)
    porT = {}
    for (t, ev), p in zip(eventos, pesos):
        d, c = porT.get(t, (0.0, 0.0))
        porT[t] = (d + p, c) if ev else (d, c + p)
    S, riesgo = 1.0, float(sum(pesos))
    for t in sorted(porT):
        if t > t_q:
            break
        d, c = porT[t]
        if riesgo > 0 and d > 0:
            S *= 1.0 - d / riesgo
        riesgo -= d + c
    return 1.0 - S


def eventos_de(filas, W):
    return [((f[W]["t_lock_ut"], True) if f[W]["t_lock_ut"] is not None
             else (float(f["hor"]), False)) for f in filas]


def kish(filas):
    m = {}
    for f in filas:
        m[f["bi"]] = m.get(f["bi"], 0) + 1
        m[f["bj"]] = m.get(f["bj"], 0) + 1
    v = np.array(list(m.values()), float)
    return {"n_nodos": len(v), "kish": round(float(v.sum() ** 2 / (v ** 2).sum()), 1)}


def boot_ic(filas, stat_fn, rng, n_boot=N_BOOT):
    """Bootstrap dos vías por nodos (D4): resampleo iid de nodos, peso fila = producto
    de multiplicidades. Publica citabilidad (arreglo 6)."""
    nodos = sorted({f["bi"] for f in filas} | {f["bj"] for f in filas})
    idx = {n: k for k, n in enumerate(nodos)}
    vals, desc = [], 0
    for _ in range(n_boot):
        cnt = np.bincount(rng.integers(0, len(nodos), len(nodos)), minlength=len(nodos))
        pesos = [float(cnt[idx[f["bi"]]] * cnt[idx[f["bj"]]]) for f in filas]
        v = stat_fn(filas, pesos)
        if v is None:
            desc += 1
        else:
            vals.append(v)
    if not vals:
        return {"ic95": [None, None], "n_nodos": len(nodos), "frac_desc": 1.0,
                "citable": False}
    lo, hi = float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))
    return {"ic95": [round(lo, 4), round(hi, 4)], "n_nodos": len(nodos),
            "frac_desc": round(desc / n_boot, 3),
            "citable": bool(len(nodos) >= 5 and hi - lo > 0)}


def tasa_w(filas, pesos, fn):
    den = sum(pesos)
    if den <= 0:
        return None
    return sum(p * fn(f) for f, p in zip(filas, pesos)) / den


def mcnemar(pares_tf, fn):
    b01 = sum(1 for t, f in pares_tf if fn(t) == 1 and fn(f) == 0)
    b10 = sum(1 for t, f in pares_tf if fn(t) == 0 and fn(f) == 1)
    n = b01 + b10
    reg = {"b01": b01, "b10": b10, "discordantes": n}
    if n < 5:
        reg["poder"] = "sin_poder"; reg["p"] = None
    else:
        k = min(b01, b10)
        reg["p"] = round(min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n), 6)
        reg["poder"] = "ok"
    return reg


def mediana_pond(valores, pesos):
    if not valores or sum(pesos) <= 0:
        return None
    o = np.argsort(valores)
    v = np.array(valores)[o]; w = np.array(pesos, float)[o]
    cum = np.cumsum(w) / w.sum()
    return float(v[np.searchsorted(cum, 0.5)])


# ------------------------------- secciones -------------------------------

def lengua(ppal, rng):
    res = {}
    for W in ("W4", "W8"):
        res[W] = {}
        for brazo in ("t", "f"):
            sel = [f for f in ppal if f["brazo"] == brazo]
            tabla = []
            for nombre, _ in BINS_LENGUA:
                fb = [f for f in sel if bin_de(f) == nombre]
                fila = {"bin": nombre, "n": len(fb)}
                if fb:
                    fila["horizontes"] = {str(h): sum(1 for f in fb if f["hor"] == h)
                                          for h in sorted({f["hor"] for f in fb})}
                    fila["lock60"] = round(float(np.mean([lock60(f, W) for f in fb])), 3)
                    fila["ic_lock60"] = boot_ic(
                        fb, lambda ff, pp, W=W: tasa_w(ff, pp, lambda g: lock60(g, W)),
                        rng)
                    f120 = [f for f in fb if f["hor"] == 120]
                    if f120:
                        fila["locK120_km"] = round(
                            km_1mS(eventos_de(fb, W), 120.0), 3)
                        fila["n_120"] = len(f120)
                    for h in (60, 120):
                        fh = [f for f in fb if f["hor"] == h]
                        if fh:
                            fila[f"firme@{h}"] = round(
                                float(np.mean([firme(f, W) for f in fh])), 3)
                    tl = [f[W]["t_lock_ut"] for f in fb
                          if firme(f, W) and f[W]["t_lock_ut"] is not None]
                    fila["n_firme_sin_tlock"] = sum(
                        1 for f in fb if firme(f, W) and f[W]["t_lock_ut"] is None)
                    fila["t_lock_med_condicionada_DESC"] = (
                        round(float(np.median(tl)), 1) if tl else None)
                    fila["censura_real"] = round(float(np.mean(
                        [1 if f[W]["t_lock_ut"] is None else 0 for f in fb])), 3)
                    sd = [f["sdw"] for f in fb if f["sdw"] is not None]
                    if sd:
                        fila["sigma_dw"] = {"mediana": round(float(np.median(sd)), 4),
                                            "max": round(float(np.max(sd)), 3)}
                fila["kish"] = kish(fb) if fb else None
                tabla.append(fila)
            res[W][brazo] = tabla
    return res


def monotonia(ppal, ws_nodo, rng):
    res = {}
    for W in ("W4", "W8"):
        res[W] = {}
        for brazo in ("t", "f"):
            sel = [f for f in ppal if f["brazo"] == brazo and not f["self"]
                   and f["dw"] > PISO_EJE]
            y = np.array([lock60(f, W) for f in sel], float)
            x = np.array([log(f["dw"]) for f in sel])
            T_obs = float(np.mean(x * y) - x.mean() * y.mean())
            nodos = sorted({f["bi"] for f in sel} | {f["bj"] for f in sel})
            wvals = np.array([ws_nodo[n] for n in nodos])
            idx = {n: k for k, n in enumerate(nodos)}
            cont = 0
            for _ in range(N_PERM):
                wp = rng.permutation(wvals)
                xp = np.array([log(max(abs(wp[idx[f["bi"]]] - wp[idx[f["bj"]]]),
                                       PISO_EJE)) for f in sel])
                Tp = float(np.mean(xp * y) - xp.mean() * y.mean())
                cont += abs(Tp) >= abs(T_obs)
            res[W][brazo] = {"T_cov_logdw_lock60": round(T_obs, 5),
                             "p_perm_por_nodo": round(cont / N_PERM, 4),
                             "n": len(sel), "kish": kish(sel)}
    return res


def contraste(ppal, rng):
    por_par = {}
    for f in ppal:
        if not f["self"]:
            por_par.setdefault(f["par"], {})[f["brazo"]] = f
    pares = [(d["t"], d["f"]) for d in por_par.values() if "t" in d and "f" in d]
    res = {"n_pares_sin_self": len(pares)}
    for W in ("W4", "W8"):
        reg = {}
        filas_par = [{"bi": t["bi"], "bj": t["bj"], "t": t, "f": f} for t, f in pares]

        def delta_fn(ff, pp, fn):
            den = sum(pp)
            return (sum(p * (fn(x["t"]) - fn(x["f"])) for x, p in zip(ff, pp)) / den
                    if den > 0 else None)

        reg["delta_lock60"] = round(float(np.mean(
            [lock60(t, W) - lock60(f, W) for t, f in pares])), 4)
        reg["ic_delta_lock60"] = boot_ic(
            filas_par, lambda ff, pp, W=W: delta_fn(ff, pp, lambda g: lock60(g, W)), rng)
        reg["mcnemar_lock60_DESC"] = mcnemar(pares, lambda g: lock60(g, W))
        for et, (a, b) in BIN_GRUESO:
            sub = [(t, f) for t, f in pares if a <= t["dw"] < b]
            if not sub:
                reg[f"region_{et}"] = {"n": 0}
                continue
            hs = sorted({t["hor"] for t, _ in sub})
            r = {"n": len(sub), "horizontes": {str(h): sum(1 for t, _ in sub
                                                           if t["hor"] == h)
                                               for h in hs},
                 "lock60_t": round(float(np.mean([lock60(t, W) for t, _ in sub])), 3),
                 "lock60_f": round(float(np.mean([lock60(f, W) for _, f in sub])), 3),
                 "mcnemar_DESC": mcnemar(sub, lambda g: lock60(g, W))}
            for h in hs:
                sh = [(t, f) for t, f in sub if t["hor"] == h]
                r[f"firme@{h}_t"] = round(float(np.mean([firme(t, W)
                                                         for t, _ in sh])), 3)
                r[f"firme@{h}_f"] = round(float(np.mean([firme(f, W)
                                                         for _, f in sh])), 3)
                r[f"delta_rw@{h}"] = round(float(np.median(
                    [t[W]["rw_final"] - f[W]["rw_final"] for t, f in sh])), 4)
            reg[f"region_{et}"] = r
        res[W] = reg
    return res


def pulling(ppal, rng):
    res = {"definicion": "1 - dw_tardia/dw_temprana (MEDIDO/MEDIDO, prereg §1); "
                         "control: denominador eje prereg"}
    for W in ("W4", "W8"):
        res[W] = {}
        for brazo in ("t", "f"):
            sel0 = [f for f in ppal if f["brazo"] == brazo and not f["self"]
                    and PISO_EJE < f["dw"] < PULL_MAX]
            for h in sorted({f["hor"] for f in sel0}):
                sel = [f for f in sel0 if f["hor"] == h]
                nf = [f for f in sel if not firme(f, W)
                      and f[W]["dw_temprana"] > PISO_EJE + (f["sdw"] or 0.0)]
                pulls = [1 - f[W]["dw_tardia"] / f[W]["dw_temprana"] for f in nf]
                med = mediana_pond(pulls, [1.0] * len(pulls))
                ic = boot_ic(nf, lambda ff, pp, W=W: mediana_pond(
                    [1 - g[W]["dw_tardia"] / g[W]["dw_temprana"] for g in ff], pp),
                    rng, n_boot=N_BOOT)
                ctrl = [1 - f[W]["dw_tardia"] / f["dw"] for f in nf]
                res[W][f"{brazo}@{h}"] = {
                    "n_no_firmes": len(nf),
                    "n_firmes_trivial": sum(1 for f in sel if firme(f, W)),
                    "pull_mediana": None if med is None else round(med, 3),
                    "ic": ic,
                    "frac_pull_neg": (round(float(np.mean([p < 0 for p in pulls])), 3)
                                      if pulls else None),
                    "pull_neg_mediana": (round(float(np.median(
                        [p for p in pulls if p < 0])), 3)
                        if any(p < 0 for p in pulls) else None),
                    "control_denom_prereg_med": (round(float(np.median(ctrl)), 3)
                                                 if ctrl else None)}
    return res


def interaccion(ppal, rng):
    res = {"nota": "citable en [0.30,2.0) (ambas tandas a 60); en [0.05,0.30) SOLO "
                   "lock60 (t1@60 vs t2@120: tanda≡horizonte para 'firme')"}
    for W in ("W4", "W8"):
        celdas = []
        for nombre, rango in BINS_LENGUA:
            if rango is None or rango[1] <= SOPORTE_COMUN[0] \
                    or rango[0] >= SOPORTE_COMUN[1]:
                continue
            grupos = {}
            for tanda in (1, 2):
                grupos[tanda] = [f for f in ppal if f["tanda"] == tanda
                                 and f["brazo"] == "t" and not f["self"]
                                 and rango[0] <= f["dw"] < rango[1]]
            fila = {"bin": nombre,
                    "n_t1": len(grupos[1]), "n_t2": len(grupos[2])}
            if grupos[1] and grupos[2]:
                l1 = float(np.mean([lock60(f, W) for f in grupos[1]]))
                l2 = float(np.mean([lock60(f, W) for f in grupos[2]]))
                fila["lock60_t1"], fila["lock60_t2"] = round(l1, 3), round(l2, 3)
                fila["delta_lock60"] = round(l2 - l1, 3)
                todas = grupos[1] + grupos[2]

                def delta_glob(ff, pp, W=W):
                    a = tasa_w([x for x in ff if x["tanda"] == 1],
                               [p for x, p in zip(ff, pp) if x["tanda"] == 1],
                               lambda g: lock60(g, W))
                    b = tasa_w([x for x in ff if x["tanda"] == 2],
                               [p for x, p in zip(ff, pp) if x["tanda"] == 2],
                               lambda g: lock60(g, W))
                    return None if (a is None or b is None) else b - a
                fila["ic_delta"] = boot_ic(todas, delta_glob, rng, n_boot=N_BOOT)
                fila["citable_firme"] = bool(rango[0] >= 0.30)
            celdas.append(fila)
        res[W] = celdas
    return res


def sensibilidad(ppal, rng):
    sel1 = json.load(open(OUT / "seleccion.json"))
    bin1 = {frozenset((a, b)) for a, b, _ in sel1["seleccion"][0]["pares"]}
    excl_pares = {f["par"] for f in ppal if f["tanda"] == 1
                  and (frozenset((f["bi"], f["bj"])) in bin1
                       or 126 <= f["par_idx"] <= 134)}
    keep = [f for f in ppal if f["par"] not in excl_pares]
    res = {"pares_excluidos": len(excl_pares),
           "filas_excluidas": len(ppal) - len(keep),
           "nota": "superset declarado: estrato [0,0.1]-grilla presente en t1 + "
                   "tap-abiertos 126-134; comparación bin a bin sobre lock60"}
    for W in ("W4", "W8"):
        tabla = []
        for nombre, _ in BINS_LENGUA:
            fb = [f for f in keep if f["brazo"] == "t" and bin_de(f) == nombre]
            fb_full = [f for f in ppal if f["brazo"] == "t" and bin_de(f) == nombre]
            fila = {"bin": nombre, "n_sin_vistazo": len(fb), "n_total": len(fb_full)}
            if fb:
                fila["lock60_sin_vistazo"] = round(
                    float(np.mean([lock60(f, W) for f in fb])), 3)
                fila["horizontes"] = {str(h): sum(1 for f in fb if f["hor"] == h)
                                      for h in sorted({f["hor"] for f in fb})}
            if fb_full:
                fila["lock60_total"] = round(
                    float(np.mean([lock60(f, W) for f in fb_full])), 3)
            tabla.append(fila)
        res[W] = tabla
    return res


def binning_sdw(ppal):
    res = {}
    for W in ("W4",):
        for signo, et in ((1, "+sdw"), (-1, "-sdw")):
            tabla = []
            for nombre, _ in BINS_LENGUA[1:]:
                fb = [f for f in ppal if f["brazo"] == "t" and not f["self"]
                      and bin_de(f, dw=max(f["dw"] + signo * (f["sdw"] or 0.0), 0.0))
                      == nombre]
                if fb:
                    tabla.append({"bin": nombre, "n": len(fb),
                                  "lock60": round(float(np.mean(
                                      [lock60(f, W) for f in fb])), 3)})
            res[et] = tabla
    return res


def reponderada(ppal, rng):
    car = json.load(open(OUT / "carriers_fina.json"))
    ws = {b: car[b]["w_fina"] for b in car}
    bids = sorted(ws)
    pob = np.array([abs(ws[bids[i]] - ws[bids[j]])
                    for i in range(len(bids)) for j in range(i + 1, len(bids))])
    shares = {n: float(np.mean((pob >= r[0]) & (pob < r[1])))
              for n, r in BINS_LENGUA[1:]}
    res = {"n_poblacion": len(pob),
           "estimando": "tasa lock60 reponderada a las duplas del zoológico de 150 "
                        "genomas, subpoblación cubierta",
           "cobertura": {"bins_muestreables": round(sum(
               shares[n] for n, _ in BINS_LENGUA[1:]
               if any(bin_de(f) == n for f in ppal if not f["self"])), 4),
               "sin_muestra": {n: round(shares[n], 4) for n, _ in BINS_LENGUA[1:]
                               if not any(bin_de(f) == n for f in ppal
                                          if not f["self"])},
               ">=50_no_muestreado": round(float(np.mean(pob >= 50.0)), 4)}}
    for W in ("W4", "W8"):
        for brazo in ("t", "f"):
            sel = [f for f in ppal if f["brazo"] == brazo and not f["self"]]

            def rep(ff, pp, W=W):
                num = den = 0.0
                nsel = sum(pp)
                if nsel <= 0:
                    return None
                for nombre, _ in BINS_LENGUA[1:]:
                    fb = [(f, p) for f, p in zip(ff, pp) if bin_de(f) == nombre]
                    wtot = sum(p for _, p in fb)
                    if wtot <= 0 or shares[nombre] <= 0:
                        continue
                    w = shares[nombre] / (wtot / nsel)
                    num += w * sum(p * lock60(f, W) for f, p in fb)
                    den += w * wtot
                return num / den if den > 0 else None
            val = rep(sel, [1.0] * len(sel))
            res[f"{W}_{brazo}"] = {"lock60_rep": None if val is None else round(val, 4),
                                   "ic": boot_ic(sel, rep, rng, n_boot=N_BOOT)}
    return res


def umbrales(ppal):
    res = {"advertencia": "re-medición outcome ii prereg §1; rw crudos (no estado); "
                          "candidato = valle del histograma — CIRCULARIDAD declarada "
                          "si se re-usa sobre estos mismos datos"}
    for W in ("W4", "W8"):
        res[W] = {}
        for brazo in ("t", "f"):
            for h in (60, 120):
                sel = [f for f in ppal if f["brazo"] == brazo and f["hor"] == h]
                if not sel:
                    continue
                for campo in ("rw_final", "rw_max"):
                    v = np.array([f[W][campo] for f in sel])
                    hist, edges = np.histogram(v, bins=20, range=(0, 1))
                    imax = int(np.argmax(hist))
                    valle = None
                    if imax < 18:
                        sub = hist[imax + 1:]
                        if sub.max() > 0:
                            i2 = imax + 1 + int(np.argmax(sub))
                            if i2 - imax > 1:
                                iv = imax + 1 + int(np.argmin(hist[imax + 1:i2]))
                                valle = round(float(edges[iv]), 3)
                    res[W][f"{brazo}@{h}_{campo}"] = {
                        "deciles": [round(float(q), 3) for q in
                                    np.percentile(v, range(0, 101, 10))],
                        "umbral_candidato_valle": valle}
    return res


# ------------------------------- comandos -------------------------------

def correr():
    rng = np.random.default_rng(SEED)
    filas = cargar()
    ppal = [f for f in filas if f["celda"] == "k03_tau02"]
    car = json.load(open(OUT / "carriers_fina.json"))
    ws_nodo = {b: car[b]["w_fina"] for b in car}
    git = subprocess.run(["git", "-C", str(STUDY07), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    shas = {p: hashlib.sha256((OUT / p).read_bytes()).hexdigest()[:16]
            for p in ("tabla_tanda1.json", "tabla_tanda2.json", "seleccion.json",
                      "seleccion_olaB.json", "carriers_fina.json")}
    res = {"_meta": {"script": "census_pooled.py post-tap wf_27523659", "git": git,
                     "sha_insumos": shas, "seed": SEED, "n_boot": N_BOOT,
                     "n_perm": N_PERM, "piso_eje": PISO_EJE, "pull_max": PULL_MAX,
                     "soporte_comun": SOPORTE_COMUN,
                     "bins": [b[0] for b in BINS_LENGUA],
                     "jerarquia": "PRIMARIO lock60/estratificada/Δboot/pulling/"
                                  "tendencia-por-nodo; ROBUSTEZ W8/sensibilidad/"
                                  "±sdw/interacción/reponderada; DESCRIPTIVO "
                                  "mcnemar/self/ktau/umbrales"},
           "n": {"total": len(filas), "celda_ppal": len(ppal),
                 "kish_global": kish(ppal)}}
    print("[pooled] A lengua…", flush=True)
    res["A_lengua"] = lengua(ppal, rng)
    print("[pooled] A2 monotonía (perm por nodo)…", flush=True)
    res["A2_monotonia"] = monotonia(ppal, ws_nodo, rng)
    print("[pooled] B pulling…", flush=True)
    res["B_pulling"] = pulling(ppal, rng)
    print("[pooled] C contraste…", flush=True)
    res["C_contraste_tf"] = contraste(ppal, rng)
    print("[pooled] D interacción…", flush=True)
    res["D_interaccion"] = interaccion(ppal, rng)
    selfs = [f for f in ppal if f["self"]]
    res["E_self_DESC"] = {W: {b: {"n": len([f for f in selfs if f["brazo"] == b]),
                                  "lock60": sum(lock60(f, W) for f in selfs
                                                if f["brazo"] == b),
                                  "firmes@120": sum(firme(f, W) for f in selfs
                                                    if f["brazo"] == b)}
                              for b in ("t", "f")} for W in ("W4", "W8")}
    ktau = [f for f in filas if f["celda"] == "k03_tau005"]
    pares_kt = []
    for f in ktau:
        g = [x for x in ppal if x["par"] == f["par"] and x["brazo"] == "t"]
        if g:
            pares_kt.append((f, g[0]))
    res["F_ktau_DESC"] = {W: {"n": len(pares_kt),
                              "lock60_tau005": sum(lock60(f, W) for f, _ in pares_kt),
                              "lock60_tau02": sum(lock60(g, W) for _, g in pares_kt),
                              "mcnemar": mcnemar(pares_kt, lambda x, W=W: lock60(x, W))}
                          for W in ("W4", "W8")}
    print("[pooled] G sensibilidad…", flush=True)
    res["G_sensibilidad"] = sensibilidad(ppal, rng)
    res["G2_binning_sdw"] = binning_sdw(ppal)
    print("[pooled] H reponderada…", flush=True)
    res["H_reponderada"] = reponderada(ppal, rng)
    res["I_umbrales_DESC"] = umbrales(ppal)
    (OUT / "POOLED.json").write_text(json.dumps(res, indent=1))
    # resumen compacto
    for W in ("W4",):
        print(f"\n== LENGUA {W} (lock60, brazo t) ==")
        for fila in res["A_lengua"][W]["t"]:
            if fila["n"]:
                print(f"  {fila['bin']:>10}: n={fila['n']:3d} lock60={fila['lock60']} "
                      f"ic={fila['ic_lock60']['ic95']} "
                      f"cit={fila['ic_lock60']['citable']}")
        print(f"  monotonía t: {res['A2_monotonia'][W]['t']}")
        print(f"  Δ lock60 t−f: {res['C_contraste_tf'][W]['delta_lock60']} "
              f"ic={res['C_contraste_tf'][W]['ic_delta_lock60']['ic95']}")
    print("\n[fin] → data/census_arnold/POOLED.json")


def matar():
    rng = np.random.default_rng(1)
    # KM verdad construida
    ev = [(10.0, True), (10.0, True), (60.0, False), (60.0, False), (90.0, True)]
    v60 = km_1mS(ev, 60.0)
    assert abs(v60 - 0.4) < 1e-9, f"KM@60: {v60}"          # 2/5 antes de 60
    v120 = km_1mS(ev, 120.0)
    assert abs(v120 - (1 - 0.6 * (1 - 1/1))) < 1e-9, f"KM@120: {v120}"  # riesgo 1, evento
    # lock60 == KM@60 cuando todos en riesgo hasta 60
    filas = [{"W4": {"t_lock_ut": t, "estado": 2, "dw_temprana": 1, "dw_tardia": 0,
                     "rw_final": 1, "rw_max": 1}, "hor": h, "self": False, "dw": 0.1,
              "sdw": None, "bi": f"n{i}", "bj": f"m{i}", "brazo": "t", "tanda": 1,
              "celda": "k03_tau02", "par": f"p{i}", "par_idx": i, "W8": {
                  "t_lock_ut": t, "estado": 2, "dw_temprana": 1, "dw_tardia": 0,
                  "rw_final": 1, "rw_max": 1}}
             for i, (t, h) in enumerate([(10, 60), (None, 60), (70, 120), (None, 120)])]
    l60 = np.mean([lock60(f, "W4") for f in filas])
    assert abs(l60 - km_1mS(eventos_de(filas, "W4"), 60.0)) < 1e-9
    assert l60 == 0.25, f"lock60: {l60}"                    # solo t=10 cuenta
    # crash None arreglado: mediana condicionada con firme sin t_lock
    filas[1]["W4"]["t_lock_ut"] = None                       # firme sin t_lock
    tl = [f["W4"]["t_lock_ut"] for f in filas
          if firme(f, "W4") and f["W4"]["t_lock_ut"] is not None]
    assert len(tl) == 2                                      # no crashea
    # bootstrap degenerado → no citable
    fb = [{"bi": "a", "bj": "b", "W4": {"t_lock_ut": 5, "estado": 2}, "hor": 60},
          {"bi": "a", "bj": "b", "W4": {"t_lock_ut": None, "estado": 0}, "hor": 60}]
    ic = boot_ic(fb, lambda ff, pp: tasa_w(ff, pp, lambda g: lock60(g, "W4")),
                 rng, n_boot=200)
    assert ic["citable"] is False, f"degenerado citable: {ic}"
    # mcnemar poder
    m = mcnemar([(1, 0)] * 3, lambda x: x if isinstance(x, int) else 0)
    assert m["poder"] == "sin_poder" and m["p"] is None
    # pulling: inversión de signo detectable (control vs primario) + med=0.0 publicable
    f_p = {"W4": {"dw_temprana": 0.09, "dw_tardia": 0.045, "estado": 1,
                  "t_lock_ut": None, "rw_final": 0, "rw_max": 0}, "dw": 0.03,
           "sdw": 0.0, "hor": 60, "self": False, "brazo": "t", "bi": "a", "bj": "b"}
    p_med = 1 - f_p["W4"]["dw_tardia"] / f_p["W4"]["dw_temprana"]
    p_ctl = 1 - f_p["W4"]["dw_tardia"] / f_p["dw"]
    assert p_med > 0 > p_ctl, "trampa de ejes no reproducida"
    med = mediana_pond([0.0, 0.0], [1, 1])
    assert med == 0.0 and (None if med is None else med) == 0.0
    # mediana ponderada exacta
    assert mediana_pond([1, 2, 3], [1, 1, 10]) == 3
    # bins todos emitidos (n=0 visible) — estructural en lengua(); check bin_de bordes
    assert bin_de({"self": False, "dw": 0.02}) == "0.02-0.05"
    assert bin_de({"self": False, "dw": 0.30}) == "0.30-0.60"
    assert bin_de({"self": False, "dw": 19.77}) == "10-50"
    assert bin_de({"self": True, "dw": 0.0}) == "self"
    print("[matar] KM/lock60/crash-None/boot-degenerado/mcnemar-poder/pulling-ejes/"
          "mediana/bins: TODO OK")


if __name__ == "__main__":
    {"matar": matar, "correr": correr}[sys.argv[1]]()
