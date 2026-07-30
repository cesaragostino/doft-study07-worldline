"""INSTRUMENT_CONTRACT ejecutable — un instrumento es una VISTA read-only sobre la worldline.

Jamás ejecuta el motor (gate de arquitectura: instruments no importa engine). Puede importar
physics (definiciones), artifacts (lector) y compat (parser de constituciones, read-only).
Una vista: falla si falta un canal · declara su observation_config completa · lleva hash y
procedencia · es recomputable y comparable con su caché · distingue dato de configuración.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict

import numpy as np

from ..artifacts.recorder import load_worldline


def worldline_hash(run_dir: Path) -> str:
    """La identidad del film = sha_total del COMPLETE (cierre íntegro)."""
    marca = json.loads((Path(run_dir) / "COMPLETE").read_text())
    return marca["sha_total"]


def config_hash(instrument_id: str, version: str, observation_config: Dict) -> str:
    cuerpo = json.dumps({"id": instrument_id, "v": version, "cfg": observation_config},
                        sort_keys=True, default=str)
    return hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()[:16]


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
        """Hash determinista del CONTENIDO (datos + manifiesto): recomputar debe reproducirlo."""
        h = hashlib.sha256()
        h.update(json.dumps(self.manifest, sort_keys=True, default=str).encode("utf-8"))
        for k in sorted(self.arrays):
            h.update(k.encode("utf-8"))
            h.update(np.ascontiguousarray(self.arrays[k]).tobytes())
        return h.hexdigest()

    def write(self, views_root: Path) -> Path:
        out = (Path(views_root) / self.manifest["worldline_hash"][:16]
               / self.manifest["instrument_id"] / self.manifest["config_hash"])
        out.mkdir(parents=True, exist_ok=True)
        self.manifest["view_hash"] = self.view_hash()
        (out / "manifest.json").write_text(json.dumps(self.manifest, indent=1, default=str))
        tmp = out / "data.tmp.npz"
        np.savez_compressed(tmp, **self.arrays)
        tmp.rename(out / "data.npz")
        return out


def load_run(run_dir: Path) -> Dict:
    """Carga verificada del film + su identidad. Los instrumentos SIEMPRE entran por acá."""
    wl = load_worldline(run_dir)          # verifica COMPLETE + hashes + manifiesto
    wl["worldline_hash"] = worldline_hash(run_dir)
    return wl


def exigir_canales(wl: Dict, requeridos) -> None:
    for c in requeridos:
        if c not in wl or (isinstance(wl[c], list) and not wl[c]):
            raise RuntimeError(f"canal requerido ausente en la worldline: {c!r} — el "
                               "instrumento FALLA, no sustituye (INSTRUMENT_CONTRACT)")
