"""INVENTARIO v4 — el explorer como productor de inventario (EXPERIMENT_CONTRACT, F5).

Recorre READ-ONLY la base v4 del oráculo (data/processed/ola1_v4_c1/ola1) y produce
data/inventario_v4.json: la identificación COMPLETA de la población (150 especímenes) con
hashes por artefacto — la fuente de `hashes_base_externa` de toda corrida F5+ y el catálogo
que una spec [M2] futura debe citar por hash (una población parcial NO es un censo).

Verificación TRIPLE del genoma por espécimen (la conformidad de la transcripción):
  manifest.genome_hash == genome_sha256_ORACULO(theta) == genome_sha256_STUDY07(theta)
y carga COMPLETA de cada cápsula con el lector de study07 (invariante de emisión incluido).
Cruces fail-loud: cápsulas ↔ dof_dna_catalog_by_block_id.csv ↔ simple_blocks_canonical.json ↔
runs_full.jsonl (0 duplicados, 0 huérfanos, run_idx consistente).

Es HERRAMIENTA (tools/): puede importar el oráculo. Fase 0.3: cero escrituras allá.
"""
import csv
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
sys.path.insert(0, str(ORACLE / "src"))
sys.path.insert(0, str(STUDY07 / "src"))

from paper5.olar.specimen_capsule import genome_sha256 as genome_oraculo  # noqa: E402
from study07.compat.study06_capsule import genome_sha256 as genome_study07  # noqa: E402
from study07.compat.study06_capsule import load_capsule  # noqa: E402

BASE = ORACLE / "data/processed/ola1_v4_c1/ola1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    raw = json.load(open(BASE / "simple_blocks_canonical.json"))
    blocks = {b["block_id"]: b for b in (raw["blocks"] if "blocks" in raw else raw)}
    with open(BASE / "dof_dna_catalog_by_block_id.csv") as f:
        catalogo = list(csv.DictReader(f))
    if "block_id" not in catalogo[0]:
        raise SystemExit("catálogo sin columna block_id: el cruce no puede adivinar la "
                         "columna (double tap F5 — el fallback silencioso era mentira)")
    bids_catalogo = {row["block_id"] for row in catalogo}
    bids_runs = set()
    with open(BASE / "runs_full.jsonl") as f:
        for linea in f:
            bids_runs.add(json.loads(linea)["block_id"])

    poblacion = []
    dirs = sorted((BASE / "specimen_capsules").glob("run_*"))
    for d in dirs:
        partes = d.name.split("_", 2)
        run_idx, bid = int(partes[1]), partes[2]
        cap = load_capsule(d)                    # verificación COMPLETA del lector study07
        man = cap["manifest"]
        if man["block_id"] != bid:
            raise SystemExit(f"{d.name}: block_id del manifiesto != dirname")
        if int(man["lineage"].get("run_idx", -1)) != run_idx:
            raise SystemExit(f"{d.name}: lineage.run_idx != dirname")
        theta = blocks[bid]["theta_internal"]
        g_orac = genome_oraculo(theta)
        g_s07 = genome_study07(theta)
        if not (man["genome_hash"] == g_orac == g_s07):
            raise SystemExit(f"{d.name}: genoma NO verifica triple — manifiesto "
                             f"{man['genome_hash'][:19]} oraculo {g_orac[:19]} "
                             f"study07 {g_s07[:19]}")
        eng = man["engine_contract"]
        poblacion.append({
            "run_idx": run_idx, "block_id": bid, "dir": d.name,
            "specimen_id": man["specimen_id"], "genome_hash": man["genome_hash"],
            "capsule_sha256": cap["capsule_sha256"],
            "state_npz_sha256": f"sha256:{sha(d / 'state.npz')}",
            "state_content_sha256": man["state_artifact"]["content_sha256"],
            "passport_sha256": f"sha256:{sha(d / 'passport.json')}",
            "n_modes": int(cap["arrays"]["x"].size), "n_z": int(cap["arrays"]["z"].size),
            "n_layers": int(cap["arrays"]["b"].size),
            "dt": float(eng["dt"]), "delay_steps": int(eng["delay_steps"]),
            "emission_scale": float(eng["emission_scale"]),
            "harvest_tick": int(man["source"]["harvest_tick"]),
        })

    bids_caps = [p["block_id"] for p in poblacion]
    assert len(poblacion) == 150, f"población {len(poblacion)} != 150"
    assert len(set(bids_caps)) == 150, "block_ids duplicados en cápsulas"
    assert set(bids_caps) == set(blocks) == bids_catalogo == bids_runs, (
        "cruce de poblaciones FALLA: capsulas/blocks/catalogo/runs no coinciden")

    def _git(repo, *args):
        return subprocess.run(["git", *args], cwd=repo,
                              capture_output=True, text=True).stdout.strip()
    oracle_commit = _git(ORACLE, "rev-parse", "--short", "HEAD")
    oracle_dirty = bool(_git(ORACLE, "status", "--porcelain"))
    # el tag se MIDE, no se asume («asumir números es asumir física» — double tap F5 A8:
    # el tag del freeze apunta a un ancestro del HEAD, no al HEAD)
    tags_head = [t for t in _git(ORACLE, "tag", "--points-at", "HEAD").splitlines() if t]
    inventario = {
        "schema": "study07_inventario_v4_v1",
        "base": {"ruta": "data/processed/ola1_v4_c1/ola1 (repo congelado del oraculo)",
                 "oracle_commit": oracle_commit, "oracle_dirty": oracle_dirty,
                 "oracle_tags_en_head": tags_head,
                 "study07_commit": _git(STUDY07, "rev-parse", "--short", "HEAD"),
                 "study07_dirty": bool(_git(STUDY07, "status", "--porcelain")),
                 "blocks_sha256": sha(BASE / "simple_blocks_canonical.json"),
                 "catalogo_by_block_sha256": sha(BASE / "dof_dna_catalog_by_block_id.csv"),
                 "catalogo_sha256": sha(BASE / "dof_dna_catalog.csv"),
                 "runs_full_sha256": sha(BASE / "runs_full.jsonl"),
                 "manifest_sha256": sha(BASE / "ola1_olar_manifest.json")},
        "verificacion": {
            "n": len(poblacion), "block_ids_unicos": len(set(bids_caps)),
            "cruce_capsulas_blocks_catalogo_runs": "150/150 identicos, 0 huerfanos, 0 dup",
            "genoma_triple": "150/150 manifiesto==oraculo==study07 (transcripcion conforme)",
            "lector_study07": "150/150 cargas completas (hashes, invariante de emision, "
                              "specimen_id recomputado)"},
        "entorno": {"numpy": np.__version__, "python": platform.python_version(),
                    "machine": platform.machine()},
        "poblacion": sorted(poblacion, key=lambda p: p["run_idx"]),
    }
    out = STUDY07 / "data/inventario_v4.json"
    out.parent.mkdir(exist_ok=True)
    cuerpo = json.dumps(inventario, indent=1)
    out.write_text(cuerpo)
    s = hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()
    (STUDY07 / "data/inventario_v4.sha256").write_text(f"{s}  data/inventario_v4.json\n")
    print(f"[inventario] {len(poblacion)} especimenes · genoma triple 150/150 · "
          f"blocks={inventario['base']['blocks_sha256'][:16]} · sha={s[:16]}")


if __name__ == "__main__":
    main()
