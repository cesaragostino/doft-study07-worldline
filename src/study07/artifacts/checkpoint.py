"""Checkpoint — CHECKPOINT_SCHEMA: continuación EXACTA (float64 + buffers + RNG + reloj).

Es un artefacto DISTINTO de la película: la película es para observar; el checkpoint es para
CONTINUAR o BIFURCAR la dinámica (worldlines hijas). Gate: corrida directa vs
checkpoint→restore→continuación deben ser BIT-exactas.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Sequence

import numpy as np

from ..physics.state import Layer, NodeSpec, NodeState

if TYPE_CHECKING:                       # el motor NO se importa en runtime de módulo: este
    from ..engine.network import Network  # módulo lo consumen los instrumentos (F4 A7)


def spec_fingerprint(spec: NodeSpec) -> str:
    """Huella de la CONSTITUCIÓN (sin e_ref, que muta por política/checkpoint). Una continuación
    con constitución distinta debe FALLAR FUERTE, no divergir en silencio (double tap F3 A4:
    gamma×1.5 era aceptado con divergencia 1.1e-06 y cero excepción)."""
    cuerpo = {
        "modes": [(m.layer.name, m.index, m.omega0, m.mass, m.gamma) for m in spec.modes],
        "intra": [(pr.i_idx, pr.j_idx, pr.k0, pr.layer.name) for pr in spec.intra_pairs],
        "direct": [(lk.deep_idx, lk.shallow_idx, lk.g0, lk.shallow_layer.name)
                   for lk in spec.direct_links],
        "mem": {layer.name: {c: getattr(spec.layer_mem[layer], c).tolist()
                             for c in ("tau0", "beta_tau", "a", "beta", "g", "kappa")}
                for layer in spec.layer_mem},
        "mem_order": [l.name for l in spec.mem_layer_order],
        "W": spec.W.tolist(),
        "struct": {l.name: (spec.struct.tau_e[l], spec.struct.tau_b[l], spec.struct.alpha_b[l])
                   for l in spec.layers_present},
        "emission_scale": spec.emission_scale,
    }
    return hashlib.sha256(json.dumps(cuerpo, sort_keys=True).encode("utf-8")).hexdigest()


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
        # A4: los parámetros del motor y la topología VIAJAN — restaurar sin ellos producía
        # k_global=0.0 silencioso con divergencia 3.6e-04 (double tap F3)
        "k_global": net.k_global, "gamma_c": net.gamma_c,
        "edges": {"ij": net.edge_ij.tolist(), "w_k": net.edge_w_k.tolist(),
                  "w_gamma": net.edge_w_g.tolist(), "tau": net.edge_tau.tolist()},
        "spec_fingerprints": [spec_fingerprint(sp) for sp in net.specs],
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


def network_from_checkpoint(specs: Sequence[NodeSpec], ck: Dict) -> Network:
    """Reconstruye la red para CONTINUAR — TODO sale de la meta del checkpoint (parámetros,
    topología) y la constitución se VERIFICA por huella fail-loud. Cero kwargs: una continuación
    con otros parámetros no es una continuación, es otra corrida (se construye Network directo
    y se declara hija con su propio linaje)."""
    from ..engine.network import Network   # acá SÍ se construye el motor: import local
    meta = ck["meta"]
    if len(specs) != int(meta["n_nodes"]):
        raise ValueError(f"specs: {len(specs)} != n_nodes {meta['n_nodes']} del checkpoint")
    for j, sp in enumerate(specs):
        fp = spec_fingerprint(sp)
        if fp != meta["spec_fingerprints"][j]:
            raise ValueError(
                f"nodo {j}: la CONSTITUCIÓN no es la de la corrida madre "
                f"({fp[:12]} != {meta['spec_fingerprints'][j][:12]}) — una continuación con "
                "otra física no puede ser silenciosa (double tap F3 A4)")
    for sp, erefs in zip(specs, meta["e_ref_por_nodo"]):
        for lname, val in erefs.items():
            sp.struct.e_ref[Layer[lname]] = float(val)
    ed = meta["edges"]
    edges = [{"i": int(ij[0]), "j": int(ij[1]), "w_k": wk, "w_gamma": wg, "tau": tv}
             for ij, wk, wg, tv in zip(ed["ij"], ed["w_k"], ed["w_gamma"], ed["tau"])]
    net = Network(specs, ck["states"], edges, dt=float(meta["dt"]), seed=int(meta["seed"]),
                  temperature=float(meta["temperature"]),
                  k_global=float(meta["k_global"]), coupling_gamma_c=float(meta["gamma_c"]),
                  history_init=(ck["buffer"], ck["head"]),
                  rng_state=meta["rng_state"])
    # LINAJE ADHERIDO (F6, patrón A5 de F5): una red restaurada lo lleva puesto — el recorder
    # EXIGE que el film declare de qué checkpoint nació; una hija sin linaje no se graba.
    # El ESTAMPADO del checkpoint (run_id/manifest_sha/intervenida_linaje/composicion —
    # double tap F6 A3/A5) viaja al origen: el padre no se inventa y el estado intervenido
    # o compuesto NO se lava en una generación.
    origen = {"sha256": ck["sha256"], "tick": int(meta["tick"])}
    extra = meta.get("extra") or {}
    for clave in ("run_id", "manifest_sha", "intervenida_linaje"):
        if clave in extra:
            origen[clave] = extra[clave]
    net.origen_checkpoint = origen
    if extra.get("composicion"):
        net.composicion_recibo = extra["composicion"]   # el enforcement F5-A5 dispara solo
    return net
