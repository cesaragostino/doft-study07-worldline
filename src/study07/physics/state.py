"""Tipos del estado causal y de la constitución de un nodo — PHYSICS_CONTRACT §0.

Este paquete es agnóstico de nivel (cláusula 1 de COA): acá no existen niveles de composición,
sólo nodos con física interna completa y una red que los integra concurrentemente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Tuple

import numpy as np


class Layer(Enum):
    Q = auto()
    S1 = auto()
    S2 = auto()


# orden canónico de capas (PHYSICS_CONTRACT §0; oráculo physics_core._layer_order)
LAYER_CANON = (Layer.Q, Layer.S1, Layer.S2)


def layer_order(layers) -> List[Layer]:
    seen = []
    for layer in LAYER_CANON:
        if layer in layers and layer not in seen:
            seen.append(layer)
    return seen


@dataclass(frozen=True)
class Mode:
    layer: Layer
    index: int
    omega0: float
    mass: float
    gamma: float


@dataclass(frozen=True)
class IntraPair:
    """Resorte intra-capa ya resuelto a índices de modo (contrato §1.2)."""
    i_idx: int
    j_idx: int
    k0: float
    layer: Layer


@dataclass(frozen=True)
class DirectLink:
    """Resorte directo inter-capa g0 (contrato §1.3) — lo ÚNICO que cruza capas como fuerza."""
    deep_idx: int
    shallow_idx: int
    g0: float
    shallow_layer: Layer


@dataclass(frozen=True)
class LayerMemory:
    """Memoria activa de UNA capa (contrato §0/§1.4) — heredada EXACTA, jamás re-sorteada."""
    tau0: np.ndarray
    beta_tau: np.ndarray
    a: np.ndarray
    beta: np.ndarray
    g: np.ndarray
    kappa: np.ndarray


@dataclass(frozen=True)
class StructParams:
    tau_e: Dict[Layer, float]
    tau_b: Dict[Layer, float]
    alpha_b: Dict[Layer, float]
    e_ref: Dict[Layer, float]  # mutable por política e_ref (§7.2) ANTES de congelar el spec


@dataclass(frozen=True)
class NodeSpec:
    """Constitución completa de un nodo. Inmutable durante la integración."""
    modes: Tuple[Mode, ...]
    intra_pairs: Tuple[IntraPair, ...]
    direct_links: Tuple[DirectLink, ...]
    layer_mem: Dict[Layer, LayerMemory]
    mem_layer_order: Tuple[Layer, ...]           # orden de capas de W (memoria serializada)
    W: np.ndarray                                # mixing capa×capa
    mem_index: Dict[Tuple[Layer, int], int]      # (capa, k) -> idx_z
    struct: StructParams
    layers_present: Tuple[Layer, ...]            # orden canónico de b/e
    layer_indices: Dict[Layer, Tuple[int, ...]]  # capa -> índices de modo
    emission_scale: float                        # §4: 1.0 ("sum") o 1/n_modes ("mean")

    @property
    def n_modes(self) -> int:
        return len(self.modes)

    @property
    def n_z(self) -> int:
        return len(self.mem_index)

    @property
    def n_layers(self) -> int:
        return len(self.layers_present)


@dataclass
class NodeState:
    """Estado causal X = (x, v, z, b, e) — contrato §0. float64 siempre."""
    x: np.ndarray
    v: np.ndarray
    z: np.ndarray
    b: np.ndarray
    e: np.ndarray

    def copy(self) -> "NodeState":
        return NodeState(self.x.copy(), self.v.copy(), self.z.copy(), self.b.copy(), self.e.copy())


def state_add(s: NodeState, k: NodeState, coef: float) -> NodeState:
    """s + coef·k campo a campo (sub-pasos RK4, contrato §5)."""
    return NodeState(
        x=s.x + coef * k.x, v=s.v + coef * k.v, z=s.z + coef * k.z,
        b=s.b + coef * k.b, e=s.e + coef * k.e,
    )


def rk4_combine(s0: NodeState, k1: NodeState, k2: NodeState, k3: NodeState,
                k4: NodeState, dt: float) -> NodeState:
    """X_next = X_0 + dt/6·(k1 + 2k2 + 2k3 + k4) campo a campo (contrato §5)."""
    c = dt / 6.0
    return NodeState(
        x=s0.x + c * (k1.x + 2 * k2.x + 2 * k3.x + k4.x),
        v=s0.v + c * (k1.v + 2 * k2.v + 2 * k3.v + k4.v),
        z=s0.z + c * (k1.z + 2 * k2.z + 2 * k3.z + k4.z),
        b=s0.b + c * (k1.b + 2 * k2.b + 2 * k3.b + k4.b),
        e=s0.e + c * (k1.e + 2 * k2.e + 2 * k3.e + k4.e),
    )


# Constantes CONGELADAS del contrato de simulación (§2) — explícitas, no defaults ocultos.
EPS_OMEGA = 0.1
EPS_K = 0.1
CLAMP_TANH_ARG = 5.0
MEM_FORCE_SCALE = 1.0
