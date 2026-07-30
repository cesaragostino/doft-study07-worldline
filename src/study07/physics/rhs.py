"""RHS del nodo — PHYSICS_CONTRACT §1, transcripción de physics_core.py:464-592 del oráculo.

UNA sola implementación de la fuerza (contrato §9): no existe ni existirá una segunda copia.
El orden de acumulación está SELLADO: self → intra → direct → memoria → drive → b/e.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from .state import (CLAMP_TANH_ARG, EPS_K, EPS_OMEGA, MEM_FORCE_SCALE, Layer, NodeSpec,
                    NodeState)


def layer_energies(spec: NodeSpec, state: NodeState, mem_energy: Dict[Layer, float]) -> Dict[Layer, float]:
    """E_inst por capa (contrato §1.4; oráculo :426-454): on-site con la MISMA b de la fuerza,
    más la energía de memoria ½·kappa·z²."""
    energies = {layer: 0.0 for layer in spec.layers_present}
    for p, m in enumerate(spec.modes):
        b_idx = spec.layers_present.index(m.layer)
        omega_eff2 = m.omega0 ** 2 * (1.0 + EPS_OMEGA * state.b[b_idx])
        energies[m.layer] += 0.5 * m.mass * state.v[p] ** 2 + 0.5 * m.mass * omega_eff2 * state.x[p] ** 2
    for layer, e_mem in mem_energy.items():
        if layer in energies:
            energies[layer] += e_mem
    return energies


def derivatives(spec: NodeSpec, state: NodeState, drive_ext: float) -> NodeState:
    """dX/dt = f(X, drive_ext). drive_ext = fuerza KV de red (contrato §3), UNA por nodo,
    recibida por superposición en TODOS los modos (§1.5)."""
    li = {layer: i for i, layer in enumerate(spec.layers_present)}

    dx = state.v.copy()                                             # §1: dx = v
    dv = np.zeros_like(state.v)
    dz = np.zeros_like(state.z)
    db = np.zeros_like(state.b)
    de = np.zeros_like(state.e)

    # (1) on-site + fricción — SIN dividir por masa (así es la ley; contrato §1.1)
    for p, m in enumerate(spec.modes):
        omega_eff2 = m.omega0 ** 2 * (1.0 + EPS_OMEGA * state.b[li[m.layer]])
        dv[p] += -omega_eff2 * state.x[p] - m.gamma * state.v[p]

    # (2) intra-capa (§1.2)
    for pr in spec.intra_pairs:
        k_eff = pr.k0 * (1.0 + EPS_K * state.b[li[pr.layer]])
        dv[pr.i_idx] += -k_eff * (state.x[pr.i_idx] - state.x[pr.j_idx]) / spec.modes[pr.i_idx].mass
        dv[pr.j_idx] += -k_eff * (state.x[pr.j_idx] - state.x[pr.i_idx]) / spec.modes[pr.j_idx].mass

    # (3) links directos inter-capa — la b del canal es la de la capa SHALLOW (§1.3)
    for lk in spec.direct_links:
        g_eff = lk.g0 * (1.0 + EPS_K * state.b[li[lk.shallow_layer]])
        dv[lk.shallow_idx] += -g_eff * (state.x[lk.shallow_idx] - state.x[lk.deep_idx]) / spec.modes[lk.shallow_idx].mass
        dv[lk.deep_idx] += -g_eff * (state.x[lk.deep_idx] - state.x[lk.shallow_idx]) / spec.modes[lk.deep_idx].mass

    # (4) memoria activa por capa (§1.4)
    mem_energy: Dict[Layer, float] = {}
    for (layer, k), idx_z in spec.mem_index.items():
        params = spec.layer_mem.get(layer)
        if params is None:
            continue
        mem_energy[layer] = mem_energy.get(layer, 0.0) + 0.5 * params.kappa[k] * state.z[idx_z] ** 2

    e_inst = layer_energies(spec, state, mem_energy)

    signals = {layer: float(np.mean([state.x[i] for i in spec.layer_indices[layer]]))
               for layer in spec.layer_indices}
    signals_vec = np.array([signals.get(layer, 0.0) for layer in spec.mem_layer_order])
    input_vec = spec.W @ signals_vec if signals_vec.size else np.array([])
    input_by_layer = ({layer: input_vec[i] for i, layer in enumerate(spec.mem_layer_order)}
                      if input_vec.size else {})

    mem_force: Dict[Layer, float] = {}
    for layer, params in spec.layer_mem.items():
        if layer not in spec.layer_indices:
            continue
        energy_layer = e_inst.get(layer, 0.0)
        input_layer = input_by_layer.get(layer, 0.0)
        for k in range(len(params.tau0)):
            idx_z = spec.mem_index[(layer, k)]
            tau_eff = max(params.tau0[k] * (1.0 + params.beta_tau[k] * energy_layer), 1e-9)
            u_clamped = float(np.clip(params.beta[k] * input_layer, -CLAMP_TANH_ARG, CLAMP_TANH_ARG))
            dz[idx_z] = -state.z[idx_z] / tau_eff + params.a[k] * np.tanh(u_clamped)
            mem_force[layer] = mem_force.get(layer, 0.0) + MEM_FORCE_SCALE * params.g[k] * state.z[idx_z]

    for layer, force in mem_force.items():
        for idx in spec.layer_indices.get(layer, ()):
            dv[idx] += -force / spec.modes[idx].mass

    # (5) recepción del campo externo por superposición (§1.5)
    if drive_ext != 0.0:
        for idx in range(spec.n_modes):
            dv[idx] += float(drive_ext) / spec.modes[idx].mass

    # (6) variables lentas (§1.6)
    for layer, idx in li.items():
        st = spec.struct
        de[idx] = (e_inst[layer] - state.e[idx]) / st.tau_e[layer]
        db[idx] = (-state.b[idx] + st.alpha_b[layer] * (state.e[idx] - st.e_ref[layer])) / st.tau_b[layer]

    return NodeState(x=dx, v=dv, z=dz, b=db, e=de)


def emitted_xv(spec: NodeSpec, state: NodeState) -> np.ndarray:
    """Coordenada EMITIDA (contrato §4): superposición de todos los modos × emission_scale."""
    return spec.emission_scale * np.array([float(np.sum(state.x)), float(np.sum(state.v))])
