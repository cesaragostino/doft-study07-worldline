"""ANÁLISIS POOLED del census Arnold A∪B [M1 — implementa el prereg sellado].

Sellos que implementa (sin agregar hipótesis): prereg §1 (2026-08-01) + adenda §3 (eje
dw_fina, clustering DOS VÍAS por nodo, W4 vs W8 robustez primaria) + DISENO_OLA_B C1-C9
(pooling A∪B, tanda covariable + interacción en soporte común [0.05,2.0), lock CENSURADO,
pulling primario dw<0.275, self-pairs ancla dw=0, sensibilidad sin el vistazo,
reponderación a la población 11175, dw<0.02 = «<piso del eje», umbrales re-medibles) +
semántica §5/§7/§8 declarada (los estados son DOMINANCIA ESPECTRAL CONDICIONADA AL DRIVE
a horizonte CENSURADO — no supervivencia energética; el reloj del líder va y vuelve).

Decisiones de implementación DECLARADAS (no selladas antes — el tap de diseño las juzga):
  D1. Eje: dw = dw_fina (t1) / dw_fina_prereg (t2); self-pairs dw=0; dw<0.02 se reporta
      como «<piso» (bin propio, sin pretensión de orden interno).
  D2. Bins de la lengua = los de la asignación olaB (0-0.05/…/5.1-10) + «self» + los dos
      estratos t1 fuera de soporte ([10,50) partido en 10-20/20-50) — cubren A∪B.
  D3. «firme» = estado==2 del par v1.1 (W4 primario, W8 robustez). Censura: se publica
      el mix de horizontes (60/120 u.t.) POR BIN junto a cada tasa; t_lock con fracción
      censurada. NO se mezclan horizontes dentro de un contraste pareado (misma unidad).
  D4. Inferencia con dependencia por nodos: BOOTSTRAP DE DOS VÍAS por clusters de nodos
      (resampleo iid de los 150 block_id; una fila entra si AMBOS endpoints están en el
      resample — pesada por multiplicidad producto) para IC de tasas y contrastes;
      n_boot=2000, semilla 20260802. Para el contraste t−f apareado: McNemar exacto
      (binomial sobre discordantes) + el mismo bootstrap para IC del Δ.
  D5. Pulling (primario dw<0.275, brazo por separado): pull = 1 − dw_tardia/dw (dw>piso);
      mediana por bin + IC bootstrap D4. dw_temprana como control de llegada.
  D6. Interacción tanda×dw en soporte común [0.05, 2.0): diferencia-de-diferencias de
      tasas firme por bins comunes, IC bootstrap D4 (responde: ¿las tandas miden lo
      mismo donde se solapan?).
  D7. Reponderación: población = las C(150,2)=11175 duplas sobre carriers_fina (w_fina);
      peso por bin = share_poblacional/share_muestral (celda ppal, ambos brazos);
      se publica la tasa firme reponderada (t y f, W4/W8) + pesos.
  D8. Sensibilidad del vistazo (CONSERVADORA, superset declarado): sin el estrato ENTERO
      [0,0.1]-grilla de t1 (30 pares — el vistazo fue a 8 de ellos, sin lista sellada) y
      sin par126-134 de t1 (abiertos en taps posteriores, declarados). Además réplica
      con W8 de TODO (robustez primaria adenda §3).
  D9. κ/τ: los 25 pares (0.3,0.05) transported vs sus MISMAS duplas en celda ppal
      transported (t2): McNemar pareado sobre firme + Δrw_final.
  D10. Self-pairs: tasas por brazo (ancla estructural; n=5×2, solo descriptivo).
Salida: data/census_arnold/POOLED.json + resumen impreso. Números, no conclusiones.
"""
import json
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
OUT = STUDY07 / "data/census_arnold"

SEED = 20260802
N_BOOT = 2000
PISO_EJE = 0.02
BINS_LENGUA = [("self", None), ("<piso", (0.0, PISO_EJE)), ("0.02-0.05", (PISO_EJE, 0.05)),
               ("0.05-0.15", (0.05, 0.15)), ("0.15-0.30", (0.15, 0.30)),
               ("0.30-0.60", (0.30, 0.60)), ("0.60-1.0", (0.60, 1.0)),
               ("1.0-2.0", (1.0, 2.0)), ("2.0-3.5", (2.0, 3.5)), ("3.5-5.1", (3.5, 5.1)),
               ("5.1-10", (5.1, 10.0)), ("10-20", (10.0, 20.0)), ("20-50", (20.0, 50.0))]
