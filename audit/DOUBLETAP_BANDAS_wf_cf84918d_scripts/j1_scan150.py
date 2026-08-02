"""JUEZ — scan independiente de lideres-chirpeantes en tanda 1 (150 unidades).
ATAJO DECLARADO (mismo status que t3): lectura cruda de chunks sin re-hash — es
identificacion de candidatos; los films citados en el veredicto pasaron por load_run.
MAS FUERTE que el scan de t3: muestrea fila 0 (chunk 0), fila final (ultimo chunk)
Y una fila del chunk MEDIO — detecta tambien lideres que carguen b DURANTE el film.
"""
import json
from pathlib import Path
import numpy as np

BASE = Path("/Volumes/ExternalDisk/study07_census_arnold/lote1/unidades")
OUT = Path(__file__).parent
UMBRAL = 0.5

rows, lideres = [], []
units = sorted(d for d in BASE.iterdir() if d.is_dir())
for unit in units:
    man = json.loads((unit / "manifest.json").read_text())
    pn = man["por_nodo"]
    comp = man["composicion"]["por_nodo"]
    chunks = sorted((unit / "worldline").glob("chunk_*.npz"))
    mid = chunks[len(chunks) // 2]
    rec = {"unit": unit.name}
    flag = False
    with np.load(chunks[0], allow_pickle=False) as f0, \
         np.load(mid, allow_pickle=False) as fM, \
         np.load(chunks[-1], allow_pickle=False) as fL:
        for j, nd in enumerate(pn):
            nm, nz = nd["n_modes"], nd["n_z"]
            lp = list(nd["layers_present"])
            if "Q" not in lp:
                continue
            iQ = 2 * nm + nz + lp.index("Q")
            b0 = float(f0[f"estados_nodo{j}"][0, iQ])
            bM = float(fM[f"estados_nodo{j}"][0, iQ])
            bF = float(fL[f"estados_nodo{j}"][-1, iQ])
            bid = (comp[j].get("block_id") or comp[j].get("genome_hash", "?"))[:12]
            rec[f"n{j}"] = {"block": bid, "bq0": b0, "bq_mid": bM, "bq_fin": bF}
            if max(abs(b0), abs(bM), abs(bF)) > UMBRAL:
                flag = True
                lideres.append({"unit": unit.name, "nodo": j, "block": bid,
                                "bq0": b0, "bq_mid": bM, "bq_fin": bF})
    rows.append(rec)
    if flag:
        print("LIDER>", rec["unit"], {k: v for k, v in rec.items() if k != "unit"}, flush=True)

json.dump(rows, open(OUT / "j1_scan150.json", "w"), indent=1)
json.dump(lideres, open(OUT / "j1_lideres.json", "w"), indent=1)
print(f"DONE {len(rows)} unidades; {len(lideres)} nodos con |b_Q|>{UMBRAL}")
blq = sorted(set(l["block"] for l in lideres))
print("bloques lideres:", blq)
todos = [abs(v["bq0"]) for r in rows for k, v in r.items() if k != "unit"]
todos_np = np.array(todos)
print(f"mediana |b_Q0| poblacion: {np.median(todos_np):.2e}; max no-lider: "
      f"{max((x for x in todos if x <= UMBRAL), default=0):.3f}")
