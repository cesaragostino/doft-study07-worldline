"""GATES F5 — ingesta de cápsulas + composición concurrente (plan §20.9 Fase 5),
ENDURECIDOS por el double tap wf_5465f7cf (A1-A10: los gates ahora custodian lo que declaran).

1.  LECTOR ESTRICTO por RAMA: cada validación tiene su tamper RE-SELLADO (recomputando
    specimen_id y hashes para que la rama auditada sea la ÚNICA que puede cazar) + regex del
    mensaje de SU rama (A2 — antes 8 ramas eran borrables con suite verde).
1b. INVARIANTE DE EMISIÓN con TODOS los hashes reparados: sólo la física delata.
2.  GENOMA: transcripción anclada a los sellos del oráculo + naturalidad + completitud v2
    (paridad con validate_theta_internal — A4) + capas no transportables.
3.  QUENCH: bit-exacto vs oráculo + extrapolación prohibida + re-base con head≠0 SINTÉTICO
    (las 150 cápsulas reales tienen head=0: sin esto el re-base jamás se ejercita — A10).
4.  CONFORMIDAD: estado + buffer + trayectoria comparada EN CADA TICK 1..1500 (A1 — el
    muestreo de 7 ticks dejaba pasar fallas intermitentes con divergencia 4e+02).
5.  Film + vistas + PROCEDENCIA EXIGIDA (A5): el film compuesto sin recibo o sin las
    cápsulas citadas NO se graba. Mezcla cápsula+fresh con ancla BIT-exacta del lado fresh
    (estado == birth_state, ring == relleno uniforme — A3).
6.  INVENTARIO sellado por constante + estructura de las 150 filas validada (A6). La
    verificación de CONTENIDO 150/150 (genoma triple, carga completa) es de
    tiempo-de-herramienta (tools/inventario_v4.py) — acá se valida estructura + sellos +
    encadenamiento a fixtures y f7/f8: DECLARADO.
7.  Rechazos del composer (genoma cruzado, T≠0, dt, emission_scale).
8.  DEFENSAS del composer con test negativo (A10): formas, capas e_ref, post-copia
    inyectada, aplicación de e_ref, naturalidad-fresh, borde canonical_ring_exact.
"""
import copy
import hashlib
import json
import re
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import numpy as np

from study07.artifacts.composer import componer_red
from study07.artifacts.recorder import WorldlineRecorder
from study07.artifacts.runner import run as run_net
from study07.compat import study06_capsule as cap6
from study07.compat.study06_v4 import birth_state, parse_theta_v2
from study07.instruments import api, energy, phase
from study07.physics import rhs

