"""Instrumento de ENERGÍA por capa — segunda vista (F4).

E[capa] = Σ_p∈capa ½·m·v² + ½·m·ω0²·(1+eps_omega·b[capa])·x²  +  Σ_k ½·kappa·z²
[oráculo physics_core.py:426-454 + NodeOscillator.energies :377-390]

Requiere la CONSTITUCIÓN (masas/ω0/kappa no viven en el film): entrada DECLARADA, con su
procedencia registrada en la vista. Usa el parser de compat (read-only) — jamás el motor.
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, List

import numpy as np

from ..compat.study06_v4 import parse_theta_v2
from ..physics.state import EPS_OMEGA
from .api import View, exigir_canales

INSTRUMENT_ID = "layer_energy"
VERSION = "1.0"
CAPAS = ("Q", "S1", "S2")


def run(wl: Dict, thetas_constitucion: List[dict],
        observation_config: Dict | None = None) -> View:
    cfg = {"t0_tick": 0, "t1_tick": None, "stride": 1, **(observation_config or {})}
    exigir_canales(wl, ["estados", "manifest", "worldline_hash"])
    man = wl["manifest"]
    if len(thetas_constitucion) != int(man["n_nodes"]):
        raise RuntimeError("constitución: cantidad de nodos no coincide con el film")
    t1 = cfg["t1_tick"] if cfg["t1_tick"] is not None else len(wl["ticks"]) - 1
    sel = np.arange(int(cfg["t0_tick"]), int(t1) + 1, int(cfg["stride"]))

    e_capa = np.zeros((sel.size, int(man["n_nodes"]), 3))
    for j, theta_int in enumerate(thetas_constitucion):
        spec, _ = parse_theta_v2(theta_int, emission_scale=1.0)   # la emisión no afecta E
        n = spec.n_modes
        est = wl["estados"][j][sel]
        x = est[:, :n]; v = est[:, n:2 * n]
        z = est[:, 2 * n:2 * n + spec.n_z]
        b = est[:, 2 * n + spec.n_z:2 * n + spec.n_z + spec.n_layers]
        li = {layer: i for i, layer in enumerate(spec.layers_present)}
        # ESPEJO ESCALAR de compute_layer_energies (physics_core.py:426-454) vía energies()
        # (:377-390): la vectorización difiere en el último ulp (array**2 = x·x vs pow escalar,
        # asociación de la memoria) y el gate exige 0.0 exacto en el entorno del generador.
        # Mismo orden: memoria acumulada APARTE por capa (orden mem_index) y sumada UNA vez.
        kap = {(layer, k): spec.layer_mem[layer].kappa[k]
               for (layer, k) in spec.mem_index}
        for row in range(sel.size):
            xe, ve, ze, be = x[row], v[row], z[row], b[row]
            mem = {}
            for (layer, k), idx_z in spec.mem_index.items():
                mem[layer] = mem.get(layer, 0.0) + 0.5 * kap[(layer, k)] * ze[idx_z] ** 2
            acc = {layer: 0.0 for layer in spec.layers_present}
            for p, m in enumerate(spec.modes):
                oe2 = m.omega0 ** 2 * (1.0 + EPS_OMEGA * be[li[m.layer]])
                acc[m.layer] += 0.5 * m.mass * ve[p] ** 2 + 0.5 * m.mass * oe2 * xe[p] ** 2
            for layer, e_mem in mem.items():
                if layer in acc:
                    acc[layer] += e_mem
            for layer, val in acc.items():
                e_capa[row, j, CAPAS.index(layer.name)] = val

    huella = hashlib.sha256(json.dumps(thetas_constitucion, sort_keys=True,
                                       default=str).encode("utf-8")).hexdigest()
    return View(INSTRUMENT_ID, VERSION, cfg, wl["worldline_hash"],
                {"ticks": wl["ticks"][sel], "e_capa": e_capa},
                {"constitucion_sha256": huella, "capas": list(CAPAS)})
