"""GATES F5 — ingesta de cápsulas + composición concurrente (plan §20.9 Fase 5).

1. LECTOR ESTRICTO: la cápsula REAL carga verificada; toda adulteración (bytes, manifiesto,
   naturalidad, esquema, invariante de emisión) es fail-loud.
2. GENOMA: la transcripción del hash canónico ancla contra las cápsulas reales SIN oráculo;
   un genoma con overrides de laboratorio se RECHAZA (naturalidad heredada).
3. QUENCH: el re-base+truncado de study07 reproduce BIT-exacto el buffer post-restore del
   oráculo (f8); extrapolar está prohibido.
4. CONFORMIDAD DE COMPOSICIÓN: componer_red desde las cápsulas reales == oráculo
   restore_specimen_capsules(topology_quench) — estado inicial, buffer y TRAYECTORIA 1500
   ticks (dos niveles: 0.0 exacto pinned / TOL medido).
5. LA COMPOSICIÓN ES UNA CORRIDA NORMAL: film grabado + vistas de fase y energía leyéndolo;
   el fuego importado (E de cápsula) está EN el film. Mezcla cápsula+fresh: capacidad NUEVA
   declarada (sin referencia del oráculo — el restore de allá exige cápsula por CADA nodo).
6. INVENTARIO: data/inventario_v4.json íntegro (150 únicos), encadenado a los fixtures y al
   blocks_sha256 de f7/f8 — la cadena de procedencia cierra.
7. RECHAZOS del composer: genoma equivocado, T≠0 con cápsulas, dt distinto, emission_scale
   adulterado.
"""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from study07.artifacts.composer import componer_red
from study07.artifacts.recorder import WorldlineRecorder
from study07.artifacts.runner import run as run_net
from study07.compat import study06_capsule as cap6
from study07.instruments import api, energy, phase

REPO = Path(__file__).resolve().parents[1]
F8 = REPO / "tests/fixtures/study07_f8_transporte.npz"
CAPS_DIR = REPO / "tests/fixtures/f8_capsulas"
INVENTARIO = REPO / "data/inventario_v4.json"
F8_SHA_SELLADA = None   # se sella tras el primer gen (sidecar es el ancla primaria)
TOL = 3.8579e-11


def _pinned(meta):
    import platform
    return (np.__version__ == meta.get("numpy") and platform.machine() == meta.get("machine"))


def _flat(st):
    return np.concatenate([st.x, st.v, st.z, st.b, st.e])


