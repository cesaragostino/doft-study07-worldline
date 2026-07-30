"""GATES F3 — worldline + checkpoint (plan §20.9 Fase 3, los cuatro gates + dos propios).

1. corrida directa vs checkpoint→restore→continuación: BIT-exactas (con T>0: el RNG viaja).
2. cerrar/reabrir en frontera de chunk: ni pérdida ni duplicado; fila 0 = PRE-step.
3. una interrupción NO publica COMPLETE; el lector la rechaza fail-loud.
4. historia NO-uniforme round-trip exacto (la restauración que las cápsulas v4 necesitan).
5. (propio) el canal de kicks es REDERIVABLE del rng_state del chunk — la worldline es
   causalmente completa, no decorativa.
6. (propio) el runner aborta fail-loud en blow-up sin publicar COMPLETE.

Red de trabajo: la MISMA composición del fixture f6 (self-contained, régimen caliente, T>0,
aristas mixtas) — sin oráculo externo.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

MAN = {"run_id": "test", "spec_tipo": "M1",
       "hashes_base_externa": {"fixture_f6": "local"}}

from study07.artifacts.checkpoint import (load_checkpoint, network_from_checkpoint,
                                          save_checkpoint)
from study07.artifacts.recorder import WorldlineRecorder, load_worldline
from study07.artifacts.runner import run
from study07.compat.study06_v4 import parse_theta_v2
from study07.engine.network import Network
from study07.physics.state import Layer, NodeState

REPO = Path(__file__).resolve().parents[1]
F6 = REPO / "tests/fixtures/study07_f6_regimen_caliente.npz"


def _f6_net(ticks_ya_corridos=0):
    fx = np.load(F6, allow_pickle=False)
    meta = json.loads(str(fx["meta_json"]))
    specs, states = [], []
    for idx, theta in enumerate(meta["thetas_embebidos"]):
        spec, _ = parse_theta_v2(theta, emission_scale=1.0 / max(len(theta["modes"]), 1))
        for lname, val in meta["e_ref_por_nodo"][idx].items():
            spec.struct.e_ref[Layer[lname]] = float(val)
        specs.append(spec)
        fila0 = fx[f"estados_nodo{idx}"][0]
        n = spec.n_modes
        states.append(NodeState(
            x=fila0[:n].copy(), v=fila0[n:2 * n].copy(),
            z=fila0[2 * n:2 * n + spec.n_z].copy(),
            b=fila0[2 * n + spec.n_z:2 * n + spec.n_z + spec.n_layers].copy(),
            e=fila0[2 * n + spec.n_z + spec.n_layers:].copy()))
    ep = meta["engine_params"]
    net = Network(specs, states, meta["edges"], dt=float(meta["dt"]), seed=int(meta["seed"]),
                  k_global=float(ep["kappa_global"]),
                  coupling_gamma_c=float(ep["coupling_gamma_c"]),
                  tau_field=float(ep.get("tau_field", 0.0)),
                  temperature=float(ep.get("temperature", 0.0)))
    for _ in range(ticks_ya_corridos):
        net.step()
    return net, specs, meta


def _flat(st):
    return np.concatenate([st.x, st.v, st.z, st.b, st.e])


class TestCheckpointRestore(unittest.TestCase):

    def test_gate1_continuacion_bit_exacta_con_ruido(self):
        """Directa 120 ticks vs [60 ticks → checkpoint → restore → 60 ticks]: BIT-exacto.
        T=0.05 ⇒ si el RNG no viajara, divergiría en el primer kick."""
        directa, _, _ = _f6_net()
        for _ in range(120):
            directa.step()

        mitad, specs, meta = _f6_net(ticks_ya_corridos=60)
        with tempfile.TemporaryDirectory() as td:
            ck_path = save_checkpoint(Path(td) / "ck.npz", mitad, tick=60)
            ck = load_checkpoint(ck_path)
            # specs FRESCOS (reconstrucción real, no reuso de objetos vivos)
            fx = np.load(F6, allow_pickle=False)
            meta2 = json.loads(str(fx["meta_json"]))
            specs2 = []
            for theta in meta2["thetas_embebidos"]:
                sp, _ = parse_theta_v2(theta, emission_scale=1.0 / max(len(theta["modes"]), 1))
                specs2.append(sp)
            ep = meta2["engine_params"]
            # A4: TODO sale de la meta del checkpoint; la constitución se verifica por huella
            cont = network_from_checkpoint(specs2, ck)
        for _ in range(60):
            cont.step()
        for j in range(3):
            d = float(np.max(np.abs(_flat(cont.states[j]) - _flat(directa.states[j]))))
            self.assertEqual(d, 0.0, f"nodo {j}: continuación difiere en {d:.3e}")
        self.assertEqual(float(np.max(np.abs(cont.history.buffer - directa.history.buffer))), 0.0)
        self.assertEqual(cont.history.head_idx, directa.history.head_idx)
        self.assertEqual(json.dumps(cont.noise_rng.bit_generator.state, default=str),
                         json.dumps(directa.noise_rng.bit_generator.state, default=str))

    def test_gate4_historia_no_uniforme_roundtrip(self):
        """Tras 60 ticks el buffer es NO-uniforme: el checkpoint debe transportarlo EXACTO
        (la API que las cápsulas v4 necesitan y que el F2 dejó declarada como no-cubierta)."""
        net, _, _ = _f6_net(ticks_ya_corridos=60)
        buf = np.asarray(net.history.buffer)
        self.assertGreater(float(np.std(buf[:, 0, 0])), 0.0, "el buffer quedó uniforme: el "
                           "escenario no ejercita la restauración no-uniforme")
        with tempfile.TemporaryDirectory() as td:
            ck = load_checkpoint(save_checkpoint(Path(td) / "ck.npz", net, tick=60))
        self.assertEqual(float(np.max(np.abs(ck["buffer"] - buf))), 0.0)
        self.assertEqual(ck["head"], net.history.head_idx)


class TestWorldline(unittest.TestCase):

    def test_gate2_chunks_sin_perdida_ni_duplicado(self):
        """chunk_ticks=32 con 100 ticks (no divide): el lector reensambla 101 filas exactas,
        fila 0 = PRE-step, y coincide con el registro en memoria."""
        net, _, _ = _f6_net()
        pre = [_flat(s).copy() for s in net.states]
        memoria = [[p] for p in pre]
        with tempfile.TemporaryDirectory() as td:
            rec = WorldlineRecorder(Path(td) / "run", net, dict(MAN), chunk_ticks=32)
            for _ in range(100):
                net.step()
                rec.record_step()
                for j, s in enumerate(net.states):
                    memoria[j].append(_flat(s).copy())
            rec.close()
            wl = load_worldline(Path(td) / "run")
            self.assertTrue(wl["complete"])
            self.assertEqual(len(wl["ticks"]), 101)
            for j in range(3):
                esperado = np.stack(memoria[j])
                self.assertEqual(float(np.max(np.abs(wl["estados"][j] - esperado))), 0.0)
                np.testing.assert_array_equal(wl["estados"][j][0], pre[j])

    def test_gate3_interrupcion_no_publica_complete(self):
        net, _, _ = _f6_net()
        with tempfile.TemporaryDirectory() as td:
            rec = WorldlineRecorder(Path(td) / "run", net, dict(MAN), chunk_ticks=8)
            for _ in range(20):
                net.step()
                rec.record_step()
            # SIN close(): interrupción
            self.assertFalse((Path(td) / "run" / "COMPLETE").exists())
            with self.assertRaises(RuntimeError):
                load_worldline(Path(td) / "run")
            restos = load_worldline(Path(td) / "run", allow_incomplete=True)
            self.assertFalse(restos["complete"])

    def test_gate3b_chunk_corrupto_se_detecta(self):
        net, _, _ = _f6_net()
        with tempfile.TemporaryDirectory() as td:
            rec = WorldlineRecorder(Path(td) / "run", net, dict(MAN), chunk_ticks=8)
            for _ in range(20):
                net.step()
                rec.record_step()
            rec.close()
            chunk = sorted((Path(td) / "run" / "worldline").glob("chunk_*.npz"))[1]
            datos = bytearray(chunk.read_bytes())
            datos[len(datos) // 2] ^= 0xFF
            chunk.write_bytes(bytes(datos))
            with self.assertRaises(RuntimeError):
                load_worldline(Path(td) / "run")

    def test_gate5_kicks_rederivables_del_rng_state(self):
        """Completitud causal: los kicks del film deben poder REDERIVARSE del rng_state del
        chunk + el contrato §6 (por nodo en orden, por modo en orden). Si esto falla, el film
        no es fuente primaria: es decorado."""
        net, specs, meta = _f6_net()
        T = float(meta["engine_params"]["temperature"])
        dt = float(meta["dt"])
        with tempfile.TemporaryDirectory() as td:
            rec = WorldlineRecorder(Path(td) / "run", net, dict(MAN), chunk_ticks=16)
            for _ in range(48):
                net.step()
                rec.record_step()
            rec.close()
            wl = load_worldline(Path(td) / "run")
        rng = np.random.default_rng()
        rng.bit_generator.state = json.loads(wl["rng_states_chunk"][0])
        # rederivar kicks del chunk 0 (filas 0..15 con chunk_ticks=16; fila 0 = PRE-step sin kick)
        for tick in range(1, 17):
            for j, sp in enumerate(specs):
                gamma = np.array([m.gamma for m in sp.modes])
                mass = np.array([max(m.mass, 1e-12) for m in sp.modes])
                sigma = np.sqrt(2.0 * gamma * T * dt / mass)
                kick = sigma * rng.standard_normal(sp.n_modes)
                grabado = wl["kicks"][j][tick]
                self.assertEqual(float(np.max(np.abs(kick - grabado))), 0.0,
                                 f"tick {tick} nodo {j}: el kick no se rederiva del contrato §6")

    def test_gate6_runner_aborta_en_blowup_sin_complete(self):
        net, specs, meta = _f6_net()
        net.states[0].x[:] = 1e200     # bomba: overflow en pocos pasos
        with tempfile.TemporaryDirectory() as td:
            rec = WorldlineRecorder(Path(td) / "run", net, dict(MAN), chunk_ticks=8)
            with self.assertRaises(FloatingPointError):
                run(net, 600, recorder=rec, finite_check_every=16)
            self.assertFalse((Path(td) / "run" / "COMPLETE").exists())


if __name__ == "__main__":
    unittest.main()
