"""CENSUS ARNOLD — generador de PRE-REGISTRO [M1] (etapa 1 del norte del link).

Diseño prescripto por el panel §16 y sellado en bitácora 2026-08-01 §1:
  · 150 composiciones de PAR ÚNICAS (sin réplicas ×4), estratificadas por Δω_fft REAL
    (portadoras por FFT de los rings de cápsula — carriers_fft.json) en 5 bins con datos:
    [0,0.1) [0.3,1) [1,3) [3,10) [10,50) × 30 pares (RNG semilla 20260801, declarada).
    El hueco [0.1,0.3) es POBLACIONAL (0 pares en los 11175): declarado.
  · Cada par en DOS brazos: TRANSPORTED (ambas cápsulas, quench) y FRESH (mismos thetas,
    nacimiento; MISMA seed ⇒ contraste apareado — el test de biografía del §16).
  · Celda principal κ=0.3, τ_arista=0.2, γ_c=κ (ratio 1.0, espejo C1), dt=8e-5, T=0,
    60 u.t. (750k ticks — t_lock medido en C1 llega a 36).
  · Subconjunto κ/τ: 24 pares (los 5 primeros de cada bin, determinista) × las otras 3
    celdas (0.2,0.2) (0.3,0.05) (0.2,0.05), sólo transported.
  · OUTCOMES pre-registrados (pasada OFFLINE con par v1.1 sobre los films archivados):
    (i) curva de pulling Δω̂_tardía/Δω̂_llegada; (ii) veredicto de link con W=4 y W=8
    (umbrales 0.95/0.80 TRANSFERIDOS POR HIPÓTESIS — su re-medición es outcome, no input);
    (iii) contraste transported−fresh apareado por par.
LOTES por disco (176 GB locales): L1 = 75 pares t+f (150 u.); L2 = 75 pares t+f;
L3 = subconjunto κ/τ (72 u.). L2/L3 esperan liberación local (archivo verificado + GO COA).
"""
import json
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
BASE = ORACLE / "data/processed/ola1_v4_c1/ola1"
OUT = STUDY07 / "data/census_arnold"

SEED_SEL = 20260801
BINS = [(0.0, 0.1), (0.3, 1.0), (1.0, 3.0), (3.0, 10.0), (10.0, 50.0)]
POR_BIN = 30
DT = 8e-5
TICKS = 750000
CELDA_PRINCIPAL = (0.3, 0.2)                  # (kappa, tau_arista)
CELDAS_EXTRA = [(0.2, 0.2), (0.3, 0.05), (0.2, 0.05)]
SUBSET_POR_BIN = 5                            # pares por bin para las celdas extra


