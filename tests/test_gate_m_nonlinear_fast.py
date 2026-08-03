from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools/link_grumo")]

from gate_m_nonlinear_fast import frozen_slow_spec, history_buffer, simulate_nonlinear
from study07.physics.state import Layer, Mode, NodeSpec, NodeState, StructParams


def _spec():
    return NodeSpec(
        modes=(Mode(layer=Layer.Q, index=0, omega0=2.0, mass=1.0, gamma=0.1),),
        intra_pairs=(), direct_links=(), layer_mem={}, mem_layer_order=(),
        W=np.empty((0, 0)), mem_index={},
        struct=StructParams(
            tau_e={Layer.Q: 2.0}, tau_b={Layer.Q: 3.0},
            alpha_b={Layer.Q: 0.2}, e_ref={Layer.Q: 0.0},
        ),
        layers_present=(Layer.Q,), layer_indices={Layer.Q: (0,)}, emission_scale=1.0,
    )


def _state(x):
    return NodeState(x=np.array([x]), v=np.array([0.0]), z=np.array([]),
                     b=np.array([0.5]), e=np.array([2.0]))


def test_frozen_spec_makes_slow_derivatives_exactly_zero():
    from study07.physics.rhs import derivatives

    spec = frozen_slow_spec(_spec())
    derivative = derivatives(spec, _state(1.0), drive_ext=0.0)
    np.testing.assert_array_equal(derivative.b, np.zeros(1))
    np.testing.assert_array_equal(derivative.e, np.zeros(1))


def test_history_buffer_roundtrip_and_zero_link_freezes_slow_state():
    history = [np.array([[1.0, 0.0], [0.8, -0.1], [0.6, -0.2]]),
               np.array([[2.0, 0.0], [1.8, -0.1], [1.6, -0.2]])]
    buffer, head = history_buffer(history)
    assert head == 0
    for age in range(3):
        np.testing.assert_array_equal(buffer[(-age) % 3],
                                      np.stack([history[0][age], history[1][age]]))

    manifest = {
        "seed": 1, "k_global": 0.0, "gamma_c": 0.0,
        "topologia": {"edges_ij": [[0, 1]], "w_k": [1.0], "w_gamma": [1.0],
                      "tau": [0.0016]},
    }
    # Acorta el horizonte del módulo sólo dentro del test.
    import gate_m_nonlinear_fast as gate_m
    previous = gate_m.HORIZON
    gate_m.HORIZON = 0.008
    try:
        result = simulate_nonlinear([_spec(), _spec()], [_state(1.0), _state(2.0)],
                                    history, manifest, dt=0.0008)
    finally:
        gate_m.HORIZON = previous
    assert result["max_abs_drift_b"] == 0.0
    assert result["max_abs_drift_e"] == 0.0
    assert np.all(np.isfinite(result["qstate"]))