class TestCapsulasF5(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sha_f8 = hashlib.sha256(F8.read_bytes()).hexdigest()
        sidecar = (REPO / "tests/fixtures/study07_f8.sha256").read_text().split()[0]
        if sha_f8 != sidecar:
            raise RuntimeError(f"f8 no coincide con su sidecar: {sha_f8[:12]} != {sidecar[:12]}")
        cls.fx = np.load(F8, allow_pickle=False)
        cls.meta = json.loads(str(cls.fx["meta_json"]))
        # las cápsulas del fixture son las EXACTAS que el oráculo restauró (selladas en meta)
        for rel, esperado in cls.meta["capsulas_sha256"].items():
            real = hashlib.sha256((CAPS_DIR / rel).read_bytes()).hexdigest()
            if real != esperado:
                raise RuntimeError(f"fixture {rel}: sha {real[:12]} != sellado {esperado[:12]}")
        cls.caps = [cap6.load_capsule(CAPS_DIR / bid) for bid in cls.meta["block_ids"]]
        cls.thetas = cls.meta["thetas_embebidos"]

    def _assert_nivel(self, d, nombre):
        if _pinned(self.meta):
            self.assertEqual(d, 0.0, f"{nombre}: debe ser 0.0 exacto en el entorno del "
                                     f"generador (midió {d:.3e})")
        else:
            print(f"[F5] ENTORNO NO PINEADO: gate de {nombre} degradado a TOL — DECLARADO")
            self.assertLessEqual(d, TOL, nombre)

    # ── 1 · lector estricto ──────────────────────────────────────────────────

    def test_gate1_lector_estricto_fail_loud(self):
        cap = self.caps[0]
        self.assertEqual(cap["manifest"]["block_id"], self.meta["block_ids"][0])
        self.assertEqual(int(cap["arrays"]["x"].size), 10)
        self.assertEqual(cap["arrays"]["history_column"].shape, (25001, 2))
        with tempfile.TemporaryDirectory() as td:
            # bytes del state.npz adulterados ⇒ hash de archivo caza
            d1 = Path(td) / "b1"; shutil.copytree(CAPS_DIR / self.meta["block_ids"][0], d1)
            datos = bytearray((d1 / "state.npz").read_bytes())
            datos[len(datos) // 2] ^= 0xFF
            (d1 / "state.npz").write_bytes(bytes(datos))
            with self.assertRaises(RuntimeError):
                cap6.load_capsule(d1)
            # manifiesto adulterado (dt) ⇒ specimen_id recomputado caza
            d2 = Path(td) / "b2"; shutil.copytree(CAPS_DIR / self.meta["block_ids"][0], d2)
            man = json.loads((d2 / "capsule.json").read_text())
            man["engine_contract"]["dt"] = 2.0 * man["engine_contract"]["dt"]
            (d2 / "capsule.json").write_text(json.dumps(man))
            with self.assertRaises(RuntimeError):
                cap6.load_capsule(d2)
            # naturalidad: natural_unintervened=False y temperature≠0 ⇒ rechazo
            for clave, valor in (("natural_unintervened", False), ("temperature", 0.5)):
                d3 = Path(td) / f"b3{clave}"
                shutil.copytree(CAPS_DIR / self.meta["block_ids"][0], d3)
                man = json.loads((d3 / "capsule.json").read_text())
                man["source"][clave] = valor
                (d3 / "capsule.json").write_text(json.dumps(man))
                with self.assertRaises(RuntimeError):
                    cap6.load_capsule(d3)
            # clave requerida de source ausente ⇒ el esquema sellado por hash caza
            d4 = Path(td) / "b4"; shutil.copytree(CAPS_DIR / self.meta["block_ids"][0], d4)
            man = json.loads((d4 / "capsule.json").read_text())
            del man["source"]["harvest_tick"]
            (d4 / "capsule.json").write_text(json.dumps(man))
            with self.assertRaises(RuntimeError):
                cap6.load_capsule(d4)

    def test_gate1b_invariante_de_emision(self):
        """Adulterar x REPARANDO todos los hashes: lo único que queda es la FÍSICA — la
        emisión del ring debe delatar el estado incoherente (oráculo :677-685)."""
        bid = self.meta["block_ids"][0]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "b"; shutil.copytree(CAPS_DIR / bid, d)
            with np.load(d / "state.npz", allow_pickle=False) as st:
                arrays = {k: st[k].copy() for k in st.files}
            arrays["x"] = arrays["x"] + 1.0            # rompe history[head] == s·[Σx,Σv]
            np.savez_compressed(d / "state.tmp.npz", **arrays)
            (d / "state.tmp.npz").rename(d / "state.npz")
            man = json.loads((d / "capsule.json").read_text())
            man["state_artifact"]["sha256"] = f"sha256:{cap6._hash_file(d / 'state.npz')}"
            man["state_artifact"]["content_sha256"] = cap6.state_content_sha256(arrays)
            man["specimen_id"] = cap6.specimen_id(man)
            (d / "capsule.json").write_text(json.dumps(man))
            with self.assertRaisesRegex(RuntimeError, "emisi"):
                cap6.load_capsule(d)

    # ── 2 · genoma ───────────────────────────────────────────────────────────

    def test_gate2_genoma_transcripto_y_naturalidad(self):
        for theta, cap in zip(self.thetas, self.caps):
            self.assertEqual(cap6.genome_sha256(theta), cap["manifest"]["genome_hash"],
                             "la transcripción del hash canónico no reproduce el genoma "
                             "sellado por el oráculo")
        # override de laboratorio ESCONDIDO en el genoma ⇒ rechazo (naturalidad)
        sucio = copy.deepcopy(self.thetas[0])
        sucio["memory"]["layers"]["Q"]["_mem_force_scale"] = 2.0
        with self.assertRaisesRegex(RuntimeError, "laboratorio"):
            cap6.genome_sha256(sucio)
        legacy = copy.deepcopy(self.thetas[0])
        legacy["schema_version"] = "theta_internal_v1"
        with self.assertRaises(RuntimeError):
            cap6.genome_sha256(legacy)

    # ── 3 · quench ───────────────────────────────────────────────────────────

    def test_gate3_quench_reproduce_al_oraculo(self):
        buffer_oraculo = self.fx["buffer_post_restore"]
        self.assertEqual(int(self.meta["head_post_restore"]), 0)
        for j, cap in enumerate(self.caps):
            col = cap6.quench_column(cap["arrays"], buffer_oraculo.shape[0] - 1)
            d = float(np.max(np.abs(col - buffer_oraculo[:, j, :])))
            print(f"[F5:quench] nodo {j}: max|d|={d:.3e}")
            self.assertEqual(d, 0.0, f"nodo {j}: el quench de study07 difiere del oráculo")
        with self.assertRaisesRegex(RuntimeError, "prohibido"):
            cap6.quench_column(self.caps[0]["arrays"], 25001)   # extrapolar

    # ── 4 · conformidad de composición ───────────────────────────────────────

    def test_gate4_composicion_conforme_al_oraculo(self):
        """componer_red == restore del oráculo: estado, buffer y 1500 ticks BIT-exactos."""
        m = self.meta; ep = m["engine_params"]
        net, specs, recibo = componer_red(
            [{"theta": t, "capsula": c} for t, c in zip(self.thetas, self.caps)],
            m["edges"], dt=float(m["dt"]), seed=int(m["seed"]),
            k_global=float(ep["kappa_global"]), coupling_gamma_c=float(ep["coupling_gamma_c"]),
            tau_field=float(ep.get("tau_field", 0.0)), temperature=0.0)
        for j in range(m["n_nodes"]):
            d0 = float(np.max(np.abs(_flat(net.states[j]) - self.fx[f"estados_nodo{j}"][0])))
            self.assertEqual(d0, 0.0, f"nodo {j}: estado post-composición != post-restore")
        self.assertEqual(float(np.max(np.abs(np.asarray(net.history.buffer)
                                             - self.fx["buffer_post_restore"]))), 0.0)
        self.assertEqual(net.history.head_idx, 0)
        self.assertEqual([o["origen"] for o in recibo["por_nodo"]], ["capsula", "capsula"])
        self.assertEqual([o["history_operation"] for o in recibo["por_nodo"]],
                         ["truncate_recent_full_rate_exact"] * 2)
        ticks = int(m["ticks"])
        for tick in range(1, ticks + 1):
            net.step()
            if tick in (1, 2, 10, 100, 500, 1000, ticks):
                for j in range(m["n_nodes"]):
                    d = float(np.max(np.abs(_flat(net.states[j])
                                            - self.fx[f"estados_nodo{j}"][tick])))
                    if tick == ticks:
                        print(f"[F5:conformidad] tick {tick} nodo {j}: max|d|={d:.3e}")
                    self._assert_nivel(d, f"tick {tick} nodo {j}")

    # ── 5 · la composición es una corrida normal (film + vistas) ─────────────

    def test_gate5_film_vistas_y_mezcla_declarada(self):
        m = self.meta; ep = m["engine_params"]
        base = {c["manifest"]["block_id"]: c["capsule_sha256"] for c in self.caps}
        base["blocks_canonical"] = m["blocks_sha256"]
        # (a) todo-cápsulas: film + vistas — el pipeline entero sobre el transporte
        net, _, recibo = componer_red(
            [{"theta": t, "capsula": c} for t, c in zip(self.thetas, self.caps)],
            m["edges"], dt=float(m["dt"]), seed=int(m["seed"]),
            k_global=float(ep["kappa_global"]), coupling_gamma_c=float(ep["coupling_gamma_c"]))
        with tempfile.TemporaryDirectory() as td:
            man = {"run_id": "f5_transporte", "spec_tipo": "M1",
                   "hashes_base_externa": dict(base), "composicion": recibo}
            rec = WorldlineRecorder(Path(td) / "run", net, man, chunk_ticks=128)
            run_net(net, 300, recorder=rec)
            rec.close()
            wl = api.load_run(Path(td) / "run")
            v_fase = phase.run(wl)
            v_e = energy.run(wl, self.thetas)
            self.assertTrue(wl["complete"])
            self.assertEqual(v_fase.arrays["theta"].shape, (301, 2))
            # el fuego importado está EN el film: E del ignitor ≫ E del callado en fila 0
            e0 = v_e.arrays["e_capa"][0]
            self.assertGreater(float(e0[0].sum()), 1e3 * max(float(e0[1].sum()), 1e-12),
                               "la biografía energética no viajó con la cápsula")
            self.assertEqual(wl["manifest"]["composicion"]["por_nodo"][0]["origen"], "capsula")
        # (b) MEZCLA cápsula+fresh: capacidad NUEVA de study07, sin referencia del oráculo
        # (el restore de allá exige cápsula por CADA nodo [oráculo :839-842]) — DECLARADA
        net2, _, recibo2 = componer_red(
            [{"theta": self.thetas[0], "capsula": self.caps[0]},
             {"theta": self.thetas[1], "capsula": None}],
            m["edges"], dt=float(m["dt"]), seed=int(m["seed"]),
            k_global=float(ep["kappa_global"]), coupling_gamma_c=float(ep["coupling_gamma_c"]))
        self.assertEqual([o["origen"] for o in recibo2["por_nodo"]],
                         ["capsula", "nacimiento"])
        e_capsula = float(np.sum(net2.states[0].e))
        e_fresh = float(np.sum(net2.states[1].e))
        self.assertGreater(e_capsula, 1e3 * max(e_fresh, 1e-12),
                           "cápsula trae biografía; el fresh nace térmico ~1e-3")
        for _ in range(50):
            net2.step()
        self.assertTrue(all(np.all(np.isfinite(_flat(s))) for s in net2.states))

    # ── 6 · inventario ───────────────────────────────────────────────────────

    def test_gate6_inventario_integro_y_encadenado(self):
        inv = json.loads(INVENTARIO.read_text())
        sidecar = (REPO / "data/inventario_v4.sha256").read_text().split()[0]
        self.assertEqual(hashlib.sha256(INVENTARIO.read_text().encode()).hexdigest(), sidecar)
        pob = inv["poblacion"]
        self.assertEqual(len(pob), 150)
        self.assertEqual(len({p["block_id"] for p in pob}), 150)
        self.assertEqual(inv["verificacion"]["n"], 150)
        por_bid = {p["block_id"]: p for p in pob}
        for cap in self.caps:
            man = cap["manifest"]
            fila = por_bid[man["block_id"]]
            self.assertEqual(fila["capsule_sha256"], cap["capsule_sha256"],
                             "el inventario no encadena con la cápsula del fixture")
            self.assertEqual(fila["genome_hash"], man["genome_hash"])
            self.assertEqual(fila["specimen_id"], man["specimen_id"])
        # la CADENA cierra: inventario ↔ f8 ↔ f7 comparten el sha de los bloques canónicos
        self.assertEqual(inv["base"]["blocks_sha256"], self.meta["blocks_sha256"])
        f7 = np.load(REPO / "tests/fixtures/study07_f7_observables_ref.npz",
                     allow_pickle=False)
        meta7 = json.loads(str(f7["meta_json"]))
        self.assertEqual(inv["base"]["blocks_sha256"], meta7["blocks_sha256"])

    # ── 7 · rechazos del composer ────────────────────────────────────────────

    def test_gate7_composer_rechaza_fail_loud(self):
        m = self.meta; ep = m["engine_params"]
        comunes = dict(dt=float(m["dt"]), seed=1, k_global=float(ep["kappa_global"]),
                       coupling_gamma_c=float(ep["coupling_gamma_c"]))
        # genoma equivocado: la cápsula del ignitor con el theta del callado
        with self.assertRaisesRegex(RuntimeError, "genoma"):
            componer_red([{"theta": self.thetas[1], "capsula": self.caps[0]},
                          {"theta": self.thetas[0], "capsula": None}], m["edges"], **comunes)
        # T≠0 con cápsulas: el RNG no viaja
        with self.assertRaisesRegex(RuntimeError, "temperature=0"):
            componer_red([{"theta": self.thetas[0], "capsula": self.caps[0]},
                          {"theta": self.thetas[1], "capsula": None}], m["edges"],
                         temperature=0.05, **comunes)
        # dt distinto
        malos = dict(comunes); malos["dt"] = 2.0 * float(m["dt"])
        with self.assertRaisesRegex(RuntimeError, "dt"):
            componer_red([{"theta": self.thetas[0], "capsula": self.caps[0]},
                          {"theta": self.thetas[1], "capsula": None}], m["edges"], **malos)
        # emission_scale adulterado en el contrato de la cápsula
        cap_mal = {"manifest": copy.deepcopy(self.caps[0]["manifest"]),
                   "arrays": self.caps[0]["arrays"],
                   "capsule_sha256": self.caps[0]["capsule_sha256"]}
        cap_mal["manifest"]["engine_contract"]["emission_scale"] = 0.5
        with self.assertRaisesRegex(RuntimeError, "emission_scale"):
            componer_red([{"theta": self.thetas[0], "capsula": cap_mal},
                          {"theta": self.thetas[1], "capsula": None}], m["edges"], **comunes)


if __name__ == "__main__":
    unittest.main()
