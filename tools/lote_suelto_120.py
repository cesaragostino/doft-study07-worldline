"""LOTE SUELTO 120 u.t. [M1, prereg bitácora 2026-08-01 §15] — des-censura del tap de bandas.

Recomendado por el juez del tap wf_cf84918d (audit/DOUBLETAP_BANDAS_*, sección «lote
suelto»); GO de COA 2026-08-01 («tenemos CPU, correlo ahora... mientras no choquen los
datos ni los registros»). CUATRO reruns del brazo transported de tanda 1, MISMA composición
/seed/física (dt=8e-5, κ=0.3, τ=0.2, T=0), SOLO ticks 750k→1.5M (60→120 u.t.):
  · s120_par134: ¿sobrevive tras cruzar entera su banda [32.89,33.61]? (predicción central)
  · s120_par132: des-censura el único negativo del líder fuerte (ρ_Q1 cerró 1.05 SUBIENDO)
  · s120_par129: la captura tardía del líder débil (consolidó @54.25, a 5.75 del corte)
  · s120_par131: el borderline disipativo del líder débil
Lectura SELLADA en §15 (criterios (a)-(d) del juez, verbatim del veredicto) ANTES de esto.
NO CHOCA con census: dir local propio (data/lote_suelto_120), archivo externo propio
(study07_lote_suelto_120), run_ids prefijados s120_, 4 workers (census usa 8 de 16 cores).
Control de determinismo pre-registrado: el prefijo de 750k ticks debe ser BIT-EXACTO
contra el film archivado de tanda 1 (T=0, misma seed) — si difiere, TODO el lote se frena.
"""
import json
import shutil
import sys
import time
from pathlib import Path

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
OUT = STUDY07 / "data/lote_suelto_120"
ARCHIVO = Path("/Volumes/ExternalDisk/study07_lote_suelto_120")

QUIERO = ("par134_t", "par132_t", "par129_t", "par131_t")
TICKS_120 = 1500000


def construir_spec() -> dict:
    base = json.loads((STUDY07 / "data/census_arnold/lote1/SPEC.json").read_text())
    unidades = []
    for u in base["unidades"]:
        if "_".join(u["run_id"].split("_")[:2]) not in QUIERO:
            continue
        v = json.loads(json.dumps(u))          # copia profunda, TODO idéntico salvo:
        v["run_id"] = "s120_" + u["run_id"]
        v["ticks"] = TICKS_120
        v["rerun_de"] = {"campana": base["campana"], "run_id": u["run_id"],
                         "ticks_orig": u["ticks"],
                         "control": "prefijo 750k bit-exacto vs film archivado"}
        unidades.append(v)
    assert len(unidades) == 4, f"esperaba 4 unidades, hay {len(unidades)}"
    orden = ("par134", "par132", "par129", "par131")   # central primero (cosmético: 4 workers)
    unidades.sort(key=lambda v: orden.index(v["run_id"].split("_")[1]))
    return {
        "spec_tipo": "M1",
        "campana": "lote_suelto_120ut",
        "porque": ("des-censurar los 4 puntos que la regla de estabilidad necesita (tap "
                   "wf_cf84918d): supervivencia post-cruce de par134, el negativo censurado "
                   "par132 (rho_Q1 1.05 subiendo al corte), la captura tardia par129 y el "
                   "borderline par131 — lectura sellada en bitacora 2026-08-01 §15"),
        "retencion": base["retencion"],
        "horizonte_emergencia_ticks": base["horizonte_emergencia_ticks"],
        "reglas_clasificacion": {
            "instrumento": "detectores etapa-2 pre-registrados (audit/DOUBLETAP_BANDAS, 8 puntos)",
            "outcomes": ["(a) SOBREVIVE: rho_j>1 sostenido en [t_salida+2,120], slip<0.1/u.t., 3 Q",
                         "(b) RELEASE tipo par132: rho<1 sostenido >=2 u.t. en [t_salida,+8], >=2 slips/5 u.t.",
                         "(c) t_salida leido del film (primer t con omega_L formula >33.61; extrap juez ~63)",
                         "(d) secundarios: pico S1 en cruce (lag 0-2 pred.), t_cap(u) re-captura, "
                         "b_Q + split multiplete del seguidor (discriminador del puente)",
                         "tercer desenlace se declara como tal"],
            "umbrales": "sellados PRE-corrida en veredicto wf_cf84918d + §15; re-medicion = outcome"},
        "seed_politica": "IDENTICA a tanda 1 (prefijo 750k bit-exacto = control de determinismo)",
        "unidades": unidades,
    }


def main():
    import hashlib
    from study07.artifacts.campana import correr_campana
    spec = construir_spec()
    OUT.mkdir(parents=True, exist_ok=True)
    cuerpo = json.dumps(spec, indent=1)
    (OUT / "SPEC_suelto120.json").write_text(cuerpo)
    sha = hashlib.sha256(cuerpo.encode()).hexdigest()
    (OUT / "SPEC_suelto120.sha256").write_text(sha + "  SPEC_suelto120.json\n")
    print(f"[suelto120] SPEC sellada sha={sha[:16]} · 4 unidades × {TICKS_120} ticks", flush=True)

    inv_sha = (STUDY07 / "data/inventario_v4.sha256").read_text().split()[0]
    blocks = (Path.home() / "code/doft-study06-fundamental-lock-dynamics"
              / "data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json")
    hashes_base = {"inventario_v4": inv_sha,
                   "blocks_canonical": hashlib.sha256(blocks.read_bytes()).hexdigest(),
                   "spec_lote1_origen": hashlib.sha256(
                       (STUDY07 / "data/census_arnold/lote1/SPEC.json").read_bytes()).hexdigest()}
    base = OUT / "lote"
    if (base / "REPORTE.json").exists():
        print("[suelto120] REPORTE ya existe — nada que hacer", flush=True)
        return
    t0 = time.time()
    print(f"[suelto120] arrancando 4 workers (libre local: "
          f"{shutil.disk_usage(OUT).free / 1e9:.0f} GB)", flush=True)
    reporte = correr_campana(spec, base, hashes_base=hashes_base, workers=4,
                             archivar_en=ARCHIVO)
    (base / "REPORTE.json").write_text(json.dumps(reporte, indent=1, default=str))
    print(f"[suelto120] TERMINADO en {(time.time()-t0)/3600:.2f} h", flush=True)


if __name__ == "__main__":
    main()
