"""Lector EXPLÍCITO de constituciones theta_internal_v2 de Study06 — read-only, sin importar
código del oráculo (dependencias unidireccionales). PHYSICS_CONTRACT §7.

Reglas heredadas fail-loud: capa 'eff' RECHAZADA · capas fuera de Q/S1/S2 RECHAZADAS ·
adaptive_couplings RECHAZADO · v2 hereda memoria y struct_params EXACTOS (sin re-sorteo) ·
el kernel taus0/amps0 se parsea y DESCARTA con warning VISIBLE (ley v1 direct-only).
V3 y anteriores: fuera de alcance (el plan §20 exige rechazo explícito de V3).
"""
from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from ..physics.state import (DirectLink, IntraPair, Layer, LayerMemory, Mode, NodeSpec,
                             NodeState, StructParams, layer_order)
from ..physics import rhs


def _layer(name: str) -> Layer:
    if name == "eff":
        raise RuntimeError("capa 'eff' (partícula efectiva): RECHAZADA — la reducción no es física")
    try:
        return Layer[name]
    except KeyError as exc:
        raise RuntimeError(f"capa desconocida {name!r} (Q/S1/S2 solamente)") from exc


def node_seed(seed: int, idx: int) -> int:
    """Derivación de semilla por nodo — contrato §6 (oráculo hash_text sha256 + [:8])."""
    h = hashlib.sha256(f"{seed}|node|{idx}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) & 0xFFFFFFFF


def parse_theta_v2(theta: dict, emission_scale: float) -> Tuple[NodeSpec, Dict]:
    """theta_internal_v2 → NodeSpec. Devuelve además el dict de memoria/struct crudos por si el
    caller quiere sellar hashes de procedencia (PROVENANCE_CONTRACT)."""
    if theta.get("schema_version") != "theta_internal_v2":
        raise RuntimeError(
            f"schema_version={theta.get('schema_version')!r}: el lector sólo acepta "
            "theta_internal_v2 (V3/legacy: RECHAZO explícito — plan §20, gate de datos)")
    if theta.get("adaptive_couplings"):
        raise RuntimeError("theta trae adaptive_couplings (generación diagnóstica): RECHAZADO")

    modes: List[Mode] = []
    for raw in theta.get("modes", []) or []:
        modes.append(Mode(layer=_layer(raw["layer"]), index=int(raw.get("index", 0)),
                          omega0=float(raw.get("omega0", 0.0)), mass=float(raw.get("mass", 1.0)),
                          gamma=float(raw.get("gamma", 0.0))))
    if not modes:
        raise RuntimeError("theta sin modos")
    index_map = {(m.layer, m.index): i for i, m in enumerate(modes)}
    layers_present = tuple(layer_order([m.layer for m in modes]))
    layer_indices = {}
    for i, m in enumerate(modes):
        layer_indices.setdefault(m.layer, []).append(i)
    layer_indices = {k: tuple(v) for k, v in layer_indices.items()}

    intra: List[IntraPair] = []
    for raw in theta.get("intra_couplings", []) or []:
        i_l = _layer(raw["i"]["layer"]); j_l = _layer(raw["j"]["layer"])
        intra.append(IntraPair(
            i_idx=index_map[(i_l, int(raw["i"].get("index", 0)))],
            j_idx=index_map[(j_l, int(raw["j"].get("index", 0)))],
            k0=float(raw.get("k_ij0", 0.0)), layer=i_l))

    direct: List[DirectLink] = []
    kernel_terms = 0
    for raw in theta.get("inter_couplings", []) or []:
        deep = _layer(raw["deep_layer"]); shallow = _layer(raw["shallow_layer"])
        g0 = float(raw.get("g0", 0.0))
        vistos = set()
        for link in raw.get("links", []) or []:
            key = (deep.name, shallow.name, int(link.get("i_deep", 0)),
                   int(link.get("j_shallow", 0)))
            if key in vistos:
                raise RuntimeError(f"link inter duplicado {key}: RECHAZO (0 duplicados en v4 — "
                                   "un duplicado silencioso duplicaría la fuerza)")
            vistos.add(key)
            direct.append(DirectLink(
                deep_idx=index_map[(deep, int(link.get("i_deep", 0)))],
                shallow_idx=index_map[(shallow, int(link.get("j_shallow", 0)))],
                g0=g0, shallow_layer=shallow))
            kernel_terms += len(link.get("taus0", []) or [])
    if kernel_terms:
        warnings.warn(
            f"inter_couplings traen {kernel_terms} términos de kernel taus0/amps0 — la ley v1 "
            "direct-only los DESCARTA (PHYSICS_CONTRACT, kernel diferido con medición §93-C5). "
            "Este warning no se suprime jamás (CODE-PHY-011).", RuntimeWarning, stacklevel=2)

    memory_ser = theta.get("memory")
    if not (isinstance(memory_ser, dict) and memory_ser):
        raise RuntimeError("theta_internal_v2 sin memoria serializada: v1 legacy fuera de alcance")
    mem_layer_order = tuple(Layer[str(n)] for n in memory_ser["layer_order"])
    layer_mem: Dict[Layer, LayerMemory] = {}
    mem_index: Dict[Tuple[Layer, int], int] = {}
    zc = 0
    for layer in mem_layer_order:
        params = memory_ser["layers"].get(layer.name)
        if not params:
            continue
        n_mem = len(params["tau0"])
        for campo in ("beta_tau", "a", "beta", "g", "kappa"):
            if len(params[campo]) != n_mem:
                raise RuntimeError(f"memoria de {layer.name}: {campo} tiene "
                                   f"{len(params[campo])} términos, tau0 tiene {n_mem}")
        for k in range(n_mem):
            mem_index[(layer, k)] = zc
            zc += 1
        layer_mem[layer] = LayerMemory(
            tau0=np.asarray(params["tau0"], float), beta_tau=np.asarray(params["beta_tau"], float),
            a=np.asarray(params["a"], float), beta=np.asarray(params["beta"], float),
            g=np.asarray(params["g"], float), kappa=np.asarray(params["kappa"], float))
    for layer in layers_present:
        if layer not in mem_layer_order:
            raise RuntimeError(f"capa {layer.name} presente en modes pero FUERA de "
                               "memory.layer_order: RECHAZO (paridad con "
                               "validate_theta_internal del oráculo — double tap F5 A4)")
        if layer not in layer_mem:
            raise RuntimeError(f"capa {layer.name} presente y en layer_order pero SIN memoria: "
                               "RECHAZO (el continue silencioso era el defecto §7.1)")
    W = np.asarray(memory_ser["W"], float)
    if W.shape != (len(mem_layer_order), len(mem_layer_order)):
        raise RuntimeError(f"W {W.shape} no coincide con layer_order {len(mem_layer_order)}")

    struct_ser = theta.get("struct_params")
    if not (isinstance(struct_ser, dict) and struct_ser):
        raise RuntimeError("theta_internal_v2 sin struct_params serializados")
    tau_e, tau_b, alpha_b, e_ref = {}, {}, {}, {}
    for layer in layers_present:
        vals = struct_ser.get(layer.name)
        if not isinstance(vals, dict):
            raise RuntimeError(f"struct_params sin capa {layer.name}")
        if "e_ref" not in vals:
            raise RuntimeError(f"struct_params.{layer.name} sin e_ref: RECHAZO (450/450 capas "
                               "de v4 lo traen — un 0.0 silencioso cambia el punto fijo de b)")
        tau_e[layer] = float(vals["tau_e"]); tau_b[layer] = float(vals["tau_b"])
        alpha_b[layer] = float(vals["alpha_b"]); e_ref[layer] = float(vals["e_ref"])

    spec = NodeSpec(modes=tuple(modes), intra_pairs=tuple(intra), direct_links=tuple(direct),
                    layer_mem=layer_mem, mem_layer_order=mem_layer_order, W=W,
                    mem_index=mem_index,
                    struct=StructParams(tau_e=tau_e, tau_b=tau_b, alpha_b=alpha_b, e_ref=e_ref),
                    layers_present=layers_present, layer_indices=layer_indices,
                    emission_scale=emission_scale)
    return spec, {"memory": memory_ser, "struct": struct_ser}


def birth_state(spec: NodeSpec, seed: int, idx: int,
                e_ref_policy: str = "receiver_initial_energy") -> NodeState:
    """Estado de nacimiento — contrato §6/§7: x0/v0 ~ N(0, 1e-3) del rng derivado del nodo
    (EN ESE ORDEN de draws), z=b=0, e = E_inst(t0), e_ref según política."""
    if e_ref_policy not in {"receiver_initial_energy", "preserve_serialized"}:
        raise ValueError(f"e_ref_policy desconocida: {e_ref_policy!r}")
    rng = np.random.default_rng(node_seed(seed, idx))
    n = spec.n_modes
    x0 = rng.normal(scale=1e-3, size=n)
    v0 = rng.normal(scale=1e-3, size=n)
    state = NodeState(x=x0, v=v0, z=np.zeros(spec.n_z),
                      b=np.zeros(spec.n_layers), e=np.zeros(spec.n_layers))
    energies = rhs.layer_energies(spec, state, {})
    for i, layer in enumerate(spec.layers_present):
        state.e[i] = energies[layer]
        if e_ref_policy == "receiver_initial_energy":
            spec.struct.e_ref[layer] = energies[layer]
    return state


def load_canonical_blocks(blocks_json: Path) -> Dict[str, dict]:
    raw = json.load(open(blocks_json))
    blocks = raw["blocks"] if isinstance(raw, dict) and "blocks" in raw else raw
    return {b["block_id"]: b for b in blocks}
