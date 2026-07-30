"""Campañas — F7: el census [M2] como TIPO VALIDADO + ejecución por lotes reproducible.

EXPERIMENT_CONTRACT vuelto ejecutable: una spec [M2] es RECHAZADA (no corregida, no
advertida) si su población no es el inventario COMPLETO identificado por hash, si trae
intervenciones, si su horizonte no cubre el horizonte de emergencia declarado, si las reglas
de clasificación no están selladas en el prereg, o si falta la probeta GOLD. El 67/150 de
§84 (Study06) acá no compila.

La spec es AUTO-CONTENIDA y hasheable: cada unidad lleva su theta EMBEBIDO + (opcional) el
directorio de su cápsula con hash PINNEADO — componer la campaña es leer la spec, nada más.
El generador de specs (tools/) es quien cruza al oráculo; este módulo no.

Ejecución: pool de PROCESOS (una unidad = una red independiente con su semilla declarada) —
el paralelismo NO puede cambiar un bit de ningún film (gate: workers=1 == workers=N).
Reanudación POR UNIDAD: una unidad con COMPLETE se REUSA (idéntica, verificada por hash);
una unidad a medias se mueve a restos_<n>/ (JAMÁS se borra) y se rehace.
Retención v1: `conformidad_completa` (films float64 enteros). Perfiles con poda/decimación
llegan con F7.2 — pedirlos hoy es fail-loud, no silencio.
Reporte: TODAS las unidades, siempre — los aburridos son datos.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import shutil
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np

from .recorder import worldline_hash

PERFILES_RETENCION = ("conformidad_completa",)
CLAVES_SPEC = ("campana", "spec_tipo", "porque", "unidades", "retencion",
               "horizonte_emergencia_ticks", "reglas_clasificacion", "seed_politica")
CLAVES_UNIDAD = ("run_id", "constituyentes", "edges", "engine_params", "seed", "ticks")


def sha_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     separators=(",", ":"), default=str).encode()).hexdigest()


def _sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validar_campana(spec: Mapping[str, Any], inventario: Mapping[str, Any] | None) -> None:
    """Validador EJECUTABLE de specs de campaña. Para [M2]: las reglas duras del
    EXPERIMENT_CONTRACT — RECHAZO, jamás corrección silenciosa. `inventario` =
    {"sha256": ..., "block_ids": iterable} (para M2 es OBLIGATORIO)."""
    faltan = [k for k in CLAVES_SPEC if k not in spec]
    if faltan:
        raise RuntimeError(f"spec de campaña sin claves {faltan} (F7)")
    if spec["spec_tipo"] not in ("M1", "M2"):
        raise RuntimeError(f"spec_tipo={spec['spec_tipo']!r}: debe ser M1 o M2")
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
    if spec["spec_tipo"] == "M1":
        return
    # ── reglas duras [M2] ──
    if inventario is None:
        raise RuntimeError("spec M2 sin inventario: la población se identifica por hash "
                           "del catálogo, no por confianza (EXPERIMENT_CONTRACT)")
    if spec.get("poblacion_inventario_sha256") != inventario["sha256"]:
        raise RuntimeError("M2: poblacion_inventario_sha256 no coincide con el inventario "
                           "presentado — el census cita SU catálogo por hash")
    poblacion_spec = {c["block_id"] for u in spec["unidades"]
                      for c in u["constituyentes"] if c.get("es_poblacion")}
    inv_ids = set(inventario["block_ids"])
    faltantes = sorted(inv_ids - poblacion_spec)
    sobrantes = sorted(poblacion_spec - inv_ids)
    if faltantes or sobrantes:
        raise RuntimeError(
            f"M2: la población NO es el inventario COMPLETO — faltan {len(faltantes)} "
            f"(p.ej. {faltantes[:2]}), sobran {len(sobrantes)}. Un census parcial no "
            "compila (el 67/150 de §84 era esto)")
    hz = int(spec["horizonte_emergencia_ticks"])
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
    """Las métricas de M1-P1, congeladas como 'basicas_v1' (definiciones idénticas)."""
    e_tot = e_capa.sum(axis=2)
    n_t = e_tot.shape[0]
    met: Dict[str, Any] = {}
    for j in range(e_tot.shape[1]):
        met[f"E0_nodo{j}"] = float(e_tot[0, j])
        met[f"E_final_nodo{j}"] = float(e_tot[-1, j])
        met[f"E_max_nodo{j}"] = float(e_tot[:, j].max())
    e0 = e_tot[0, 0]
    for etiqueta, frac in (("t_half", 0.5), ("t_dec10", 0.1)):
        debajo = np.where(e_tot[:, 0] <= frac * e0)[0]
        met[etiqueta + "_tick"] = int(debajo[0]) if debajo.size else None
    met["R_final_media_ult10pct"] = float(r[-max(n_t // 10, 1):].mean())
    met["R_max"] = float(r.max())
    met["omega_valid_frac"] = float(omega_valid.mean())
    ok = (r >= 0.99).astype(np.int64)
    w = min(1000, len(ok))
    ventana = np.convolve(ok, np.ones(w, dtype=np.int64), mode="valid")
    sitios = np.where(ventana == w)[0]
    met["t_lock_tick"] = int(sitios[0]) if sitios.size else None
    return met


def _correr_unidad(args: Dict[str, Any]) -> Dict[str, Any]:
    """Corre UNA unidad (proceso worker): componer → film+checkpoints → vistas → métricas.
    Determinista: nada acá depende del pool ni del orden de ejecución."""
    from .composer import componer_red
    from .recorder import WorldlineRecorder
    from .runner import run as run_net
    from ..compat.study06_capsule import load_capsule
    from ..instruments import api, energy, phase

    u = args["unidad"]
    run_dir = Path(args["run_dir"])
    ep = u["engine_params"]
    constituyentes = []
    for c in u["constituyentes"]:
        cap = None
        if c.get("capsula_dir"):
            cap = load_capsule(c["capsula_dir"])
            if cap["capsule_sha256"] != c["capsule_sha256"]:
                raise RuntimeError(f"{u['run_id']}: cápsula {c['capsula_dir']} no es la "
                                   f"PINNEADA en la spec ({c['capsule_sha256'][:19]})")
        constituyentes.append({"theta": c["theta"], "capsula": cap})
    net, specs, recibo = componer_red(
        constituyentes, u["edges"], dt=float(ep["dt"]), seed=int(u["seed"]),
        k_global=float(ep["kappa_global"]),
        coupling_gamma_c=float(ep["coupling_gamma_c"]),
        tau_field=float(ep.get("tau_field", 0.0)),
        temperature=float(ep.get("temperature", 0.0)))
    base = dict(args["hashes_base"])
    for idx, c in enumerate(u["constituyentes"]):        # citar las cápsulas PINNEADAS
        if c.get("capsule_sha256"):                      # (PROVENANCE / F5-A5)
            base[f"capsula_nodo{idx}"] = c["capsule_sha256"]
    man = {"run_id": u["run_id"], "spec_tipo": args["spec_tipo"],
           "porque": args["porque"], "campana": args["campana"],
           "campana_spec_sha256": args["spec_sha256"],
           "hashes_base_externa": base,
           "composicion": recibo, "perfil": "conformidad"}
    rec = WorldlineRecorder(run_dir, net, man, chunk_ticks=int(args["chunk_ticks"]))
    run_net(net, int(u["ticks"]), recorder=rec,
            checkpoint_every=args.get("checkpoint_every"), finite_check_every=1024)
    rec.close()
    wl = api.load_run(run_dir)
    thetas = [c["theta"] for c in u["constituyentes"]]
    v_e = energy.run(wl, thetas)
    v_f = phase.run(wl)
    views_root = Path(args["views_root"])
    p_e = v_e.write(views_root); p_f = v_f.write(views_root)
    lv_e = api.load_view(p_e); lv_f = api.load_view(p_f)    # caché re-verificado fail-loud
    met = metricas_basicas_v1(lv_e["arrays"]["e_capa"], lv_f["arrays"]["r"],
                              lv_f["arrays"]["omega_valid"], float(ep["dt"]))
    return {"run_id": u["run_id"], "estado": "completa",
            "worldline_hash": wl["worldline_hash"],
            "view_hash_energy": lv_e["view_hash"], "view_hash_phase": lv_f["view_hash"],
            "metricas": met}


def correr_campana(spec: Mapping[str, Any], base_dir: Path,
                   inventario: Mapping[str, Any] | None = None,
                   hashes_base: Mapping[str, str] | None = None,
                   workers: int = 1, chunk_ticks: int = 4096,
                   checkpoint_every: int | None = None,
                   archivar_en: Path | None = None) -> Dict[str, Any]:
    """Corre la campaña ENTERA: valida la spec, ejecuta las unidades (pool de procesos),
    REUSA unidades ya COMPLETE (verificadas), mueve restos a un lado (jamás borra), escribe
    LEDGER + REPORTE con TODAS las unidades y archiva verificado si se pide."""
    validar_campana(spec, inventario)
    spec_sha = sha_json(spec)
    base_dir = Path(base_dir)
    unidades_dir = base_dir / "unidades"
    unidades_dir.mkdir(parents=True, exist_ok=True)
    views_root = base_dir / "views"

    pendientes, resultados = [], {}
    for u in spec["unidades"]:
        run_dir = unidades_dir / u["run_id"]
        if (run_dir / "COMPLETE").exists():
            man = json.loads((run_dir / "manifest.json").read_text())
            if man.get("campana_spec_sha256") != spec_sha:
                raise RuntimeError(f"{u['run_id']}: COMPLETE de OTRA spec "
                                   f"({str(man.get('campana_spec_sha256'))[:12]} != "
                                   f"{spec_sha[:12]}) — una campaña no pisa otra (F7)")
            resultados[u["run_id"]] = {"run_id": u["run_id"], "estado": "reusada",
                                       "worldline_hash": worldline_hash(run_dir)}
            continue
        if run_dir.exists():                       # restos de una interrupción: A UN LADO
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
            ctx = mp.get_context("spawn")          # determinista y sin herencia de estado
            with ctx.Pool(int(workers)) as pool:
                corridos = pool.map(_correr_unidad, pendientes)
        for r in corridos:
            resultados[r["run_id"]] = r

    # REPORTE = TODAS las unidades, en el ORDEN de la spec — los aburridos son datos
    reporte = [resultados[u["run_id"]] for u in spec["unidades"]]
    if len(reporte) != len(spec["unidades"]):
        raise RuntimeError("reporte incompleto: una campaña reporta su población ENTERA")
    ledger = {"schema": "study07_campana_v1", "campana": spec["campana"],
              "spec_tipo": spec["spec_tipo"], "spec_sha256": spec_sha,
              "n_unidades": len(reporte),
              "reusadas": sum(1 for r in reporte if r["estado"] == "reusada"),
              "probeta_gold_block_id": spec.get("probeta_gold_block_id"),
              "reglas_clasificacion": spec["reglas_clasificacion"],
              "hashes_base_externa": dict(hashes_base or {}),
              "unidades": reporte}
    cuerpo = json.dumps(ledger, indent=1, default=str)
    tmp = base_dir / "LEDGER.tmp.json"
    tmp.write_text(cuerpo)
    tmp.rename(base_dir / "LEDGER.json")
    (base_dir / "LEDGER.sha256").write_text(
        hashlib.sha256(cuerpo.encode()).hexdigest() + "  LEDGER.json\n")

    if archivar_en is not None:
        destino = Path(archivar_en)
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            raise RuntimeError(f"archivado: {destino} ya existe — el archivo no se pisa "
                               "(elegir OTRO destino; jamás borrar)")
        shutil.copytree(base_dir, destino)
        malos = [str(p.relative_to(base_dir)) for p in sorted(base_dir.rglob("*"))
                 if p.is_file() and _sha_file(p) != _sha_file(destino / p.relative_to(base_dir))]
        if malos:
            raise RuntimeError(f"archivado FALLÓ la verificación: {malos[:5]}")
        n = sum(1 for p in destino.rglob("*") if p.is_file())
        (destino / "ARCHIVADO.json").write_text(json.dumps(
            {"origen": str(base_dir), "archivos_verificados": n,
             "verificacion": "sha256 por archivo, 0 discrepancias"}, indent=1))
    return ledger
