"""Campañas — F7: el census [M2] como TIPO VALIDADO + ejecución por lotes reproducible.
Endurecido por el double tap wf_2f58724b (A1-A9): la reanudación VERIFICA y reconstruye filas
COMPLETAS, el ledger jamás se degrada, una unidad que falla es un DATO (no mata el census),
un worker muerto es fail-loud, la procedencia no es fabricable y la población se verifica
por GENOMA contra el inventario, no por nombre.

EXPERIMENT_CONTRACT ejecutable: una spec [M2] es RECHAZADA si su población no es el
inventario COMPLETO (identidad por hash del catálogo Y genoma por genoma), si trae
intervenciones, si su horizonte no cubre el de emergencia (≥1), si las reglas de
clasificación no están selladas o si falta la probeta GOLD. El 67/150 de §84 no compila.

La spec es AUTO-CONTENIDA y hasheable (canónico, invariante al orden de claves): thetas
EMBEBIDOS + cápsulas pinneadas por sha + retención (con chunk_ticks: los bytes del film son
función de la spec). Se PERSISTE en el base_dir (SPEC.json) — la campaña es re-ejecutable
desde sus propios papeles. El generador de specs (tools/) es quien cruza al oráculo.

Ejecución: ProcessPoolExecutor (contexto spawn PINNEADO — sin herencia de estado; un worker
muerto ⇒ BrokenProcessPool fail-loud, jamás cuelgue). El paralelismo NO puede cambiar un bit
(gate: workers=N == workers=1, filas ENTERAS). El caller con workers>1 debe correr bajo
`if __name__ == "__main__"` (spawn). Excepciones de unidad = estado 'fallida' con el error
como DATO del reporte; la reanudación las rehace. Reanudación POR UNIDAD: COMPLETE de la
MISMA spec se re-VERIFICA (load_worldline: chunks+manifiesto) y su fila se RECONSTRUYE
completa (vistas re-verificadas + métricas recomputadas); restos a restos_*/ (JAMÁS borrar).
Preflight de DISCO: la proyección se compara contra el espacio libre ANTES de correr.
Retención v1: `conformidad_completa`. Reporte: TODAS las unidades, en el orden de la spec.
El LEDGER es determinista (sin timestamps); el rendimiento va aparte (RENDIMIENTO.json,
declarado NO-determinista y fuera de la identidad de la campaña).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import multiprocessing as mp

import numpy as np

from .recorder import load_worldline, worldline_hash

PERFILES_RETENCION = ("conformidad_completa",)
CLAVES_SPEC = ("campana", "spec_tipo", "porque", "unidades", "retencion",
               "horizonte_emergencia_ticks", "reglas_clasificacion", "seed_politica")
CLAVES_UNIDAD = ("run_id", "constituyentes", "edges", "engine_params", "seed", "ticks")
FACTOR_DISCO = 2.2          # film + vistas + checkpoints + margen, medido en M1-P1


def sha_json(obj: Any) -> str:
    """Hash CANÓNICO (sort_keys + separadores fijos): invariante al orden de claves —
    una spec regenerada idéntica DEBE dar el mismo sha (F7/M17)."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     separators=(",", ":"), default=str).encode()).hexdigest()


def _sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _escribir_atomico(path: Path, cuerpo: str, con_fsync: bool = True) -> None:
    """tmp + fsync + rename: el par archivo/sidecar jamás queda a medias (F7/M14)."""
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w") as f:
        f.write(cuerpo)
        if con_fsync:
            f.flush()
            os.fsync(f.fileno())
    tmp.rename(path)


