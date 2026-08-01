"""CENSUS ARNOLD — OLA B, generador SELLADO (tap de diseño wf_4d2144d4: COINCIDE CON
CAMBIOS C1-C9; regla de COA «si coinciden avanza»). Ver DISENO_OLA_B.md sellado.

Implementa la asignación FINAL del juez:
  [0,0.05):10 · self-pairs:5 · [0.05,0.15):10 · [0.15,0.30):12 · [0.30,0.60):15 ·
  [0.60,1.0):18 · [1.0,2.0):17 · [2.0,3.5):6 · [3.5,5.1):4 · [5.1,10):3  = 100 pares
  × 2 brazos (t/f, misma seed) = 200 u.  +  κ/τ: 25 pares de B con dw∈[0.8,2.8] × celda
  única (0.3, 0.05) transported = 25 u.  → 225 unidades en 4 SUB-LOTES (cadena
  archivo→liberación GO §2 entre ellos).

C3: horizonte 120 u.t. (1.5M ticks) en bins <0.30 y self-pairs; 60 u.t. resto. Lock
censurado declarado en TODA la ola; pulling primario bajo dw<0.275.
C5: eje = dw_fina continuo con σ_dw por par declarada (σ_nodo = max(|wx−wv|, |wx−wnls|),
σ_dw = √(σi²+σj²) — dispersión empírica de 3 estimadores); pools de bins <0.15 =
intersección dw_fina∩dw_nls; VETO de eje blando en bins <0.30 (|wx−wv|>0.15 ∨ relres>0.3);
tope de reuso 3 DURO (self-pair cuenta 2); w_hilbert retirado de validador; dw<0.02 se
reporta «<piso del eje».
C7: self-pairs = mismo bloque en ambos nodos (misma cápsula ×2 en brazo t — legal en el
composer, declarado; mismo theta ×2 fresh en brazo f) — ancla ESTRUCTURAL de dw=0.
C9: familia DNA registrada por nodo (covariable, ola C decide su estratificación).
RNG selección: 20260802 (sellada ACÁ, post-tap).
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
BASE = ORACLE / "data/processed/ola1_v4_c1/ola1"
OUT = STUDY07 / "data/census_arnold"

SEED_SEL = 20260802
DT = 8e-5
TICKS_LARGO, TICKS_CORTO = 1500000, 750000
CELDA_PPAL = (0.3, 0.2)
CELDA_KTAU = (0.3, 0.05)
BINS = [((0.0, 0.05), 10), ((0.05, 0.15), 10), ((0.15, 0.30), 12), ((0.30, 0.60), 15),
        ((0.60, 1.0), 18), ((1.0, 2.0), 17), ((2.0, 3.5), 6), ((3.5, 5.1), 4),
        ((5.1, 10.0), 3)]
N_SELF = 5
TOPE_REUSO = 3
N_SUBLOTES = 4


def main():
    eje = json.load(open(OUT / "eje_nodos.json"))
    wx, wv, wn, rr = eje["wx"], eje["wv"], eje["wnls"], eje["relres"]
    fina = {b: json.load(open(OUT / "carriers_fina.json"))[b]["w_fina"] for b in wx}
    inv = json.load(open(STUDY07 / "data/inventario_v4.json"))
    dir_b = {p["block_id"]: p["dir"] for p in inv["poblacion"]}
    sha_b = {p["block_id"]: p["capsule_sha256"] for p in inv["poblacion"]}
    raw = json.load(open(BASE / "simple_blocks_canonical.json"))
    blocks = {b["block_id"]: b for b in (raw["blocks"] if "blocks" in raw else raw)}
    familia = {}
    with open(BASE / "dof_dna_catalog_by_block_id.csv") as f:
        for row in csv.DictReader(f):
            familia[row["block_id"]] = row.get("dof_family_id", "")

    veto = {b for b in wx if abs(wx[b] - wv[b]) > 0.15} | {b for b in rr if rr[b] > 0.3}
    sel_a = json.load(open(OUT / "seleccion.json"))
    pares_a = {frozenset((a, b)) for s in sel_a["seleccion"] for a, b, _ in s["pares"]}

    bids = sorted(wx)
    candidatos = []
    for i in range(len(bids)):
        for j in range(i + 1, len(bids)):
            a, b = bids[i], bids[j]
            if frozenset((a, b)) in pares_a:
                continue
            candidatos.append((a, b, abs(fina[a] - fina[b]), abs(wn[a] - wn[b])))

    rng = np.random.default_rng(SEED_SEL)
    uso = {b: 0 for b in bids}
    elegidos = []
    for (lo, hi), n_obj in BINS:
        con_veto = lo < 0.30
        pool = [c for c in candidatos
                if lo <= c[2] < hi
                and (c[2] < 0.15) <= (lo <= c[3] < hi or not (c[2] < 0.15))  # ver abajo
                ]
        # pools <0.15: intersección fina∩nls (C5b) — re-filtrar explícito y legible:
        if hi <= 0.15:
            pool = [c for c in candidatos if lo <= c[2] < hi and lo <= c[3] < hi]
        else:
            pool = [c for c in candidatos if lo <= c[2] < hi]
        if con_veto:
            pool = [c for c in pool if c[0] not in veto and c[1] not in veto]
        orden = rng.permutation(len(pool))
        tomados = 0
        for k in orden:
            a, b, dwf, dwn = pool[int(k)]
            if uso[a] >= TOPE_REUSO or uso[b] >= TOPE_REUSO:
                continue
            uso[a] += 1; uso[b] += 1
            elegidos.append({"block_i": a, "block_j": b, "dw_fina": dwf, "dw_nls": dwn,
                             "bin": [lo, hi],
                             "sigma_dw": float(np.hypot(
                                 max(abs(wx[a] - wv[a]), abs(wx[a] - wn[a])),
                                 max(abs(wx[b] - wv[b]), abs(wx[b] - wn[b])))),
                             "familia_i": familia.get(a, ""), "familia_j": familia.get(b, ""),
                             "self": False})
            tomados += 1
            if tomados == n_obj:
                break
        if tomados < n_obj:
            raise SystemExit(f"bin [{lo},{hi}): sólo {tomados}/{n_obj} con tope duro "
                             f"{TOPE_REUSO} — el diseño no cierra, NO se relaja (C5d)")
    # self-pairs (C7): nodos sanos (sin veto), banda estable w>9, uso+2 dentro del tope
    sanos = [b for b in bids if b not in veto and abs(wx[b]) > 9.0
             and uso[b] + 2 <= TOPE_REUSO]
    idx = rng.choice(len(sanos), size=N_SELF, replace=False)
    for k in sorted(int(x) for x in idx):
        b = sanos[k]
        uso[b] += 2
        elegidos.append({"block_i": b, "block_j": b, "dw_fina": 0.0, "dw_nls": 0.0,
                         "bin": "self", "sigma_dw": 0.0,
                         "familia_i": familia.get(b, ""), "familia_j": familia.get(b, ""),
                         "self": True})

    def unidad(par_idx, e, kappa, tau, brazo, ticks):
        cons = []
        for bid in (e["block_i"], e["block_j"]):
            c = {"theta": blocks[bid]["theta_internal"], "block_id": bid}
            if brazo == "t":
                c["capsula_dir"] = str(BASE / "specimen_capsules" / dir_b[bid])
                c["capsule_sha256"] = sha_b[bid]
            cons.append(c)
        et = f"k{kappa}_tau{tau}".replace(".", "")
        return {"run_id": f"olaB_par{par_idx:03d}_{brazo}_{et}",
                "constituyentes": cons,
                "edges": [{"i": 0, "j": 1, "w_k": 1.0, "w_gamma": 1.0, "tau": tau}],
                "engine_params": {"dt": DT, "kappa_global": kappa,
                                  "coupling_gamma_c": kappa, "tau_field": 0.0,
                                  "temperature": 0.0},
                "seed": 2000 + par_idx, "ticks": ticks,
                "dw_fina_prereg": e["dw_fina"], "sigma_dw_prereg": e["sigma_dw"],
                "self_par": e["self"]}

    unidades = []
    k0, t0 = CELDA_PPAL
    for pi, e in enumerate(elegidos):
        largo = e["self"] or (not e["self"] and e["dw_fina"] < 0.30)
        ticks = TICKS_LARGO if largo else TICKS_CORTO
        for brazo in ("t", "f"):
            unidades.append(unidad(pi, e, k0, t0, brazo, ticks))
    ktau = [(pi, e) for pi, e in enumerate(elegidos)
            if not e["self"] and 0.8 <= e["dw_fina"] < 2.8][:25]
    if len(ktau) < 25:
        raise SystemExit(f"κ/τ: sólo {len(ktau)} pares en [0.8,2.8) — revisar asignación")
    for pi, e in ktau:
        unidades.append(unidad(pi, e, *CELDA_KTAU, "t", TICKS_CORTO))

    comunes = {
        "spec_tipo": "M1",
        "porque": ("census Arnold OLA B (rediseño post-tap wf_4d2144d4, C1-C9): densificar "
                   "nucleo/frontera en el eje fino, lock CENSURADO declarado, pulling "
                   "primario bajo 0.275, contraste t-f apareado, self-pairs como ancla "
                   "estructural de dw=0"),
        "retencion": {"perfil": "conformidad_completa", "chunk_ticks": 65536},
        "horizonte_emergencia_ticks": TICKS_CORTO,
        "reglas_clasificacion": {
            "instrumento": "par_link v1.1 OFFLINE",
            "outcomes": ["pulling (primario bajo dw<0.275)",
                         "lock CENSURADO (supervivencia, t_lock censura al horizonte)",
                         "estado W=4 y W=8", "contraste t-f apareado"],
            "inferencia": ("dw continuo con sigma_dw declarada; clustering dos vias por "
                           "nodo; ola como covariable + interaccion ola x dw en soporte "
                           "comun [0.05,2.0); sensibilidad sin los 8 pares del vistazo; "
                           "reponderacion a la poblacion 11175; dw<0.02 = <piso del eje")},
        "seed_politica": "seed=2000+idx_par, IDENTICA en brazos t/f",
    }
    orden = rng.permutation(len(unidades))
    unidades = [unidades[int(i)] for i in orden]      # round-robin estratificado de facto
    tam = (len(unidades) + N_SUBLOTES - 1) // N_SUBLOTES
    shas = {}
    for s in range(N_SUBLOTES):
        spec = dict(comunes)
        spec["campana"] = f"census_arnold_olaB_sub{s + 1}"
        spec["unidades"] = unidades[s * tam:(s + 1) * tam]
        cuerpo = json.dumps(spec, indent=1)
        (OUT / f"SPEC_olaB_sub{s + 1}.json").write_text(cuerpo)
        shas[f"sub{s + 1}"] = hashlib.sha256(cuerpo.encode()).hexdigest()
        n_largo = sum(1 for u in spec["unidades"] if u["ticks"] == TICKS_LARGO)
        print(f"[olaB] sub{s + 1}: {len(spec['unidades'])} u. ({n_largo} largas) "
              f"sha={shas[f'sub{s + 1}'][:16]}")
    (OUT / "seleccion_olaB.json").write_text(json.dumps(
        {"seed_seleccion": SEED_SEL, "tap_diseno": "wf_4d2144d4 COINCIDE CON CAMBIOS C1-C9",
         "asignacion": [[list(b), n] for b, n in BINS] + [["self", N_SELF]],
         "tope_reuso_duro": TOPE_REUSO, "vetados_eje_blando": sorted(veto),
         "celda_ktau": CELDA_KTAU, "n_ktau": len(ktau),
         "pares": elegidos, "spec_shas": shas}, indent=1))
    print(f"[olaB] {len(elegidos)} pares ({N_SELF} self) · {len(unidades)} unidades · "
          f"reuso max {max(uso.values())} · vetados {len(veto)}")


if __name__ == "__main__":
    main()
