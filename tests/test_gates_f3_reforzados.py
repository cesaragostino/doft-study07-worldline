"""GATES F3 ADICIONALES (double tap, JUEZ) — cierran los agujeros por los que 5 mutantes
del recorder pasaban 7/7 verde:

gate2b (replay-compare total): re-corre 130 ticks (>=3 fronteras de chunk, y mas alla de los
  100 de gate2 y de la ventana 1..16 del gate5) acumulando memoria de estados+drive+kicks y
  exige igualdad EXACTA fila a fila + dtype float64 + guard de no-vacuidad (drive != 0).
  Mata: drive=ceros, drive-float32, kicks corruptos tarde, estados corruptos tarde.

gate5b (rederivacion por chunk): itera TODOS los chunks rederivando los kicks de CADA tick
  desde el rng_state PROPIO del chunk (no solo el chunk 0, cuyo estado viene del __init__ y
  jamas ejercita el refresco de _flush_chunk). Mata: rng_state estancado/basura en chunks >=1.
"""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from study07.artifacts.recorder import WorldlineRecorder, load_worldline
from test_worldline_checkpoint import MAN, _f6_net, _flat


class TestGatesJuez(unittest.TestCase):

    def test_gate2b_replay_compare_total(self):
        net, specs, meta = _f6_net()
        memoria = [[_flat(s).copy()] for s in net.states]
        drive_mem = [np.zeros(len(specs))]
        kicks_mem = [[np.zeros(sp.n_modes)] for sp in specs]
        with tempfile.TemporaryDirectory() as td:
            rec = WorldlineRecorder(Path(td) / "run", net, dict(MAN), chunk_ticks=16)
            for _ in range(130):
                net.step()
                rec.record_step()
                for j, s in enumerate(net.states):
                    memoria[j].append(_flat(s).copy())
                    kicks_mem[j].append(net.last_noise_kicks[j].copy())
                drive_mem.append(net.last_drive0.copy())
            rec.close()
            wl = load_worldline(Path(td) / "run")
        # dtype float64 en TODOS los canales (schema: float64 primario)
        self.assertEqual(wl["drive"].dtype, np.float64, "drive no es float64")
        for j in range(len(specs)):
            self.assertEqual(wl["estados"][j].dtype, np.float64, f"estados nodo {j} no float64")
            self.assertEqual(wl["kicks"][j].dtype, np.float64, f"kicks nodo {j} no float64")
        # guard de no-vacuidad: el escenario debe tener drive real
        drive_esp = np.stack(drive_mem)
        self.assertGreater(float(np.max(np.abs(drive_esp[1:]))), 0.0,
                           "escenario vacuo: drive identicamente cero")
        # igualdad EXACTA fila a fila, 130 ticks, 3+ fronteras de chunk
        self.assertEqual(float(np.max(np.abs(wl["drive"] - drive_esp))), 0.0,
                         "canal drive difiere de la memoria del step")
        for j in range(len(specs)):
            self.assertEqual(float(np.max(np.abs(wl["estados"][j] - np.stack(memoria[j])))), 0.0,
                             f"estados nodo {j} difieren")
            self.assertEqual(float(np.max(np.abs(wl["kicks"][j] - np.stack(kicks_mem[j])))), 0.0,
                             f"kicks nodo {j} difieren")

    def test_gate5b_kicks_rederivables_en_TODOS_los_chunks(self):
        net, specs, meta = _f6_net()
        T = float(meta["engine_params"]["temperature"])
        dt = float(meta["dt"])
        with tempfile.TemporaryDirectory() as td:
            rec = WorldlineRecorder(Path(td) / "run", net, dict(MAN), chunk_ticks=16)
            for _ in range(48):
                net.step()
                rec.record_step()
            rec.close()
            chunk_paths = sorted((Path(td) / "run" / "worldline").glob("chunk_*.npz"))
            self.assertGreaterEqual(len(chunk_paths), 3, "escenario vacuo: <3 chunks")
            for ci, p in enumerate(chunk_paths):
                fx = np.load(p, allow_pickle=False)
                rng = np.random.default_rng()
                rng.bit_generator.state = json.loads(str(fx["rng_state_json"]))
                for row, tick in enumerate(np.asarray(fx["ticks"])):
                    if tick == 0:
                        continue        # fila PRE-step: sin kick
                    for j, sp in enumerate(specs):
                        gamma = np.array([m.gamma for m in sp.modes])
                        mass = np.array([max(m.mass, 1e-12) for m in sp.modes])
                        sigma = np.sqrt(2.0 * gamma * T * dt / mass)
                        kick = sigma * rng.standard_normal(sp.n_modes)
                        grabado = np.asarray(fx[f"kicks_nodo{j}"][row])
                        self.assertEqual(grabado.dtype, np.float64)
                        self.assertEqual(float(np.max(np.abs(kick - grabado))), 0.0,
                                         f"chunk {ci} tick {tick} nodo {j}: kick no rederiva "
                                         "del rng_state PROPIO del chunk")


if __name__ == "__main__":
    unittest.main()
