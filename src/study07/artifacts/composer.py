"""Composición CONCURRENTE de una red desde constituyentes COMPLETOS (F5).

Cláusula 1 de COA ejecutada: el motor no interpreta proxies ni sabe de niveles — la red se
compone acá (constitución + estado + historia por constituyente) y el motor integra TODOS los
constituyentes juntos. Dos orígenes por nodo:
  · CÁPSULA (transporte): estado x/v/z/b/e + e_ref + ring de historia re-basado al delay del
    receptor (quench) — espejo de restore_specimen_capsules del oráculo
    [specimen_capsule.py:843-963], modo topology_quench.
  · NACIMIENTO (fresh): birth_state del contrato §6/§7 (x0/v0 térmicos del rng derivado del
    nodo, historia = relleno uniforme del ring con la emisión inicial — la semántica fresh
    del oráculo).
La MEZCLA cápsula+fresh en una misma red es capacidad NUEVA de study07 (el restore del
oráculo exige una cápsula por CADA nodo [oráculo :839-842]): sin referencia bit-exacta del
oráculo, DECLARADA — sus dos esquinas (todo-cápsula, todo-fresh) sí están ancladas.

Verificaciones fail-loud por nodo-cápsula (espejo del oráculo):
  genoma [oráculo :849-854] · dt [:856-859] · capacidad de historia [:866-870] ·
  emission_scale [:871-876] · formas y capas de e_ref [:740-760] · verificación post-copia
  [:791-813]. El receptor con cápsulas exige temperature=0 [:305-309] (el RNG no viaja).
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

import numpy as np

from ..compat.study06_capsule import genome_sha256, quench_column
from ..compat.study06_v4 import birth_state, parse_theta_v2
from ..physics.state import Layer, NodeState


def componer_red(constituyentes: Sequence[Mapping[str, Any]], edges, *, dt: float, seed: int,
                 k_global: float, coupling_gamma_c: float, tau_field: float = 0.0,
                 temperature: float = 0.0):
    """constituyentes: lista de {"theta": dict, "capsula": load_capsule(...) | None}.
    Devuelve (net, specs, recibo). El recibo va al manifiesto del film (procedencia)."""
    from ..engine.network import Network   # import local: el motor entra SOLO acá

    if any(c.get("capsula") for c in constituyentes) and float(temperature) != 0.0:
        raise RuntimeError("composición con cápsulas exige temperature=0: el estado del RNG "
                           "no viaja en la cápsula (contrato del oráculo :305-309)")
    specs, states, origenes = [], [], []
    for idx, cons in enumerate(constituyentes):
        theta = cons["theta"]
        spec, _ = parse_theta_v2(theta, emission_scale=1.0 / max(len(theta["modes"]), 1))
        cap = cons.get("capsula")
        if cap is None:
            st = birth_state(spec, seed=int(seed), idx=idx)
            origenes.append({"target_node_index": idx, "origen": "nacimiento",
                             "seed": int(seed), "idx": idx,
                             "e_ref_policy": "receiver_initial_energy"})
        else:
            man = cap["manifest"]; arrays = cap["arrays"]
            genoma = genome_sha256(theta)
            if man["genome_hash"] != genoma:
                raise RuntimeError(f"nodo {idx}: genoma no coincide — cápsula "
                                   f"{man['genome_hash'][:19]} vs theta {genoma[:19]} "
                                   "(oráculo :849-854)")
            engine = man["engine_contract"]
            if float(engine["dt"]) != float(dt):
                raise RuntimeError(f"nodo {idx}: dt difiere — cápsula {engine['dt']} vs "
                                   f"receptor {dt} (oráculo :856-859)")
            if float(engine["emission_scale"]) != float(spec.emission_scale):
                raise RuntimeError(f"nodo {idx}: emission_scale difiere — cápsula "
                                   f"{engine['emission_scale']} vs receptor "
                                   f"{spec.emission_scale} (oráculo :871-876)")
            formas = {"x": spec.n_modes, "v": spec.n_modes, "z": spec.n_z,
                      "b": spec.n_layers, "e": spec.n_layers}
            for campo, n in formas.items():
                if arrays[campo].shape != (n,):
                    raise RuntimeError(f"nodo {idx}: {campo} de la cápsula "
                                       f"{arrays[campo].shape} != spec ({n},)")
            capas_spec = {l.name for l in spec.layers_present}
            capas_cap = [str(v) for v in arrays["e_ref_keys"]]
            if capas_spec != set(capas_cap):
                raise RuntimeError(f"nodo {idx}: capas de e_ref {sorted(capas_cap)} != "
                                   f"spec {sorted(capas_spec)} (oráculo :748-755)")
            st = NodeState(x=arrays["x"].copy(), v=arrays["v"].copy(),
                           z=arrays["z"].copy(), b=arrays["b"].copy(),
                           e=arrays["e"].copy())
            for nombre in capas_cap:
                spec.struct.e_ref[Layer[nombre]] = float(
                    arrays["e_ref_values"][capas_cap.index(nombre)])
            origenes.append({"target_node_index": idx, "origen": "capsula",
                             "specimen_id": man["specimen_id"],
                             "block_id": man["block_id"],
                             "capsule_sha256": cap["capsule_sha256"],
                             "genome_hash": man["genome_hash"],
                             "source_state_content_sha256":
                                 man["state_artifact"]["content_sha256"],
                             "source": dict(man["source"])})   # procedencia OPACA, tal cual
        specs.append(spec)
        states.append(st)

    net = Network(specs, states, edges, dt=float(dt), seed=int(seed),
                  k_global=float(k_global), coupling_gamma_c=float(coupling_gamma_c),
                  tau_field=float(tau_field), temperature=float(temperature))
    target_delay = int(net.history.delay_steps)
    for idx, cons in enumerate(constituyentes):
        cap = cons.get("capsula")
        if cap is None:
            continue
        columna = quench_column(cap["arrays"], target_delay)
        net.history.buffer[:, idx, :] = columna
        source_delay = int(cap["manifest"]["engine_contract"]["delay_steps"])
        origenes[idx]["history_operation"] = (
            "canonical_ring_exact" if source_delay == target_delay
            else "truncate_recent_full_rate_exact")
        origenes[idx]["source_delay_steps"] = source_delay
        origenes[idx]["target_delay_steps"] = target_delay
    net.history.head_idx = 0   # head del receptor tras quench [oráculo :927]

    # verificación POST-COPIA (espejo del oráculo :791-813): lo aplicado ES lo sellado
    for idx, cons in enumerate(constituyentes):
        cap = cons.get("capsula")
        if cap is None:
            continue
        arrays = cap["arrays"]
        for campo in ("x", "v", "z", "b", "e"):
            if not np.array_equal(getattr(net.states[idx], campo), arrays[campo]):
                raise RuntimeError(f"post-composición: nodo {idx} campo {campo} difiere del "
                                   "espécimen sellado")
        esperada = quench_column(arrays, target_delay)
        if not np.array_equal(net.history.buffer[:, idx, :], esperada):
            raise RuntimeError(f"post-composición: historia del nodo {idx} difiere del quench")
    recibo = {"schema": "study07_composicion_v1", "n_nodes": len(specs),
              "temperature": float(temperature), "target_delay_steps": target_delay,
              "por_nodo": origenes}
    return net, specs, recibo
