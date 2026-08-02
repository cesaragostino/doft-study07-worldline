"""Respuesta lineal congelada de un onion, sin parámetros ajustados."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from study07.compat.study06_v4 import parse_theta_v2
from study07.physics import rhs
from study07.physics.state import Layer, NodeState


def load_blocks(path: Path) -> dict[str, dict]:
    blocks = json.loads(Path(path).read_text())
    return {str(block["block_id"]): block for block in blocks}


def parse_block(block: dict, emission_scale: float = 0.1):
    spec, _ = parse_theta_v2(block["theta_internal"], emission_scale=emission_scale)
    return spec


def jacobian_fd(spec, b_fixed: np.ndarray | None = None,
                e_fixed: np.ndarray | None = None, h: float = 1e-6):
    """Jacobiano (x,v,z), con variables lentas congeladas, y vector de entrada drive."""
    n, nz, nl = spec.n_modes, spec.n_z, spec.n_layers
    dim = 2 * n + nz
    b = np.zeros(nl) if b_fixed is None else np.asarray(b_fixed, dtype=float)
    e = np.zeros(nl) if e_fixed is None else np.asarray(e_fixed, dtype=float)
    if b.shape != (nl,) or e.shape != (nl,):
        raise ValueError("b/e no coinciden con n_layers")

    def evaluate(vector: np.ndarray, drive: float = 0.0) -> np.ndarray:
        state = NodeState(x=vector[:n].copy(), v=vector[n:2 * n].copy(),
                          z=vector[2 * n:].copy(), b=b.copy(), e=e.copy())
        derivative = rhs.derivatives(spec, state, drive_ext=drive)
        return np.concatenate([derivative.x, derivative.v, derivative.z])

    matrix = np.zeros((dim, dim))
    for column in range(dim):
        delta = np.zeros(dim)
        delta[column] = h
        matrix[:, column] = (evaluate(delta) - evaluate(-delta)) / (2.0 * h)
    zero = np.zeros(dim)
    drive_vector = evaluate(zero, drive=1.0) - evaluate(zero, drive=0.0)
    return matrix, drive_vector


def chi_modes(matrix: np.ndarray, drive_vector: np.ndarray,
              omega: float | np.ndarray, n_modes: int) -> np.ndarray:
    ws = np.atleast_1d(np.asarray(omega, dtype=float))
    identity = np.eye(matrix.shape[0])
    result = np.array([np.linalg.solve(1j * w * identity - matrix,
                                       drive_vector)[:n_modes] for w in ws])
    return result[0] if np.ndim(omega) == 0 else result


def layer_indices(spec, layer: str = "Q") -> np.ndarray:
    enum = Layer[layer]
    return np.asarray(spec.layer_indices[enum], dtype=int)


def chi_layer_sum(spec, matrix: np.ndarray, drive_vector: np.ndarray,
                  omega: float | np.ndarray, layer: str = "Q") -> np.ndarray:
    modes = chi_modes(matrix, drive_vector, omega, spec.n_modes)
    indices = layer_indices(spec, layer)
    return np.sum(modes[..., indices], axis=-1)


def chi_emitted(spec, matrix: np.ndarray, drive_vector: np.ndarray,
                omega: float | np.ndarray) -> np.ndarray:
    """Transferencia drive externo -> coordenada emitida (suma de modos × escala)."""
    modes = chi_modes(matrix, drive_vector, omega, spec.n_modes)
    return spec.emission_scale * np.sum(modes, axis=-1)


def local_minima(x: np.ndarray, y: np.ndarray) -> list[dict]:
    mask = np.r_[False, (y[1:-1] < y[:-2]) & (y[1:-1] < y[2:]), False]
    return [{"omega": float(x[i]), "valor": float(y[i])} for i in np.flatnonzero(mask)]
