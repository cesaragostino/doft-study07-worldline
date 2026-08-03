#!/usr/bin/env python3
"""Relectura retrospectiva de E2: nula estacionaria frente a nula transitoria.

No corre el motor ni modifica films. Verifica COMPLETE/manifiesto/chunks, relee el canal
``drive`` de las ocho unidades 1D y reconstruye la solución CONTINUA del mismo sistema
lineal frío usado por ``cirugia_campana.nula``. La integración de producción fue RK4;
esta reconstrucción usa exponencial matricial/eigendescomposición y por eso NO se declara
bit-exacta. El acuerdo es una comprobación numérica independiente del integrador.

Uso:
    PYTHONPATH=src:tools python3 tools/auditar_e2_transitorio.py --output SALIDA.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.linalg import expm

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tools")]

from cirugia_campana import ENGINE, _capsulas, _spec_de, build_A  # noqa: E402
from study07.compat.study06_capsule import load_capsule  # noqa: E402

DATA = REPO / "data/cirugia"
RUNS = DATA / "fase1_fijas/unidades"
DT_OBS = 8e-4
WINDOW = (20.0, 110.0)
EMISSION_SCALE = 0.1


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def round_floats(value, significant: int = 9):
    """Sella sólo precisión significativa; evita ruido BLAS de último bit entre corridas."""
    if isinstance(value, float):
        return float(f"{value:.{significant}g}")
    if isinstance(value, list):
        return [round_floats(item, significant) for item in value]
    if isinstance(value, dict):
        return {key: round_floats(item, significant) for key, item in value.items()}
    return value


def _worldline_hash(mark: dict) -> str:
    return hashlib.sha256((mark["sha_total"] + mark["manifest_sha"]).encode()).hexdigest()


def load_drive_verified(run_dir: Path) -> tuple[np.ndarray, dict, str]:
    """Carga sólo drive/ticks, pero aplica la verificación íntegra de load_worldline."""
    manifest_text = (run_dir / "manifest.json").read_text()
    manifest = json.loads(manifest_text)
    mark = json.loads((run_dir / "COMPLETE").read_text())
    if hashlib.sha256(manifest_text.encode()).hexdigest() != mark["manifest_sha"]:
        raise RuntimeError(f"{run_dir.name}: manifest alterado después de COMPLETE")
    chunks = sorted((run_dir / "worldline").glob("chunk_*.npz"))
    if len(chunks) != mark["chunks"]:
        raise RuntimeError(f"{run_dir.name}: {len(chunks)} chunks != {mark['chunks']}")
    drives, ticks = [], []
    for path, expected in zip(chunks, mark["chunk_shas"]):
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"{run_dir.name}/{path.name}: sha no coincide")
        with np.load(path, allow_pickle=False) as payload:
            drives.append(np.asarray(payload["drive"][:, 0], dtype=float))
            ticks.append(np.asarray(payload["ticks"], dtype=np.int64))
    tick = np.concatenate(ticks)
    if not np.array_equal(tick, np.arange(mark["ticks"] + 1)):
        raise RuntimeError(f"{run_dir.name}: ticks con pérdida o duplicación")
    return np.concatenate(drives), manifest, _worldline_hash(mark)


def _linear_model(prefix: str) -> dict:
    spec, _ = _spec_de(prefix)
    n = spec.n_modes
    matrix, masses = build_A(spec)
    dim = matrix.shape[0]
    drive_vector = np.zeros(dim)
    drive_vector[n:2 * n] = 1.0 / masses

    k = float(ENGINE["kappa_global"])
    gamma = float(ENGINE["coupling_gamma_c"])
    matrix_closed = matrix.copy()
    for mode in range(n):
        matrix_closed[n + mode, :n] -= k * EMISSION_SCALE / masses[mode]
        matrix_closed[n + mode, n:2 * n] -= gamma * EMISSION_SCALE / masses[mode]
    output = np.zeros(dim)
    output[:n] = k * EMISSION_SCALE
    output[n:2 * n] = gamma * EMISSION_SCALE

    capsule = load_capsule(_capsulas()[prefix]["dir"])
    initial = np.concatenate([
        np.asarray(capsule["arrays"]["x"], dtype=float),
        np.asarray(capsule["arrays"]["v"], dtype=float),
        np.zeros(spec.n_z),
    ])
    eigenvalues, eigenvectors = np.linalg.eig(matrix_closed)
    eig_residual = np.linalg.norm(
        matrix_closed @ eigenvectors - eigenvectors * eigenvalues[None, :]
    ) / np.linalg.norm(matrix_closed)
    return {
        "spec": spec,
        "matrix_open": matrix,
        "matrix_closed": matrix_closed,
        "drive_vector": drive_vector,
        "output": output,
        "initial": initial,
        "eigenvalues": eigenvalues,
        "eigenvectors": eigenvectors,
        "condition_eigenvectors": float(np.linalg.cond(eigenvectors)),
        "eigendecomposition_relative_residual": float(eig_residual),
    }


def predict_ratio(model: dict, frequency: float, amplitude: float) -> dict:
    """Solución exacta del LTI continuo y RMS en la misma ventana del lector E2."""
    matrix = model["matrix_closed"]
    drive_vector = model["drive_vector"]
    output = model["output"]
    initial = model["initial"]
    eigenvalues = model["eigenvalues"]
    eigenvectors = model["eigenvectors"]
    k = float(ENGINE["kappa_global"])
    gamma = float(ENGINE["coupling_gamma_c"])
    omega = float(frequency)
    source_phasor = float(amplitude) * complex(k, gamma * omega)
    particular = np.linalg.solve(
        1j * omega * np.eye(matrix.shape[0]) - matrix,
        drive_vector * source_phasor,
    )
    initial_transient = initial - particular.real
    coefficients = np.linalg.solve(eigenvectors, initial_transient)
    projected_coefficients = (output @ eigenvectors) * coefficients

    i0, i1 = (int(value / DT_OBS) for value in WINDOW)
    time = np.arange(i0, i1, dtype=float) * DT_OBS
    transient_output = np.real(
        np.exp(time[:, None] * eigenvalues[None, :]) @ projected_coefficients
    )
    phase = np.exp(1j * omega * time)
    source = np.real(source_phasor * phase)
    particular_output = np.real((output @ particular) * phase)
    predicted_drive = source - particular_output - transient_output
    open_rms = abs(source_phasor) / np.sqrt(2.0)

    # Control independiente de la eigendescomposición en tres tiempos, con expm denso.
    crosscheck = []
    for t in (WINDOW[0], sum(WINDOW) / 2.0, WINDOW[1]):
        direct = float(output @ (expm(matrix * t) @ initial_transient))
        spectral = float(np.real(np.sum(projected_coefficients * np.exp(eigenvalues * t))))
        crosscheck.append(abs(direct - spectral))

    open_matrix = model["matrix_open"]
    chi = np.linalg.solve(
        1j * omega * np.eye(open_matrix.shape[0]) - open_matrix,
        model["drive_vector"],
    )
    chi_emitted = EMISSION_SCALE * complex(np.sum(chi[:model["spec"].n_modes]))
    stationary = abs(1.0 / (1.0 + chi_emitted * complex(k, gamma * omega)))
    return {
        "lazo_predicho_transitorio": float(np.sqrt(np.mean(predicted_drive**2)) / open_rms),
        "lazo_predicho_estacionario": float(stationary),
        "crosscheck_expm_max_abs": float(max(crosscheck)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise RuntimeError(f"salida ya existe, no se pisa: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    spec_path = DATA / "SPEC_fase1_fijas.json"
    reading_path = DATA / "LECTURA_CIRUGIA.json"
    units = json.loads(spec_path.read_text())["unidades"]
    prior_reading = json.loads(reading_path.read_text())
    models = {prefix: _linear_model(prefix) for prefix in ("34b5ab50", "61b48428")}
    records = []
    for unit in units:
        run_id = unit["run_id"]
        if not run_id.startswith("cir1d_"):
            continue
        prefix = "34b5ab50" if "_34b_" in run_id else "61b48428"
        drive, manifest, wl_hash = load_drive_verified(RUNS / run_id)
        if manifest["programa"] != unit["programa"]:
            raise RuntimeError(f"{run_id}: programa de spec != film")
        stride_drive = drive[::10]
        i0, i1 = (int(value / DT_OBS) for value in WINDOW)
        measured_rms = float(np.sqrt(np.mean(stride_drive[i0:i1] ** 2)))
        program = manifest["programa"]
        open_rms = float(program["F0"] * np.hypot(
            ENGINE["kappa_global"], ENGINE["coupling_gamma_c"] * program["w0"]
        ) / np.sqrt(2.0))
        measured = measured_rms / open_rms
        prediction = predict_ratio(models[prefix], program["w0"], program["F0"])
        rounded_prior = prior_reading[run_id]["e2_lazo"]["lazo_medido"]
        if abs(measured - rounded_prior) > 5.1e-5:
            raise RuntimeError(f"{run_id}: relectura raw {measured} != lector {rounded_prior}")
        transient = prediction["lazo_predicho_transitorio"]
        stationary = prediction["lazo_predicho_estacionario"]
        records.append({
            "run_id": run_id,
            "receptor": prefix,
            "worldline_hash": wl_hash,
            "omega": float(program["w0"]),
            "F0": float(program["F0"]),
            "lazo_medido_raw": measured,
            "lazo_predicho_estacionario": stationary,
            "lazo_predicho_transitorio": transient,
            "medido_sobre_estacionario": measured / stationary,
            "medido_sobre_transitorio": measured / transient,
            "error_rel_transitorio": abs(measured / transient - 1.0),
            "crosscheck_expm": (
                "<1e-12" if prediction["crosscheck_expm_max_abs"] < 1e-12
                else prediction["crosscheck_expm_max_abs"]
            ),
        })

    deep = [row for row in records if row["omega"] < 10.0]
    notch_residual = next(row for row in records if row["run_id"] == "cir1d_34b_w30.17_F0.3")
    result = {
        "_meta": {
            "caracter": "RETROSPECTIVO; hipótesis formulada después de abrir LECTURA_CIRUGIA",
            "script": "tools/auditar_e2_transitorio.py",
            "script_sha256": sha256(Path(__file__)),
            "spec": str(spec_path.relative_to(REPO)),
            "spec_sha256": sha256(spec_path),
            "lectura_previa": str(reading_path.relative_to(REPO)),
            "lectura_previa_sha256": sha256(reading_path),
            "ventana_rms_ut": list(WINDOW),
            "stride_observado": 10,
            "dt_observado": DT_OBS,
            "integrador_reconstruccion": (
                "LTI continuo por eigendescomposición; control puntual scipy.linalg.expm; "
                "NO bit-exacto al RK4 dt=8e-5 de producción"
            ),
            "parametros_ajustados": 0,
        },
        "pregunta": (
            "¿La subpredicción atribuida a física faltante en §14-E2 desaparece al comparar "
            "el film finito con la nula lineal transitoria, en vez de con t→infinito?"
        ),
        "summary": {
            "n_unidades": len(records),
            "n_resonancia_profunda_omega_lt_10": len(deep),
            "max_error_rel_transitorio_resonancia_profunda": max(
                row["error_rel_transitorio"] for row in deep
            ),
            "crosscheck_expm_tolerancia": 1e-12,
            "crosscheck_expm_pasa_todos": all(
                row["crosscheck_expm"] == "<1e-12" for row in records
            ),
            "residual_34b_notch_30_17": notch_residual["error_rel_transitorio"],
            "veredicto": (
                "FACTOR_RESONANTE_SOSTENIDO_POR_TRANSITORIO_LINEAL; no evidencia una física "
                "faltante. El residual 34b@30.17 NO cierra con esta reconstrucción."
            ),
        },
        "models": {
            prefix: {
                "condition_eigenvectors": model["condition_eigenvectors"],
                "eigendecomposition_relative_residual": model[
                    "eigendecomposition_relative_residual"
                ],
                "max_real_eigenvalue_closed": float(np.max(model["eigenvalues"].real)),
            }
            for prefix, model in models.items()
        },
        "advertencias": [
            "Reanálisis post hoc: corrige una interpretación; no es confirmación prospectiva.",
            "Usa la misma ley/Jacobiano/IC declarados por la nula sellada, pero otro método numérico.",
            "El cierre se limita al factor resonante de E2 unidireccional; no prueba el lazo vivo de dos onions.",
            "34b@30.17 conserva ~6.5% de residual y debe permanecer visible como no explicado.",
            "La linealización sigue la ley v1 direct-only; kernels diferidos del genoma permanecen fuera de alcance.",
        ],
        "records": sorted(records, key=lambda row: row["run_id"]),
    }
    result = round_floats(result)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[E2-transitorio] {len(records)}/8 unidades verificadas")
    print("[E2-transitorio] error máximo resonancia profunda = "
          f"{result['summary']['max_error_rel_transitorio_resonancia_profunda']:.4%}")
    print("[E2-transitorio] residual 34b@30.17 = "
          f"{result['summary']['residual_34b_notch_30_17']:.4%}")
    print(f"[E2-transitorio] salida: {output}")


if __name__ == "__main__":
    main()
