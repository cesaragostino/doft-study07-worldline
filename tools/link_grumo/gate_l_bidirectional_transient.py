#!/usr/bin/env python3
"""Gate L: nula rápida transitoria de dos onions con KV recíproco y delay.

Relectura read-only del panel Gate F, conforme al preregistro
``audit/LINK_GRUMO_GATE_L_BIDIRECTIONAL_TRANSIENT_PREREG.md``. No ejecuta el motor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.linalg import expm

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tools/link_grumo")]

from linear_response import jacobian_fd, load_blocks, parse_block  # noqa: E402
from study07.artifacts.checkpoint import spec_fingerprint  # noqa: E402
from study07.compat.study06_capsule import load_capsule, quench_column  # noqa: E402

EXPECTED = {
    "bank": "3e31e9439f0ac1b5ce226b7d5cf2bbf29d51ae66865db7d2949dc4638e4f9612",
    "gate_f_evaluate": "1a0d8998329c90607126d57b0965b350f22862932a337f563cae1000c9281162",
    "inventory": "1fb29af2e58475c2175dd5d8bb7ad4090fb386cbf21bec01f653dc04b4e28a67",
    "blocks": "adf8d436ef5da468a8ecaecf4c170e983b36f1599e439f8e23502b9801a5da9a",
}
HORIZON = 20.0
DT_PRODUCTION = 8e-5
DT_OBS = 8e-4
DT_FINE = 4e-4
SERIES_BIN = 0.008
WINDOWS = ((0.2, 2.0), (2.0, 10.0), (10.0, 20.0))
NUMERIC_LIMIT = 0.02


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def round_floats(value, significant: int = 8):
    if isinstance(value, float):
        return float(f"{value:.{significant}g}") if np.isfinite(value) else None
    if isinstance(value, list):
        return [round_floats(item, significant) for item in value]
    if isinstance(value, dict):
        return {key: round_floats(item, significant) for key, item in value.items()}
    return value


def verify_input(path: Path, label: str) -> str:
    actual = sha256(path)
    if actual != EXPECTED[label]:
        raise RuntimeError(f"{label}: sha {actual} != prereg {EXPECTED[label]}")
    return actual


def flatten_bank(bank: dict) -> list[dict]:
    rows = []
    for pair in bank["pairs"]:
        for role in ("target", "control"):
            row = dict(pair[role])
            row["pair_id"] = pair["pair_id"]
            row["selection_role"] = role
            row["outcome_relation"] = pair["outcome_relation"]
            rows.append(row)
    if len(rows) != 16 or len({row["run_id"] for row in rows}) != 16:
        raise RuntimeError("Gate L exige exactamente los 16 films únicos del banco F")
    return rows


def route_map(evaluation: dict) -> dict[str, str]:
    routes = {}
    for name, payload in evaluation["summary"]["routes"].items():
        for run_id in payload["run_ids"]:
            if run_id in routes:
                raise RuntimeError(f"ruta duplicada para {run_id}")
            routes[run_id] = name
    return routes


def load_prefix_verified(run_dir: Path, manifest_expected: str) -> tuple[dict, list[np.ndarray], np.ndarray, str]:
    """Verifica el film entero por hash y carga estados/drive sólo hasta 20 u.t."""
    manifest_text = (run_dir / "manifest.json").read_text()
    if hashlib.sha256(manifest_text.encode()).hexdigest() != manifest_expected:
        raise RuntimeError(f"{run_dir.name}: manifest != banco F")
    manifest = json.loads(manifest_text)
    complete = json.loads((run_dir / "COMPLETE").read_text())
    if complete["manifest_sha"] != manifest_expected:
        raise RuntimeError(f"{run_dir.name}: COMPLETE no sella el manifest del banco")
    chunks = sorted((run_dir / "worldline").glob("chunk_*.npz"))
    if len(chunks) != complete["chunks"]:
        raise RuntimeError(f"{run_dir.name}: cantidad de chunks no coincide")
    max_tick = int(round(HORIZON / float(manifest["dt"])))
    states = [[], []]
    drives, ticks = [], []
    for path, expected in zip(chunks, complete["chunk_shas"]):
        if sha256(path) != expected:
            raise RuntimeError(f"{run_dir.name}/{path.name}: chunk adulterado")
        with np.load(path, allow_pickle=False) as payload:
            chunk_ticks = np.asarray(payload["ticks"], dtype=np.int64)
            if chunk_ticks[0] > max_tick:
                continue
            mask = chunk_ticks <= max_tick
            ticks.append(chunk_ticks[mask])
            drives.append(np.asarray(payload["drive"][mask], dtype=float))
            for node in range(2):
                states[node].append(np.asarray(payload[f"estados_nodo{node}"][mask], dtype=float))
    tick = np.concatenate(ticks)
    if not np.array_equal(tick, np.arange(max_tick + 1)):
        raise RuntimeError(f"{run_dir.name}: prefijo sin ticks consecutivos")
    worldline_hash = hashlib.sha256(
        (complete["sha_total"] + complete["manifest_sha"]).encode()
    ).hexdigest()
    return manifest, [np.concatenate(items) for items in states], np.concatenate(drives), worldline_hash


def split_state(flat: np.ndarray, spec) -> dict[str, np.ndarray]:
    n, nz, nl = spec.n_modes, spec.n_z, spec.n_layers
    return {
        "x": flat[..., :n],
        "v": flat[..., n:2 * n],
        "z": flat[..., 2 * n:2 * n + nz],
        "b": flat[..., 2 * n + nz:2 * n + nz + nl],
        "e": flat[..., 2 * n + nz + nl:2 * n + nz + 2 * nl],
    }


def emitted_from_y(y: np.ndarray, n_modes: int, scale: float) -> np.ndarray:
    return scale * np.stack((np.sum(y[..., :n_modes], axis=-1),
                             np.sum(y[..., n_modes:2 * n_modes], axis=-1)), axis=-1)


def qstate_from_y(y: np.ndarray, q_indices: np.ndarray, n_modes: int) -> np.ndarray:
    return np.concatenate((y[..., q_indices], y[..., n_modes + q_indices]), axis=-1)


def step_matrices(matrix: np.ndarray, drive: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    dim = matrix.shape[0]
    augmented = np.zeros((dim + 1, dim + 1))
    augmented[:dim, :dim] = matrix
    augmented[:dim, dim] = drive
    transition = expm(augmented * dt)
    return transition[:dim, :dim], transition[:dim, dim]


def history_for_node(origin: dict, actual_initial: np.ndarray, spec, inventory: dict,
                     capsule_root: Path, delay_prod: int, dt_model: float) -> np.ndarray:
    factor = int(round(dt_model / DT_PRODUCTION))
    if abs(factor * DT_PRODUCTION - dt_model) > 1e-15 or delay_prod % factor:
        raise RuntimeError("dt_model debe dividir exactamente el delay de producción")
    delay_model = delay_prod // factor
    if origin["origen"] == "nacimiento":
        current = emitted_from_y(actual_initial, spec.n_modes, spec.emission_scale)
        return np.tile(current, (delay_model + 1, 1))
    if origin["origen"] != "capsula":
        raise RuntimeError(f"origen no soportado {origin['origen']}")
    entry = inventory[origin["block_id"]]
    capsule = load_capsule(capsule_root / entry["dir"])
    if capsule["capsule_sha256"] != origin["capsule_sha256"]:
        raise RuntimeError(f"cápsula no coincide para {origin['block_id']}")
    column = quench_column(capsule["arrays"], delay_prod)
    history = np.asarray([
        column[(-steps_ago * factor) % len(column)]
        for steps_ago in range(delay_model + 1)
    ])
    actual_emission = emitted_from_y(actual_initial, spec.n_modes, spec.emission_scale)
    if not np.array_equal(history[0], actual_emission):
        raise RuntimeError(f"historia t=0 != estado inicial para {origin['block_id']}")
    return history


def simulate(models: list[dict], histories: list[np.ndarray], k: float, gamma: float,
             delay: float, dt: float, coupled: bool) -> dict[str, np.ndarray]:
    steps = int(round(HORIZON / dt))
    delay_steps = int(round(delay / dt))
    if abs(delay_steps * dt - delay) > 1e-12:
        raise RuntimeError("delay no es entero en dt_model")
    ys = [np.empty((steps + 1, len(model["initial"]))) for model in models]
    emissions = np.empty((steps + 1, 2, 2))
    drives = np.zeros((steps + 1, 2))
    for node, model in enumerate(models):
        ys[node][0] = model["initial"]
        emissions[0, node] = emitted_from_y(
            model["initial"], model["spec"].n_modes, model["spec"].emission_scale
        )
    matrices = []
    for model in models:
        matrix = model["matrix"]
        if coupled:
            n = model["spec"].n_modes
            output = np.zeros(len(model["initial"]))
            output[:n] = k * model["spec"].emission_scale
            output[n:2 * n] = gamma * model["spec"].emission_scale
            matrix = matrix - np.outer(model["drive_vector"], output)
        matrices.append(step_matrices(matrix, model["drive_vector"], dt))

    for step in range(steps):
        delayed = []
        for node in range(2):
            if step < delay_steps:
                delayed.append(histories[node][delay_steps - step])
            else:
                delayed.append(emissions[step - delay_steps, node])
        for node in range(2):
            other = 1 - node
            if coupled:
                force_source = k * delayed[other][0] + gamma * delayed[other][1]
                self_emission = emissions[step, node]
                drives[step, node] = (force_source - k * self_emission[0]
                                      - gamma * self_emission[1])
            else:
                force_source = 0.0
                self_emission = emissions[step, node]
                drives[step, node] = (k * (delayed[other][0] - self_emission[0])
                                      + gamma * (delayed[other][1] - self_emission[1]))
            phi, gain = matrices[node]
            ys[node][step + 1] = phi @ ys[node][step] + gain * force_source
            emissions[step + 1, node] = emitted_from_y(
                ys[node][step + 1], models[node]["spec"].n_modes,
                models[node]["spec"].emission_scale,
            )
    # Fuerza en el punto final, útil sólo para completar la grilla de observación.
    for node in range(2):
        other = 1 - node
        delayed_other = emissions[steps - delay_steps, other]
        drives[steps, node] = (k * (delayed_other[0] - emissions[steps, node, 0])
                               + gamma * (delayed_other[1] - emissions[steps, node, 1]))
    qstates = np.stack([
        qstate_from_y(ys[node], models[node]["q_indices"], models[node]["spec"].n_modes)
        for node in range(2)
    ], axis=1)
    return {"emission": emissions, "qstate": qstates, "drive": drives}


def sym_error(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    rms_actual = float(np.sqrt(np.mean(actual**2)))
    rms_pred = float(np.sqrt(np.mean(predicted**2)))
    denom = rms_actual + rms_pred
    return 0.0 if denom == 0.0 else float(2.0 * np.sqrt(np.mean((predicted - actual)**2)) / denom)


def score_core(actual: dict, predicted: dict, sl: slice) -> dict:
    emit_x = sym_error(actual["emission"][sl, :, 0], predicted["emission"][sl, :, 0])
    emit_v = sym_error(actual["emission"][sl, :, 1], predicted["emission"][sl, :, 1])
    qdim = actual["qstate"].shape[-1] // 2
    q_x = sym_error(actual["qstate"][sl, :, :qdim], predicted["qstate"][sl, :, :qdim])
    q_v = sym_error(actual["qstate"][sl, :, qdim:], predicted["qstate"][sl, :, qdim:])
    return {
        "E_emit": (emit_x + emit_v) / 2.0,
        "E_emit_X": emit_x,
        "E_emit_V": emit_v,
        "E_Q": (q_x + q_v) / 2.0,
        "E_Q_X": q_x,
        "E_Q_V": q_v,
        "E_drive": sym_error(actual["drive"][sl], predicted["drive"][sl]),
    }


def score_window(actual: dict, predicted: dict, sl: slice) -> dict:
    combined = score_core(actual, predicted, sl)
    combined["per_node"] = {}
    for node in range(2):
        actual_node = {
            "emission": actual["emission"][:, node:node + 1],
            "qstate": actual["qstate"][:, node:node + 1],
            "drive": actual["drive"][:, node:node + 1],
        }
        predicted_node = {
            "emission": predicted["emission"][:, node:node + 1],
            "qstate": predicted["qstate"][:, node:node + 1],
            "drive": predicted["drive"][:, node:node + 1],
        }
        combined["per_node"][str(node)] = score_core(actual_node, predicted_node, sl)
    return combined


def compact_series(actual: dict, predictions: dict[str, dict]) -> dict:
    width = int(round(SERIES_BIN / DT_OBS))
    start = int(round(0.2 / DT_OBS))
    centers, result = [], {name: {"E_Q": [], "E_emit": []} for name in predictions}
    for left in range(start, len(actual["drive"]) - width + 1, width):
        sl = slice(left, left + width)
        centers.append((left + width / 2.0) * DT_OBS)
        for name, predicted in predictions.items():
            score = score_window(actual, predicted, sl)
            result[name]["E_Q"].append(score["E_Q"])
            result[name]["E_emit"].append(score["E_emit"])
    return {"dt_bin_ut": SERIES_BIN, "t_center_ut": centers, "models": result}


def med(values: list[float]) -> float | None:
    return float(np.median(values)) if values else None


def summarize_rows(rows: list[dict]) -> dict:
    out = {"n": len(rows), "windows": {}}
    for label in ("0.2_2", "2_10", "10_20"):
        out["windows"][label] = {
                "median_feedback_improvement_Q": med([
                    row["windows"][label]["feedback_improvement_Q"] for row in rows
                ]),
                "median_feedback_improvement_emit": med([
                    row["windows"][label]["feedback_improvement_emit"] for row in rows
                ]),
                "median_E_Q_coupled_frozen": med([
                    row["windows"][label]["coupled_frozen"]["E_Q"] for row in rows
                ]),
                "median_E_drive_coupled_frozen": med([
                    row["windows"][label]["coupled_frozen"]["E_drive"] for row in rows
                ]),
                "median_frozen_advantage_Q": med([
                    row["windows"][label]["frozen_advantage_Q"] for row in rows
                ]),
            }
    return out


def summarize(records: list[dict]) -> dict:
    groups = {
        "all": records,
        "healthy": [row for row in records if row["health60"]],
        "not_healthy": [row for row in records if not row["health60"]],
        "transported": [row for row in records if row["arm"] == "t"],
        "fresh": [row for row in records if row["arm"] == "f"],
    }
    out = {name: summarize_rows(rows) for name, rows in groups.items()}
    routes = sorted({row["route"] for row in records})
    out["by_route"] = {
        route: summarize_rows([row for row in records if row["route"] == route])
        for route in routes
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--gate-f-evaluate", required=True, type=Path)
    parser.add_argument("--blocks", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--capsule-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
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
    hashes = {label: verify_input(path, label) for label, path in paths.items()}
    bank = json.loads(paths["bank"].read_text())
    evaluation = json.loads(paths["gate_f_evaluate"].read_text())
    routes = route_map(evaluation)
    blocks = load_blocks(paths["blocks"])
    specs_by_block = {}
    block_by_fingerprint = {}
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

    records = []
    for index, source in enumerate(flatten_bank(bank), 1):
        run_dir = Path(source["run_dir"])
        manifest, states_raw, drive_raw, wl_hash = load_prefix_verified(
            run_dir, source["manifest_sha256"]
        )
        if wl_hash != source["outcome"]["worldline_hash"]:
            raise RuntimeError(f"{source['run_id']}: worldline_hash != banco")
        if float(manifest["dt"]) != DT_PRODUCTION:
            raise RuntimeError(f"{source['run_id']}: dt no canónico")
        topology = manifest["topologia"]
        if topology["edges_ij"] != [[0, 1]] or len(topology["tau"]) != 1:
            raise RuntimeError(f"{source['run_id']}: topología no es par único")
        k = float(manifest["k_global"]) * float(topology["w_k"][0])
        gamma = float(manifest["gamma_c"]) * float(topology["w_gamma"][0])
        delay = float(topology["tau"][0])
        delay_prod = int(round(delay / DT_PRODUCTION))

        models_frozen, models_cold, node_meta = [], [], []
        actual_parts = []
        for node, origin in enumerate(manifest["composicion"]["por_nodo"]):
            fingerprint = manifest["spec_fingerprints"][node]
            block_id = origin.get("block_id", block_by_fingerprint.get(fingerprint))
            if block_id is None:
                raise RuntimeError(f"{source['run_id']} nodo {node}: fingerprint sin bloque")
            spec = specs_by_block[block_id]
            if spec_fingerprint(spec) != manifest["spec_fingerprints"][node]:
                raise RuntimeError(f"{source['run_id']} nodo {node}: fingerprint distinto")
            parts = split_state(states_raw[node], spec)
            actual_parts.append(parts)
            initial = np.concatenate((parts["x"][0], parts["v"][0], parts["z"][0]))
            matrix_frozen, drive_frozen = jacobian_fd(
                spec, b_fixed=parts["b"][0], e_fixed=parts["e"][0]
            )
            matrix_cold, drive_cold = jacobian_fd(spec)
            q_indices = np.asarray(spec.layer_indices[next(
                layer for layer in spec.layer_indices if layer.name == "Q"
            )], dtype=int)
            common = {"spec": spec, "initial": initial, "q_indices": q_indices}
            models_frozen.append({**common, "matrix": matrix_frozen,
                                  "drive_vector": drive_frozen})
            models_cold.append({**common, "matrix": matrix_cold,
                                "drive_vector": drive_cold})
            node_meta.append({
                "node": node,
                "block_id": block_id,
                "origin": origin["origen"],
                "b0": parts["b"][0].tolist(),
                "e0": parts["e"][0].tolist(),
                "norm_b0": float(np.linalg.norm(parts["b"][0])),
                "norm_e0": float(np.linalg.norm(parts["e"][0])),
                "max_real_eigenvalue_frozen": float(np.max(np.linalg.eigvals(matrix_frozen).real)),
                "max_real_eigenvalue_cold": float(np.max(np.linalg.eigvals(matrix_cold).real)),
            })

        obs_indices = np.arange(0, int(round(HORIZON / DT_PRODUCTION)) + 1, 10)
        actual_y = [np.concatenate((parts["x"], parts["v"], parts["z"]), axis=1)[obs_indices]
                    for parts in actual_parts]
        actual = {
            "emission": np.stack([
                emitted_from_y(actual_y[node], models_frozen[node]["spec"].n_modes,
                               models_frozen[node]["spec"].emission_scale)
                for node in range(2)
            ], axis=1),
            "qstate": np.stack([
                qstate_from_y(actual_y[node], models_frozen[node]["q_indices"],
                              models_frozen[node]["spec"].n_modes)
                for node in range(2)
            ], axis=1),
            "drive": drive_raw[obs_indices],
        }

        histories_coarse = [history_for_node(
            manifest["composicion"]["por_nodo"][node], models_frozen[node]["initial"],
            models_frozen[node]["spec"], inventory, capsule_root, delay_prod, DT_OBS
        ) for node in range(2)]
        histories_fine = [history_for_node(
            manifest["composicion"]["por_nodo"][node], models_frozen[node]["initial"],
            models_frozen[node]["spec"], inventory, capsule_root, delay_prod, DT_FINE
        ) for node in range(2)]

        predictions = {
            "independent_frozen": simulate(models_frozen, histories_coarse, k, gamma,
                                            delay, DT_OBS, coupled=False),
            "coupled_frozen": simulate(models_frozen, histories_coarse, k, gamma,
                                        delay, DT_OBS, coupled=True),
            "coupled_cold": simulate(models_cold, histories_coarse, k, gamma,
                                      delay, DT_OBS, coupled=True),
        }
        fine = simulate(models_frozen, histories_fine, k, gamma, delay, DT_FINE, coupled=True)
        fine_on_obs = {key: value[::2] for key, value in fine.items()}

        window_scores = {}
        convergence_max = 0.0
        for start, end in WINDOWS:
            label = f"{start:g}_{end:g}"
            sl = slice(int(round(start / DT_OBS)), int(round(end / DT_OBS)))
            scores = {name: score_window(actual, pred, sl)
                      for name, pred in predictions.items()}
            convergence = score_window(predictions["coupled_frozen"], fine_on_obs, sl)
            convergence_max = max(convergence_max, convergence["E_Q"], convergence["E_emit"])
            window_scores[label] = {
                **scores,
                "feedback_improvement_Q": (
                    scores["independent_frozen"]["E_Q"] - scores["coupled_frozen"]["E_Q"]
                ),
                "feedback_improvement_emit": (
                    scores["independent_frozen"]["E_emit"]
                    - scores["coupled_frozen"]["E_emit"]
                ),
                "frozen_advantage_Q": (
                    scores["coupled_cold"]["E_Q"] - scores["coupled_frozen"]["E_Q"]
                ),
                "convergence_coarse_vs_fine": convergence,
            }
        health = bool(source["outcome"]["salud_60"])
        record = {
            "run_id": source["run_id"], "pair_id": source["pair_id"],
            "selection_role": source["selection_role"], "arm": source["arm"],
            "health60": health, "outcome_relation": source["outcome_relation"],
            "route": routes[source["run_id"]], "run_dir": str(run_dir),
            "manifest_sha256": source["manifest_sha256"], "worldline_hash": wl_hash,
            "origins": [item["origen"] for item in manifest["composicion"]["por_nodo"]],
            "nodes": node_meta,
            "k": k, "gamma": gamma, "delay": delay,
            "convergence_max_EQ_Eemit": convergence_max,
            "numeric_status": ("RESOLVED" if convergence_max <= NUMERIC_LIMIT
                               else "NUMERICALLY_UNRESOLVED"),
            "windows": window_scores,
            "series": compact_series(actual, predictions),
        }
        records.append(record)
        print(f"[Gate L] {index:02d}/16 {source['run_id']} "
              f"conv={convergence_max:.4f} {record['numeric_status']}", flush=True)

    unresolved = [row["run_id"] for row in records
                  if row["numeric_status"] == "NUMERICALLY_UNRESOLVED"]
    result = {
        "_meta": {
            "script": "tools/link_grumo/gate_l_bidirectional_transient.py",
            "script_sha256": sha256(Path(__file__)),
            "prereg": "audit/LINK_GRUMO_GATE_L_BIDIRECTIONAL_TRANSIENT_PREREG.md",
            "prereg_sha256": sha256(REPO / "audit/LINK_GRUMO_GATE_L_BIDIRECTIONAL_TRANSIENT_PREREG.md"),
            "input_sha256": hashes,
            "capsule_root": str(capsule_root),
            "policy": "entradas y disco externo read-only; no se ejecutó el motor",
            "dt_production": DT_PRODUCTION, "dt_observed": DT_OBS,
            "dt_convergence": DT_FINE, "horizon_ut": HORIZON,
        },
        "model": {
            "primary": "COUPLED-FROZEN",
            "comparators": ["INDEPENDENT-FROZEN", "COUPLED-COLD"],
            "integration": "transición local exacta por expm + drive retardado ZOH",
            "windows_ut": [list(window) for window in WINDOWS],
            "numeric_limit": NUMERIC_LIMIT,
        },
        "summary": {
            "n": len(records), "n_health60": sum(row["health60"] for row in records),
            "n_numeric_unresolved": len(unresolved), "numeric_unresolved": unresolved,
            "groups": summarize(records),
        },
        "warnings": [
            "RETROSPECTIVO: panel Gate F seleccionado después de outcomes; sin p-values ni claim poblacional.",
            "La nula congela b/e y usa la ley v1 direct-only; no modela plasticidad ni kernels diferidos.",
            "El paso ZOH no es bit-exacto al RK4; la doble resolución cuantifica el error.",
            "health60 se usa sólo para descripción; no se optimizó ningún umbral de clasificación.",
            "Cicatriz de ejecución: el primer intento murió antes de scores porque fresh no lleva block_id; se resolvió por spec_fingerprint canónico, sin consultar outcomes.",
            "Cicatriz de contrato: la primera salida temporal agregó ambos nodos y omitió el desglose exigido; se descartó antes de canonizar y se reranearon los 16 films con per_node.",
        ],
        "records": records,
    }
    result = round_floats(result)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[Gate L] salida: {output}")


if __name__ == "__main__":
    main()
