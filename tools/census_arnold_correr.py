"""CENSUS ARNOLD — runner de lotes [M1]. Un nohup por batch (protocolo).

Corre los SPEC_lote*.json en orden, salteando los que ya tienen REPORTE.json. Cada lote:
correr_campana (workers=8, spawn) → archivo ATÓMICO VERIFICADO al disco externo → REPORTE
→ LIBERACIÓN local de unidades/ y views/ (GO EXPLÍCITO de COA 2026-08-01, bitácora §2;
patrón §93-e): re-verificación INDEPENDIENTE sha-por-sha contra el archivo ANTES del rm,
marcador LIBERADO.json con el conteo. Los papeles (SPEC/REPORTE/ledger) quedan locales."""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
OUT = STUDY07 / "data/census_arnold"
ARCHIVO = Path("/Volumes/ExternalDisk/study07_census_arnold")


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def liberar_lote(base: Path, destino: Path) -> None:
    """Libera unidades/ y views/ de un lote YA archivado: re-verifica INDEPENDIENTE
    sha-por-sha (no confía en la verificación del archivado) y recién ahí borra.
    GO de COA 2026-08-01 (§2). Fail-loud ante cualquier discrepancia."""
    if (base / "LIBERADO.json").exists() or not (base / "unidades").exists():
        return
    if not (base / "REPORTE.json").exists():
        raise RuntimeError(f"liberar {base.name}: sin REPORTE — no se libera un lote a medias")
    if not (destino / "ARCHIVADO.json").exists():
        raise RuntimeError(f"liberar {base.name}: el archivo {destino} no está sellado")
    verificados = 0
    for sub in ("unidades", "views"):
        for p in sorted((base / sub).rglob("*")):
            if not p.is_file():
                continue
            q = destino / p.relative_to(base)
            if not q.exists() or _sha(p) != _sha(q):
                raise RuntimeError(f"liberar {base.name}: {p.relative_to(base)} difiere o "
                                   "falta en el archivo — NO SE BORRA NADA (fail-loud)")
            verificados += 1
    for sub in ("unidades", "views"):
        shutil.rmtree(base / sub, ignore_errors=False)
    (base / "LIBERADO.json").write_text(json.dumps(
        {"go": "COA 2026-08-01 (bitacora 2026-08-01 §2)", "destino": str(destino),
         "archivos_reverificados_sha256": verificados,
         "borrado": ["unidades/", "views/"], "papeles_locales": "SPEC/REPORTE/ledger"},
        indent=1))
    print(f"[census] {base.name}: liberado local tras re-verificar {verificados} archivos",
          flush=True)


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
    # COLA post-tap de diseño (wf_4d2144d4): lote1 (ola A) → ola B sub1..4.
    # lote2/lote3 SUPERSEDIDOS via centinelas REPORTE.json (C1) — no aparecen acá.
    cola = [("SPEC_lote1.json", "lote1")] + \
           [(f"SPEC_olaB_sub{s}.json", f"olaB_sub{s}") for s in (1, 2, 3, 4)]
    for k, (spec_nombre, nombre) in enumerate(cola):
        spec_p = OUT / spec_nombre
        base = OUT / nombre
        # liberar lotes ANTERIORES ya archivados (GO COA §2) antes del preflight de éste
        for _, previo in cola[:k]:
            liberar_lote(OUT / previo, ARCHIVO / previo)
        if (base / "REPORTE.json").exists():
            print(f"[census] {nombre}: REPORTE ya existe — salteado", flush=True)
            continue
        spec = json.loads(spec_p.read_text())
        t0 = time.time()
        print(f"[census] {nombre}: {len(spec['unidades'])} unidades, arrancando "
              f"(libre local: {shutil.disk_usage(OUT).free / 1e9:.0f} GB)", flush=True)
        try:
            reporte = correr_campana(spec, base, hashes_base=hashes_base, workers=8,
                                     archivar_en=ARCHIVO / nombre)
        except RuntimeError as exc:
            if "preflight" in str(exc):
                print(f"[census] {nombre} BLOQUEADO por disco: {exc}\n"
                      "[census] PARO LIMPIO — liberar local = archivo verificado + GO de "
                      "COA; relanzar este runner después", flush=True)
                return
            raise
        (base / "REPORTE.json").write_text(json.dumps(reporte, indent=1, default=str))
        completas = sum(1 for f in reporte.get("filas", reporte.get("unidades", []))
                        if (f.get("estado") == "completa")) if isinstance(reporte, dict) else "?"
        print(f"[census] {nombre} TERMINADO en {(time.time()-t0)/3600:.1f} h — "
              f"completas: {completas}", flush=True)
    print("[census] todos los lotes procesados", flush=True)


if __name__ == "__main__":
    main()
