"""LECTURA OFFLINE de la TANDA 1 del census [M1, prereg §1+§4] — par_link v1.1.

Films: archivo externo (read-only) study07_census_arnold/lote1/unidades/*. Vistas: locales
(data/census_arnold/views_tanda1/) — JAMÁS se escribe dentro del archivo.
Por unidad: par.run con W=4 (default declarado) y W=8 (robustez primaria §3) → fila con
estado/rw/t_lock/episodios/pulling/mudos/armónicos + metadata del prereg (dw_fina, brazo).
Des-enmascaramiento PARCIAL declarado (bitácora): tanda 2 sellada antes de esta lectura.
"""
import json
import time
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(STUDY07 / "src"))
ARCHIVO = Path("/Volumes/ExternalDisk/study07_census_arnold/lote1")
OUT = STUDY07 / "data/census_arnold"
VIEWS = OUT / "views_tanda1"


def main():
    from study07.instruments import api, par
    spec = json.loads((ARCHIVO / "SPEC.json").read_text())
    meta_u = {u["run_id"]: u for u in spec["unidades"]}
    filas = []
    t0 = time.time()
    unidades = sorted((ARCHIVO / "unidades").iterdir())
    for k, run_dir in enumerate(unidades):
        if not (run_dir / "COMPLETE").exists():
            continue
        wl = api.load_run(run_dir)
        u = meta_u[wl["manifest"]["run_id"]]
        fila = {"run_id": u["run_id"], "brazo": u["run_id"].split("_")[1],
                "par_idx": int(u["run_id"].split("_")[0].replace("par", "")),
                "dw_fina": None, "seed": u["seed"], "ticks": u["ticks"]}
        # dw fino desde la selección sellada (dw_fino_seleccion.json, clave por bloques)
        bi = u["constituyentes"][0]["block_id"]; bj = u["constituyentes"][1]["block_id"]
        fila["block_i"], fila["block_j"] = bi, bj
        for w_ut in (4.0, 8.0):
            v = par.run(wl, {"w_ut": w_ut})
            v.write(VIEWS)
            et = f"W{int(w_ut)}"
            fila[et] = {
                "estado": int(v.arrays["estado"][0]),
                "rw_final": float(v.arrays["rw_final"][0]),
                "rw_max": float(v.arrays["rw_max"][0]),
                "t_lock_ut": (None if np.isnan(v.arrays["t_lock_ut"][0])
                              else float(v.arrays["t_lock_ut"][0])),
                "episodios": int(v.arrays["episodios"][0]),
                "dur_max_ut": float(v.arrays["dur_max_ut"][0]),
                "frac_coqueteo": float(v.arrays["frac_coqueteo"][0]),
                "dw_temprana": float(v.arrays["dw_temprana"][0]),
                "dw_tardia": float(v.arrays["dw_tardia"][0]),
                "nodos_mudos": v.manifest["nodos_mudos"],
                "nodos_armonico": v.manifest["nodos_armonico"],
            }
        filas.append(fila)
        if (k + 1) % 15 == 0:
            print(f"[{k+1}/{len(unidades)}] {time.time()-t0:.0f}s", flush=True)
    dwf = json.loads((OUT / "dw_fino_seleccion.json").read_text())
    por_bloques = {}
    for v in dwf.values():
        por_bloques[frozenset((v["block_i"], v["block_j"]))] = v["dw_fina"]
    for f in filas:
        f["dw_fina"] = por_bloques.get(frozenset((f["block_i"], f["block_j"])))
    (OUT / "tabla_tanda1.json").write_text(json.dumps(filas, indent=1))
    print(f"[fin] {len(filas)} unidades leídas en {time.time()-t0:.0f}s → tabla_tanda1.json")
    # resumen crudo (sin inferencia): conteo de estados por W y por brazo
    import collections
    for et in ("W4", "W8"):
        for brazo in ("t", "f"):
            c = collections.Counter(f[et]["estado"] for f in filas if f["brazo"] == brazo)
            print(f"  {et} brazo {brazo}: " +
                  " ".join(f"{n}={c.get(cod,0)}" for cod, n in
                           ((2, 'firme'), (1, 'coqueteo'), (0, 'muerto'), (3, 'mudo'))))


if __name__ == "__main__":
    main()