def main():
    carriers = json.loads((OUT / "carriers_fft.json").read_text())
    inv = json.loads((STUDY07 / "data/inventario_v4.json").read_text())
    dir_por_block = {p["block_id"]: p["dir"] for p in inv["poblacion"]}
    sha_por_block = {p["block_id"]: p["capsule_sha256"] for p in inv["poblacion"]}
    raw = json.load(open(BASE / "simple_blocks_canonical.json"))
    blocks = {b["block_id"]: b for b in (raw["blocks"] if "blocks" in raw else raw)}

    bids = sorted(carriers)
    pares_todos = []
    for a in range(len(bids)):
        for b in range(a + 1, len(bids)):
            dw = abs(carriers[bids[a]] - carriers[bids[b]])
            pares_todos.append((bids[a], bids[b], dw))
    rng = np.random.default_rng(SEED_SEL)
    seleccion = []
    for lo, hi in BINS:
        cand = [p for p in pares_todos if lo <= p[2] < hi]
        idx = rng.choice(len(cand), size=POR_BIN, replace=False)
        elegidos = [cand[i] for i in sorted(int(x) for x in idx)]
        seleccion.append({"bin": [lo, hi], "pares": elegidos})

    def unidad(par_idx, bid_i, bid_j, dw, kappa, tau, brazo):
        seed = 1000 + par_idx                    # MISMA seed en ambos brazos: apareado
        cons = []
        for bid in (bid_i, bid_j):
            c = {"theta": blocks[bid]["theta_internal"], "block_id": bid}
            if brazo == "t":
                c["capsula_dir"] = str(BASE / "specimen_capsules" / dir_por_block[bid])
                c["capsule_sha256"] = sha_por_block[bid]
            cons.append(c)
        etiqueta_celda = f"k{kappa}_tau{tau}".replace(".", "")
        return {"run_id": f"par{par_idx:03d}_{brazo}_{etiqueta_celda}",
                "constituyentes": cons,
                "edges": [{"i": 0, "j": 1, "w_k": 1.0, "w_gamma": 1.0, "tau": tau}],
                "engine_params": {"dt": DT, "kappa_global": kappa,
                                  "coupling_gamma_c": kappa, "tau_field": 0.0,
                                  "temperature": 0.0},
                "seed": seed, "ticks": TICKS,
                "dw_fft_prereg": dw, "bin_prereg": None}

    comunes = {
        "spec_tipo": "M1",
        "porque": ("census Arnold (etapa 1 del norte del link, §16-§18): medir la lengua "
                   "con detuning REAL de llegada y el contraste de biografía apareado — "
                   "calibra k_eff y el detector de links para el census de emergencia"),
        "retencion": {"perfil": "conformidad_completa", "chunk_ticks": 65536},
        "horizonte_emergencia_ticks": TICKS,
        "reglas_clasificacion": {
            "instrumento": "par_link v1.1 (declarado §19) OFFLINE sobre films archivados",
            "outcomes": ["pulling dw_tardia/dw_llegada", "estado con W=4 y W=8",
                         "contraste transported-fresh apareado por par"],
            "umbrales": "0.95/0.80 transferidos POR HIPOTESIS; re-medicion = outcome"},
        "seed_politica": "seed=1000+idx_par, IDENTICA en brazos t/f (contraste apareado)",
    }
    lotes = {1: [], 2: [], 3: []}
    par_idx = 0
    k0, t0 = CELDA_PRINCIPAL
    for bin_k, sel in enumerate(seleccion):
        for n_en_bin, (bi, bj, dw) in enumerate(sel["pares"]):
            destino = 1 if n_en_bin < 15 else 2
            for brazo in ("t", "f"):
                u = unidad(par_idx, bi, bj, dw, k0, t0, brazo)
                u["bin_prereg"] = bin_k
                lotes[destino].append(u)
            if n_en_bin < SUBSET_POR_BIN:
                for kx, tx in CELDAS_EXTRA:
                    u = unidad(par_idx, bi, bj, dw, kx, tx, "t")
                    u["bin_prereg"] = bin_k
                    lotes[3].append(u)
            par_idx += 1

    import hashlib
    shas = {}
    for n, unidades in lotes.items():
        spec = dict(comunes)
        spec["campana"] = f"census_arnold_lote{n}"
        spec["unidades"] = unidades
        cuerpo = json.dumps(spec, indent=1)
        p = OUT / f"SPEC_lote{n}.json"
        p.write_text(cuerpo)
        shas[f"lote{n}"] = hashlib.sha256(cuerpo.encode()).hexdigest()
        print(f"[prereg] lote{n}: {len(unidades)} unidades  sha={shas[f'lote{n}'][:16]}")
    (OUT / "seleccion.json").write_text(json.dumps(
        {"seed_seleccion": SEED_SEL, "bins": BINS, "por_bin": POR_BIN,
         "celda_principal": CELDA_PRINCIPAL, "celdas_extra": CELDAS_EXTRA,
         "hueco_poblacional": "[0.1,0.3): 0 pares en los 11175 — dato de poblacion",
         "seleccion": seleccion, "spec_shas": shas}, indent=1))
    print(f"[prereg] seleccion.json + carriers ya escritos en {OUT}")


if __name__ == "__main__":
    main()
