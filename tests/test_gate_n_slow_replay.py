from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools/link_grumo")]

import gate_m_nonlinear_fast as gate_m
import gate_n_slow_replay as gate_n
from study07.physics.rhs import derivatives
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


def _state(x=1.0, b=0.5, e=2.0):
    return NodeState(x=np.array([x]), v=np.array([0.0]), z=np.array([]),
                     b=np.array([b]), e=np.array([e]))


def test_e_is_algebraically_inert_in_fast_rhs_when_slow_derivatives_are_frozen():
    spec = gate_m.frozen_slow_spec(_spec())
    first = derivatives(spec, _state(e=-100.0), drive_ext=0.3)
    second = derivatives(spec, _state(e=100.0), drive_ext=0.3)
    np.testing.assert_array_equal(first.x, second.x)
    np.testing.assert_array_equal(first.v, second.v)
    np.testing.assert_array_equal(first.z, second.z)
    np.testing.assert_array_equal(first.b, np.zeros(1))
    np.testing.assert_array_equal(second.b, np.zeros(1))


def test_schedule_and_masks_are_exact():
    previous = gate_n.HORIZON
    gate_n.HORIZON = 0.0016
    try:
        observed = np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0],
                             [6.0], [7.0], [8.0], [9.0], [10.0], [11.0],
                             [12.0], [13.0], [14.0], [15.0], [16.0],
                             [17.0], [18.0], [19.0], [20.0]])
        schedule = gate_n.b_schedule(observed, 0.0008)
        np.testing.assert_allclose(schedule[:, 0], [0.0, 5.0, 10.0, 15.0, 20.0])
        masks = gate_n.replay_masks([_spec(), _spec()], "SOURCE_Q_B")
        np.testing.assert_array_equal(masks[0], [True])
        np.testing.assert_array_equal(masks[1], [False])
    finally:
        gate_n.HORIZON = previous


def test_replay_projects_b_at_step_end_and_freezes_unselected_node():
    previous = gate_n.HORIZON
    gate_n.HORIZON = 0.0016
    try:
        manifest = {
            "seed": 1, "k_global": 0.0, "gamma_c": 0.0,
            "topologia": {"edges_ij": [[0, 1]], "w_k": [1.0], "w_gamma": [1.0],
                          "tau": [0.0016]},
        }
        history = [np.array([[1.0, 0.0], [0.9, -0.1], [0.8, -0.2]]),
                   np.array([[2.0, 0.0], [1.9, -0.1], [1.8, -0.2]])]
        b0 = np.linspace(0.5, 1.5, 21)[:, None]
        b1 = np.linspace(2.0, 3.0, 21)[:, None]
        result = gate_n.simulate_replay([_spec(), _spec()],
                                        [_state(1.0, 0.5), _state(2.0, 2.0)],
                                        history, [b0, b1], manifest, 0.0008,
                                        "SOURCE_Q_B")
        assert result["max_abs_replay_projection_error"] == 0.0
        assert result["max_abs_frozen_coordinate_drift"] == 0.0
        assert np.all(np.isfinite(result["qstate"]))
    finally:
        gate_n.HORIZON = previous
