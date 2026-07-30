"""GATE F2 — el motor mínimo de Study07 reproduce los 5 fixtures del oráculo Study06.

Tolerancia: ≤ 3.8579e-11 = el piso numérico MEDIDO (dt vs dt/2, §93-C3 del oráculo) — no un
número inventado. Los fixtures traen: estado PRE-step (tick 0) + todos los estados por tick
float64 + historia causal inicial + engine_params + (f5) el estado del RNG antes de cada step.

El oráculo se localiza por STUDY06_ORACLE_PATH o por la ruta hermana por defecto.
"""
import json
import os
import unittest
from pathlib import Path

import numpy as np

from study07.compat.study06_v4 import birth_state, load_canonical_blocks, parse_theta_v2
from study07.engine.network import Network
from study07.physics.state import NodeState

ORACLE = Path(os.environ.get(
    "STUDY06_ORACLE_PATH",
    Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"))
FIXTURES = ORACLE / "tests" / "fixtures"
BLOCKS_JSON = ORACLE / "data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json"

TOL = 3.8579e-11   # piso medido §93-C3 — el gate del contrato


def _flat(state: NodeState) -> np.ndarray:
    return np.concatenate([state.x, state.v, state.z, state.b, state.e])


def _build_from_fixture(fx) -> tuple:
    meta = json.loads(str(fx["meta_json"]))
    blocks = load_canonical_blocks(BLOCKS_JSON)
    emission_norm = meta["emission_norm"]
    specs, states = [], []
    for idx, bid in enumerate(meta["block_ids"]):
        theta = blocks[bid]["theta_internal"]
        n_modes = len(theta.get("modes", []))
        scale = 1.0 / max(n_modes, 1) if emission_norm == "mean" else 1.0
        spec, _ = parse_theta_v2(theta, emission_scale=scale)
        specs.append(spec)
        states.append(birth_state(spec, meta["seed"], idx,
                                  e_ref_policy=meta.get("e_ref_policy",
                                                        "receiver_initial_energy")))
    ep = meta["engine_params"]
    net = Network(
        specs, states, meta["edges"], dt=float(meta["dt"]), seed=int(meta["seed"]),
        k_global=float(ep.get("kappa_global", ep.get("K_global", 0.0))),
        coupling_damp_ratio=float(ep.get("coupling_damp_ratio", 0.0)),
        coupling_gamma_c=(float(ep["coupling_gamma_c"]) if "coupling_gamma_c" in ep else None),
        tau_field=float(ep.get("tau_field", 0.0)),
        temperature=float(ep.get("temperature", 0.0)),
    )
    return net, meta


def _replay(nombre: str, use_rng_states: bool = False) -> dict:
    path = FIXTURES / f"study07_{nombre}.npz"
    if not path.exists():
        raise unittest.SkipTest(f"oráculo no disponible: {path}")
    fx = np.load(path, allow_pickle=False)
    net, meta = _build_from_fixture(fx)
    n_nodes = len(net.specs)
    esperados = [fx[f"estados_nodo{j}"] for j in range(n_nodes)]

    # estado inicial PRE-step (tick 0) debe coincidir ANTES de integrar nada
    max_d0 = max(float(np.max(np.abs(_flat(net.states[j]) - esperados[j][0])))
                 for j in range(n_nodes))
    # historia causal inicial
    d_buf = float(np.max(np.abs(net.history.buffer - fx["buffer0"])))

    rng_states = ([json.loads(s) for s in fx["rng_states_json"]] if use_rng_states else None)
    ticks = int(meta["ticks"])
    max_d = 0.0
    peor = (0, -1)
    for tick in range(1, ticks + 1):
        if rng_states is not None:
            # replay EXACTO del stream: el estado del RNG capturado ANTES de este step
            net.noise_rng.bit_generator.state = rng_states[tick - 1]
        net.step()
        for j in range(n_nodes):
            d = float(np.max(np.abs(_flat(net.states[j]) - esperados[j][tick])))
            if d > max_d:
                max_d, peor = d, (tick, j)
    return {"max_d0": max_d0, "d_buf": d_buf, "max_d": max_d, "peor": peor,
            "ticks": ticks, "n_nodes": n_nodes}


class TestConformidad(unittest.TestCase):
    """Cada fixture es un test; el reporte imprime el residuo real (queda en el log del gate)."""

    def _gate(self, nombre, use_rng=False):
        r = _replay(nombre, use_rng_states=use_rng)
        print(f"\n[gate:{nombre}] d0={r['max_d0']:.3e} buf={r['d_buf']:.3e} "
              f"max|d|={r['max_d']:.3e} (tick {r['peor'][0]}, nodo {r['peor'][1]}) "
              f"ticks={r['ticks']}")
        self.assertEqual(r["max_d0"], 0.0,
                         "el estado PRE-step debe ser BIT-exacto (misma semilla derivada)")
        self.assertEqual(r["d_buf"], 0.0, "la historia causal inicial debe ser bit-exacta")
        self.assertLessEqual(r["max_d"], TOL,
                             f"max|d|={r['max_d']:.3e} > piso {TOL:.4e} — la transcripción "
                             "difiere del oráculo: revisar contra PHYSICS_CONTRACT")

    def test_f1_gold_aislado(self):
        self._gate("f1_gold_aislado")

    def test_f2_par_sin_delay(self):
        self._gate("f2_par_sin_delay")

    def test_f3_par_delay_fraccional(self):
        self._gate("f3_par_delay_fraccional")

    def test_f4_red_heterogenea(self):
        self._gate("f4_red_heterogenea")

    def test_f5_ruido_rng(self):
        self._gate("f5_ruido_rng", use_rng=True)


class TestArquitectura(unittest.TestCase):
    def test_physics_no_conoce_olas(self):
        """Cláusula 1 de COA como gate ejecutable. Límite de PALABRA: la primera versión
        matcheaba substrings y se cazó a sí misma con «una sOLA implementación»."""
        import re
        rx = re.compile(r"\bolas?\b|\bola\d", re.IGNORECASE)
        raiz = Path(__file__).resolve().parents[1] / "src" / "study07" / "physics"
        for p in raiz.glob("*.py"):
            m = rx.search(p.read_text())
            self.assertIsNone(m, f"{p.name} menciona {m.group(0) if m else ''!r} — "
                                 "physics/ es agnóstico de nivel")

    def test_engine_no_importa_instrumentos_ni_io(self):
        raiz = Path(__file__).resolve().parents[1] / "src" / "study07"
        for sub in ("physics", "engine"):
            for p in (raiz / sub).glob("*.py"):
                t = p.read_text()
                for prohibido in ("import matplotlib", "import pandas", "open(", "savez",
                                  "instruments"):
                    self.assertNotIn(prohibido, t, f"{sub}/{p.name} contiene {prohibido!r}")


if __name__ == "__main__":
    unittest.main()