def validar_campana(spec: Mapping[str, Any], inventario: Mapping[str, Any] | None) -> None:
    """Validador EJECUTABLE. Para [M2]: reglas duras del EXPERIMENT_CONTRACT — RECHAZO,
    jamás corrección silenciosa. `inventario` = {"sha256":…, "block_ids":…, y (A9)
    "genome_hash_por_block": {block_id: genome_hash}} — para M2 es OBLIGATORIO."""
    faltan = [k for k in CLAVES_SPEC if k not in spec]
    if faltan:
        raise RuntimeError(f"spec de campaña sin claves {faltan} (F7)")
    if spec["spec_tipo"] not in ("M1", "M2"):
        raise RuntimeError(f"spec_tipo={spec['spec_tipo']!r}: debe ser M1 o M2")
    malas = sorted(k for k in spec if str(k).startswith("filtro"))
    if malas:
        raise RuntimeError(f"spec con claves de FILTRO {malas}: el gate-portero no compila "
                           "— el reporte es la población entera (EXPERIMENT_CONTRACT)")
    perfil = spec["retencion"].get("perfil")
    if perfil not in PERFILES_RETENCION:
        raise RuntimeError(f"retención {perfil!r} NO implementada — perfiles v1: "
                           f"{PERFILES_RETENCION}; poda/decimación llegan con F7.2 "
                           "(fail-loud, no silencio)")
    if not spec["unidades"]:
        raise RuntimeError("campaña sin unidades")
    ids = [u.get("run_id") for u in spec["unidades"]]
    if len(set(ids)) != len(ids):
        raise RuntimeError("run_id duplicado entre unidades")
    for u in spec["unidades"]:
        faltan_u = [k for k in CLAVES_UNIDAD if k not in u]
        if faltan_u:
            raise RuntimeError(f"unidad {u.get('run_id')!r} sin claves {faltan_u}")
        if "eventos" in u or "intervenciones" in u:
            raise RuntimeError(f"unidad {u['run_id']!r} con intervenciones: una campaña "
                               "corre evolución libre — las hijas se crean con hija.py, "
                               "una por una y con su porqué (EXPERIMENT_CONTRACT)")
        for c in u["constituyentes"]:
            if "theta" not in c:
                raise RuntimeError(f"unidad {u['run_id']!r}: constituyente sin theta "
                                   "EMBEBIDO — la spec es auto-contenida (F7)")
            if c.get("capsula_dir") and not c.get("capsule_sha256"):
                raise RuntimeError(f"unidad {u['run_id']!r}: cápsula sin hash PINNEADO")
            if c.get("capsule_sha256") and not c.get("capsula_dir"):
                raise RuntimeError(f"unidad {u['run_id']!r}: capsule_sha256 SIN capsula_dir "
                                   "— un hash sin artefacto es procedencia FABRICADA "
                                   "(double tap F7 A5)")
            if c.get("es_poblacion") and not c.get("block_id"):
                raise RuntimeError(f"unidad {u['run_id']!r}: es_poblacion sin block_id — "
                                   "la población se identifica, no se insinúa (F7 A9)")
    if spec["spec_tipo"] == "M1":
        return
    # ── reglas duras [M2] ──
    if inventario is None:
        raise RuntimeError("spec M2 sin inventario: la población se identifica por hash "
                           "del catálogo, no por confianza (EXPERIMENT_CONTRACT)")
    if spec.get("poblacion_inventario_sha256") != inventario["sha256"]:
        raise RuntimeError("M2: poblacion_inventario_sha256 no coincide con el inventario "
                           "presentado — el census cita SU catálogo por hash")
    poblacion = [c["block_id"] for u in spec["unidades"]
                 for c in u["constituyentes"] if c.get("es_poblacion")]
    if len(poblacion) != len(set(poblacion)):
        dup = sorted({b for b in poblacion if poblacion.count(b) > 1})
        raise RuntimeError(f"M2: bloques de población DUPLICADOS entre unidades "
                           f"({dup[:2]}): cada individuo cuenta UNA vez (F7 A9)")
    inv_ids = set(inventario["block_ids"])
    faltantes = sorted(inv_ids - set(poblacion))
    sobrantes = sorted(set(poblacion) - inv_ids)
    if faltantes or sobrantes:
        raise RuntimeError(
            f"M2: la población NO es el inventario COMPLETO — faltan {len(faltantes)} "
            f"(p.ej. {faltantes[:2]}), sobran {len(sobrantes)}. Un census parcial no "
            "compila (el 67/150 de §84 era esto)")
    # A9: identidad por GENOMA, no por nombre — el theta embebido de cada individuo de la
    # población debe SER el del inventario (block_id swapeado o theta trocado no compilan)
    genomas_inv = inventario.get("genome_hash_por_block")
    if not genomas_inv:
        raise RuntimeError("M2: el inventario no trae genome_hash_por_block — la población "
                           "se verifica por GENOMA, no por nombre (double tap F7 A9)")
    from ..compat.study06_capsule import genome_sha256
    for u in spec["unidades"]:
        for c in u["constituyentes"]:
            if c.get("es_poblacion"):
                g = genome_sha256(c["theta"])
                if g != genomas_inv.get(c["block_id"]):
                    raise RuntimeError(
                        f"M2: unidad {u['run_id']!r} bloque {c['block_id'][:12]}: el GENOMA "
                        f"embebido ({g[:19]}) no es el del inventario — atribución "
                        "equivocada o theta trocado (double tap F7 A9/J4)")
    hz = int(spec["horizonte_emergencia_ticks"])
    if hz < 1:
        raise RuntimeError(f"M2: horizonte_emergencia_ticks={hz} — un horizonte sin piso "
                           "es un census de cero evolución (F7 A9)")
    cortas = [u["run_id"] for u in spec["unidades"] if int(u["ticks"]) < hz]
    if cortas:
        raise RuntimeError(f"M2: {len(cortas)} unidades con horizonte menor al de "
                           f"emergencia declarado ({hz}): {cortas[:3]}")
    if not spec["reglas_clasificacion"]:
        raise RuntimeError("M2: reglas de clasificación sin sellar en el prereg — "
                           "clasificar después de mirar es el gate-portero")
    gold = spec.get("probeta_gold_block_id")
    if not gold:
        raise RuntimeError("M2: sin probeta GOLD declarada (regla heredada de Study06)")
    en_spec = any(c.get("block_id") == gold for u in spec["unidades"]
                  for c in u["constituyentes"])
    if not en_spec:
        raise RuntimeError(f"M2: la probeta GOLD {gold[:12]} no está en ninguna unidad")


