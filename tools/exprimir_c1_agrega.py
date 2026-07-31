"""Agregador de EXPRIMIR C1 [M1-análisis] — cruza los 144 resúmenes con la constitución.

Produce data/c1_exprimido/_agregado.json + reporte por consola:
  A. UMBRAL EMPÍRICO: distribución de rw_final sobre TODAS las aristas (¿bimodal?).
  B. ARNOLD DE INTEGRACIÓN: lock vs Δω(omega_ref), estratificado por (κ, τ_field, topología).
  C. BANDAS VIABLES (hipótesis COA): compatibilidad de bandas de vida (17 por onion,
     runs_full) vs lock — métrica declarada: Σ_a w_a·min_b|E_a−E_b| simetrizada,
     normalizada por el spacing medio.
  D. FRICCIÓN: P_damp pre vs post lock (pareado por film) + transported vs fresh.
  E. EXCLUSIVIDAD (valencia): en cadenas/triángulos, P(arista trabada | la otra arista del
     nodo compartido trabada) vs tasa base — la hipótesis «un link inhabilita otro».
  F. SIN-RUPTURA: r interno final vs inicial por nodo, condicionado a participar en arista
     trabada.
"""
import json
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
OUT = STUDY07 / "data/c1_exprimido"
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
BASE = ORACLE / "data/processed/ola1_v4_c1/ola1"

UMBRAL_LOCK = 0.95   # candidato; el reporte muestra la distribución para revisarlo


def cargar_vidas():
    vidas = {}
    for linea in open(BASE / "runs_full.jsonl"):
        r = json.loads(linea)
        vidas[r["block_id"]] = {
            "omega_ref": float(r["omega_ref"]),
            "bandas_E": [float(x) for x in r.get("band_energies_gev", [])],
            # peso de banda = suma de fracciones por capa (Q+S1+S2 ≈ 1 por banda; usamos
            # la ENERGÍA de banda ponderada por su participación total)
            "bandas_w": [float(sum(w.values())) if isinstance(w, dict) else float(w)
                         for w in r.get("band_weights", [])],
            "r_intra_final": (float(np.mean(r["r_intra"][-20:]))
                              if r.get("r_intra") else None),
        }
    return vidas


def compat_bandas(va, vb):
    """Métrica declarada de compatibilidad: distancia mínima ponderada entre bandas,
    simetrizada, normalizada por el spacing medio conjunto. MENOR = más compatible."""
    Ea, wa = np.asarray(va["bandas_E"]), np.asarray(va["bandas_w"])
    Eb, wb = np.asarray(vb["bandas_E"]), np.asarray(vb["bandas_w"])
    if Ea.size == 0 or Eb.size == 0:
        return None
    esc = 0.5 * (np.mean(np.diff(np.sort(Ea))) + np.mean(np.diff(np.sort(Eb))))
    if not np.isfinite(esc) or esc <= 0:
        return None
    d_ab = np.sum(wa * np.min(np.abs(Ea[:, None] - Eb[None, :]), axis=1)) / max(np.sum(wa), 1e-12)
    d_ba = np.sum(wb * np.min(np.abs(Eb[:, None] - Ea[None, :]), axis=1)) / max(np.sum(wb), 1e-12)
    return float(0.5 * (d_ab + d_ba) / esc)


