"""Checkpoint — CHECKPOINT_SCHEMA: continuación EXACTA (float64 + buffers + RNG + reloj).

Es un artefacto DISTINTO de la película: la película es para observar; el checkpoint es para
CONTINUAR o BIFURCAR la dinámica (worldlines hijas). Gate: corrida directa vs
checkpoint→restore→continuación deben ser BIT-exactas.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Sequence

import numpy as np

from ..engine.network import Network
from ..physics.state import NodeSpec, NodeState


def save_checkpoint(path: Path, net: Network, tick: int, extra_meta: Dict | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {
        "buffer": np.asarray(net.history.buffer, dtype=np.float64),
        "head": np.int64(net.history.head_idx),
        "tick": np.int64(tick),
    }
    for j, st in enumerate(net.states):
        for campo in ("x", "v", "z", "b", "e"):
            arrays[f"n{j}_{campo}"] = np.asarray(getattr(st, campo), dtype=np.float64)
    meta = {
        "schema": "study07_checkpoint_v1",
        "n_nodes": len(net.specs), "dt": net.dt, "seed": net.seed,
        "temperature": net.temperature, "tick": int(tick),
        "rng_state": net.noise_rng.bit_generator.state,
        # e_ref vive en el spec (mutable por política SOLO en el nacimiento): viaja en el
        # checkpoint para que la reconstrucción no dependa de re-correr la política
        "e_ref_por_nodo": [{layer.name: float(v) for layer, v in sp.struct.e_ref.items()}
                           for sp in net.specs],
    }
    if extra_meta:
        meta["extra"] = extra_meta
    arrays["meta_json"] = np.array(json.dumps(meta, default=str))
    # savez_compressed APPENDEA .npz si el nombre no lo trae: el tmp DEBE terminar en .npz
    tmp = path.with_name(path.stem + ".tmp.npz")
    np.savez_compressed(tmp, **arrays)
    tmp.rename(path)
    return path


def load_checkpoint(path: Path) -> Dict:
    fx = np.load(Path(path), allow_pickle=False)
    meta = json.loads(str(fx["meta_json"]))
    n = int(meta["n_nodes"])
    states = []
    for j in range(n):
        states.append(NodeState(x=np.asarray(fx[f"n{j}_x"]).copy(),
                                v=np.asarray(fx[f"n{j}_v"]).copy(),
                                z=np.asarray(fx[f"n{j}_z"]).copy(),
                                b=np.asarray(fx[f"n{j}_b"]).copy(),
                                e=np.asarray(fx[f"n{j}_e"]).copy()))
    return {"meta": meta, "states": states,
            "buffer": np.asarray(fx["buffer"]).copy(), "head": int(fx["head"]),
            "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def network_from_checkpoint(specs: Sequence[NodeSpec], ck: Dict, edges, **kwargs) -> Network:
    """Reconstruye la red para CONTINUAR. Los specs se reconstruyen de la constitución (por hash,
    responsabilidad del caller — PROVENANCE_CONTRACT); el checkpoint aporta estado + historia +
    RNG + e_ref. kwargs = los mismos engine params de la corrida madre."""
    from ..physics.state import Layer
    meta = ck["meta"]
    for sp, erefs in zip(specs, meta["e_ref_por_nodo"]):
        for lname, val in erefs.items():
            sp.struct.e_ref[Layer[lname]] = float(val)
    return Network(specs, ck["states"], edges, dt=float(meta["dt"]), seed=int(meta["seed"]),
                   temperature=float(meta["temperature"]),
                   history_init=(ck["buffer"], ck["head"]),
                   rng_state=meta["rng_state"], **kwargs)
