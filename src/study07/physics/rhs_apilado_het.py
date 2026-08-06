"""derivatives_apilado_het — kernel apilado HETEROGÉNEO [M2-build 1; §35].

Transcripción del kernel certificado rhs_apilado.py con parámetros POR ONION
(SpecLote): cada escalar de spec (ω, γ, m, k0, g0, W, memoria, struct) pasa a su
columna (N,) en la MISMA secuencia de operaciones — como las ops son elementwise,
la aritmética de cada onion es EXACTAMENTE la del kernel homogéneo con su propio
genoma ⇒ el gate de certificación es diff==0 POR GENOMA contra physics/rhs.py
(intocado, LA referencia) Y bit-igualdad con derivatives_apilado en el caso
N-idénticos (regresión: caldo 1 sigue válido). f_ext POR MODO como el homogéneo.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from .spec_lote import SpecLote
from .state import CLAMP_TANH_ARG, EPS_K, EPS_OMEGA, MEM_FORCE_SCALE, Layer


def derivatives_apilado_het(lote: SpecLote, x: np.ndarray, v: np.ndarray,
                            z: np.ndarray, b: np.ndarray, e: np.ndarray,
                            f_ext: np.ndarray):
    spec = lote.ref
    li = {layer: i for i, layer in enumerate(spec.layers_present)}
    n = x.shape[0]

    dx = v.copy()
    dv = np.zeros_like(v)
    dz = np.zeros_like(z)
    db = np.zeros_like(b)
    de = np.zeros_like(e)

    # (1) on-site + fricción
    for p, m in enumerate(spec.modes):
        omega_eff2 = lote.omega0[:, p] ** 2 * (1.0 + EPS_OMEGA * b[:, li[m.layer]])
        dv[:, p] += -omega_eff2 * x[:, p] - lote.gamma[:, p] * v[:, p]

    # (2) intra-capa
    for q, pr in enumerate(spec.intra_pairs):
        k_eff = lote.k0[:, q] * (1.0 + EPS_K * b[:, li[pr.layer]])
        dv[:, pr.i_idx] += -k_eff * (x[:, pr.i_idx] - x[:, pr.j_idx]) / lote.mass[:, pr.i_idx]
        dv[:, pr.j_idx] += -k_eff * (x[:, pr.j_idx] - x[:, pr.i_idx]) / lote.mass[:, pr.j_idx]

    # (3) links directos inter-capa
    for q, lk in enumerate(spec.direct_links):
        g_eff = lote.g0[:, q] * (1.0 + EPS_K * b[:, li[lk.shallow_layer]])
        dv[:, lk.shallow_idx] += -g_eff * (x[:, lk.shallow_idx] - x[:, lk.deep_idx]) / lote.mass[:, lk.shallow_idx]
        dv[:, lk.deep_idx] += -g_eff * (x[:, lk.deep_idx] - x[:, lk.shallow_idx]) / lote.mass[:, lk.deep_idx]

    # (4) memoria activa
    mem_energy: Dict[Layer, np.ndarray] = {}
    for (layer, k), idx_z in spec.mem_index.items():
        if layer not in spec.layer_mem:
            continue
        prev = mem_energy.get(layer)
        term = 0.5 * lote.mem[(layer, k)]["kappa"] * z[:, idx_z] ** 2
        mem_energy[layer] = term if prev is None else prev + term

    energies: Dict[Layer, np.ndarray] = {layer: np.zeros(n) for layer in spec.layers_present}
    for p, m in enumerate(spec.modes):
        b_idx = spec.layers_present.index(m.layer)
        omega_eff2 = lote.omega0[:, p] ** 2 * (1.0 + EPS_OMEGA * b[:, b_idx])
        energies[m.layer] = energies[m.layer] + (
            0.5 * lote.mass[:, p] * v[:, p] ** 2
            + 0.5 * lote.mass[:, p] * omega_eff2 * x[:, p] ** 2)
    for layer, e_mem in mem_energy.items():
        if layer in energies:
            energies[layer] = energies[layer] + e_mem

    signals = {layer: np.mean(x[:, list(spec.layer_indices[layer])], axis=1)
               for layer in spec.layer_indices}
    orden = list(spec.mem_layer_order)
    if orden:
        signals_mat = np.stack([signals.get(layer, np.zeros(n)) for layer in orden],
                               axis=1)
        input_mat = np.zeros((n, len(orden)))
        for fila in range(spec.W.shape[0]):
            acum = np.zeros(n)
            for col in range(spec.W.shape[1]):
                acum = acum + lote.W[:, fila, col] * signals_mat[:, col]
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
            pm = lote.mem[(layer, k)]
            tau_eff = np.maximum(pm["tau0"] * (1.0 + pm["beta_tau"] * energy_layer), 1e-9)
            u_clamped = np.clip(pm["beta"] * input_layer, -CLAMP_TANH_ARG, CLAMP_TANH_ARG)
            dz[:, idx_z] = -z[:, idx_z] / tau_eff + pm["a"] * np.tanh(u_clamped)
            prev = mem_force.get(layer)
            term = MEM_FORCE_SCALE * pm["g"] * z[:, idx_z]
            mem_force[layer] = term if prev is None else prev + term

    for layer, force in mem_force.items():
        for idx in spec.layer_indices.get(layer, ()):
            dv[:, idx] += -force / lote.mass[:, idx]

    # (5) campo externo por modo
    for idx in range(spec.n_modes):
        dv[:, idx] += f_ext[:, idx] / lote.mass[:, idx]

    # (6) variables lentas
    for layer, idx in li.items():
        de[:, idx] = (energies[layer] - e[:, idx]) / lote.tau_e[layer]
        db[:, idx] = (-b[:, idx] + lote.alpha_b[layer] * (e[:, idx] - lote.e_ref[layer])) / lote.tau_b[layer]

    return dx, dv, dz, db, de