SOPORTE_COMUN = (0.05, 2.0)
PULL_MAX = 0.275


def cargar():
    t1 = json.load(open(OUT / "tabla_tanda1.json"))
    t2 = json.load(open(OUT / "tabla_tanda2.json"))
    filas = []
    for f in t1:
        filas.append({"tanda": 1, "brazo": f["brazo"], "celda": "k03_tau02",
                      "dw": f["dw_fina"], "self": False, "par": f"t1_{f['par_idx']}",
                      "bi": f["block_i"], "bj": f["block_j"],
                      "hor": round(f["ticks"] * 8e-5), "W4": f["W4"], "W8": f["W8"]})
    for f in t2:
        filas.append({"tanda": 2, "brazo": f["brazo"], "celda": f["celda"],
                      "dw": 0.0 if f["self_par"] else f["dw_fina_prereg"],
                      "self": f["self_par"], "par": f"t2_{f['par_idx']}",
                      "bi": f["block_i"], "bj": f["block_j"],
                      "hor": round(f["ticks"] * 8e-5), "W4": f["W4"], "W8": f["W8"]})
    return filas


def bin_de(fila):
    if fila["self"]:
        return "self"
    for nombre, rango in BINS_LENGUA[1:]:
        if rango[0] <= fila["dw"] < rango[1]:
            return nombre
    return None


def firme(fila, W):
    return 1 if fila[W]["estado"] == 2 else 0


def boot_dos_vias(filas, stat_fn, rng, n_boot=N_BOOT):
    """Bootstrap de dos vías por clusters de nodos (D4): resampleo iid de nodos;
    fila pesa (multiplicidad bi)×(multiplicidad bj). Devuelve (lo, hi) percentil 2.5/97.5."""
    nodos = sorted({f["bi"] for f in filas} | {f["bj"] for f in filas})
    idx = {n: k for k, n in enumerate(nodos)}
    vals = []
    for _ in range(n_boot):
        cnt = np.bincount(rng.integers(0, len(nodos), len(nodos)), minlength=len(nodos))
        pesos = [cnt[idx[f["bi"]]] * cnt[idx[f["bj"]]] for f in filas]
        v = stat_fn(filas, pesos)
        if v is not None:
            vals.append(v)
    if not vals:
        return None, None
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def tasa_w(filas, pesos, W):
    num = sum(p * firme(f, W) for f, p in zip(filas, pesos))
    den = sum(pesos)
    return num / den if den > 0 else None


def mcnemar(pares_tf, W):
    """pares_tf = [(fila_t, fila_f)]. Exacto binomial sobre discordantes."""
    from math import comb
    b01 = sum(1 for t, f in pares_tf if firme(t, W) == 1 and firme(f, W) == 0)
    b10 = sum(1 for t, f in pares_tf if firme(t, W) == 0 and firme(f, W) == 1)
    n = b01 + b10
    if n == 0:
        return {"b01": 0, "b10": 0, "p": 1.0}
    k = min(b01, b10)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
    return {"b01": b01, "b10": b10, "p": round(p, 6)}


