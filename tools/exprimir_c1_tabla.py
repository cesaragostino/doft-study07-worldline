"""Tabla maestra de C1 [M1-recolección, SIN conclusiones]: el join de todo.

ARISTAS (288 filas): identidad del par + Δω constitucional Y efectivo + compatibilidad de
bandas + lock (rw/t_lock/episodios/coqueteo, con fresh) + fricción por arista + energías.
NODOS (432 filas): identidad + biografía de vida ola1 (escalares seleccionados de runs_full
+ grado DNA) + estado en red (enfriamiento, r interno, frecuencia efectiva, participación
en aristas trabadas).

Salida: data/c1_exprimido/tabla_aristas.csv + tabla_nodos.csv + _tabla_resumen.json.
Datos, no veredictos.
"""
import csv
import json
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
OUT = STUDY07 / "data/c1_exprimido"
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
BASE = ORACLE / "data/processed/ola1_v4_c1/ola1"

VIDA_CAMPOS = ("omega_ref", "lyapunov_mean", "lyapunov_local", "participation_entropy",
               "complexity", "lock_quality_Q", "lock_quality_S1", "lock_quality_S2",
               "E_internal", "R_mean_lastW", "phase_var_lastW", "s2_state",
               "rho_lock", "phase_compactness")


def main():
    vidas = {}
    for linea in open(BASE / "runs_full.jsonl"):
        r = json.loads(linea)
        v = {c: r.get(c) for c in VIDA_CAMPOS}
        v["r_intra_final_vida"] = (float(np.mean(r["r_intra"][-20:]))
                                   if r.get("r_intra") else None)
        vidas[r["block_id"]] = v
    grados = {}
    with open(BASE / "dof_dna_catalog_by_block_id.csv") as f:
        for row in csv.DictReader(f):
            grados[row["block_id"]] = row.get("dof_grade")

    ag = json.loads((OUT / "_agregado.json").read_text())
    compat = {(a["eval_id"], a["nodo_i"], a["nodo_j"]): a["compat_bandas"]
              for a in ag["aristas"]}

    filas_a, filas_n = [], []
    for p1 in sorted(OUT.glob("*.json")):
        if p1.name.startswith(("_", "v2_", "tabla")):
            continue
        r1 = json.loads(p1.read_text())
        p2 = OUT / f"v2_{r1['eval_id']}.json"
        if not p2.exists():
            continue
        r2 = json.loads(p2.read_text())
        bloques = {int(k): v for k, v in r1["bloques_por_nodo"].items()}
        frecs = r2["frecuencias"]
        fric = {(f["i"], f["j"]): f for f in r2["friccion_arista"]}
        coq = {(c["i"], c["j"]): c for c in r2["coqueteo"]}
        trabados = {}
        for p, pf in zip(r1["pares"], r1["pares_fresh"]):
            i, j = p["i"], p["j"]
            fi, fj = frecs[i]["temprana"], frecs[j]["temprana"]
            fr = fric.get((i, j), {})
            cq = coq.get((i, j), {})
            va, vb = vidas[bloques[i]], vidas[bloques[j]]
            filas_a.append({
                "eval_id": r1["eval_id"], "n_nodos": r1["topologia"]["n"],
                "n_aristas": r1["topologia"]["aristas"],
                "kappa": r1["kappa_global"], "tau_field": r1["tau_field"],
                "block_i": bloques[i], "block_j": bloques[j],
                "dw_constitucional": abs(float(va["omega_ref"]) - float(vb["omega_ref"])),
                "dw_efectivo": (abs(fi - fj) if fi is not None and fj is not None else ""),
                "compat_bandas": compat.get((r1["eval_id"], i, j), ""),
                "rw_final": p["rw_final"], "frac95": p["frac_sobre_0.95"],
                "t_lock95_ut": p["t_lock"]["0.95"] or "",
                "rw_final_fresh": pf["rw_final"],
                "coqueteo_eps": cq.get("n_episodios", ""),
                "coqueteo_durmax_ut": cq.get("dur_max_ut", ""),
                "coqueteo_frac": cq.get("frac_total", ""),
                "coqueteo_fresh_eps": (cq.get("fresh") or {}).get("n_episodios", ""),
                "p_edge_mediana": (fr.get("p_edge_percentiles") or ["", "", ""])[2],
                "p_edge_ini10": fr.get("p_edge_primeras_10ut", ""),
                "p_edge_fin10": fr.get("p_edge_ultimas_10ut", ""),
                "E0_i": r1["apagado"][i]["E0"], "E0_j": r1["apagado"][j]["E0"],
            })
            if p["rw_final"] >= 0.8:
                trabados[i] = max(trabados.get(i, 0.0), p["rw_final"])
                trabados[j] = max(trabados.get(j, 0.0), p["rw_final"])
        for jn, bloque in bloques.items():
            v = vidas[bloque]
            ap = r1["apagado"][jn]
            filas_n.append({
                "eval_id": r1["eval_id"], "nodo": jn, "block_id": bloque,
                "dof_grade": grados.get(bloque, ""),
                "kappa": r1["kappa_global"], "tau_field": r1["tau_field"],
                "n_nodos": r1["topologia"]["n"], "n_aristas": r1["topologia"]["aristas"],
                "E0": ap["E0"], "t_mitad_ut": ap["t_mitad"] or "",
                "t_decimo_ut": ap["t_decimo"] or "", "E_final_W": ap["E_final_W"],
                "r_int_ini": r1["interno"][jn]["r_ini_5ut"],
                "r_int_final": r1["interno"][jn]["r_final_W"],
                "freq_ef_temprana": frecs[jn]["temprana"] or "",
                "freq_ef_tardia": frecs[jn]["tardia"] or "",
                "freq_ef_fresh": frecs[jn]["fresh_temprana"] or "",
                "rw_max_de_sus_aristas": trabados.get(jn, 0.0),
                **{f"vida_{c}": v.get(c) for c in VIDA_CAMPOS},
                "vida_r_intra_final": v["r_intra_final_vida"],
            })

    for nombre, filas in (("tabla_aristas.csv", filas_a), ("tabla_nodos.csv", filas_n)):
        with open(OUT / nombre, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
            w.writeheader()
            w.writerows(filas)
        print(f"[tabla] {nombre}: {len(filas)} filas × {len(filas[0])} columnas")
    resumen = {"aristas": len(filas_a), "nodos": len(filas_n),
               "columnas_aristas": list(filas_a[0].keys()),
               "columnas_nodos": list(filas_n[0].keys())}
    (OUT / "_tabla_resumen.json").write_text(json.dumps(resumen, indent=1))


if __name__ == "__main__":
    main()
