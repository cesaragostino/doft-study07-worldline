#!/usr/bin/env python3
"""Gate M: nula rápida no lineal con b/e congelados y KV recíproco.

Relectura retrospectiva del mismo panel de Gate L. Los films y las cápsulas son
entradas read-only; este programa integra una nula local y escribe sólo su auditoría.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tools/link_grumo")]

import gate_l_bidirectional_transient as gate_l  # noqa: E402
from linear_response import load_blocks, parse_block  # noqa: E402
from study07.artifacts.checkpoint import spec_fingerprint  # noqa: E402
from study07.engine.network import Network  # noqa: E402
from study07.physics.rhs import emitted_xv  # noqa: E402
from study07.physics.state import NodeState  # noqa: E402


EXPECTED_GATE_L = "e92276d77189b7804ed82f40a4ff0782fd9002149f034ac6de1bd40b50b94c53"
HORIZON = gate_l.HORIZON
DT_PRODUCTION = gate_l.DT_PRODUCTION
DT_OBS = gate_l.DT_OBS
DT_FINE = gate_l.DT_FINE
SERIES_BIN = gate_l.SERIES_BIN
WINDOWS = gate_l.WINDOWS
NUMERIC_LIMIT = gate_l.NUMERIC_LIMIT
PRIMARY_RUNS = ("par133_t_k03_tau02", "par134_t_k03_tau02")
CONTROL_RUNS = ("par133_f_k03_tau02", "par134_f_k03_tau02")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def frozen_slow_spec(spec):
    """Misma constitución, con derivadas b/e exactamente nulas por tau=inf."""
    struct = replace(
        spec.struct,
        tau_e={layer: np.inf for layer in spec.layers_present},
        tau_b={layer: np.inf for layer in spec.layers_present},
    )
    return replace(spec, struct=struct)


def node_state(parts: dict[str, np.ndarray], index: int = 0) -> NodeState:
    return NodeState(
        x=np.asarray(parts["x"][index], dtype=float).copy(),
        v=np.asarray(parts["v"][index], dtype=float).copy(),
        z=np.asarray(parts["z"][index], dtype=float).copy(),
        b=np.asarray(parts["b"][index], dtype=float).copy(),
        e=np.asarray(parts["e"][index], dtype=float).copy(),
    )


def history_buffer(histories: list[np.ndarray]) -> tuple[np.ndarray, int]:
    """Convierte [t=0,t=-dt,...] por nodo al ring canónico con head=0."""
    if len(histories) != 2 or histories[0].shape != histories[1].shape:
        raise ValueError("Gate M exige dos historias con la misma forma")
    size = histories[0].shape[0]
    if histories[0].shape[1:] != (2,):
        raise ValueError("cada historia debe contener emisión (X,V)")
    buffer = np.empty((size, 2, 2), dtype=float)
    for age in range(size):
        index = (-age) % size
        for node in range(2):
            buffer[index, node] = histories[node][age]
    for age in range(size):
        np.testing.assert_array_equal(buffer[(-age) % size], np.stack([
            histories[0][age], histories[1][age]
        ]))
    return buffer, 0


def q_state(states: list[NodeState], q_indices: list[np.ndarray]) -> np.ndarray:
    return np.stack([
        np.concatenate((state.x[q_indices[node]], state.v[q_indices[node]]))
        for node, state in enumerate(states)
    ])


def simulate_nonlinear(specs, initial_states: list[NodeState], histories: list[np.ndarray],
                       manifest: dict, dt: float) -> dict:
    """Integra el Network real con RHS completo y tau_b=tau_e=inf."""
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
    frozen_specs = [frozen_slow_spec(spec) for spec in specs]
    initial_b = [state.b.copy() for state in initial_states]
    initial_e = [state.e.copy() for state in initial_states]
    net = Network(
        frozen_specs, initial_states, edges, dt=dt, seed=int(manifest["seed"]),
        k_global=float(manifest["k_global"]),
        coupling_gamma_c=float(manifest["gamma_c"]),
        tau_field=float(topology["tau"][0]), temperature=0.0,
        history_init=history_buffer(histories),
    )
    q_indices = [np.asarray(spec.layer_indices[next(
        layer for layer in spec.layer_indices if layer.name == "Q"
    )], dtype=int) for spec in frozen_specs]
    emission = np.empty((steps + 1, 2, 2), dtype=float)
    qstates = np.empty((steps + 1, 2, 2 * len(q_indices[0])), dtype=float)
    drives = np.zeros((steps + 1, 2), dtype=float)
    emission[0] = np.stack([
        emitted_xv(spec, state) for spec, state in zip(frozen_specs, net.states)
    ])
    qstates[0] = q_state(net.states, q_indices)
    for step in range(1, steps + 1):
        net.step()
        emission[step] = np.stack([
            emitted_xv(spec, state) for spec, state in zip(frozen_specs, net.states)
        ])
        qstates[step] = q_state(net.states, q_indices)
        drives[step] = net.last_drive0
        if not (np.all(np.isfinite(emission[step])) and np.all(np.isfinite(qstates[step]))):
            raise FloatingPointError(f"nula no finita en t={step * dt:g}")
    drift_b = max(float(np.max(np.abs(state.b - initial_b[node])))
                  for node, state in enumerate(net.states))
    drift_e = max(float(np.max(np.abs(state.e - initial_e[node])))
                  for node, state in enumerate(net.states))
    return {"emission": emission, "qstate": qstates, "drive": drives,
            "max_abs_drift_b": drift_b, "max_abs_drift_e": drift_e}


def protected_ratio(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0.0 else float(numerator / denominator)


def compare_scores(linear: dict, nonlinear: dict) -> dict:
    result = {}
    for key in ("E_Q", "E_emit", "E_drive"):
        result[f"linear_to_nonlinear_gain_{key[2:]}"] = float(linear[key] - nonlinear[key])
        result[f"nonlinear_over_linear_{key[2:]}"] = protected_ratio(
            float(nonlinear[key]), float(linear[key])
        )
    result["per_node"] = {
        node: compare_scores(linear["per_node"][node], nonlinear["per_node"][node])
        for node in ("0", "1")
    } if "per_node" in linear else {}
    return result


def compact_series(actual: dict, predicted: dict) -> dict:
    width = int(round(SERIES_BIN / DT_OBS))
    start = int(round(0.2 / DT_OBS))
    centers, joint_q, joint_emit = [], [], []
    per_node = {"0": {"E_Q": [], "E_emit": []},
                "1": {"E_Q": [], "E_emit": []}}
    for left in range(start, len(actual["drive"]) - width + 1, width):
        sl = slice(left, left + width)
        score = gate_l.score_window(actual, predicted, sl)
        centers.append((left + width / 2.0) * DT_OBS)
        joint_q.append(score["E_Q"]); joint_emit.append(score["E_emit"])
        for node in ("0", "1"):
            per_node[node]["E_Q"].append(score["per_node"][node]["E_Q"])
            per_node[node]["E_emit"].append(score["per_node"][node]["E_emit"])
    return {"dt_bin_ut": SERIES_BIN, "t_center_ut": centers,
            "joint": {"E_Q": joint_q, "E_emit": joint_emit},
            "per_node": per_node}


def first_crossings(series: dict, thresholds=(0.01, 0.1, 0.5, 1.0)) -> dict:
    times = np.asarray(series["t_center_ut"], dtype=float)
    result = {}
    for node in ("0", "1"):
        errors = np.asarray(series["per_node"][node]["E_Q"], dtype=float)
        result[node] = {}
        for threshold in thresholds:
            indices = np.flatnonzero(errors >= threshold)
            result[node][f"{threshold:g}"] = (float(times[indices[0]])
                                                 if len(indices) else None)
    return result


def median(values) -> float | None:
    vals = [value for value in values if value is not None and np.isfinite(value)]
    return float(np.median(vals)) if vals else None


def summarize_rows(rows: list[dict]) -> dict:
    summary = {"n": len(rows), "windows": {}}
    for start, end in WINDOWS:
        label = f"{start:g}_{end:g}"
        summary["windows"][label] = {
            "median_E_Q_nonlinear": median(
                row["windows"][label]["nonlinear_frozen"]["E_Q"] for row in rows),
            "median_gain_Q": median(
                row["windows"][label]["comparison"]["linear_to_nonlinear_gain_Q"]
                for row in rows),
            "median_ratio_Q": median(
                row["windows"][label]["comparison"]["nonlinear_over_linear_Q"]
                for row in rows),
        }
    return summary


def classify_primary(records: list[dict]) -> dict:
    selected = [row for row in records if row["run_id"] in PRIMARY_RUNS]
    if len(selected) != 2:
        raise RuntimeError(f"casos primarios incompletos: {[row['run_id'] for row in selected]}")
    values = []
    for row in selected:
        window = row["windows"]["2_10"]
        values.append({
            "run_id": row["run_id"], "numeric_status": row["numeric_status"],
            "E_Q_nonlinear_node0": window["nonlinear_frozen"]["per_node"]["0"]["E_Q"],
            "ratio_Q_node0": window["comparison"]["per_node"]["0"][
                "nonlinear_over_linear_Q"],
        })
    if any(value["numeric_status"] != "RESOLVED" for value in values):
        verdict = "NUMERICALLY_UNRESOLVED"
    elif all(value["E_Q_nonlinear_node0"] <= 0.10 and value["ratio_Q_node0"] <= 0.25
             for value in values):
        verdict = "STRONG_FINITE_AMPLITUDE_CLOSURE"
    else:
        ratio = float(np.median([value["ratio_Q_node0"] for value in values]))
        if ratio <= 0.50:
            verdict = "MATERIAL_IMPROVEMENT_NOT_STRONG_CLOSURE"
        elif ratio >= 0.80:
            verdict = "DOES_NOT_CLOSE"
        else:
            verdict = "PARTIAL_INTERMEDIATE"
    return {"verdict": verdict, "cases": values}


def fresh_priority_controls(records: list[dict]) -> list[dict]:
    controls = []
    for row in records:
        if row["run_id"] not in CONTROL_RUNS:
            continue
        window = row["windows"]["2_10"]
        linear = window["linear_frozen_gate_l"]["E_Q"]
        nonlinear_error = window["nonlinear_frozen"]["E_Q"]
        controls.append({
            "run_id": row["run_id"], "E_Q_linear": linear,
            "E_Q_nonlinear": nonlinear_error,
            "tensioned": bool((nonlinear_error - linear) > 0.02 or
                              (linear > 0.0 and nonlinear_error / linear > 5.0)),
        })
    return controls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--gate-f-evaluate", required=True, type=Path)
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--capsule-root", required=True, type=Path)
    parser.add_argument("--gate-l", required=True, type=Path)
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
    gate_l_path = args.gate_l.expanduser().resolve()
    if sha256(gate_l_path) != EXPECTED_GATE_L:
        raise RuntimeError("la salida Gate L no coincide con el preregistro M")
    gate_l_result = json.loads(gate_l_path.read_text())
    linear_by_run = {row["run_id"]: row for row in gate_l_result["records"]}

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
        if source["run_id"] not in linear_by_run:
            raise RuntimeError(f"{source['run_id']}: ausente de Gate L")

        specs, initial_states, actual_parts = [], [], []
        node_meta = []
        for node, origin in enumerate(manifest["composicion"]["por_nodo"]):
            fingerprint = manifest["spec_fingerprints"][node]
            block_id = origin.get("block_id", block_by_fingerprint.get(fingerprint))
            if block_id is None:
                raise RuntimeError(f"{source['run_id']} nodo {node}: fingerprint sin bloque")
            spec = specs_by_block[block_id]
            if spec_fingerprint(spec) != fingerprint:
                raise RuntimeError(f"{source['run_id']} nodo {node}: fingerprint distinto")
            parts = gate_l.split_state(states_raw[node], spec)
            state0 = node_state(parts)
            specs.append(spec); initial_states.append(state0); actual_parts.append(parts)
            node_meta.append({"node": node, "block_id": block_id, "origin": origin["origen"],
                              "norm_b0": float(np.linalg.norm(state0.b)),
                              "norm_e0": float(np.linalg.norm(state0.e))})

        obs_indices = np.arange(0, int(round(HORIZON / DT_PRODUCTION)) + 1, 10)
        actual_y = [np.concatenate((parts["x"], parts["v"], parts["z"]), axis=1)[obs_indices]
                    for parts in actual_parts]
        q_indices = [np.asarray(spec.layer_indices[next(
            layer for layer in spec.layer_indices if layer.name == "Q"
        )], dtype=int) for spec in specs]
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

        nonlinear = simulate_nonlinear(specs, initial_states, histories_coarse, manifest, DT_OBS)
        fine = simulate_nonlinear(specs, initial_states, histories_fine, manifest, DT_FINE)
        fine_on_obs = {key: value[::2] for key, value in fine.items()
                       if isinstance(value, np.ndarray)}
        fine_on_obs["max_abs_drift_b"] = fine["max_abs_drift_b"]
        fine_on_obs["max_abs_drift_e"] = fine["max_abs_drift_e"]

        windows, convergence_max = {}, 0.0
        linear_record = linear_by_run[source["run_id"]]
        for start, end in WINDOWS:
            label = f"{start:g}_{end:g}"
            sl = slice(int(round(start / DT_OBS)), int(round(end / DT_OBS)))
            nonlinear_score = gate_l.score_window(actual, nonlinear, sl)
            convergence = gate_l.score_window(nonlinear, fine_on_obs, sl)
            convergence_max = max(convergence_max, convergence["E_Q"], convergence["E_emit"])
            linear_score = linear_record["windows"][label]["coupled_frozen"]
            windows[label] = {
                "linear_frozen_gate_l": linear_score,
                "nonlinear_frozen": nonlinear_score,
                "comparison": compare_scores(linear_score, nonlinear_score),
                "convergence_coarse_vs_fine": convergence,
            }
        series = compact_series(actual, nonlinear)
        record = {
            "panel_index": index,
            "run_id": source["run_id"], "pair_id": source["pair_id"],
            "selection_role": source["selection_role"], "arm": source["arm"],
            "health60": bool(source["outcome"]["salud_60"]),
            "outcome_relation": source["outcome_relation"],
            "route": routes[source["run_id"]], "run_dir": str(run_dir),
            "manifest_sha256": source["manifest_sha256"], "worldline_hash": wl_hash,
            "nodes": node_meta, "delay": delay,
            "max_abs_drift_b": max(nonlinear["max_abs_drift_b"], fine["max_abs_drift_b"]),
            "max_abs_drift_e": max(nonlinear["max_abs_drift_e"], fine["max_abs_drift_e"]),
            "convergence_max_EQ_Eemit": convergence_max,
            "numeric_status": ("RESOLVED" if convergence_max <= NUMERIC_LIMIT
                               else "NUMERICALLY_UNRESOLVED"),
            "windows": windows, "series": series,
            "first_crossings_EQ_by_node": first_crossings(series),
        }
        records.append(record)
        print(f"[Gate M s{args.shard_index}/{args.shard_count}] {index:02d}/16 "
              f"{source['run_id']} "
              f"conv={convergence_max:.4g} {record['numeric_status']}", flush=True)

    if any(row["max_abs_drift_b"] != 0.0 or row["max_abs_drift_e"] != 0.0 for row in records):
        raise RuntimeError("la nula violó SLOW_FROZEN")
    groups = {
        "all": records,
        "healthy": [row for row in records if row["health60"]],
        "not_healthy": [row for row in records if not row["health60"]],
        "transported": [row for row in records if row["arm"] == "t"],
        "fresh": [row for row in records if row["arm"] == "f"],
    }
    controls = fresh_priority_controls(records)
    unresolved = [row["run_id"] for row in records
                  if row["numeric_status"] != "RESOLVED"]
    result = {
        "_meta": {
            "script": "tools/link_grumo/gate_m_nonlinear_fast.py",
            "script_sha256": sha256(Path(__file__)),
            "prereg": "audit/LINK_GRUMO_GATE_M_NONLINEAR_FAST_PREREG.md",
            "prereg_sha256": sha256(REPO / "audit/LINK_GRUMO_GATE_M_NONLINEAR_FAST_PREREG.md"),
            "input_sha256": {**hashes, "gate_l": EXPECTED_GATE_L},
            "capsule_root": str(capsule_root),
            "policy": "films/cápsulas/disco externo read-only; nula local sin motor de campaña",
            "dt_production": DT_PRODUCTION, "dt_observed": DT_OBS,
            "dt_convergence": DT_FINE, "horizon_ut": HORIZON,
            "shard": {"index": args.shard_index, "count": args.shard_count,
                      "panel_indices": [row["panel_index"] for row in records]},
        },
        "model": {
            "primary": "COUPLED-NONLINEAR-FAST/SLOW-FROZEN",
            "comparator": "COUPLED-LINEAR-FROZEN de Gate L",
            "integration": "Network RK4 productivo; tau_e=tau_b=inf",
            "windows_ut": [list(window) for window in WINDOWS],
            "numeric_limit": NUMERIC_LIMIT,
        },
        "summary": {
            "n": len(records), "n_numeric_unresolved": len(unresolved),
            "numeric_unresolved": unresolved,
            "primary": (classify_primary(records) if len(records) == len(all_sources)
                        else {"verdict": "DEFERRED_TO_EXHAUSTIVE_MERGE"}),
            "fresh_priority_controls": controls,
            "groups": {name: summarize_rows(rows) for name, rows in groups.items()},
        },
        "warnings": [
            "RETROSPECTIVO y outcome-selected: sin p-values, AUC ni claim poblacional.",
            "SLOW_FROZEN es una intervención diagnóstica; no es la dinámica real del onion.",
            "El comparador Gate L usa expm+ZOH y Gate M usa RK4 productivo; ambas convergencias se publican.",
            "RHS v1 direct-only; kernels diferidos fuera de alcance.",
            "Un cierre de trayectoria no convierte la no-linealidad en regla de salud.",
        ],
        "records": records,
    }
    result = gate_l.round_floats(result)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[Gate M] salida: {output}")


if __name__ == "__main__":
    main()
