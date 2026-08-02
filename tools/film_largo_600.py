"""FILM LARGO 600 u.t. [M1, prereg bitácora 2026-08-02 §3] — la medición decisiva del tap.

GO de COA 2026-08-02 («dale GO al film largo en paralelo... la máquina está solo para
esto»). Mandato del juez (wf_cfb44e2e, medición decisiva): par132_t + par134_t a
300-600 u.t. Extensión DECLARADA (cores libres): par129_t + par131_t — des-censura la
migración del líder débil y da el control «drive que se apaga» para P1.
CUATRO reruns transported, MISMA composición/seed/física que s120 (y que tanda 1),
SOLO ticks 1.5M→7.5M (120→600 u.t.). Cadena de determinismo pre-registrada:
prefijo de 1.5M ticks BIT-EXACTO contra los films s120 (que ya verificaron su prefijo
de 750k contra tanda 1): custodia 60→120→600. Lo que decide (sellado en §3):
  (1) P4: b_S1 de par132 PICA ≈0.293 en t≈281 y DECAE (τ_b≈330) — o el modelo
      filtro-que-olvida MUERE (subida monótona sin máximo hasta 600);
  (2) P1: tasa corregida por drive en ventanas estacionarias, ¿converge a |σ|?;
  (3) P3: cobertura de canal v2 / relevos / huecos hasta 600 (des-censura).
NO CHOCA: dir local propio (data/film_largo_600), archivo externo propio
(study07_film_largo_600), run_ids s600_, 4 workers (census usa 8 de 16).
Lector v2 (prescripciones del tap) se escribe y committea ANTES de abrir film alguno.
"""
import json
import shutil
import sys
import time
from pathlib import Path

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
OUT = STUDY07 / "data/film_largo_600"
ARCHIVO = Path("/Volumes/ExternalDisk/study07_film_largo_600")

QUIERO = ("par134_t", "par132_t", "par129_t", "par131_t")
TICKS_600 = 7500000


def construir_spec() -> dict:
    base = json.loads((STUDY07 / "data/lote_suelto_120/SPEC_suelto120.json").read_text())
    unidades = []
    for u in base["unidades"]:
        v = json.loads(json.dumps(u))          # copia profunda, TODO idéntico salvo:
        v["run_id"] = u["run_id"].replace("s120_", "s600_")
        v["ticks"] = TICKS_600
        v["rerun_de"] = {"campana": base["campana"], "run_id": u["run_id"],
                         "ticks_orig": u["ticks"],
                         "control": "prefijo 1.5M bit-exacto vs film s120 (cadena 60-120-600)"}
        unidades.append(v)
    assert len(unidades) == 4, f"esperaba 4 unidades, hay {len(unidades)}"
    assert all("_".join(u["run_id"].split("_")[1:3]) in QUIERO for u in unidades)
    return {
        "spec_tipo": "M1",
        "campana": "film_largo_600ut",
        "porque": ("medicion decisiva del tap wf_cfb44e2e: (1) prediccion falsable de "
                   "biografia (b_S1 par132 pica ~0.293 @t~281 y decae, o el filtro-que-"
                   "olvida muere); (2) tasa corregida por drive vs sigma con lider "
                   "aterrizado; (3) des-censura de cobertura/relevos del canal v2. "
                   "Extension declarada: par129/131 (migracion del lider debil + control "
                   "drive-que-se-apaga). Prereg bitacora 2026-08-02 §3"),
        "retencion": base["retencion"],
        "horizonte_emergencia_ticks": base["horizonte_emergencia_ticks"],
        "reglas_clasificacion": {
            "instrumento": "lector v2 (prescripciones 1-8 del tap wf_cfb44e2e) — se "
                           "escribe y committea ANTES de abrir film alguno",
            "outcomes": ["b_S1(t) par132: maximo local en t=[230,340] con pico [0.22,0.37] "
                         "y b_S1(600)<0.9*pico = SOSTIENE; monotono sin maximo = MUERE",
                         "b_S1(t) par134: replica de FORMA (pica ~0.007 @t~347 y decae)",
                         "P1: tasa corregida por drive en ventanas estacionarias "
                         "(|dlnF/dt|<0.005, >=30 u.t.) de modos no-capturados sin hovering: "
                         "|sigma|x[0.7,1.3] = sigma es EL numero; >=1.5x = co-ordena",
                         "P3: cobertura de canal v2 (dominancia ambas familias, t(u), "
                         "relevos solapados, huecos) hasta 600; preguntas selladas: "
                         "par134 Q0 re-captura?; par132 completa modos?; relevos en lider "
                         "fuerte?; lider debil alcanza banda tarde (b_Q>~69)?"],
            "umbrales": "sellados PRE-corrida en §3; re-medicion = outcome"},
        "seed_politica": "IDENTICA a tanda 1/s120 (prefijo 1.5M bit-exacto = control)",
        "unidades": unidades,
    }


def main():
    import hashlib
    from study07.artifacts.campana import correr_campana
    spec = construir_spec()
    OUT.mkdir(parents=True, exist_ok=True)
    cuerpo = json.dumps(spec, indent=1)
    (OUT / "SPEC_largo600.json").write_text(cuerpo)
    sha = hashlib.sha256(cuerpo.encode()).hexdigest()
    (OUT / "SPEC_largo600.sha256").write_text(sha + "  SPEC_largo600.json\n")
    print(f"[largo600] SPEC sellada sha={sha[:16]} · 4 unidades × {TICKS_600} ticks",
          flush=True)

    inv_sha = (STUDY07 / "data/inventario_v4.sha256").read_text().split()[0]
    blocks = (Path.home() / "code/doft-study06-fundamental-lock-dynamics"
              / "data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json")
    hashes_base = {"inventario_v4": inv_sha,
                   "blocks_canonical": hashlib.sha256(blocks.read_bytes()).hexdigest(),
                   "spec_s120_origen": hashlib.sha256(
                       (STUDY07 / "data/lote_suelto_120/SPEC_suelto120.json"
                        ).read_bytes()).hexdigest()}
    base = OUT / "lote"
    if (base / "REPORTE.json").exists():
        print("[largo600] REPORTE ya existe — nada que hacer", flush=True)
        return
    t0 = time.time()
    print(f"[largo600] arrancando 4 workers (libre local: "
          f"{shutil.disk_usage(OUT).free / 1e9:.0f} GB)", flush=True)
    reporte = correr_campana(spec, base, hashes_base=hashes_base, workers=4,
                             archivar_en=ARCHIVO)
    (base / "REPORTE.json").write_text(json.dumps(reporte, indent=1, default=str))
    print(f"[largo600] TERMINADO en {(time.time()-t0)/3600:.2f} h", flush=True)


if __name__ == "__main__":
    main()
