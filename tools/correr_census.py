"""RUNNER del primer CENSUS [M2] — corre las dos campañas prerregistradas (transported +
fresh, 150 unidades c/u) secuencialmente en UN batch (un nohup), con 12 workers spawn,
checkpoints cada 50k, archivado atómico verificado al disco externo al cierre de cada una.

GO de COA condicionado al arbitraje de M1-P1 contra el oráculo (0.0 exacto) — este runner
NO se lanza sin ese veredicto limpio. El rendimiento (NO-determinista) va a
RENDIMIENTO.json, fuera de la identidad de la campaña.
"""
import json
import time
from pathlib import Path

import sys
STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

from study07.artifacts.campana import correr_campana                    # noqa: E402

CAMPANAS = ("census01_par_transported", "census01_par_fresh")
WORKERS = 12
EXTERNO = Path("/Volumes/ExternalDisk/doft-study07-worldline/corridas")


def main():
    inv = json.loads((STUDY07 / "data/inventario_v4.json").read_text())
    inv_sha = (STUDY07 / "data/inventario_v4.sha256").read_text().split()[0]
    inventario = {"sha256": inv_sha,
                  "block_ids": [p["block_id"] for p in inv["poblacion"]],
                  "genome_hash_por_block": {p["block_id"]: p["genome_hash"]
                                            for p in inv["poblacion"]}}
    hashes_base = {"inventario_v4": inv_sha,
                   "blocks_canonical": inv["base"]["blocks_sha256"]}
    rendimiento = {}
    for nombre in CAMPANAS:
        spec = json.loads((STUDY07 / "docs/prereg" / f"{nombre}.json").read_text())
        base = STUDY07 / "data/corridas" / nombre
        t0 = time.time()
        print(f"[census] ── {nombre}: {len(spec['unidades'])} unidades, "
              f"{WORKERS} workers ──", flush=True)
        ledger = correr_campana(spec, base, inventario=inventario,
                                hashes_base=hashes_base, workers=WORKERS,
                                checkpoint_every=50000,
                                archivar_en=EXTERNO / nombre)
        dur = time.time() - t0
        rendimiento[nombre] = {"duracion_s": round(dur, 1),
                               "unidades": ledger["n_unidades"],
                               "reusadas": ledger["reusadas"],
                               "fallidas": ledger["fallidas"],
                               "completa": ledger["completa"]}
        print(f"[census] {nombre}: completa={ledger['completa']} "
              f"fallidas={len(ledger['fallidas'])} en {dur / 3600:.2f} h — "
              f"ledger {ledger['spec_sha256'][:12]}, archivada y verificada", flush=True)
    (STUDY07 / "data/corridas/RENDIMIENTO_census01.json").write_text(
        json.dumps(rendimiento, indent=1))
    print("[census] BATCH COMPLETO", flush=True)


if __name__ == "__main__":
    main()