REPO = Path(__file__).resolve().parents[1]
F8 = REPO / "tests/fixtures/study07_f8_transporte.npz"
CAPS_DIR = REPO / "tests/fixtures/f8_capsulas"
INVENTARIO = REPO / "data/inventario_v4.json"
# anclas SELLADAS (patrón f1-f7): regenerar exige re-sellar acá, a la vista (F5 A6)
F8_SHA_SELLADA = "d501cca05179f16fd1b32e0bb7dc3c39a7b03d9b398edd99eb9303e6a250fd93"
INVENTARIO_SHA_SELLADO = "1fb29af2e58475c2175dd5d8bb7ad4090fb386cbf21bec01f653dc04b4e28a67"
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
        if not (sha_f8 == sidecar == F8_SHA_SELLADA):
            raise RuntimeError(f"f8 no coincide con su sello triple: disco={sha_f8[:12]} "
                               f"sidecar={sidecar[:12]} sellado={F8_SHA_SELLADA[:12]}")
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

    def _forjada(self, td, nombre, mutar_manifest):
        """Tamper RE-SELLADO (patrón gate1b): muta el manifiesto y recomputa specimen_id,
        de modo que la rama auditada sea la ÚNICA que puede cazar (F5 A2 — sin esto el
        check de specimen_id enmascaraba TODAS las ramas)."""
        d = Path(td) / nombre
        shutil.copytree(CAPS_DIR / self.meta["block_ids"][0], d)
        man = json.loads((d / "capsule.json").read_text())
        mutar_manifest(man)
        man["specimen_id"] = cap6.specimen_id(man)
        (d / "capsule.json").write_text(json.dumps(man))
        return d

    # ── 1 · lector estricto, rama por rama ───────────────────────────────────

    def test_gate1_lector_carga_y_es_read_only(self):
        cap = self.caps[0]
        self.assertEqual(cap["manifest"]["block_id"], self.meta["block_ids"][0])
        self.assertEqual(int(cap["arrays"]["x"].size), 10)
        self.assertEqual(cap["arrays"]["history_column"].shape, (25001, 2))
        for k, a in cap["arrays"].items():
            self.assertFalse(a.flags.writeable, f"{k}: los arrays del lector deben ser "
                                                "read-only (contrato del lector)")

    def test_gate1_ramas_del_manifiesto_cada_una_con_su_regex(self):
        casos = [
            ("naturalidad_flag", lambda m: m["source"].update(natural_unintervened=False),
             "natural"),
            ("naturalidad_temp", lambda m: m["source"].update(temperature=0.5), "natural"),
            ("esquema_source", lambda m: m["source"].pop("harvest_tick"), "esquema v1"),
            ("head_miente", lambda m: m["source"].update(history_head=7),
             "history_head difiere"),
            # regex al MENSAJE EXACTO de la rama: con el check borrado, la rama vecina
            # (index fuera de range(0)) también nombra source_node_count y enmascaraba
            ("node_count", lambda m: m["source"].update(source_node_count=0),
             "source_node_count debe ser positivo"),
            ("node_index", lambda m: m["source"].update(source_node_index=99),
             "source_node_index inconsistente"),
            ("dt_invalido", lambda m: m["engine_contract"].update(dt=-1.0),
             "dt o delay_steps"),
            ("fields_contrato", lambda m: m["state_artifact"]["fields"].append("zz"),
             "contrato v1"),
        ]
        with tempfile.TemporaryDirectory() as td:
            for nombre, mutador, regex in casos:
                d = self._forjada(td, nombre, mutador)
                with self.assertRaisesRegex(RuntimeError, regex,
                                            msg=f"rama {nombre}: no cazó con su mensaje"):
                    cap6.load_capsule(d)
            # el guardián specimen_id sigue vivo: tamper SIN re-sellar
            d = Path(td) / "sin_resellar"
            shutil.copytree(CAPS_DIR / self.meta["block_ids"][0], d)
            man = json.loads((d / "capsule.json").read_text())
            man["engine_contract"]["dt"] = 2.0 * man["engine_contract"]["dt"]
            (d / "capsule.json").write_text(json.dumps(man))
            with self.assertRaisesRegex(RuntimeError, "specimen_id"):
                cap6.load_capsule(d)

    def test_gate1_hash_de_archivo_y_de_contenido_separables(self):
        bid = self.meta["block_ids"][0]
        with tempfile.TemporaryDirectory() as td:
            # (a) byte-flip crudo ⇒ hash de ARCHIVO
            d1 = Path(td) / "bytes"; shutil.copytree(CAPS_DIR / bid, d1)
            datos = bytearray((d1 / "state.npz").read_bytes())
            datos[len(datos) // 2] ^= 0xFF
            (d1 / "state.npz").write_bytes(bytes(datos))
            with self.assertRaisesRegex(RuntimeError, "hash del state artifact"):
                cap6.load_capsule(d1)
            # (b) re-serialización con los MISMOS arrays ⇒ SOLO el hash de archivo difiere
            # (contenido idéntico): la rama file-sha es la única que puede cazar (A2/c2-M1).
            # El original del oráculo va SIN comprimir (y numpy escribe npz determinista):
            # comprimirlo garantiza otros bytes con idéntico contenido.
            d2 = Path(td) / "reser"; shutil.copytree(CAPS_DIR / bid, d2)
            with np.load(d2 / "state.npz", allow_pickle=False) as st:
                arrays = {k: st[k].copy() for k in st.files}
            np.savez_compressed(d2 / "state.tmp.npz", **arrays)
            (d2 / "state.tmp.npz").rename(d2 / "state.npz")
            self.assertNotEqual(cap6._hash_file(d2 / "state.npz"),
                                cap6._hash_file(CAPS_DIR / bid / "state.npz"),
                                "escenario vacuo: los bytes no difieren")
            self.assertEqual(cap6.state_content_sha256(arrays),
                             json.loads((d2 / "capsule.json").read_text())
                             ["state_artifact"]["content_sha256"], "escenario vacuo")
            with self.assertRaisesRegex(RuntimeError, "hash del state artifact"):
                cap6.load_capsule(d2)
            # (c) contenido adulterado con el hash de ARCHIVO reparado ⇒ SOLO la rama de
            # CONTENIDO puede cazar (A2/c2-M2)
            d3 = Path(td) / "contenido"; shutil.copytree(CAPS_DIR / bid, d3)
            with np.load(d3 / "state.npz", allow_pickle=False) as st:
                arrays = {k: st[k].copy() for k in st.files}
            arrays["z"] = arrays["z"] + 1.0
            np.savez_compressed(d3 / "state.tmp.npz", **arrays)
            (d3 / "state.tmp.npz").rename(d3 / "state.npz")
            man = json.loads((d3 / "capsule.json").read_text())
            man["state_artifact"]["sha256"] = f"sha256:{cap6._hash_file(d3 / 'state.npz')}"
            (d3 / "capsule.json").write_text(json.dumps(man))
            with self.assertRaisesRegex(RuntimeError, "CONTENIDO"):
                cap6.load_capsule(d3)

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

    def test_gate2_genoma_transcripto_naturalidad_y_completitud(self):
        for theta, cap in zip(self.thetas, self.caps):
            self.assertEqual(cap6.genome_sha256(theta), cap["manifest"]["genome_hash"],
                             "la transcripción del hash canónico no reproduce el genoma "
                             "sellado por el oráculo")
        sucio = copy.deepcopy(self.thetas[0])
        sucio["memory"]["layers"]["Q"]["_mem_force_scale"] = 2.0
        with self.assertRaisesRegex(RuntimeError, "laboratorio"):
            cap6.genome_sha256(sucio)
        legacy = copy.deepcopy(self.thetas[0])
        legacy["schema_version"] = "theta_internal_v1"
        with self.assertRaises(RuntimeError):
            cap6.genome_sha256(legacy)
        # capa no transportable (A10/c2-M24)
        s3 = copy.deepcopy(self.thetas[0])
        s3["modes"][0]["layer"] = "S3"
        with self.assertRaisesRegex(RuntimeError, "no transportables"):
            cap6.genome_sha256(s3)
        # COMPLETITUD v2 (A4): capa en modes fuera de memory.layer_order — el oráculo lo
        # RECHAZA; study07 lo aceptaba y componía física silenciosamente distinta
        incompleto = copy.deepcopy(self.thetas[0])
        incompleto["memory"]["layer_order"] = ["Q", "S1"]
        del incompleto["memory"]["layers"]["S2"]
        with self.assertRaisesRegex(RuntimeError, "incompleto"):
            cap6.genome_sha256(incompleto)
        with self.assertRaisesRegex(RuntimeError, "FUERA de"):
            parse_theta_v2(incompleto, emission_scale=0.1)

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

    def test_gate3b_rebase_con_head_sintetico(self):
        """Las 150 cápsulas reales traen head=0 ⇒ el RE-BASE del ring jamás se ejercita con
        datos reales (A10/c2-M6). Ring sintético con head≠0: re-base cronológico a mano."""
        rng = np.random.default_rng(7)
        ring = rng.standard_normal((11, 2))
        for head in (1, 3, 10):
            arrays = {"history_column": ring, "history_head": np.int64(head)}
            col = cap6.quench_column(arrays, 5)
            self.assertEqual(col.shape, (6, 2))
            np.testing.assert_array_equal(col[0], ring[head],
                                          err_msg=f"head={head}: col[0] != emisión actual")
            for pasos_atras in range(6):
                np.testing.assert_array_equal(
                    col[(-pasos_atras) % 6], ring[(head - pasos_atras) % 11],
                    err_msg=f"head={head}, hace {pasos_atras}: re-base equivocado")

    # ── 4 · conformidad de composición ───────────────────────────────────────

    def test_gate4_composicion_conforme_al_oraculo(self):
        """componer_red == restore del oráculo: estado, buffer y CADA UNO de los 1500 ticks
        (A1: el muestreo de 7 ticks dejaba pasar una falla intermitente con d=4e+02)."""
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
        self.assertTrue(recibo["topology_quench"])
        self.assertEqual(recibo["stationary_claim_exclusion_ticks"],
                         recibo["target_delay_steps"])
        ticks = int(m["ticks"])
        esperados = [self.fx[f"estados_nodo{j}"] for j in range(m["n_nodes"])]
        peor = 0.0
        for tick in range(1, ticks + 1):
            net.step()
            for j in range(m["n_nodes"]):
                d = float(np.max(np.abs(_flat(net.states[j]) - esperados[j][tick])))
                peor = max(peor, d)
                self._assert_nivel(d, f"tick {tick} nodo {j}")
        print(f"[F5:conformidad] {ticks} ticks x {m['n_nodes']} nodos, TODOS comparados: "
              f"max|d| global={peor:.3e}")

    # ── 5 · film + vistas + procedencia exigida + mezcla anclada ─────────────

    def test_gate5_film_vistas_y_procedencia_exigida(self):
        m = self.meta; ep = m["engine_params"]
        base = {c["manifest"]["block_id"]: c["capsule_sha256"] for c in self.caps}
        base["blocks_canonical"] = m["blocks_sha256"]
        net, _, recibo = componer_red(
            [{"theta": t, "capsula": c} for t, c in zip(self.thetas, self.caps)],
            m["edges"], dt=float(m["dt"]), seed=int(m["seed"]),
            k_global=float(ep["kappa_global"]), coupling_gamma_c=float(ep["coupling_gamma_c"]))
        with tempfile.TemporaryDirectory() as td:
            # PROCEDENCIA EXIGIDA (A5): sin recibo ⇒ el recorder RECHAZA
            with self.assertRaisesRegex(ValueError, "COMPOSICI"):
                WorldlineRecorder(Path(td) / "sin_recibo", net,
                                  {"run_id": "x", "spec_tipo": "M1",
                                   "hashes_base_externa": dict(base)}, chunk_ticks=64)
            # con recibo pero sin las cápsulas citadas ⇒ RECHAZA
            with self.assertRaisesRegex(ValueError, "huérfano"):
                WorldlineRecorder(Path(td) / "sin_base", net,
                                  {"run_id": "x", "spec_tipo": "M1",
                                   "hashes_base_externa": {}, "composicion": recibo},
                                  chunk_ticks=64)
            # completo: film + vistas — el pipeline entero sobre el transporte
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
            e0 = v_e.arrays["e_capa"][0]
            self.assertGreater(float(e0[0].sum()), 1e3 * max(float(e0[1].sum()), 1e-12),
                               "la biografía energética no viajó con la cápsula")
            self.assertEqual(wl["manifest"]["composicion"]["por_nodo"][0]["origen"], "capsula")
            self.assertIn("set_digest", wl["manifest"]["composicion"])

    def test_gate5b_mezcla_con_el_lado_fresh_ANCLADO(self):
        """La capacidad NUEVA de F5 (sin referencia del oráculo: el restore de allá exige
        cápsula por CADA nodo :839-842) — su lado fresh queda BIT-anclado (A3): estado ==
        birth_state del contrato §6/§7 y ring == relleno uniforme de la emisión inicial."""
        m = self.meta; ep = m["engine_params"]
        net2, specs2, recibo2 = componer_red(
            [{"theta": self.thetas[0], "capsula": self.caps[0]},
             {"theta": self.thetas[1], "capsula": None}],
            m["edges"], dt=float(m["dt"]), seed=int(m["seed"]),
            k_global=float(ep["kappa_global"]), coupling_gamma_c=float(ep["coupling_gamma_c"]))
        self.assertEqual([o["origen"] for o in recibo2["por_nodo"]],
                         ["capsula", "nacimiento"])
        # ancla bit-exacta del ESTADO fresh (mata la semilla de nodo equivocada — c2-M18)
        sp_f, _ = parse_theta_v2(self.thetas[1],
                                 emission_scale=1.0 / len(self.thetas[1]["modes"]))
        st_f = birth_state(sp_f, seed=int(m["seed"]), idx=1)
        self.assertEqual(float(np.max(np.abs(_flat(net2.states[1]) - _flat(st_f)))), 0.0,
                         "el estado fresh no es el birth_state del contrato §6/§7")
        # ancla bit-exacta del RING fresh (mata el ring vaciado — c4-M1/JM5)
        uniforme = np.tile(rhs.emitted_xv(sp_f, st_f),
                           (int(recibo2["target_delay_steps"]) + 1, 1))
        np.testing.assert_array_equal(np.asarray(net2.history.buffer)[:, 1, :], uniforme,
                                      err_msg="el ring del fresh no es el relleno uniforme")
        # el genoma fresh es CITABLE (A4): huella en el recibo
        self.assertEqual(recibo2["por_nodo"][1]["genome_hash"],
                         cap6.genome_sha256(self.thetas[1]))
        e_capsula = float(np.sum(net2.states[0].e))
        e_fresh = float(np.sum(net2.states[1].e))
        self.assertGreater(e_capsula, 1e3 * max(e_fresh, 1e-12),
                           "cápsula trae biografía; el fresh nace térmico ~1e-3")
        for _ in range(50):
            net2.step()
        self.assertTrue(all(np.all(np.isfinite(_flat(s))) for s in net2.states))

    # ── 6 · inventario sellado y validado ────────────────────────────────────

    def test_gate6_inventario_sellado_estructura_y_cadena(self):
        texto = INVENTARIO.read_text()
        sha = hashlib.sha256(texto.encode()).hexdigest()
        sidecar = (REPO / "data/inventario_v4.sha256").read_text().split()[0]
        self.assertEqual(sha, sidecar, "inventario != sidecar")
        self.assertEqual(sha, INVENTARIO_SHA_SELLADO,
                         "inventario != constante SELLADA (regenerar exige re-sellar acá)")
        inv = json.loads(texto)
        pob = inv["poblacion"]
        self.assertEqual(len(pob), 150)
        self.assertEqual(len({p["block_id"] for p in pob}), 150)
        # ESTRUCTURA de las 150 filas (A6 — antes 148 filas basura pasaban):
        rx_sha = re.compile(r"^sha256:[0-9a-f]{64}$")
        rx_hex40 = re.compile(r"^[0-9a-f]{40}$")
        claves = {"run_idx", "block_id", "dir", "specimen_id", "genome_hash",
                  "capsule_sha256", "state_npz_sha256", "state_content_sha256",
                  "passport_sha256", "n_modes", "n_z", "n_layers", "dt", "delay_steps",
                  "emission_scale", "harvest_tick"}
        for p in pob:
            self.assertEqual(set(p), claves, f"fila {p.get('run_idx')}: claves")
            self.assertTrue(rx_hex40.match(p["block_id"]))
            self.assertTrue(p["specimen_id"].startswith("onion-"))
            for h in ("genome_hash", "capsule_sha256", "state_npz_sha256",
                      "state_content_sha256", "passport_sha256"):
                self.assertTrue(rx_sha.match(p[h]), f"{p['run_idx']}: {h} malformado")
            self.assertEqual(p["dt"], float(self.meta["dt"]))
            self.assertEqual(p["delay_steps"], 25000)
            self.assertEqual(p["emission_scale"], 0.1)
            self.assertGreater(p["harvest_tick"], 0)
        for h in ("specimen_id", "capsule_sha256", "state_npz_sha256", "genome_hash"):
            self.assertEqual(len({p[h] for p in pob}), 150, f"{h} duplicados")
        # procedencia MEDIDA, no asumida (A8)
        self.assertIn("oracle_tags_en_head", inv["base"])
        self.assertNotIn("oracle_tag", inv["base"])
        self.assertIn("study07_commit", inv["base"])
        # encadenamiento a los fixtures y a f7/f8
        por_bid = {p["block_id"]: p for p in pob}
        for cap in self.caps:
            man = cap["manifest"]
            fila = por_bid[man["block_id"]]
            self.assertEqual(fila["capsule_sha256"], cap["capsule_sha256"])
            self.assertEqual(fila["genome_hash"], man["genome_hash"])
            self.assertEqual(fila["specimen_id"], man["specimen_id"])
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
        with self.assertRaisesRegex(RuntimeError, "genoma"):
            componer_red([{"theta": self.thetas[1], "capsula": self.caps[0]},
                          {"theta": self.thetas[0], "capsula": None}], m["edges"], **comunes)
        with self.assertRaisesRegex(RuntimeError, "temperature=0"):
            componer_red([{"theta": self.thetas[0], "capsula": self.caps[0]},
                          {"theta": self.thetas[1], "capsula": None}], m["edges"],
                         temperature=0.05, **comunes)
        malos = dict(comunes); malos["dt"] = 2.0 * float(m["dt"])
        with self.assertRaisesRegex(RuntimeError, "dt"):
            componer_red([{"theta": self.thetas[0], "capsula": self.caps[0]},
                          {"theta": self.thetas[1], "capsula": None}], m["edges"], **malos)
        cap_mal = {"manifest": copy.deepcopy(self.caps[0]["manifest"]),
                   "arrays": self.caps[0]["arrays"],
                   "capsule_sha256": self.caps[0]["capsule_sha256"]}
        cap_mal["manifest"]["engine_contract"]["emission_scale"] = 0.5
        with self.assertRaisesRegex(RuntimeError, "emission_scale"):
            componer_red([{"theta": self.thetas[0], "capsula": cap_mal},
                          {"theta": self.thetas[1], "capsula": None}], m["edges"], **comunes)

    # ── 8 · defensas del composer con test negativo (A10) ────────────────────

    def _cap_con_arrays(self, base_cap, **overrides):
        arrays = {k: v for k, v in base_cap["arrays"].items()}
        arrays.update(overrides)
        return {"manifest": copy.deepcopy(base_cap["manifest"]), "arrays": arrays,
                "capsule_sha256": base_cap["capsule_sha256"]}

    def test_gate8_defensas_del_composer(self):
        m = self.meta; ep = m["engine_params"]
        comunes = dict(dt=float(m["dt"]), seed=int(m["seed"]),
                       k_global=float(ep["kappa_global"]),
                       coupling_gamma_c=float(ep["coupling_gamma_c"]))
        mixto = lambda cap: [{"theta": self.thetas[0], "capsula": cap},
                             {"theta": self.thetas[1], "capsula": None}]
        # (a) forma adulterada de un array de estado (c1-M10)
        cap_forma = self._cap_con_arrays(self.caps[0],
                                         x=np.append(self.caps[0]["arrays"]["x"], 0.0))
        with self.assertRaisesRegex(RuntimeError, "de la cápsula"):
            componer_red(mixto(cap_forma), m["edges"], **comunes)
        # (b) capa de e_ref renombrada (c1-M11)
        keys_mal = self.caps[0]["arrays"]["e_ref_keys"].copy()
        keys_mal[0] = "QX"
        cap_capas = self._cap_con_arrays(self.caps[0], e_ref_keys=keys_mal)
        with self.assertRaisesRegex(RuntimeError, "capas de e_ref"):
            componer_red(mixto(cap_capas), m["edges"], **comunes)
        # (c) la verificación POST-COPIA caza corrupción inyectada (c2-M16): un buffer que
        # degrada a float32 rompe el bit-exacto y el composer debe morir, no callar
        from study07.engine import network as red_mod
        class BufferF32(red_mod.HistoryBuffer):
            def __init__(self, delay_steps, initial):
                super().__init__(delay_steps, initial)
                self.buffer = self.buffer.astype(np.float32)
        with mock.patch.object(red_mod, "HistoryBuffer", BufferF32):
            with self.assertRaisesRegex(RuntimeError, "post-composici"):
                componer_red(mixto(self.caps[0]), m["edges"], **comunes)
        # (d) el e_ref de la cápsula SE APLICA al spec (c2-M12): e_ref×2 en memoria ⇒ el
        # spec compuesto lo lleva (el composer no re-hashea e_ref: entra tal cual)
        vals2 = self.caps[0]["arrays"]["e_ref_values"] * 2.0
        cap_eref = self._cap_con_arrays(self.caps[0], e_ref_values=vals2)
        net_e, specs_e, _ = componer_red(mixto(cap_eref), m["edges"], **comunes)
        capas = [str(v) for v in self.caps[0]["arrays"]["e_ref_keys"]]
        for i, nombre in enumerate(capas):
            from study07.physics.state import Layer
            self.assertEqual(specs_e[0].struct.e_ref[Layer[nombre]], float(vals2[i]),
                             f"e_ref[{nombre}] de la cápsula no se aplicó al spec")
        # (e) naturalidad-FRESH (c3): un theta con override de laboratorio NO entra ni como
        # nacimiento — el genoma fresh pasa por el mismo peaje (A4)
        sucio = copy.deepcopy(self.thetas[1])
        sucio["memory"]["layers"]["Q"]["_mem_force_scale"] = 2.0
        with self.assertRaisesRegex(RuntimeError, "laboratorio"):
            componer_red([{"theta": self.thetas[0], "capsula": self.caps[0]},
                          {"theta": sucio, "capsula": None}], m["edges"], **comunes)
        # (f) borde canonical_ring_exact (c4): delay receptor == delay fuente (tau=2.0)
        borde = [{"i": 0, "j": 1, "w_k": 1.0, "w_gamma": 1.0, "tau": 2.0}]
        net_b, _, recibo_b = componer_red(
            [{"theta": t, "capsula": c} for t, c in zip(self.thetas, self.caps)],
            borde, **comunes)
        self.assertEqual(recibo_b["target_delay_steps"], 25000)
        self.assertEqual([o["history_operation"] for o in recibo_b["por_nodo"]],
                         ["canonical_ring_exact"] * 2)
        for j, cap in enumerate(self.caps):
            np.testing.assert_array_equal(
                np.asarray(net_b.history.buffer)[:, j, :],
                cap6.quench_column(cap["arrays"], 25000),
                err_msg=f"nodo {j}: el camino canonical_ring_exact no re-basa bien")
        self.assertEqual(net_b.history.head_idx, 0)


if __name__ == "__main__":
    unittest.main()
