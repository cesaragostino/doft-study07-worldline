"""LIMPIEZA FINAL [GO de COA 2026-08-02 «dejar la cocina limpia»] — patrón GO §2:
re-verificación INDEPENDIENTE sha-por-sha contra el archivo externo ANTES de cada rm;
marcador LIBERADO.json; papeles (SPEC/REPORTE/LEDGER/lecturas) quedan locales.
Libera: census olaB_sub4 + lote_suelto_120 + film_largo_600 + cirugía (4 fases)."""
import hashlib
import json
import shutil
from pathlib import Path

STUDY07 = Path(__file__).resolve().parents[1]
EXT = Path("/Volumes/ExternalDisk")

PARES = [
    (STUDY07 / "data/census_arnold/olaB_sub4", EXT / "study07_census_arnold/olaB_sub4"),
    (STUDY07 / "data/lote_suelto_120/lote", EXT / "study07_lote_suelto_120"),
    (STUDY07 / "data/film_largo_600/lote", EXT / "study07_film_largo_600"),
    (STUDY07 / "data/cirugia/fase0", EXT / "study07_cirugia_linea_fija/fase0"),
    (STUDY07 / "data/cirugia/fase1_fijas", EXT / "study07_cirugia_linea_fija/fase1_fijas"),
    (STUDY07 / "data/cirugia/fase1A", EXT / "study07_cirugia_linea_fija/fase1A"),
    (STUDY07 / "data/cirugia/fase1E", EXT / "study07_cirugia_linea_fija/fase1E"),
]


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def liberar(base: Path, destino: Path) -> None:
    if (base / "LIBERADO.json").exists() or not (base / "unidades").exists():
        print(f"[limpieza] {base.name}: nada que liberar", flush=True)
        return
    if not (base / "REPORTE.json").exists():
        raise RuntimeError(f"{base}: sin REPORTE — no se libera un lote a medias")
    if not (destino / "ARCHIVADO.json").exists():
        raise RuntimeError(f"{destino}: archivo no sellado — NO SE BORRA NADA")
    verificados = 0
    subs = [s for s in ("unidades", "views") if (base / s).exists()]
    for sub in subs:
        for p in sorted((base / sub).rglob("*")):
            if not p.is_file():
                continue
            q = destino / p.relative_to(base)
            if not q.exists() or _sha(p) != _sha(q):
                raise RuntimeError(f"{base.name}: {p.relative_to(base)} difiere o falta "
                                   "en el archivo — NO SE BORRA NADA (fail-loud)")
            verificados += 1
    for sub in subs:
        shutil.rmtree(base / sub, ignore_errors=False)
    (base / "LIBERADO.json").write_text(json.dumps(
        {"go": "COA 2026-08-02 (limpieza final, bitacora §16; patron GO §2)",
         "destino": str(destino), "archivos_reverificados_sha256": verificados,
         "borrado": subs, "papeles_locales": "SPEC/REPORTE/LEDGER/lecturas"}, indent=1))
    print(f"[limpieza] {base.name}: liberado tras re-verificar {verificados} archivos",
          flush=True)


if __name__ == "__main__":
    for base, destino in PARES:
        liberar(base, destino)
    libre = shutil.disk_usage(STUDY07).free / 1e9
    print(f"[limpieza] COMPLETA — libre local: {libre:.0f} GB", flush=True)
