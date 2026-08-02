"""LECTURA OFFLINE de la TANDA 2 del census [M1, prereg §1+§4 + DISENO_OLA_B sellado].

Instrumento: par_link v1.1 (el MISMO pre-registrado y usado en tanda 1 — la lectura del
census NO cambia de instrumento a mitad de camino; el lector v2/§5 se aplica en la capa
de INFERENCIA como covariables/semántica declarada, no acá). W=4 y W=8 por unidad.
Fuentes: olaB_sub1..3 desde el ARCHIVO EXTERNO verificado (liberados localmente, GO §2);
olaB_sub4 desde local (mismo contenido, archivado+verificado — declarado). Views locales
en views_tanda2/. Paralelo con 8 procesos (lectura pura, films read-only).
Fila por unidad: mismo esquema que tabla_tanda1.json + metadata prereg de ola B
(dw_fina_prereg, sigma_dw_prereg, self_par, celda κ/τ, ticks/horizonte).
Semántica §5 DECLARADA para la capa de inferencia: ρ/estados de par v1.1 miden DOMINANCIA
ESPECTRAL CONDICIONADA AL DRIVE, no supervivencia energética; el lock a horizonte es
CENSURADO (sellado C3) y ahora se sabe que el reloj del líder va y vuelve (§4).
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
ARCHIVO = Path("/Volumes/ExternalDisk/study07_census_arnold")
OUT = STUDY07 / "data/census_arnold"
VIEWS = OUT / "views_tanda2"

LOTES = {"olaB_sub1": ARCHIVO / "olaB_sub1", "olaB_sub2": ARCHIVO / "olaB_sub2",
         "olaB_sub3": ARCHIVO / "olaB_sub3", "olaB_sub4": OUT / "olaB_sub4"}


def _leer_unidad(args):
    lote, run_dir_s, meta = args
    import numpy as np
    from study07.instruments import api, par
    run_dir = Path(run_dir_s)
    wl = api.load_run(run_dir)
    fila = {"run_id": meta["run_id"], "lote": lote,
            "brazo": meta["run_id"].split("_")[2],
            "par_idx": int(meta["run_id"].split("_")[1].replace("par", "")),
            "celda": meta["run_id"].split("_", 3)[3],
            "dw_fina_prereg": meta.get("dw_fina_prereg"),
            "sigma_dw_prereg": meta.get("sigma_dw_prereg"),
            "self_par": meta.get("self_par", False),
            "ticks": meta["ticks"], "seed": meta["seed"],
            "block_i": meta["constituyentes"][0]["block_id"],
            "block_j": meta["constituyentes"][1]["block_id"]}
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
    del wl
    return fila


def main():
    VIEWS.mkdir(parents=True, exist_ok=True)
    trabajos = []
    for lote, base in LOTES.items():
        spec = json.loads((base / "SPEC.json").read_text())
        meta_u = {u["run_id"]: u for u in spec["unidades"]}
        for run_dir in sorted((base / "unidades").iterdir()):
            if not (run_dir / "COMPLETE").exists():
                print(f"[AVISO] {run_dir.name}: sin COMPLETE — salteada", flush=True)
                continue
            rid = run_dir.name
            # run_id = nombre del dir (convención campana)
            if rid not in meta_u:
                raise SystemExit(f"{lote}/{rid}: no está en SPEC — se frena")
            trabajos.append((lote, str(run_dir), meta_u[rid]))
    print(f"[tanda2] {len(trabajos)} unidades a leer (8 procesos)", flush=True)
    t0 = time.time()
    filas = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for k, fila in enumerate(ex.map(_leer_unidad, trabajos, chunksize=1)):
            filas.append(fila)
            if (k + 1) % 15 == 0:
                print(f"[{k+1}/{len(trabajos)}] {time.time()-t0:.0f}s", flush=True)
    filas.sort(key=lambda f: f["run_id"])
    (OUT / "tabla_tanda2.json").write_text(json.dumps(filas, indent=1))
    print(f"[fin] {len(filas)} unidades en {time.time()-t0:.0f}s → tabla_tanda2.json",
          flush=True)
    import collections
    for et in ("W4", "W8"):
        for brazo in ("t", "f"):
            c = collections.Counter(f[et]["estado"] for f in filas
                                    if f["brazo"] == brazo and f["celda"] == "k03_tau02")
            print(f"  {et} brazo {brazo} (celda ppal): " +
                  " ".join(f"{n}={c.get(cod, 0)}" for cod, n in
                           ((2, 'firme'), (1, 'coqueteo'), (0, 'muerto'), (3, 'mudo'))),
                  flush=True)


if __name__ == "__main__":
    main()
