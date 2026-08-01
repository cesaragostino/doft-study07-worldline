"""CENSUS ARNOLD — runner de lotes [M1]. Un nohup por batch (protocolo).

Corre los SPEC_lote*.json en orden, salteando los que ya tienen REPORTE.json. Cada lote:
correr_campana (workers=8, spawn) → archivo ATÓMICO VERIFICADO al disco externo → REPORTE.
Si el preflight de disco de un lote no pasa (los films del lote anterior siguen locales),
PARA LIMPIO y lo dice: la liberación local es archivo-verificado + GO de COA, jamás
automática (regla de la casa)."""
import json
import shutil
import sys
import time
from pathlib import Path

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
OUT = STUDY07 / "data/census_arnold"
ARCHIVO = Path("/Volumes/ExternalDisk/study07_census_arnold")


def main():
    import hashlib
    from study07.artifacts.campana import correr_campana
    inv_sha = (STUDY07 / "data/inventario_v4.sha256").read_text().split()[0]
    blocks = (Path.home() / "code/doft-study06-fundamental-lock-dynamics"
              / "data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json")
    hashes_base = {"inventario_v4": inv_sha,
                   "blocks_canonical": hashlib.sha256(blocks.read_bytes()).hexdigest(),
                   "carriers_fft": hashlib.sha256(
                       (OUT / "carriers_fft.json").read_bytes()).hexdigest(),
                   "seleccion": hashlib.sha256(
                       (OUT / "seleccion.json").read_bytes()).hexdigest()}
    for n in (1, 2, 3):
        spec_p = OUT / f"SPEC_lote{n}.json"
        base = OUT / f"lote{n}"
        if (base / "REPORTE.json").exists():
            print(f"[census] lote{n}: REPORTE ya existe — salteado", flush=True)
            continue
        spec = json.loads(spec_p.read_text())
        t0 = time.time()
        print(f"[census] lote{n}: {len(spec['unidades'])} unidades, arrancando "
              f"(libre local: {shutil.disk_usage(OUT).free / 1e9:.0f} GB)", flush=True)
        try:
            reporte = correr_campana(spec, base, hashes_base=hashes_base, workers=8,
                                     archivar_en=ARCHIVO / f"lote{n}")
        except RuntimeError as exc:
            if "preflight" in str(exc):
                print(f"[census] lote{n} BLOQUEADO por disco: {exc}\n"
                      "[census] PARO LIMPIO — liberar local = archivo verificado + GO de "
                      "COA; relanzar este runner después", flush=True)
                return
            raise
        (base / "REPORTE.json").write_text(json.dumps(reporte, indent=1, default=str))
        completas = sum(1 for f in reporte.get("filas", reporte.get("unidades", []))
                        if (f.get("estado") == "completa")) if isinstance(reporte, dict) else "?"
        print(f"[census] lote{n} TERMINADO en {(time.time()-t0)/3600:.1f} h — "
              f"completas: {completas}", flush=True)
    print("[census] todos los lotes procesados", flush=True)


if __name__ == "__main__":
    main()