def main():
    vidas = cargar_vidas()
    regs = [json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))
            if not p.name.startswith("_")]
    print(f"[agregado] {len(regs)} films")

    aristas = []          # una fila por arista por film (transported)
    for r in regs:
        bloques = {int(k): v for k, v in r["bloques_por_nodo"].items()}
        topo = (r["topologia"]["n"], r["topologia"]["aristas"])
        e0 = {j: a["E0"] for j, a in enumerate(r["apagado"])}
        for p, pf in zip(r["pares"], r["pares_fresh"]):
            ba, bb = bloques[p["i"]], bloques[p["j"]]
            va, vb = vidas[ba], vidas[bb]
            aristas.append({
                "eval_id": r["eval_id"], "topo": topo,
                "kappa": r["kappa_global"], "tau": r["tau_field"],
                "dω": abs(va["omega_ref"] - vb["omega_ref"]),
                "compat_bandas": compat_bandas(va, vb),
                "E0_max": max(e0[p["i"]], e0[p["j"]]),
                "rw_final": p["rw_final"], "frac95": p["frac_sobre_0.95"],
                "t_lock95": p["t_lock"]["0.95"],
                "rw_final_fresh": pf["rw_final"], "frac95_fresh": pf["frac_sobre_0.95"],
                "nodo_i": p["i"], "nodo_j": p["j"],
            })

    rw = np.array([a["rw_final"] for a in aristas])
    rwf = np.array([a["rw_final_fresh"] for a in aristas])
    print(f"\nA. UMBRAL — rw_final sobre {len(rw)} aristas (transported):")
    h, ed = np.histogram(rw, bins=np.arange(0, 1.05, 0.05))
    for c, lo in zip(h, ed):
        print(f"   {lo:.2f}-{lo+0.05:.2f}: {'#' * c} {c}")
    tr95 = int(np.sum(rw >= UMBRAL_LOCK)); fr95 = int(np.sum(rwf >= UMBRAL_LOCK))
    print(f"   trabadas @{UMBRAL_LOCK}: transported {tr95}/{len(rw)} · fresh {fr95}/{len(rwf)}")

    print("\nB. ARNOLD — lock vs Δω (por estrato κ/τ; media rw_final por bin de Δω):")
    dws = np.array([a["dω"] for a in aristas])
    for kap in sorted({a["kappa"] for a in aristas}):
        for tau in sorted({a["tau"] for a in aristas}):
            sel = [a for a in aristas if a["kappa"] == kap and a["tau"] == tau]
            if not sel:
                continue
            d = np.array([a["dω"] for a in sel]); rr = np.array([a["rw_final"] for a in sel])
            bins = np.percentile(dws, [0, 25, 50, 75, 100])
            fila = []
            for lo, hi in zip(bins[:-1], bins[1:]):
                m = (d >= lo) & (d <= hi)
                fila.append(f"Δω∈[{lo:.2f},{hi:.2f}]: {np.mean(rr[m]):.3f}(n={m.sum()})"
                            if m.any() else "-")
            print(f"   κ={kap} τ={tau}: " + " · ".join(fila))
    # correlación global
    from scipy import stats as st  # noqa
    print(f"   Spearman rw~Δω: {st.spearmanr(dws, rw).statistic:+.3f} "
          f"(p={st.spearmanr(dws, rw).pvalue:.2e})")

    print("\nC. BANDAS (hipótesis COA) — rw_final vs compatibilidad de bandas:")
    cb = np.array([a["compat_bandas"] for a in aristas], dtype=float)
    ok = np.isfinite(cb)
    if ok.any():
        rho = st.spearmanr(cb[ok], rw[ok])
        print(f"   Spearman rw~compat_bandas: {rho.statistic:+.3f} (p={rho.pvalue:.2e}, "
              f"n={int(ok.sum())})  [métrica: MENOR=más compatible ⇒ esperado NEGATIVO]")
        rho2 = st.spearmanr(cb[ok], dws[ok])
        print(f"   (control: compat~Δω Spearman {rho2.statistic:+.3f} — ¿aporta más que Δω?)")

    print("\nD. FRICCIÓN — P_damp:")
    pares_fric = [(r["friccion"].get("p_damp_pre_lock"), r["friccion"].get("p_damp_post_lock"))
                  for r in regs if "p_damp_pre_lock" in r["friccion"]]
    if pares_fric:
        pre = np.array([p[0] for p in pares_fric]); post = np.array([p[1] for p in pares_fric])
        print(f"   films con lock: {len(pre)} · P_damp pre→post: "
              f"mediana {np.median(pre):.3e} → {np.median(post):.3e} "
              f"(post<pre en {int(np.sum(post < pre))}/{len(pre)})")
    pd_t = np.array([r["friccion"]["p_damp_final_W"] for r in regs])
    pd_f = np.array([r["friccion"]["p_damp_fresh_final_W"] for r in regs])
    print(f"   final_W transported vs fresh: mediana {np.median(pd_t):.3e} vs "
          f"{np.median(pd_f):.3e} (transported>fresh en {int(np.sum(pd_t > pd_f))}/{len(pd_t)})")

    print("\nE. EXCLUSIVIDAD — cadenas y triángulos (nodo compartido):")
    base_rate = float(np.mean(rw >= UMBRAL_LOCK))
    cond, cond_n = 0, 0
    for r in regs:
        if r["topologia"]["aristas"] < 2:
            continue
        ps = r["pares"]
        for i, p in enumerate(ps):
            for q in ps[i + 1:]:
                if {p["i"], p["j"]} & {q["i"], q["j"]}:      # comparten nodo
                    a_lock = p["rw_final"] >= UMBRAL_LOCK
                    b_lock = q["rw_final"] >= UMBRAL_LOCK
                    if a_lock or b_lock:
                        cond_n += 1
                        if a_lock and b_lock:
                            cond += 1
    print(f"   tasa base de lock por arista: {base_rate:.3f}")
    print(f"   P(ambas | alguna) en aristas que comparten nodo: "
          f"{cond}/{cond_n}" + (f" = {cond/cond_n:.3f}" if cond_n else " (sin casos)"))

    print("\nF. SIN-RUPTURA — r interno (final − inicial) por nodo:")
    en_lock, fuera = [], []
    for r in regs:
        trabados = set()
        for p in r["pares"]:
            if p["rw_final"] >= UMBRAL_LOCK:
                trabados |= {p["i"], p["j"]}
        for j, nodo in enumerate(r["interno"]):
            d = nodo["r_final_W"] - nodo["r_ini_5ut"]
            (en_lock if j in trabados else fuera).append(d)
    for etiqueta, xs in (("nodos EN arista trabada", en_lock), ("nodos sin lock", fuera)):
        if xs:
            xs = np.array(xs)
            print(f"   {etiqueta}: n={len(xs)} Δr_int mediana {np.median(xs):+.4f} "
                  f"(cae en {int(np.sum(xs < 0))}/{len(xs)})")

    salida = {"n_films": len(regs), "n_aristas": len(aristas),
              "umbral_reporte": UMBRAL_LOCK, "aristas": aristas}
    (OUT / "_agregado.json").write_text(json.dumps(salida, indent=1))
    print(f"\n[agregado] escrito {OUT}/_agregado.json")


if __name__ == "__main__":
    main()
