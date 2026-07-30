"""GATES F4 — el primer instrumento offline (plan §20.9 Fase 4).

A. La vista de FASE reproduce la referencia del oráculo (theta/Z/R/J/omega calculados ONLINE por
   el motor de Study06 con SUS funciones) leyendo SÓLO la worldline de study07. Dos niveles.
B. La vista de ENERGÍA reproduce las energías por capa del oráculo (step() return).
C. LA DEMO FUNDACIONAL: dos configuraciones de observación distintas sobre la MISMA película →
   dos vistas con el mismo worldline_hash y config_hash distinto, SIN re-simular.
D. Recomputar una vista reproduce su view_hash (caché = recompute, INSTRUMENT_CONTRACT).
E. Canal ausente ⇒ el instrumento FALLA (no sustituye).

La worldline de trabajo se genera UNA vez por clase con el motor de study07 (misma composición
f6, 1500 ticks) — después de eso, el motor no se toca más: todo es lectura.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from study07.artifacts.recorder import WorldlineRecorder
from study07.artifacts.runner import run as run_net
from study07.instruments import api, energy, phase
from test_worldline_checkpoint import MAN, _f6_net

REPO = Path(__file__).resolve().parents[1]
F7 = REPO / "tests/fixtures/study07_f7_observables_ref.npz"
TOL = 3.8579e-11


def _pinned(meta7):
    import platform
    return (np.__version__ == meta7.get("numpy") and platform.machine() == meta7.get("machine"))


class TestInstrumentos(unittest.TestCase):
    """La worldline se graba UNA vez (setUpClass); los gates son todos lecturas."""

    @classmethod
    def setUpClass(cls):
        cls.ref = np.load(F7, allow_pickle=False)
        cls.meta7 = json.loads(str(cls.ref["meta_json"]))
        cls.tmp = Path(tempfile.mkdtemp())
        net, specs, meta6 = _f6_net()
        cls.meta6 = meta6
        rec = WorldlineRecorder(cls.tmp / "run", net, dict(MAN), chunk_ticks=256)
        run_net(net, int(cls.meta7["ticks"]), recorder=rec)
        rec.close()
        cls.wl = api.load_run(cls.tmp / "run")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _assert_nivel(self, d, nombre):
        if _pinned(self.meta7):
            self.assertEqual(d, 0.0, f"{nombre}: en el entorno del generador debe ser 0.0 "
                                     f"exacto (midió {d:.3e})")
        else:
            self.assertLessEqual(d, TOL, nombre)

    def test_gateA_fase_reproduce_al_oraculo(self):
        v = phase.run(self.wl)
        for canal, ref in (("theta", self.ref["theta"]), ("r", self.ref["r"]),
                           ("j", self.ref["j"])):
            d = float(np.max(np.abs(v.arrays[canal] - ref)))
            print(f"[F4:fase] {canal}: max|d|={d:.3e}")
            self._assert_nivel(d, canal)
        # omega tiene NaN donde no es válido: comparar validez + valores válidos
        np.testing.assert_array_equal(v.arrays["omega_valid"], self.ref["omega_valid"])
        m = self.ref["omega_valid"]
        d = float(np.max(np.abs(v.arrays["omega"][m] - self.ref["omega"][m]))) if m.any() else 0.0
        print(f"[F4:fase] omega(valida): max|d|={d:.3e} ({int(m.sum())}/{len(m)})")
        self._assert_nivel(d, "omega")

    def test_gateB_energia_reproduce_al_oraculo(self):
        v = energy.run(self.wl, self.meta6["thetas_embebidos"])
        d = float(np.max(np.abs(v.arrays["e_capa"] - self.ref["e_capa"])))
        print(f"[F4:energia] e_capa: max|d|={d:.3e}")
        self._assert_nivel(d, "e_capa")

    def test_gateC_demo_fundacional_dos_ventanas_sin_resimular(self):
        """Lo que en Study06 costaba re-integrar 4.8h: acá son dos LECTURAS."""
        va = phase.run(self.wl)                                        # ventana completa
        vb = phase.run(self.wl, {"t0_tick": 500, "t1_tick": 1000})     # sub-ventana
        vc = phase.run(self.wl, {"stride": 5})                         # otra cadencia
        self.assertEqual(va.manifest["worldline_hash"], vb.manifest["worldline_hash"])
        self.assertEqual(va.manifest["worldline_hash"], vc.manifest["worldline_hash"])
        self.assertNotEqual(va.manifest["config_hash"], vb.manifest["config_hash"])
        self.assertNotEqual(va.manifest["config_hash"], vc.manifest["config_hash"])
        # la sub-ventana es un RECORTE de la completa (misma física, otra vista)
        np.testing.assert_array_equal(vb.arrays["theta"], va.arrays["theta"][500:1001])
        # y las tres se escriben bajo el MISMO árbol del film
        with tempfile.TemporaryDirectory() as td:
            pa = va.write(Path(td)); pb = vb.write(Path(td)); pc = vc.write(Path(td))
            self.assertEqual(pa.parent.parent, pb.parent.parent)
            self.assertEqual(len({pa, pb, pc}), 3)

    def test_gateD_recompute_reproduce_el_view_hash(self):
        h1 = phase.run(self.wl, {"stride": 3}).view_hash()
        h2 = phase.run(self.wl, {"stride": 3}).view_hash()
        self.assertEqual(h1, h2, "recomputar una vista debe reproducir su hash")

    def test_gateE_canal_ausente_falla(self):
        wl_mutilada = dict(self.wl)
        wl_mutilada["estados"] = []
        with self.assertRaises(RuntimeError):
            phase.run(wl_mutilada)

    def test_gateF_config_en_el_manifiesto_de_la_vista(self):
        """La vista declara TODO: config completa (con defaults resueltos), hash del film,
        instrumento+versión — nada implícito."""
        v = phase.run(self.wl, {"r_min": 0.10})
        self.assertEqual(v.manifest["observation_config"]["r_min"], 0.10)
        self.assertEqual(v.manifest["observation_config"]["eps_den"], 1e-12)
        self.assertEqual(v.manifest["instrument_id"], "phase_lock")
        self.assertIn("worldline_hash", v.manifest)


if __name__ == "__main__":
    unittest.main()
