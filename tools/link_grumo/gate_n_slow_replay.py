#!/usr/bin/env python3
"""Gate N: replay diagnóstico de b(t) observado dentro del RHS rápido completo."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tools/link_grumo")]

import gate_l_bidirectional_transient as gate_l  # noqa: E402
import gate_m_nonlinear_fast as gate_m  # noqa: E402
from linear_response import load_blocks, parse_block  # noqa: E402
from study07.artifacts.checkpoint import spec_fingerprint  # noqa: E402
from study07.engine.network import Network  # noqa: E402
from study07.physics.rhs import derivatives, emitted_xv  # noqa: E402
from study07.physics.state import Layer, NodeState, rk4_combine, state_add  # noqa: E402


EXPECTED_GATE_M = "230381973ce113db05e2bdae08d89d790b11b0c5fede61df79ff99cf1cf8e9b8"
EXPECTED_GATE_M_SIMULATOR = "43317c0856d5c9cec1ff32215a2c7326b95d404e2105dcb52ed5640f0886b49e"
HORIZON = gate_m.HORIZON
DT_PRODUCTION = gate_m.DT_PRODUCTION
DT_OBS = gate_m.DT_OBS
DT_FINE = gate_m.DT_FINE
WINDOWS = gate_m.WINDOWS
NUMERIC_LIMIT = gate_m.NUMERIC_LIMIT
PRIMARY_RUNS = gate_m.PRIMARY_RUNS
CONTROL_RUNS = gate_m.CONTROL_RUNS
PRIORITY_RUNS = set(PRIMARY_RUNS + CONTROL_RUNS)
VARIANT_ORDER = ("SOURCE_Q_B", "SOURCE_ALL_B", "ALL_B")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def replay_masks(specs, variant: str) -> list[np.ndarray]:
    if variant not in VARIANT_ORDER:
        raise ValueError(f"variante desconocida: {variant}")
    masks = [np.zeros(spec.n_layers, dtype=bool) for spec in specs]
    if variant == "ALL_B":
        return [np.ones(spec.n_layers, dtype=bool) for spec in specs]
    if variant == "SOURCE_ALL_B":
        masks[0][:] = True
        return masks
    masks[0][specs[0].layers_present.index(Layer.Q)] = True
    return masks


def b_schedule(observed_b: np.ndarray, dt: float) -> np.ndarray:
    """b observada interpolada en todos los medios pasos RK4."""
    steps = int(round(HORIZON / dt))
    target_t = np.arange(2 * steps + 1, dtype=float) * (dt / 2.0)
    source_t = np.arange(len(observed_b), dtype=float) * DT_PRODUCTION
    if source_t[-1] + 1e-12 < HORIZON:
        raise ValueError("worldline b no cubre el horizonte")
    result = np.column_stack([
        np.interp(target_t, source_t, observed_b[:, layer])
        for layer in range(observed_b.shape[1])
    ])
    np.testing.assert_array_equal(result[0], observed_b[0])
    return result


def prescribed_state(state: NodeState, replay_b: np.ndarray, initial_b: np.ndarray,
                     initial_e: np.ndarray, mask: np.ndarray) -> NodeState:
    result = state.copy()
    result.b = np.where(mask, replay_b, initial_b).astype(float, copy=False)
    result.e = initial_e.copy()
    return result


def replay_step(net: Network, schedules: list[np.ndarray], masks: list[np.ndarray],
                initial_b: list[np.ndarray], initial_e: list[np.ndarray], step: int) -> None:
    """Paso RK4 productivo con proyección b en las cuatro etapas."""
    base = 2 * step
    s0 = [prescribed_state(state, schedules[node][base], initial_b[node],
                           initial_e[node], masks[node])
          for node, state in enumerate(net.states)]
    net.states = s0
    f0 = net._f_inter(s0, 0.0)
    net.last_drive0 = f0.copy()
    k1 = [derivatives(spec, state, f0[node])
          for node, (spec, state) in enumerate(zip(net.specs, s0))]

    s1 = [prescribed_state(state_add(state, k, net.dt * 0.5),
                           schedules[node][base + 1], initial_b[node], initial_e[node],
                           masks[node])
          for node, (state, k) in enumerate(zip(s0, k1))]
    f1 = net._f_inter(s1, 0.5)
    k2 = [derivatives(spec, state, f1[node])
          for node, (spec, state) in enumerate(zip(net.specs, s1))]

    s2 = [prescribed_state(state_add(state, k, net.dt * 0.5),
                           schedules[node][base + 1], initial_b[node], initial_e[node],
                           masks[node])
          for node, (state, k) in enumerate(zip(s0, k2))]
    f2 = net._f_inter(s2, 0.5)
    k3 = [derivatives(spec, state, f2[node])
          for node, (spec, state) in enumerate(zip(net.specs, s2))]

    s3 = [prescribed_state(state_add(state, k, net.dt), schedules[node][base + 2],
                           initial_b[node], initial_e[node], masks[node])
          for node, (state, k) in enumerate(zip(s0, k3))]
    f3 = net._f_inter(s3, 1.0)
    k4 = [derivatives(spec, state, f3[node])
          for node, (spec, state) in enumerate(zip(net.specs, s3))]

    nuevos = []
    for node in range(len(net.specs)):
        combined = rk4_combine(s0[node], k1[node], k2[node], k3[node], k4[node], net.dt)
        nuevos.append(prescribed_state(combined, schedules[node][base + 2],
                                       initial_b[node], initial_e[node], masks[node]))
        net.last_noise_kicks[node] = np.zeros(net.specs[node].n_modes)
    net.states = nuevos
    net.history.push(net._xv(nuevos))


def simulate_replay(specs, initial_states: list[NodeState], histories: list[np.ndarray],
                    observed_b: list[np.ndarray], manifest: dict, dt: float,
                    variant: str) -> dict:
    steps = int(round(HORIZON / dt))
    if abs(steps * dt - HORIZON) > 1e-12:
        raise ValueError("el horizonte debe ser entero en dt")
    topology = manifest["topologia"]
    edges = [
        {"i": int(i), "j": int(j), "w_k": float(topology["w_k"][edge]),
         "w_gamma": float(topology["w_gamma"][edge]),
         "tau": float(topology["tau"][edge])}
        for edge, (i, j) in enumerate(topology["edges_ij"])
    ]
    frozen_specs = [gate_m.frozen_slow_spec(spec) for spec in specs]
    masks = replay_masks(frozen_specs, variant)
    initial_b = [state.b.copy() for state in initial_states]
    initial_e = [state.e.copy() for state in initial_states]
    schedules = [b_schedule(series, dt) for series in observed_b]
    net = Network(
        frozen_specs, initial_states, edges, dt=dt, seed=int(manifest["seed"]),
        k_global=float(manifest["k_global"]),
        coupling_gamma_c=float(manifest["gamma_c"]),
        tau_field=float(topology["tau"][0]), temperature=0.0,
        history_init=gate_m.history_buffer(histories),
    )
    q_indices = [np.asarray(spec.layer_indices[Layer.Q], dtype=int) for spec in frozen_specs]
    emission = np.empty((steps + 1, 2, 2), dtype=float)
    qstates = np.empty((steps + 1, 2, 2 * len(q_indices[0])), dtype=float)
    drives = np.zeros((steps + 1, 2), dtype=float)
    emission[0] = np.stack([emitted_xv(spec, state)
                            for spec, state in zip(frozen_specs, net.states)])
    qstates[0] = gate_m.q_state(net.states, q_indices)
    replay_error = 0.0
    frozen_error = 0.0
    for step in range(steps):
        replay_step(net, schedules, masks, initial_b, initial_e, step)
        emission[step + 1] = np.stack([emitted_xv(spec, state)
                                       for spec, state in zip(frozen_specs, net.states)])
        qstates[step + 1] = gate_m.q_state(net.states, q_indices)
        drives[step + 1] = net.last_drive0
        for node, state in enumerate(net.states):
            expected = np.where(masks[node], schedules[node][2 * (step + 1)],
                                initial_b[node])
            replay_error = max(replay_error, float(np.max(np.abs(state.b - expected))))
            frozen = ~masks[node]
            if np.any(frozen):
                frozen_error = max(frozen_error,
                                   float(np.max(np.abs(state.b[frozen] - initial_b[node][frozen]))))
            frozen_error = max(frozen_error, float(np.max(np.abs(state.e - initial_e[node]))))
        if not (np.all(np.isfinite(emission[step + 1])) and
                np.all(np.isfinite(qstates[step + 1]))):
            raise FloatingPointError(f"replay no finito en t={(step + 1) * dt:g}")
    return {
        "emission": emission, "qstate": qstates, "drive": drives,
        "max_abs_replay_projection_error": replay_error,
        "max_abs_frozen_coordinate_drift": frozen_error,
    }


def summarize_all_b(records: list[dict]) -> dict:
    summary = {"n": len(records), "windows": {}}
    for start, end in WINDOWS:
        label = f"{start:g}_{end:g}"
        rows = [row["variants"]["ALL_B"]["windows"][label] for row in records]
        summary["windows"][label] = {
            "median_E_Q_replay": gate_m.median(row["observed_b_replay"]["E_Q"]
                                                for row in rows),
            "median_gain_Q_vs_gate_m": gate_m.median(
                row["comparison_to_gate_m"]["linear_to_nonlinear_gain_Q"]
                for row in rows),
            "median_ratio_Q_vs_gate_m": gate_m.median(
                row["comparison_to_gate_m"]["nonlinear_over_linear_Q"]
                for row in rows),
        }
    return summary


def primary_case(records: list[dict], run_id: str, variant: str) -> dict:
    row = next(record for record in records if record["run_id"] == run_id)
    data = row["variants"][variant]
    window = data["windows"]["2_10"]
    return {
        "run_id": run_id, "variant": variant,
        "numeric_status": data["numeric_status"],
        "E_Q_replay_node0": window["observed_b_replay"]["per_node"]["0"]["E_Q"],
        "ratio_Q_vs_gate_m_node0": window["comparison_to_gate_m"]["per_node"]["0"]
        ["nonlinear_over_linear_Q"],
    }


def closes(cases: list[dict]) -> bool:
    return all(case["numeric_status"] == "RESOLVED" and
               case["E_Q_replay_node0"] <= 0.10 and
               case["ratio_Q_vs_gate_m_node0"] <= 0.25 for case in cases)


def classify_primary(records: list[dict]) -> dict:
    by_variant = {variant: [primary_case(records, run_id, variant)
                            for run_id in PRIMARY_RUNS]
                  for variant in VARIANT_ORDER}
    all_b = by_variant["ALL_B"]
    if any(case["numeric_status"] != "RESOLVED" for case in all_b):
        verdict = "NUMERICALLY_UNRESOLVED"
    elif closes(all_b):
        verdict = "STRONG_SLOW_CLOSURE"
    else:
        ratio = float(np.median([case["ratio_Q_vs_gate_m_node0"] for case in all_b]))
        if ratio <= 0.50:
            verdict = "MATERIAL_IMPROVEMENT_NOT_STRONG_CLOSURE"
        elif ratio >= 0.80:
            verdict = "DOES_NOT_CLOSE"
        else:
            verdict = "PARTIAL_INTERMEDIATE"
    if verdict == "STRONG_SLOW_CLOSURE":
        if closes(by_variant["SOURCE_Q_B"]):
            localization = "SOURCE_Q_B_SUFFICIENT"
        elif closes(by_variant["SOURCE_ALL_B"]):
            localization = "SOURCE_NON_Q_B_REQUIRED"
        else:
            localization = "RECEIVER_B_REQUIRED"
    else:
        localization = "OBSERVED_B_NOT_SUFFICIENT"
    return {"verdict": verdict, "localization": localization,
            "cases_by_variant": by_variant}


def priority_controls(records: list[dict]) -> list[dict]:
    controls = []
    for run_id in CONTROL_RUNS:
        row = next(record for record in records if record["run_id"] == run_id)
        for variant in VARIANT_ORDER:
            window = row["variants"][variant]["windows"]["2_10"]
            baseline = window["gate_m_frozen"]["E_Q"]
            replay = window["observed_b_replay"]["E_Q"]
            controls.append({
                "run_id": run_id, "variant": variant, "E_Q_gate_m": baseline,
                "E_Q_replay": replay,
                "tensioned": bool((replay - baseline) > 0.02 or
                                   (baseline > 0.0 and replay / baseline > 5.0)),
            })
    return controls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--gate-f-evaluate", required=True, type=Path)
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--capsule-root", required=True, type=Path)
    parser.add_argument("--gate-m", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    if output.exists():
        raise RuntimeError(f"salida ya existe, no se pisa: {output}")
    if str(output).startswith("/Volumes/ExternalDisk/"):
        raise RuntimeError("escribir en el disco externo está prohibido")
    output.parent.mkdir(parents=True, exist_ok=True)

    paths = {
        "bank": args.bank.expanduser().resolve(),
        "gate_f_evaluate": args.gate_f_evaluate.expanduser().resolve(),
        "blocks": args.blocks.expanduser().resolve(),
        "inventory": args.inventory.expanduser().resolve(),
    }
    hashes = {label: gate_l.verify_input(path, label) for label, path in paths.items()}
    gate_m_path = args.gate_m.expanduser().resolve()
    if sha256(gate_m_path) != EXPECTED_GATE_M:
        raise RuntimeError("la salida Gate M no coincide con el preregistro N")
    if sha256(REPO / "tools/link_grumo/gate_m_nonlinear_fast.py") != EXPECTED_GATE_M_SIMULATOR:
        raise RuntimeError("el simulador Gate M cambió desde la salida canónica")
    gate_m_result = json.loads(gate_m_path.read_text())
    gate_m_by_run = {row["run_id"]: row for row in gate_m_result["records"]}

    bank = json.loads(paths["bank"].read_text())
    evaluation = json.loads(paths["gate_f_evaluate"].read_text())
    routes = gate_l.route_map(evaluation)
    blocks = load_blocks(paths["blocks"])
    specs_by_block, block_by_fingerprint = {}, {}
    for block_id, block in blocks.items():
        spec = parse_block(block)
        fingerprint = spec_fingerprint(spec)
        if fingerprint in block_by_fingerprint:
            raise RuntimeError(f"fingerprint constitucional duplicado: {fingerprint}")
        specs_by_block[block_id] = spec
        block_by_fingerprint[fingerprint] = block_id
    inventory_raw = json.loads(paths["inventory"].read_text())
    inventory = {row["block_id"]: row for row in inventory_raw["poblacion"]}
    capsule_root = args.capsule_root.expanduser().resolve()

    all_sources = gate_l.flatten_bank(bank)
    if args.shard_count < 1 or not (0 <= args.shard_index < args.shard_count):
        raise ValueError("shard inválido")
    indexed_sources = [(index, source) for index, source in enumerate(all_sources, 1)
                       if (index - 1) % args.shard_count == args.shard_index]
    if not indexed_sources:
        raise ValueError("shard vacío")

    records = []
    for index, source in indexed_sources:
        run_dir = Path(source["run_dir"])
        manifest, states_raw, drive_raw, wl_hash = gate_l.load_prefix_verified(
            run_dir, source["manifest_sha256"]
        )
        if wl_hash != source["outcome"]["worldline_hash"]:
            raise RuntimeError(f"{source['run_id']}: worldline_hash != banco")
        if float(manifest["dt"]) != DT_PRODUCTION:
            raise RuntimeError(f"{source['run_id']}: dt no canónico")
        if source["run_id"] not in gate_m_by_run:
            raise RuntimeError(f"{source['run_id']}: ausente de Gate M")

        specs, initial_states, actual_parts, node_meta = [], [], [], []
        for node, origin in enumerate(manifest["composicion"]["por_nodo"]):
            fingerprint = manifest["spec_fingerprints"][node]
            block_id = origin.get("block_id", block_by_fingerprint.get(fingerprint))
            if block_id is None:
                raise RuntimeError(f"{source['run_id']} nodo {node}: fingerprint sin bloque")
            spec = specs_by_block[block_id]
            if spec_fingerprint(spec) != fingerprint:
                raise RuntimeError(f"{source['run_id']} nodo {node}: fingerprint distinto")
            parts = gate_l.split_state(states_raw[node], spec)
            state0 = gate_m.node_state(parts)
            specs.append(spec); initial_states.append(state0); actual_parts.append(parts)
            node_meta.append({
                "node": node, "block_id": block_id, "origin": origin["origen"],
                "layers": [layer.name for layer in spec.layers_present],
                "b0": state0.b.tolist(),
                "b20": parts["b"][int(round(HORIZON / DT_PRODUCTION))].tolist(),
            })

        obs_indices = np.arange(0, int(round(HORIZON / DT_PRODUCTION)) + 1, 10)
        actual_y = [np.concatenate((parts["x"], parts["v"], parts["z"]), axis=1)[obs_indices]
                    for parts in actual_parts]
        q_indices = [np.asarray(spec.layer_indices[Layer.Q], dtype=int) for spec in specs]
        actual = {
            "emission": np.stack([
                gate_l.emitted_from_y(actual_y[node], specs[node].n_modes,
                                      specs[node].emission_scale) for node in range(2)
            ], axis=1),
            "qstate": np.stack([
                gate_l.qstate_from_y(actual_y[node], q_indices[node], specs[node].n_modes)
                for node in range(2)
            ], axis=1),
            "drive": drive_raw[obs_indices],
        }
        delay = float(manifest["topologia"]["tau"][0])
        delay_prod = int(round(delay / DT_PRODUCTION))
        histories_coarse = [gate_l.history_for_node(
            manifest["composicion"]["por_nodo"][node],
            np.concatenate((initial_states[node].x, initial_states[node].v,
                            initial_states[node].z)), specs[node], inventory,
            capsule_root, delay_prod, DT_OBS
        ) for node in range(2)]
        histories_fine = [gate_l.history_for_node(
            manifest["composicion"]["por_nodo"][node],
            np.concatenate((initial_states[node].x, initial_states[node].v,
                            initial_states[node].z)), specs[node], inventory,
            capsule_root, delay_prod, DT_FINE
        ) for node in range(2)]
        observed_b = [parts["b"][:int(round(HORIZON / DT_PRODUCTION)) + 1]
                      for parts in actual_parts]
        variants = VARIANT_ORDER if source["run_id"] in PRIORITY_RUNS else ("ALL_B",)
        variant_results = {}
        gate_m_record = gate_m_by_run[source["run_id"]]
        for variant in variants:
            replay = simulate_replay(specs, initial_states, histories_coarse, observed_b,
                                     manifest, DT_OBS, variant)
            fine = simulate_replay(specs, initial_states, histories_fine, observed_b,
                                   manifest, DT_FINE, variant)
            fine_on_obs = {key: value[::2] for key, value in fine.items()
                           if isinstance(value, np.ndarray)}
            windows, convergence_max = {}, 0.0
            for start, end in WINDOWS:
                label = f"{start:g}_{end:g}"
                sl = slice(int(round(start / DT_OBS)), int(round(end / DT_OBS)))
                replay_score = gate_l.score_window(actual, replay, sl)
                convergence = gate_l.score_window(replay, fine_on_obs, sl)
                convergence_max = max(convergence_max, convergence["E_Q"],
                                      convergence["E_emit"])
                gate_m_score = gate_m_record["windows"][label]["nonlinear_frozen"]
                gate_l_score = gate_m_record["windows"][label]["linear_frozen_gate_l"]
                windows[label] = {
                    "gate_l_linear_frozen": gate_l_score,
                    "gate_m_frozen": gate_m_score,
                    "observed_b_replay": replay_score,
                    "comparison_to_gate_m": gate_m.compare_scores(gate_m_score,
                                                                   replay_score),
                    "convergence_coarse_vs_fine": convergence,
                }
            series = gate_m.compact_series(actual, replay)
            variant_results[variant] = {
                "replayed_coordinates": [
                    {"node": node, "layers": [specs[node].layers_present[i].name
                                               for i in np.flatnonzero(mask)]}
                    for node, mask in enumerate(replay_masks(specs, variant))
                ],
                "max_abs_replay_projection_error": max(
                    replay["max_abs_replay_projection_error"],
                    fine["max_abs_replay_projection_error"]),
                "max_abs_frozen_coordinate_drift": max(
                    replay["max_abs_frozen_coordinate_drift"],
                    fine["max_abs_frozen_coordinate_drift"]),
                "convergence_max_EQ_Eemit": convergence_max,
                "numeric_status": ("RESOLVED" if convergence_max <= NUMERIC_LIMIT
                                   else "NUMERICALLY_UNRESOLVED"),
                "windows": windows, "series": series,
                "first_crossings_EQ_by_node": gate_m.first_crossings(series),
            }
            print(f"[Gate N s{args.shard_index}/{args.shard_count}] {index:02d}/16 "
                  f"{source['run_id']} {variant} conv={convergence_max:.4g} "
                  f"{variant_results[variant]['numeric_status']}", flush=True)

        records.append({
            "panel_index": index, "run_id": source["run_id"],
            "pair_id": source["pair_id"], "selection_role": source["selection_role"],
            "arm": source["arm"], "health60": bool(source["outcome"]["salud_60"]),
            "outcome_relation": source["outcome_relation"],
            "route": routes[source["run_id"]], "run_dir": str(run_dir),
            "manifest_sha256": source["manifest_sha256"], "worldline_hash": wl_hash,
            "nodes": node_meta, "delay": delay, "variants": variant_results,
        })

    unresolved = [{"run_id": row["run_id"], "variant": variant}
                  for row in records for variant, result in row["variants"].items()
                  if result["numeric_status"] != "RESOLVED"]
    result = {
        "_meta": {
            "script": "tools/link_grumo/gate_n_slow_replay.py",
            "script_sha256": sha256(Path(__file__)),
            "prereg": "audit/LINK_GRUMO_GATE_N_SLOW_REPLAY_PREREG.md",
            "prereg_sha256": sha256(REPO / "audit/LINK_GRUMO_GATE_N_SLOW_REPLAY_PREREG.md"),
            "input_sha256": {**hashes, "gate_m": EXPECTED_GATE_M,
                              "gate_m_simulator": EXPECTED_GATE_M_SIMULATOR},
            "capsule_root": str(capsule_root),
            "policy": "replay outcome-leaking; films/cápsulas/disco externo read-only",
            "dt_production": DT_PRODUCTION, "dt_observed": DT_OBS,
            "dt_convergence": DT_FINE, "horizon_ut": HORIZON,
            "shard": {"index": args.shard_index, "count": args.shard_count,
                      "panel_indices": [row["panel_index"] for row in records]},
        },
        "model": {
            "primary": "COUPLED-NONLINEAR-FAST/OBSERVED-B-REPLAY",
            "variants": list(VARIANT_ORDER),
            "integration": "Network forces/delay + RK4 adapter with b projection at 4 stages",
            "windows_ut": [list(window) for window in WINDOWS],
            "numeric_limit": NUMERIC_LIMIT,
        },
        "summary": {
            "n": len(records), "n_numeric_unresolved": len(unresolved),
            "numeric_unresolved": unresolved,
            "primary": (classify_primary(records) if len(records) == len(all_sources)
                        else {"verdict": "DEFERRED_TO_EXHAUSTIVE_MERGE"}),
            "priority_controls": (priority_controls(records)
                                  if len(records) == len(all_sources) else []),
            "groups_all_b": {},
        },
        "warnings": [
            "RETROSPECTIVO y outcome-selected: sin p-values, AUC ni claim poblacional.",
            "OBSERVED_B_REPLAY usa información futura del outcome: suficiencia, no causalidad/predicción/salud.",
            "e(t) no entra en la dinámica rápida; con b prescrita su replay es degenerado y no se corrió.",
            "RHS v1 direct-only; kernels diferidos fuera de alcance.",
            "Nodo 0 se llama source sólo para los primarios; no es un rol poblacional.",
        ],
        "records": records,
    }
    result = gate_l.round_floats(result)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[Gate N] salida: {output}")


if __name__ == "__main__":
    main()
