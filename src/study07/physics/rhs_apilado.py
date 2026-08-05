"""derivatives_apilado — transcripción CERTIFICADA de physics/rhs.py al eje N
[SPEC_MOTOR_TAU_V1 §9 + enmienda PHYSICS_CONTRACT 2026-08-05].

physics/rhs.py queda INTOCADO como LA referencia. Esta transcripción vectoriza sobre
el eje onion (habilitado por todos-iguales: UN NodeSpec compartido) preservando el
ORDEN EXACTO de operaciones por onion (cada op escalar de la referencia pasa a la
misma op elementwise (N,) en la MISMA secuencia — condición medida para diff==0).
DIFERENCIA DECLARADA DE LEY (no de transcripción): el campo externo entra POR MODO
(f_ext (N, n_modes)) en vez del escalar uniforme del §1.5 v1 — la identidad de
recepción del caldo (contrato v1 §3.1). Con f_ext=0 la igualdad con la referencia es
EXACTA (doble gate: test elementwise + guarda 1 integral).
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from .state import CLAMP_TANH_ARG, EPS_K, EPS_OMEGA, MEM_FORCE_SCALE, Layer, NodeSpec


def derivatives_apilado(spec: NodeSpec, x: np.ndarray, v: np.ndarray, z: np.ndarray,
                        b: np.ndarray, e: np.ndarray, f_ext: np.ndarray):
    """dX/dt apilado. x,v: (N, n_modes); z: (N, n_z); b,e: (N, n_layers);
    f_ext: (N, n_modes) — fuerza externa POR MODO (caldo: solo modos S ≠ 0)."""
    li = {layer: i for i, layer in enumerate(spec.layers_present)}
    n = x.shape[0]

    dx = v.copy()                                                   # §1: dx = v
    dv = np.zeros_like(v)
    dz = np.zeros_like(z)
    db = np.zeros_like(b)
    de = np.zeros_like(e)

    # (1) on-site + fricción — mismo orden por modo
    for p, m in enumerate(spec.modes):
        omega_eff2 = m.omega0 ** 2 * (1.0 + EPS_OMEGA * b[:, li[m.layer]])
        dv[:, p] += -omega_eff2 * x[:, p] - m.gamma * v[:, p]

    # (2) intra-capa
    for pr in spec.intra_pairs:
        k_eff = pr.k0 * (1.0 + EPS_K * b[:, li[pr.layer]])
        dv[:, pr.i_idx] += -k_eff * (x[:, pr.i_idx] - x[:, pr.j_idx]) / spec.modes[pr.i_idx].mass
        dv[:, pr.j_idx] += -k_eff * (x[:, pr.j_idx] - x[:, pr.i_idx]) / spec.modes[pr.j_idx].mass

    # (3) links directos inter-capa
    for lk in spec.direct_links:
        g_eff = lk.g0 * (1.0 + EPS_K * b[:, li[lk.shallow_layer]])
        dv[:, lk.shallow_idx] += -g_eff * (x[:, lk.shallow_idx] - x[:, lk.deep_idx]) / spec.modes[lk.shallow_idx].mass
        dv[:, lk.deep_idx] += -g_eff * (x[:, lk.deep_idx] - x[:, lk.shallow_idx]) / spec.modes[lk.deep_idx].mass

    # (4) memoria activa — transcripción del bloque completo
    mem_energy: Dict[Layer, np.ndarray] = {}
    for (layer, k), idx_z in spec.mem_index.items():
        params = spec.layer_mem.get(layer)
        if params is None:
            continue
        prev = mem_energy.get(layer)
        term = 0.5 * params.kappa[k] * z[:, idx_z] ** 2
        mem_energy[layer] = term if prev is None else prev + term

    # e_inst = layer_energies transcrito (mismo orden de acumulación por modo)
    energies: Dict[Layer, np.ndarray] = {layer: np.zeros(n) for layer in spec.layers_present}
    for p, m in enumerate(spec.modes):
        b_idx = spec.layers_present.index(m.layer)
        omega_eff2 = m.omega0 ** 2 * (1.0 + EPS_OMEGA * b[:, b_idx])
        energies[m.layer] = energies[m.layer] + (
            0.5 * m.mass * v[:, p] ** 2 + 0.5 * m.mass * omega_eff2 * x[:, p] ** 2)
    for layer, e_mem in mem_energy.items():
        if layer in energies:
            energies[layer] = energies[layer] + e_mem

    # señales por capa: np.mean sobre los MISMOS índices (mismo algoritmo por onion)
    signals = {layer: np.mean(x[:, list(spec.layer_indices[layer])], axis=1)
               for layer in spec.layer_indices}
    orden = list(spec.mem_layer_order)
    if orden:
        signals_mat = np.stack([signals.get(layer, np.zeros(n)) for layer in orden],
                               axis=1)                              # (N, L)
        # W @ signals por onion — acumulación explícita en orden j (certificable)
        input_mat = np.zeros((n, len(orden)))
        for fila in range(spec.W.shape[0]):
            acum = np.zeros(n)
            for col in range(spec.W.shape[1]):
                acum = acum + spec.W[fila, col] * signals_mat[:, col]
            input_mat[:, fila] = acum
        input_by_layer = {layer: input_mat[:, i] for i, layer in enumerate(orden)}
    else:
        input_by_layer = {}

    mem_force: Dict[Layer, np.ndarray] = {}
    for layer, params in spec.layer_mem.items():
        if layer not in spec.layer_indices:
            continue
        energy_layer = energies.get(layer, np.zeros(n))
        input_layer = input_by_layer.get(layer, np.zeros(n))
        for k in range(len(params.tau0)):
            idx_z = spec.mem_index[(layer, k)]
            tau_eff = np.maximum(params.tau0[k] * (1.0 + params.beta_tau[k] * energy_layer), 1e-9)
            u_clamped = np.clip(params.beta[k] * input_layer, -CLAMP_TANH_ARG, CLAMP_TANH_ARG)
            dz[:, idx_z] = -z[:, idx_z] / tau_eff + params.a[k] * np.tanh(u_clamped)
            prev = mem_force.get(layer)
            term = MEM_FORCE_SCALE * params.g[k] * z[:, idx_z]
            mem_force[layer] = term if prev is None else prev + term

    for layer, force in mem_force.items():
        for idx in spec.layer_indices.get(layer, ()):
            dv[:, idx] += -force / spec.modes[idx].mass

    # (5) CAMPO EXTERNO POR MODO — la ley del caldo (identidad de recepción)
    for idx in range(spec.n_modes):
        dv[:, idx] += f_ext[:, idx] / spec.modes[idx].mass

    # (6) variables lentas
    for layer, idx in li.items():
        st = spec.struct
        de[:, idx] = (energies[layer] - e[:, idx]) / st.tau_e[layer]
        db[:, idx] = (-b[:, idx] + st.alpha_b[layer] * (e[:, idx] - st.e_ref[layer])) / st.tau_b[layer]

    return dx, dv, dz, db, de
