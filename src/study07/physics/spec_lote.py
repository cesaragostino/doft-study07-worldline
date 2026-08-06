"""SpecLote — población heterogénea con ARQUITECTURA COMPARTIDA [M2-build 1; §35].

N NodeSpecs distintos (los genomas del gimnasio) que comparten TOPOLOGÍA: mismos
conteos (n_modes, n_z, n_layers), misma capa por índice de modo, mismos pares
intra/links directos (índices y capa), mismo mem_index y mem_layer_order. Los
PARÁMETROS numéricos (ω, γ, m, k0, g0, W, memoria, struct) difieren por onion y se
apilan como arrays (N, ...) para el kernel het. Validación FAIL-LOUD: cualquier
divergencia de arquitectura es excepción, no silencio. El caso N-idénticos debe
reproducir el kernel homogéneo BIT-EXACTO (test de regresión — caldo 1 sigue válido).
"""
from __future__ import annotations

from typing import List, Sequence

import numpy as np

from .state import NodeSpec


class SpecLote:
    def __init__(self, specs: Sequence[NodeSpec], genoma_ids: Sequence[str]) -> None:
        if len(specs) != len(genoma_ids):
            raise ValueError("SpecLote: len(specs) != len(genoma_ids)")
        s0 = specs[0]
        for k, s in enumerate(specs[1:], 1):
            if s.n_modes != s0.n_modes or s.n_z != s0.n_z or s.n_layers != s0.n_layers:
                raise ValueError(f"SpecLote: conteos difieren en spec {k} (arquitectura)")
            if tuple(m.layer for m in s.modes) != tuple(m.layer for m in s0.modes):
                raise ValueError(f"SpecLote: capa-por-modo difiere en spec {k}")
            if [(p.i_idx, p.j_idx, p.layer) for p in s.intra_pairs] != \
               [(p.i_idx, p.j_idx, p.layer) for p in s0.intra_pairs]:
                raise ValueError(f"SpecLote: intra_pairs difieren en spec {k}")
            if [(l.shallow_idx, l.deep_idx, l.shallow_layer) for l in s.direct_links] != \
               [(l.shallow_idx, l.deep_idx, l.shallow_layer) for l in s0.direct_links]:
                raise ValueError(f"SpecLote: direct_links difieren en spec {k}")
            if s.mem_index != s0.mem_index or tuple(s.mem_layer_order) != tuple(s0.mem_layer_order):
                raise ValueError(f"SpecLote: estructura de memoria difiere en spec {k}")
            if tuple(s.layers_present) != tuple(s0.layers_present):
                raise ValueError(f"SpecLote: layers_present difiere en spec {k}")
            if s.W.shape != s0.W.shape:
                raise ValueError(f"SpecLote: shape de W difiere en spec {k}")
        self.specs: List[NodeSpec] = list(specs)
        self.genoma_ids = [str(g) for g in genoma_ids]
        self.n = len(specs)
        self.ref = s0                      # arquitectura (índices, capas, orden)
        n, nm = self.n, s0.n_modes
        self.omega0 = np.array([[m.omega0 for m in s.modes] for s in specs])   # (N, nm)
        self.gamma = np.array([[m.gamma for m in s.modes] for s in specs])
        self.mass = np.array([[m.mass for m in s.modes] for s in specs])
        self.k0 = np.array([[p.k0 for p in s.intra_pairs] for s in specs])     # (N, nP)
        self.g0 = np.array([[l.g0 for l in s.direct_links] for s in specs])    # (N, nL)
        self.W = np.array([s.W for s in specs])                                # (N, L, L)
        # memoria: por (layer, k) → arrays (N,)
        self.mem = {}
        for (layer, k) in s0.mem_index:
            self.mem[(layer, k)] = {
                nombre: np.array([getattr(s.layer_mem[layer], nombre)[k] for s in specs])
                for nombre in ("kappa", "tau0", "beta_tau", "beta", "a", "g")}
        # struct: por capa → arrays (N,)
        self.tau_e = {ly: np.array([s.struct.tau_e[ly] for s in specs])
                      for ly in s0.layers_present}
        self.tau_b = {ly: np.array([s.struct.tau_b[ly] for s in specs])
                      for ly in s0.layers_present}
        self.alpha_b = {ly: np.array([s.struct.alpha_b[ly] for s in specs])
                        for ly in s0.layers_present}
        self.e_ref = {ly: np.array([s.struct.e_ref[ly] for s in specs])
                      for ly in s0.layers_present}
