"""JUEZ — extraccion propia via load_run (verificacion completa de worldline, sin atajos).
Guarda x por nodo, b por nodo, capas, dt efectivo. Stride 10 (dt_s=8e-4)."""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, "/Users/cagostino/code/doft-study07-worldline/src")
from study07.instruments.api import load_run

BASE = Path("/Volumes/ExternalDisk/study07_census_arnold/lote1/unidades")
OUT = Path(__file__).parent
STRIDE = 10

UNITS = ["par132_t", "par133_t", "par134_t",
         "par126_t", "par127_t", "par128_t", "par129_t", "par130_t", "par131_t",
         "par133_f", "par134_f"]

for u in UNITS:
    dest = OUT / f"{u}_jz.npz"
    if dest.exists():
        print(u, "ya extraido", flush=True); continue
    wl = load_run(BASE / f"{u}_k03_tau02")
    man = wl["manifest"]
    arrays = {"dt_s": np.array(float(man["dt"]) * STRIDE)}
    for j, nd in enumerate(man["por_nodo"]):
        nm, nz, nl = nd["n_modes"], nd["n_z"], nd["n_layers"]
        est = wl["estados"][j]
        arrays[f"x{j}"] = est[::STRIDE, :nm].astype(np.float64)
        arrays[f"b{j}"] = est[::STRIDE, 2 * nm + nz: 2 * nm + nz + nl].astype(np.float64)
        arrays[f"capas{j}"] = np.array(nd["capas_por_modo"])
    np.savez_compressed(dest, **arrays)
    print(u, "ok", wl["worldline_hash"][:12], len(wl["ticks"]), "ticks", flush=True)
    del wl
print("EXTRACCION DONE")