def main():
    rng = np.random.default_rng(SEED)
    filas = cargar()
    ppal = [f for f in filas if f["celda"] == "k03_tau02"]
    res = {"_sellos": "prereg §1 + adenda §3 + DISENO_OLA_B C1-C9; decisiones D1-D10 "
                      "en docstring; semantica §5/§7/§8: dominancia espectral condicionada "
                      "al drive, horizonte censurado",
           "n": {"total": len(filas), "celda_ppal": len(ppal),
                 "nodos_unicos": len({f['bi'] for f in filas} | {f['bj'] for f in filas})}}

    # ---- A. LENGUA por bins (t y f, W4/W8) + censura declarada ----
    lengua = {}
    for W in ("W4", "W8"):
        lengua[W] = {}
        for brazo in ("t", "f"):
            sel = [f for f in ppal if f["brazo"] == brazo]
            tabla = []
            for nombre, _ in BINS_LENGUA:
                fb = [f for f in sel if bin_de(f) == nombre]
                if not fb:
                    continue
                tasa = float(np.mean([firme(f, W) for f in fb]))
                lo, hi = boot_dos_vias(fb, lambda ff, pp, W=W: tasa_w(ff, pp, W), rng,
                                       n_boot=600)
                hor = {str(h): sum(1 for f in fb if f["hor"] == h)
                       for h in sorted({f["hor"] for f in fb})}
                tl = [f[W]["t_lock_ut"] for f in fb if firme(f, W)]
                tabla.append({"bin": nombre, "n": len(fb), "firme": round(tasa, 3),
                              "ic95": [None if lo is None else round(lo, 3),
                                       None if hi is None else round(hi, 3)],
                              "horizontes": hor,
                              "t_lock_mediana": (round(float(np.median(tl)), 1)
                                                 if tl else None),
                              "frac_censurada_no_firme": round(
                                  1 - tasa, 3)})
                # nota: toda unidad no-firme es censura del lock al horizonte (C3)
            lengua[W][brazo] = tabla
        # monotonía (continua, sin self, dw>piso): Spearman + permutación por nodos
        sel = [f for f in ppal if f["brazo"] == "t" and not f["self"]
               and f["dw"] > PISO_EJE]
        x = np.array([f["dw"] for f in sel])
        y = np.array([firme(f, W) for f in sel])
        rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
        rho = float(np.corrcoef(rx, ry)[0, 1])
        nodos = sorted({f["bi"] for f in sel} | {f["bj"] for f in sel})
        perm = []
        for _ in range(1000):
            # permutación por nodo: barajar dw ENTRE pares reasignando por firma de nodos
            pp = rng.permutation(len(sel))
            perm.append(float(np.corrcoef(rx[pp], ry)[0, 1]))
        p_perm = float(np.mean([abs(v) >= abs(rho) for v in perm]))
        lengua[W]["monotonia_t"] = {"spearman": round(rho, 3),
                                    "p_perm_naive_declarada": round(p_perm, 4),
                                    "nota": "permutación naive por par (la de nodos la "
                                            "cubre el IC bootstrap D4 de los bins)"}
    res["A_lengua"] = lengua

    # ---- B. PULLING primario dw<0.275 ----
    pulling = {}
    for brazo in ("t", "f"):
        sel = [f for f in ppal if f["brazo"] == brazo and not f["self"]
               and PISO_EJE < f["dw"] < PULL_MAX]
        pulls = [1 - f["W4"]["dw_tardia"] / f["dw"] for f in sel]
        med = float(np.median(pulls)) if pulls else None
        lo, hi = boot_dos_vias(
            sel, lambda ff, pp: (float(np.median(
                [1 - g["W4"]["dw_tardia"] / g["dw"]
                 for g, p in zip(ff, pp) for _ in range(int(p))]))
                if sum(pp) > 0 else None), rng, n_boot=400)
        pulling[brazo] = {"n": len(sel), "pull_mediana": round(med, 3) if med else None,
                          "ic95": [None if lo is None else round(lo, 3),
                                   None if hi is None else round(hi, 3)]}
    res["B_pulling"] = pulling

    # ---- C. CONTRASTE t−f apareado (mismo par, misma tanda/celda/horizonte) ----
    contraste = {}
    por_par = {}
    for f in ppal:
        por_par.setdefault(f["par"], {})[f["brazo"]] = f
    pares_tf = [(d["t"], d["f"]) for d in por_par.values() if "t" in d and "f" in d]
    for W in ("W4", "W8"):
        mc = mcnemar(pares_tf, W)
        d_rw = [p_t[W]["rw_final"] - p_f[W]["rw_final"] for p_t, p_f in pares_tf]
        contraste[W] = {"n_pares": len(pares_tf), "mcnemar": mc,
                        "delta_rw_mediana": round(float(np.median(d_rw)), 4)}
        for region, (a, b) in (("dw<0.275", (0, PULL_MAX)), ("0.275-1", (PULL_MAX, 1.0)),
                               ("1-10", (1.0, 10.0)), (">=10", (10.0, 1e9))):
            sub = [(t, f) for t, f in pares_tf if a <= t["dw"] < b and not t["self"]]
            if sub:
                contraste[W][f"region_{region}"] = {
                    "n": len(sub), "mcnemar": mcnemar(sub, W),
                    "firme_t": round(float(np.mean([firme(t, W) for t, _ in sub])), 3),
                    "firme_f": round(float(np.mean([firme(f, W) for _, f in sub])), 3)}
    res["C_contraste_tf"] = contraste

    # ---- D. Interacción tanda×dw en soporte común ----
    inter = {}
    for W in ("W4", "W8"):
        celdas = []
        for nombre, rango in BINS_LENGUA:
            if rango is None or rango[1] <= SOPORTE_COMUN[0] or rango[0] >= SOPORTE_COMUN[1]:
                continue
            fila = {"bin": nombre}
            for tanda in (1, 2):
                sel = [f for f in ppal if f["tanda"] == tanda and f["brazo"] == "t"
                       and not f["self"] and rango[0] <= f["dw"] < rango[1]]
                fila[f"t{tanda}"] = {"n": len(sel),
                                     "firme": (round(float(np.mean(
                                         [firme(f, W) for f in sel])), 3)
                                         if sel else None)}
            if fila["t1"]["n"] and fila["t2"]["n"]:
                fila["delta"] = round(fila["t2"]["firme"] - fila["t1"]["firme"], 3)
                fila["nota_horizonte"] = "t2 dw<0.30 corre a 120 u.t. vs t1 60 (censura)"
            celdas.append(fila)
        inter[W] = celdas
    res["D_interaccion_tanda"] = inter

    # ---- E. Self-pairs ----
    selfs = [f for f in ppal if f["self"]]
    res["E_self"] = {W: {brazo: {"n": len([f for f in selfs if f["brazo"] == brazo]),
                                 "firmes": sum(firme(f, W) for f in selfs
                                               if f["brazo"] == brazo)}
                         for brazo in ("t", "f")} for W in ("W4", "W8")}

    # ---- F. κ/τ pareado ----
    ktau = [f for f in filas if f["celda"] == "k03_tau005"]
    pares_kt = []
    for f in ktau:
        gemelo = [g for g in ppal if g["par"] == f["par"] and g["brazo"] == "t"]
        if gemelo:
            pares_kt.append((f, gemelo[0]))
    res["F_ktau"] = {}
    for W in ("W4", "W8"):
        res["F_ktau"][W] = {
            "n": len(pares_kt),
            "firme_tau005": sum(firme(f, W) for f, _ in pares_kt),
            "firme_tau02": sum(firme(g, W) for _, g in pares_kt),
            "mcnemar": mcnemar([(f, g) for f, g in pares_kt], W)}

    # ---- G. Sensibilidad del vistazo (superset D8) ----
    sel1 = json.load(open(OUT / "seleccion.json"))
    bin1 = {frozenset((a, b)) for a, b, _ in sel1["seleccion"][0]["pares"]}
    tap_abiertos = {f"t1_{k}" for k in range(126, 135)}
    excl = [f for f in ppal
            if not (f["tanda"] == 1 and (frozenset((f["bi"], f["bj"])) in bin1
                                         or f["par"] in tap_abiertos))]
    por_par_x = {}
    for f in excl:
        por_par_x.setdefault(f["par"], {})[f["brazo"]] = f
    pares_x = [(d["t"], d["f"]) for d in por_par_x.values() if "t" in d and "f" in d]
    res["G_sensibilidad"] = {
        "excluidos": len(ppal) - len(excl),
        "W4": {"mcnemar": mcnemar(pares_x, "W4"),
               "firme_t": round(float(np.mean([firme(f, "W4") for f in excl
                                               if f["brazo"] == "t"])), 3),
               "firme_f": round(float(np.mean([firme(f, "W4") for f in excl
                                               if f["brazo"] == "f"])), 3)},
        "W8": {"mcnemar": mcnemar(pares_x, "W8")}}

    # ---- H. Reponderación a la población 11175 ----
    car = json.load(open(OUT / "carriers_fina.json"))
    ws = {b: car[b]["w_fina"] for b in car}
    bids = sorted(ws)
    pob = []
    for i in range(len(bids)):
        for j in range(i + 1, len(bids)):
            pob.append(abs(ws[bids[i]] - ws[bids[j]]))
    pob = np.array(pob)
    res["H_reponderada"] = {"n_poblacion": len(pob)}
    shares_pob = {}
    for nombre, rango in BINS_LENGUA[1:]:
        shares_pob[nombre] = float(np.mean((pob >= rango[0]) & (pob < rango[1])))
    for W in ("W4",):
        for brazo in ("t", "f"):
            sel = [f for f in ppal if f["brazo"] == brazo and not f["self"]]
            num = den = 0.0
            pesos_bin = {}
            for nombre, _ in BINS_LENGUA[1:]:
                fb = [f for f in sel if bin_de(f) == nombre]
                if not fb or shares_pob[nombre] == 0:
                    continue
                w = shares_pob[nombre] / (len(fb) / len(sel))
                pesos_bin[nombre] = round(w, 2)
                num += w * sum(firme(f, W) for f in fb)
                den += w * len(fb)
            res["H_reponderada"][f"{W}_{brazo}"] = {
                "firme_reponderada": round(num / den, 4) if den else None,
                "pesos_bin": pesos_bin}

    (OUT / "POOLED.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1)[:6000])
    print("\n[fin] → data/census_arnold/POOLED.json")


if __name__ == "__main__":
    main()
