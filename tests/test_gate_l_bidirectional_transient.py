from types import SimpleNamespace
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/link_grumo"))

from gate_l_bidirectional_transient import simulate, sym_error  # noqa: E402


def _model(initial):
    spec = SimpleNamespace(n_modes=1, emission_scale=1.0)
    return {
        "spec": spec,
        "initial": np.asarray(initial, dtype=float),
        "q_indices": np.asarray([0], dtype=int),
        "matrix": np.asarray([[0.0, 1.0], [-1.0, -0.1]]),
        "drive_vector": np.asarray([0.0, 1.0]),
    }


def test_gate_l_zero_link_equals_independent():
    models = [_model([1.0, 0.0]), _model([0.0, 1.0])]
    histories = [np.tile([1.0, 0.0], (21, 1)),
                 np.tile([0.0, 1.0], (21, 1))]
    independent = simulate(models, histories, k=0.0, gamma=0.0,
                           delay=0.2, dt=0.01, coupled=False)
    coupled = simulate(models, histories, k=0.0, gamma=0.0,
                       delay=0.2, dt=0.01, coupled=True)
    for key in ("emission", "qstate", "drive"):
        assert np.array_equal(independent[key], coupled[key])


def test_gate_l_symmetric_error_identity_and_scale():
    signal = np.asarray([1.0, -2.0, 3.0])
    assert sym_error(signal, signal) == 0.0
    assert 0.0 < sym_error(signal, signal * 2.0) < 2.0
