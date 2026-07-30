"""INSTRUMENT_CONTRACT ejecutable — un instrumento es una VISTA read-only sobre la worldline.

Jamás ejecuta el motor (gate de arquitectura: instruments no importa engine — ni directo ni
transitivo: gate de subproceso limpio). Puede importar physics (definiciones), artifacts
(lector) y compat (parser de constituciones, read-only).
Una vista: falla si falta un canal · declara su observation_config completa (claves con
whitelist: un typo es error de contrato, no una config nueva) · lleva hash y procedencia ·
es recomputable y comparable con su caché EN DISCO (load_view) · distingue DATO (canal
transformado del film) de INFERENCIA (estimador con config) y de VEREDICTO (umbral declarado):
la taxonomía viaja en el manifiesto de la vista.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict

import numpy as np

# worldline_hash vive en artifacts (F6: también lo consume el linaje de hijas) y se
# re-exporta acá: los instrumentos siguen entrando por api.worldline_hash
from ..artifacts.recorder import load_worldline, worldline_hash  # noqa: F401


def config_hash(instrument_id: str, version: str, observation_config: Dict) -> str:
    cuerpo = json.dumps({"id": instrument_id, "v": version, "cfg": observation_config},
                        sort_keys=True, default=str)
    return hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()[:16]


def armar_config(defaults: Dict, observation_config: Dict | None) -> Dict:
    """Whitelist de claves: una clave fuera de DEFAULTS es un ERROR de contrato, jamás una
    config declarada — un typo ('r_mim') corría con el default mientras el manifiesto
    declaraba la clave basura (double tap F4 A8)."""
    obs = dict(observation_config or {})
    desconocidas = sorted(set(obs) - set(defaults))
    if desconocidas:
        raise RuntimeError(f"observation_config con claves desconocidas {desconocidas}; "
                           f"válidas: {sorted(defaults)} (INSTRUMENT_CONTRACT: la config se "
                           "declara contra el vocabulario del instrumento, no se adivina)")
    return {**defaults, **obs}


def ventana(wl: Dict, cfg: Dict) -> np.ndarray:
    """Validación COMPARTIDA de la ventana de observación (la ventana es parte de la interfaz).
    t0 negativo wrapeaba en silencio; t0>t1 producía vista vacía publicable; t1 fuera de rango
    reventaba con IndexError crudo (double tap F4 A8)."""
    n = len(wl["ticks"])
    t0 = int(cfg["t0_tick"])
    t1 = int(cfg["t1_tick"]) if cfg["t1_tick"] is not None else n - 1
    stride = int(cfg["stride"])
    if not (0 <= t0 <= t1 < n) or stride < 1:
        raise RuntimeError(f"ventana inválida: t0_tick={t0}, t1_tick={t1}, stride={stride} "
                           f"para un film de {n} ticks — se exige 0 <= t0 <= t1 < {n} y "
                           "stride >= 1 (INSTRUMENT_CONTRACT)")
    sel = np.arange(t0, t1 + 1, stride)
    if sel.size == 0:
        raise RuntimeError("ventana vacía: la vista no observa nada")
    return sel


def exigir_completo(wl: Dict, permitir_incompleto: bool) -> None:
    """Sólo COMPLETE entra al catálogo — también en la capa que OBSERVA. La auditoría de restos
    exige el flag EXPLÍCITO, que queda declarado en la config y por lo tanto en el config_hash."""
    if bool(permitir_incompleto):
        return
    if wl.get("complete") is not True:
        raise RuntimeError("film sin COMPLETE: no se observa por defecto — auditoría de restos "
                           "sólo con permitir_incompleto=True EXPLÍCITO en la config "
                           "(WORLDLINE_SCHEMA regla 1 / double tap F4 A8)")


class View:
    def __init__(self, instrument_id: str, version: str, observation_config: Dict,
                 wl_hash: str, arrays: Dict[str, np.ndarray], extra_manifest: Dict | None = None):
        self.arrays = dict(arrays)
        self.manifest = {
            "schema": "study07_view_v1",
            "instrument_id": instrument_id, "version": version,
            "observation_config": observation_config,
            "worldline_hash": wl_hash,
            "config_hash": config_hash(instrument_id, version, observation_config),
            **(extra_manifest or {}),
        }

    def view_hash(self) -> str:
        """Hash determinista del CONTENIDO (datos + manifiesto SIN la clave view_hash):
        recomputar debe reproducirlo SIEMPRE — hashear el propio hash rompía la idempotencia
        de write() (double tap F4 A3)."""
        h = hashlib.sha256()
        base = {k: v for k, v in self.manifest.items() if k != "view_hash"}
        h.update(json.dumps(base, sort_keys=True, default=str).encode("utf-8"))
        for k in sorted(self.arrays):
            h.update(k.encode("utf-8"))
            h.update(np.ascontiguousarray(self.arrays[k]).tobytes())
        return h.hexdigest()

    def write(self, views_root: Path) -> Path:
        """Escritura con CIERRE: data.npz primero, manifest.json (con view_hash) AL FINAL como
        marca — media-vista sin manifiesto es visible. No muta self.manifest. Un path ocupado
        con OTRO view_hash es rechazo fuerte: corrección de instrumento ⇒ nueva versión ⇒
        nueva ruta (WORLDLINE_SCHEMA regla 2), jamás un pisado silencioso."""
        vh = self.view_hash()
        out = (Path(views_root) / self.manifest["worldline_hash"][:16]
               / self.manifest["instrument_id"] / self.manifest["config_hash"])
        previo = out / "manifest.json"
        if previo.exists():
            vh_previo = json.loads(previo.read_text()).get("view_hash")
            if vh_previo != vh:
                raise RuntimeError(f"vista ya publicada en {out} con view_hash "
                                   f"{str(vh_previo)[:12]} != {vh[:12]}: no se pisa una vista "
                                   "(corrección de instrumento ⇒ nueva versión, "
                                   "WORLDLINE_SCHEMA regla 2)")
        out.mkdir(parents=True, exist_ok=True)
        tmp = out / "data.tmp.npz"
        np.savez_compressed(tmp, **self.arrays)
        tmp.rename(out / "data.npz")
        cuerpo = dict(self.manifest)
        cuerpo["view_hash"] = vh
        tmp_man = out / "manifest.tmp.json"
        tmp_man.write_text(json.dumps(cuerpo, indent=1, default=str))
        tmp_man.rename(out / "manifest.json")
        return out


def load_view(view_dir: Path) -> Dict:
    """Lector-verificador del caché: relee manifest.json + data.npz, RECOMPUTA el view_hash
    desde disco y lo compara con el sellado — fail-loud. Sin esto, «recomputable y comparable
    con su caché» era prosa (double tap F4 A3: data.npz vacío/float32 pasaba todo)."""
    view_dir = Path(view_dir)
    man_path = view_dir / "manifest.json"
    if not man_path.exists():
        raise RuntimeError(f"{view_dir}: sin manifest.json — vista sin marca de cierre "
                           "(media-vista o path equivocado)")
    manifest = json.loads(man_path.read_text())
    sellado = manifest.get("view_hash")
    if not sellado:
        raise RuntimeError(f"{view_dir}: manifest.json sin view_hash — vista pre-esquema")
    with np.load(view_dir / "data.npz", allow_pickle=False) as fx:
        arrays = {k: fx[k].copy() for k in fx.files}
    v = View.__new__(View)
    v.arrays = arrays
    v.manifest = {k: val for k, val in manifest.items() if k != "view_hash"}
    recomputado = v.view_hash()
    if recomputado != sellado:
        raise RuntimeError(f"{view_dir}: view_hash recomputado {recomputado[:12]} != sellado "
                           f"{sellado[:12]} — el caché no reproduce su manifiesto "
                           "(adulteración, degradación de dtype o media-vista)")
    return {"manifest": manifest, "arrays": arrays, "view_hash": sellado}


def load_run(run_dir: Path) -> Dict:
    """Carga verificada del film + su identidad. Los instrumentos SIEMPRE entran por acá."""
    wl = load_worldline(run_dir)          # verifica COMPLETE + hashes + manifiesto
    wl["worldline_hash"] = worldline_hash(run_dir)
    return wl


def exigir_canales(wl: Dict, requeridos) -> None:
    for c in requeridos:
        v = wl.get(c, None)
        ausente = (c not in wl or v is None
                   or (isinstance(v, (list, tuple)) and len(v) == 0)
                   or (isinstance(v, np.ndarray) and v.size == 0)
                   or (isinstance(v, str) and not v))
        if ausente:
            raise RuntimeError(f"canal requerido ausente en la worldline: {c!r} — el "
                               "instrumento FALLA, no sustituye (INSTRUMENT_CONTRACT)")