def metricas_basicas_v1(e_capa: np.ndarray, r: np.ndarray, omega_valid: np.ndarray,
                        dt: float) -> Dict[str, Any]:
    """Las métricas de M1-P1, congeladas como 'basicas_v1' (definiciones idénticas).
    n_nodes==1 ⇒ R es IDENTIDAD por construcción (|exp(iθ)|=1): R/t_lock = None declarado."""
    e_tot = e_capa.sum(axis=2)
    n_t, n_nodos = e_tot.shape
    met: Dict[str, Any] = {}
    for j in range(n_nodos):
        met[f"E0_nodo{j}"] = float(e_tot[0, j])
        met[f"E_final_nodo{j}"] = float(e_tot[-1, j])
        met[f"E_max_nodo{j}"] = float(e_tot[:, j].max())
    e0 = e_tot[0, 0]
    for etiqueta, frac in (("t_half", 0.5), ("t_dec10", 0.1)):
        debajo = np.where(e_tot[:, 0] <= frac * e0)[0]
        met[etiqueta + "_tick"] = int(debajo[0]) if debajo.size else None
    if n_nodos < 2:
        met.update({"R_final_media_ult10pct": None, "R_max": None,
                    "omega_valid_frac": None, "t_lock_tick": None,
                    "nota_n1": "R identidad por construccion con 1 nodo (F4 NO-CUBIERTO 4)"})
        return met
    met["R_final_media_ult10pct"] = float(r[-max(n_t // 10, 1):].mean())
    met["R_max"] = float(r.max())
    met["omega_valid_frac"] = float(omega_valid.mean())
    ok = (r >= 0.99).astype(np.int64)
    w = min(1000, len(ok))
    ventana = np.convolve(ok, np.ones(w, dtype=np.int64), mode="valid")
    sitios = np.where(ventana == w)[0]
    met["t_lock_tick"] = int(sitios[0]) if sitios.size else None
    return met


def _vistas_y_metricas(run_dir: Path, views_root: Path, thetas, dt: float) -> Dict[str, Any]:
    """Vistas escritas (o reusadas) y RE-verificadas desde disco + métricas recomputadas —
    el MISMO camino para unidades corridas y reusadas (F7 A1)."""
    from ..instruments import api, energy, phase
    wl = api.load_run(run_dir)                 # verifica COMPLETE + chunks + manifiesto
    v_e = energy.run(wl, thetas)
    v_f = phase.run(wl)
    p_e = v_e.write(views_root); p_f = v_f.write(views_root)
    lv_e = api.load_view(p_e); lv_f = api.load_view(p_f)   # caché re-verificado fail-loud
    met = metricas_basicas_v1(lv_e["arrays"]["e_capa"], lv_f["arrays"]["r"],
                              lv_f["arrays"]["omega_valid"], dt)
    return {"worldline_hash": wl["worldline_hash"],
            "view_hash_energy": lv_e["view_hash"], "view_hash_phase": lv_f["view_hash"],
            "metricas": met}


def _correr_unidad(args: Dict[str, Any]) -> Dict[str, Any]:
    """Corre UNA unidad (proceso worker). Determinista. TODA excepción vuelve como estado
    'fallida' con el error como DATO (F7 A3): una unidad no mata el census."""
    u = args["unidad"]
    try:
        return _correr_unidad_cruda(args)
    except Exception as exc:
        return {"run_id": u["run_id"], "estado": "fallida",
                "error_clase": type(exc).__name__, "error": str(exc)[:500]}


def _correr_unidad_cruda(args: Dict[str, Any]) -> Dict[str, Any]:
    from .composer import componer_red
    from .recorder import WorldlineRecorder
    from .runner import run as run_net
    from ..compat.study06_capsule import load_capsule

    u = args["unidad"]
    run_dir = Path(args["run_dir"])
    ep = u["engine_params"]
    constituyentes, base = [], dict(args["hashes_base"])
    for idx, c in enumerate(u["constituyentes"]):
        cap = None
        if c.get("capsula_dir"):
            cap = load_capsule(c["capsula_dir"])
            if cap["capsule_sha256"] != c["capsule_sha256"]:
                raise RuntimeError(f"{u['run_id']}: cápsula {c['capsula_dir']} no es la "
                                   f"PINNEADA en la spec ({c['capsule_sha256'][:19]})")
            if c.get("block_id") and cap["manifest"]["block_id"] != c["block_id"]:
                raise RuntimeError(f"{u['run_id']}: la cápsula cargada es del bloque "
                                   f"{cap['manifest']['block_id'][:12]} pero la spec "
                                   f"atribuye {c['block_id'][:12]} — atribución swapeada "
                                   "(double tap F7 A6/J4)")
            base[f"capsula_nodo{idx}"] = cap["capsule_sha256"]   # citada SOLO si cargada
        constituyentes.append({"theta": c["theta"], "capsula": cap})
    net, specs, recibo = componer_red(
        constituyentes, u["edges"], dt=float(ep["dt"]), seed=int(u["seed"]),
        k_global=float(ep["kappa_global"]),
        coupling_gamma_c=float(ep["coupling_gamma_c"]),
        tau_field=float(ep.get("tau_field", 0.0)),
        temperature=float(ep.get("temperature", 0.0)))
    man = {"run_id": u["run_id"], "spec_tipo": args["spec_tipo"],
           "porque": args["porque"], "campana": args["campana"],
           "campana_spec_sha256": args["spec_sha256"],
           "hashes_base_externa": base,
           "composicion": recibo, "perfil": "conformidad"}
    rec = WorldlineRecorder(run_dir, net, man, chunk_ticks=int(args["chunk_ticks"]))
    run_net(net, int(u["ticks"]), recorder=rec,
            checkpoint_every=args.get("checkpoint_every"), finite_check_every=1024)
    rec.close()
    fila = _vistas_y_metricas(run_dir, Path(args["views_root"]),
                              [c["theta"] for c in u["constituyentes"]], float(ep["dt"]))
    fila.update({"run_id": u["run_id"], "estado": "completa"})
    return fila


def _preflight_disco(spec, base_dir: Path, archivar_en: Path | None) -> int:
    """Proyección de disco ANTES de correr: films float64 completos + factor medido.
    Abortar acá es barato; quedarse sin disco a mitad del census no (F7 NO-CUBIERTO 1)."""
    dims_est = 0
    for u in spec["unidades"]:
        n_estado = sum(2 * len(c["theta"]["modes"]) + 13 for c in u["constituyentes"])
        dims_est += (int(u["ticks"]) + 1) * n_estado * 8
    proyeccion = int(dims_est * FACTOR_DISCO)
    libre = shutil.disk_usage(base_dir).free
    if proyeccion > libre * 0.8:
        raise RuntimeError(f"preflight de DISCO: proyección {proyeccion / 1e9:.1f} GB > 80% "
                           f"del libre ({libre / 1e9:.1f} GB) en {base_dir} — el census no "
                           "arranca si no entra (F7)")
    if archivar_en is not None:
        ancla = Path(archivar_en).parent
        while not ancla.exists() and ancla != ancla.parent:
            ancla = ancla.parent               # el destino puede no existir aún: medir el
        libre_ext = shutil.disk_usage(ancla).free   # filesystem del ancestro más cercano
        if proyeccion > libre_ext * 0.8:
            raise RuntimeError(f"preflight de DISCO (archivo): proyección "
                               f"{proyeccion / 1e9:.1f} GB no entra en el destino")
    return proyeccion


def correr_campana(spec: Mapping[str, Any], base_dir: Path,
                   inventario: Mapping[str, Any] | None = None,
                   hashes_base: Mapping[str, str] | None = None,
                   workers: int = 1,
                   checkpoint_every: int | None = None,
                   archivar_en: Path | None = None) -> Dict[str, Any]:
    """Corre la campaña ENTERA. Ver el docstring del módulo: validación, spec persistida,
    preflight de disco, pool spawn fail-loud, contención por unidad, reanudación verificada
    con filas completas, ledger jamás degradado, archivado atómico verificado."""
    validar_campana(spec, inventario)
    spec_sha = sha_json(spec)
    chunk_ticks = int(spec["retencion"].get("chunk_ticks", 4096))
    base_dir = Path(base_dir)
    unidades_dir = base_dir / "unidades"
    unidades_dir.mkdir(parents=True, exist_ok=True)
    views_root = base_dir / "views"
    _preflight_disco(spec, base_dir, archivar_en)
    # la SPEC se PERSISTE: la campaña es re-ejecutable desde sus papeles (F7 NO-CUBIERTO 4)
    _escribir_atomico(base_dir / "SPEC.json", json.dumps(spec, indent=1, default=str))
    _escribir_atomico(base_dir / "SPEC.sha256", spec_sha + "  SPEC.json\n")

    pendientes, resultados = [], {}
    for u in spec["unidades"]:
        run_dir = unidades_dir / u["run_id"]
        if (run_dir / "COMPLETE").exists():
            try:
                man = json.loads((run_dir / "manifest.json").read_text())
                if man.get("campana_spec_sha256") != spec_sha:
                    raise RuntimeError(
                        f"{u['run_id']}: COMPLETE de OTRA spec "
                        f"({str(man.get('campana_spec_sha256'))[:12]} != {spec_sha[:12]}) "
                        "— una campaña no pisa otra (F7)")
                load_worldline(run_dir)        # A1: la reusa se VERIFICA (chunks+manifiesto)
                fila = _vistas_y_metricas(run_dir, views_root,
                                          [c["theta"] for c in u["constituyentes"]],
                                          float(u["engine_params"]["dt"]))
                fila.update({"run_id": u["run_id"], "estado": "reusada"})
                resultados[u["run_id"]] = fila
                continue
            except RuntimeError as exc:
                if "no pisa" in str(exc):
                    raise                       # spec ajena: eso SÍ aborta
                # film COMPLETO pero corrupto/inverificable: a restos y se rehace (A1)
        if run_dir.exists():                    # restos: A UN LADO, jamás borrar
            n = len(list(unidades_dir.glob(f"restos_{u['run_id']}_*")))
            run_dir.rename(unidades_dir / f"restos_{u['run_id']}_{n}")
        pendientes.append({"unidad": u, "run_dir": str(run_dir),
                           "views_root": str(views_root),
                           "spec_tipo": spec["spec_tipo"], "porque": spec["porque"],
                           "campana": spec["campana"], "spec_sha256": spec_sha,
                           "hashes_base": dict(hashes_base or {}),
                           "chunk_ticks": chunk_ticks,
                           "checkpoint_every": checkpoint_every})
    if pendientes:
        if int(workers) <= 1:
            corridos = [_correr_unidad(a) for a in pendientes]
        else:
            # spawn PINNEADO (sin herencia de estado) + fail-loud si un worker MUERE
            # (BrokenProcessPool), jamás cuelgue silencioso (F7 A4/J6)
            with ProcessPoolExecutor(max_workers=int(workers),
                                     mp_context=mp.get_context("spawn")) as ex:
                corridos = list(ex.map(_correr_unidad, pendientes, chunksize=1))
        for r in corridos:
            resultados[r["run_id"]] = r

    # REPORTE = TODAS las unidades, en el ORDEN de la spec — los aburridos son datos
    reporte = [resultados[u["run_id"]] for u in spec["unidades"]]
    fallidas = [r["run_id"] for r in reporte if r["estado"] == "fallida"]
    ledger = {"schema": "study07_campana_v2", "campana": spec["campana"],
              "spec_tipo": spec["spec_tipo"], "spec_sha256": spec_sha,
              "n_unidades": len(reporte),
              "reusadas": sum(1 for r in reporte if r["estado"] == "reusada"),
              "fallidas": fallidas,
              "completa": not fallidas,
              "probeta_gold_block_id": spec.get("probeta_gold_block_id"),
              "reglas_clasificacion": spec["reglas_clasificacion"],
              "hashes_base_externa": dict(hashes_base or {}),
              "unidades": reporte}
    # A2: el LEDGER previo JAMÁS se degrada — se aparta antes de escribir el nuevo
    if (base_dir / "LEDGER.json").exists():
        n = len(list(base_dir.glob("restos_LEDGER_*")))
        (base_dir / "LEDGER.json").rename(base_dir / f"restos_LEDGER_{n}.json")
    cuerpo = json.dumps(ledger, indent=1, default=str)
    _escribir_atomico(base_dir / "LEDGER.json", cuerpo)
    _escribir_atomico(base_dir / "LEDGER.sha256",
                      hashlib.sha256(cuerpo.encode()).hexdigest() + "  LEDGER.json\n")

    if archivar_en is not None:
        _archivar(base_dir, Path(archivar_en))
    return ledger


def _archivar(base_dir: Path, destino: Path) -> None:
    """Archivado ATÓMICO verificado: copiar a *.tmp_archivo, verificar sha-por-sha, sellar
    ARCHIVADO.json y RENAME final. Un tmp huérfano de una interrupción se aparta (jamás se
    borra); el destino final ocupado NO se pisa."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        raise RuntimeError(f"archivado: {destino} ya existe — el archivo no se pisa "
                           "(elegir OTRO destino; jamás borrar)")
    tmp = destino.with_name(destino.name + ".tmp_archivo")
    if tmp.exists():
        n = len(list(destino.parent.glob(f"{destino.name}.restos_archivo_*")))
        tmp.rename(destino.parent / f"{destino.name}.restos_archivo_{n}")
    shutil.copytree(base_dir, tmp)
    malos = [str(p.relative_to(base_dir)) for p in sorted(base_dir.rglob("*"))
             if p.is_file() and _sha_file(p) != _sha_file(tmp / p.relative_to(base_dir))]
    if malos:
        raise RuntimeError(f"archivado FALLÓ la verificación: {malos[:5]}")
    n = sum(1 for p in tmp.rglob("*") if p.is_file())
    _escribir_atomico(tmp / "ARCHIVADO.json", json.dumps(
        {"origen": str(base_dir), "archivos_verificados": n,
         "verificacion": "sha256 por archivo, 0 discrepancias"}, indent=1))
    tmp.rename(destino)
