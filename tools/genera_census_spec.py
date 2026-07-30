"""Generador de specs de CENSUS [M2] desde el inventario v4 (F7 — cierra el gap del tap:
un census escrito a mano es exactamente la clase de bug que J4/A9 demuestran que nada
atrapa; este generador es la ÚNICA vía prevista para armar la spec de 150 unidades).

Diseño del census parametrizable por CLI-args mínimos; el resultado es una spec
AUTO-CONTENIDA (thetas hidratados de los bloques canónicos del oráculo y verificados contra
el genome_hash del inventario ANTES de embeber; cápsulas pinneadas por el sha del
inventario) que se escribe a docs/prereg/ y DEBE committearse antes de correr (protocolo).

Uso:
  python3 tools/genera_census_spec.py <nombre> <plantilla> <ticks> [companero_block]
  plantillas v1:
    par_transported   — cada individuo: par [individuo CAPSULA + companero CAPSULA fija]
    par_fresh         — cada individuo: par [individuo NACIMIENTO + companero NACIMIENTO]
  (el companero default es la mediana de M1-P1: 92466fe3...)
"""
import json
import sys
from pathlib import Path

STUDY07 = Path(__file__).resolve().parents[1]
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
BASE = ORACLE / "data/processed/ola1_v4_c1/ola1"
sys.path.insert(0, str(STUDY07 / "src"))

from study07.artifacts.campana import sha_json, validar_campana        # noqa: E402
from study07.compat.study06_capsule import genome_sha256               # noqa: E402

COMPANERO_DEFAULT = "92466fe3a8cf6cc3c0e4d778b7ba4256c2593913"
GOLD = "01a53ee2550de1cb5639de63041329a449a902bd"
EDGES = [{"i": 0, "j": 1, "w_k": 1.0, "w_gamma": 1.0, "tau": 0.02}]
ENGINE = {"dt": 8e-05, "temperature": 0.0, "kappa_global": 0.7,
          "coupling_gamma_c": 0.15, "tau_field": 0.0}
SEED = 2026


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    nombre, plantilla, ticks = sys.argv[1], sys.argv[2], int(sys.argv[3])
    companero = sys.argv[4] if len(sys.argv) > 4 else COMPANERO_DEFAULT
    if plantilla not in ("par_transported", "par_fresh"):
        raise SystemExit(f"plantilla desconocida: {plantilla}")

    inv = json.loads((STUDY07 / "data/inventario_v4.json").read_text())
    inv_sha = (STUDY07 / "data/inventario_v4.sha256").read_text().split()[0]
    por_bid = {p["block_id"]: p for p in inv["poblacion"]}
    raw = json.load(open(BASE / "simple_blocks_canonical.json"))
    blocks = {b["block_id"]: b for b in (raw["blocks"] if "blocks" in raw else raw)}

    def constituyente(bid, origen, es_poblacion=False):
        theta = blocks[bid]["theta_internal"]
        g = genome_sha256(theta)
        if g != por_bid[bid]["genome_hash"]:            # verificado ANTES de embeber (A9)
            raise SystemExit(f"{bid[:12]}: genoma del bloque canónico != inventario — "
                             "la base está corrupta o desincronizada")
        c = {"block_id": bid, "theta": theta}
        if origen == "capsula":
            c["capsula_dir"] = str(BASE / "specimen_capsules" / por_bid[bid]["dir"])
            c["capsule_sha256"] = por_bid[bid]["capsule_sha256"]
        if es_poblacion:
            c["es_poblacion"] = True
        return c

    origen = "capsula" if plantilla == "par_transported" else "nacimiento"
    unidades = []
    for p in inv["poblacion"]:                          # inventario COMPLETO, en su orden
        bid = p["block_id"]
        unidades.append({
            "run_id": f"{plantilla}_{p['run_idx']:06d}_{bid[:12]}",
            "constituyentes": [constituyente(bid, origen, es_poblacion=True),
                               constituyente(companero, origen)],
            "edges": EDGES, "engine_params": dict(ENGINE),
            "seed": SEED, "ticks": ticks})
    spec = {
        "campana": nombre, "spec_tipo": "M2",
        "porque": (f"CENSUS [M2] '{nombre}': cada individuo del inventario v4 COMPLETO "
                   f"(150) medido en el par estandarizado ({plantilla}, companero "
                   f"{companero[:12]}, tau=0.02) — las preguntas abiertas de M1-P1 "
                   "(¿t_half del fuego es del individuo?, ¿la obstruccion biografica del "
                   "lock escala con E de capsula?) respondidas sobre la poblacion entera; "
                   "los aburridos son datos."),
        "poblacion_inventario_sha256": inv_sha,
        "unidades": unidades,
        "retencion": {"perfil": "conformidad_completa", "chunk_ticks": 4096},
        "horizonte_emergencia_ticks": ticks,
        "reglas_clasificacion": {
            "metricas": "basicas_v1 (selladas en campana.py, identicas a M1-P1)",
            "fuego": "t_half/t_dec10 primera-cruzada del nodo 0 (el individuo)",
            "lock": "t_lock = R>=0.99 sostenido 1000 ticks; R_final = media ultimo 10%",
            "exclusion": "ningun claim estacionario en los primeros 250 ticks post-quench"},
        "probeta_gold_block_id": GOLD,
        "seed_politica": f"seed unica {SEED} declarada (paridad con M1-P1)"}

    inventario = {"sha256": inv_sha,
                  "block_ids": [p["block_id"] for p in inv["poblacion"]],
                  "genome_hash_por_block": {p["block_id"]: p["genome_hash"]
                                            for p in inv["poblacion"]}}
    validar_campana(spec, inventario)                   # la spec nace VALIDADA
    out = STUDY07 / "docs/prereg" / f"{nombre}.json"
    out.write_text(json.dumps(spec, indent=1))
    print(f"[census] {out.name}: {len(unidades)} unidades ({plantilla}, {ticks} ticks) "
          f"spec_sha={sha_json(spec)[:16]} — VALIDADA contra el inventario. "
          "Committear ANTES de correr.")


if __name__ == "__main__":
    main()
