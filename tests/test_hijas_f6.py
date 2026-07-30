"""GATES F6 — worldlines HIJAS (plan §20.9 Fase 6), ENDURECIDOS por el double tap
wf_ae4164d4 (A1-A5 + lote): la rama arista del verificador ahora ANCLA a la topología
sellada, el quench de pesos recomputa wsum (cerraba una divergencia viva-vs-restore de
4.66e-04), el linaje se VERIFICA contra el padre real y el estado intervenido/compuesto NO
se lava en una generación (estampado del checkpoint).

1.  MADRE INMUTABLE medida (y RE-medida en tearDownClass — c1 M-E).
2.  GEMELA bit-exacta TODOS los canales/ticks + ancla del RNG del film hijo (M-B).
3.  KICK: espejo manual bit-exacto + multi-evento (desorden declarado, encadenado mismo
    tick/mismo nodo, nodos distintos, bordes tick 1 y tick final — mata M5/M20).
4.  HOTCUT: espejo + drive delata + WSUM: hija viva post-escala == checkpoint→restore→
    continuación BIT-exacta (el bug A2 muere acá).
5.  LINAJE: por-clave (7 individuales — M21), fabricado sin red restaurada, padre inventado
    (run_id y worldline_hash contra el padre REAL), madre sin cerrar, sin porqué, nieta
    LAVADA rechazada.
6.  PRE-REGISTRO: 12 casos inválidos sin rastro (incl. vacuos y factor negativo).
7.  La hija es corrida normal + la VISTA declara la procedencia del film.
8.  events.jsonl: 10 adulteraciones detectadas (incl. forja de arista coherente, tick_global,
    clave extra — V1/M17/M19/M-D).
9.  ABORT: blow-up más corto que la ventana de chequeo NO sella COMPLETE (V5/A4), aborta
    TEMPRANO (M11) y deja los eventos ejecutados legibles (M8).
10. HIJA DE COMPUESTA: la procedencia F5 viaja en el checkpoint (V6/A5).
11. NIETAS: el linaje encadena por el estampado; la nieta de una intervenida HEREDA.
"""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from study07.artifacts import hija as hj
from study07.artifacts.checkpoint import (load_checkpoint, network_from_checkpoint,
                                          save_checkpoint)
from study07.artifacts.composer import componer_red
from study07.artifacts.recorder import WorldlineRecorder, load_worldline
from study07.artifacts.runner import run as run_net
from study07.compat import study06_capsule as cap6
from study07.compat.study06_v4 import parse_theta_v2
from study07.instruments import api, energy, phase
from test_worldline_checkpoint import MAN, _f6_net, _flat

REPO = Path(__file__).resolve().parents[1]
F6 = REPO / "tests/fixtures/study07_f6_regimen_caliente.npz"
F8 = REPO / "tests/fixtures/study07_f8_transporte.npz"
CAPS_DIR = REPO / "tests/fixtures/f8_capsulas"

TICKS_MADRE, TICK_CK, TICKS_HIJA = 200, 100, 100
DELTA_KICK = [0.01 * (k + 1) for k in range(10)]


def _specs_frescos():
    fx = np.load(F6, allow_pickle=False)
    meta = json.loads(str(fx["meta_json"]))
    specs = []
    for theta in meta["thetas_embebidos"]:
        sp, _ = parse_theta_v2(theta, emission_scale=1.0 / max(len(theta["modes"]), 1))
        specs.append(sp)
    return specs, meta


def _hash_dir(d):
    return {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(d).rglob("*")) if p.is_file()}


class TestHijasF6(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        net, specs, meta = _f6_net()
        cls.meta6 = meta
        cls.madre_dir = cls.tmp / "madre"
        rec = WorldlineRecorder(cls.madre_dir, net, dict(MAN), chunk_ticks=64)
        for _ in range(TICK_CK):
            net.step()
            rec.record_step()
        cls.ck_path = rec.save_checkpoint()
        for _ in range(TICKS_MADRE - TICK_CK):
            net.step()
            rec.record_step()
        rec.close()
        cls.wl_madre = api.load_run(cls.madre_dir)
        cls.ck_sha = hashlib.sha256(cls.ck_path.read_bytes()).hexdigest()
        cls.madre_hashes_pre = _hash_dir(cls.madre_dir)
        cls.man_hija = {"run_id": "hija", "spec_tipo": "M1",
                        "hashes_base_externa": dict(MAN["hashes_base_externa"]),
                        "porque": "gates F6: gemela/kick/hotcut sobre la madre f6",
                        "parent_run_id": MAN["run_id"],
                        "parent_worldline_hash": cls.wl_madre["worldline_hash"]}
        cls.dir_gemela, _, _ = hj.correr_hija(
            _specs_frescos()[0], cls.ck_path, cls.tmp / "gemela", dict(cls.man_hija),
            [], TICKS_HIJA, chunk_ticks=32)
        cls.ev_kick = [{"tipo": "kick", "tick_hija": 30, "nodo": 0, "canal": "v",
                       "delta": list(DELTA_KICK)}]
        cls.dir_kick, _, cls.ejec_kick = hj.correr_hija(
            _specs_frescos()[0], cls.ck_path, cls.tmp / "kick", dict(cls.man_hija),
            cls.ev_kick, TICKS_HIJA, chunk_ticks=32, checkpoint_every=50)
        cls.ev_hotcut = [{"tipo": "escala_arista", "tick_hija": 40, "arista": 0,
                          "factor_w_k": 0.0, "factor_w_gamma": 0.0}]
        cls.dir_hotcut, _, _ = hj.correr_hija(
            _specs_frescos()[0], cls.ck_path, cls.tmp / "hotcut", dict(cls.man_hija),
            cls.ev_hotcut, TICKS_HIJA, chunk_ticks=32)

    @classmethod
    def tearDownClass(cls):
        # RE-medición al FINAL (c1 M-E): ningún test de la clase ensució a la madre
        post = _hash_dir(cls.madre_dir)
        assert post == cls.madre_hashes_pre, "algún test modificó el run de la madre"
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ── 1 · madre inmutable ──────────────────────────────────────────────────

    def test_gate1_madre_inmutable_medido(self):
        post = _hash_dir(self.madre_dir)
        self.assertEqual(post, self.madre_hashes_pre,
                         "crear hijas modificó el run de la madre — PROHIBIDO")
        self.assertTrue((self.madre_dir / "COMPLETE").exists())

    # ── 2 · gemela: el control apareado ──────────────────────────────────────

    def test_gate2_gemela_continua_a_la_madre_bit_exacta(self):
        wl = load_worldline(self.dir_gemela)
        man = wl["manifest"]
        self.assertFalse(man["intervenida"])
        self.assertFalse(man["linaje_intervenido"])
        self.assertEqual(man["eventos_declarados"], [])
        self.assertEqual(man["parent_checkpoint_sha256"], self.ck_sha)
        self.assertEqual(man["tick_madre"], TICK_CK)
        self.assertEqual(man["parent_run_id"], MAN["run_id"])
        self.assertEqual(man["parent_worldline_hash"], self.wl_madre["worldline_hash"])
        for j in range(3):
            np.testing.assert_array_equal(
                wl["estados"][j], self.wl_madre["estados"][j][TICK_CK:TICK_CK + TICKS_HIJA + 1],
                err_msg=f"nodo {j}: la gemela no continúa a la madre bit-exacta")
            np.testing.assert_array_equal(
                wl["kicks"][j][1:], self.wl_madre["kicks"][j][TICK_CK + 1:TICK_CK + TICKS_HIJA + 1],
                err_msg=f"nodo {j}: el canal de kicks térmicos difiere (el RNG no viajó)")
        np.testing.assert_array_equal(
            wl["drive"][1:], self.wl_madre["drive"][TICK_CK + 1:TICK_CK + TICKS_HIJA + 1])
        # ancla del RNG del film hijo (M-B): el estado del chunk 0 ES el restaurado
        specs, _ = _specs_frescos()
        net2 = network_from_checkpoint(specs, load_checkpoint(self.ck_path))
        esperado = json.dumps(net2.noise_rng.bit_generator.state, default=str)
        self.assertEqual(wl["rng_states_chunk"][0], esperado,
                         "el rng_state del chunk 0 de la hija no es el del checkpoint")
        self.assertEqual(hj.verificar_hija(self.dir_gemela), [])
        self.assertEqual((self.dir_gemela / "events.jsonl").read_text(), "")

    # ── 3 · kick: espejo + multi-evento ──────────────────────────────────────

    def test_gate3_kick_diverge_donde_declara_y_espejo_bit_exacto(self):
        wl = load_worldline(self.dir_kick)
        madre = self.wl_madre
        for j in range(3):
            np.testing.assert_array_equal(
                wl["estados"][j][:30], madre["estados"][j][TICK_CK:TICK_CK + 30],
                err_msg=f"nodo {j}: la hija difiere ANTES del evento declarado")
        d30 = float(np.max(np.abs(wl["estados"][0][30] - madre["estados"][0][TICK_CK + 30])))
        self.assertGreater(d30, 0.0, "el kick declarado no cambió nada")
        specs, _ = _specs_frescos()
        net2 = network_from_checkpoint(specs, load_checkpoint(self.ck_path))
        filas = [[_flat(s).copy() for s in net2.states]]
        for tick in range(1, TICKS_HIJA + 1):
            if tick == 30:
                net2.states[0].v += np.asarray(DELTA_KICK)
            net2.step()
            filas.append([_flat(s).copy() for s in net2.states])
        for j in range(3):
            esperado = np.stack([f[j] for f in filas])
            np.testing.assert_array_equal(wl["estados"][j], esperado,
                                          err_msg=f"nodo {j}: la hija no es su espejo manual")
        ej = self.ejec_kick[0]
        self.assertEqual(ej["estado_pre_sha256"],
                         hashlib.sha256(np.ascontiguousarray(
                             wl["estados"][0][29]).tobytes()).hexdigest())
        self.assertEqual(ej["tick_global"], TICK_CK + 30)
        hj.verificar_hija(self.dir_kick)

    def test_gate3b_multi_evento_desorden_encadenado_y_bordes(self):
        """Mata M5 (sin sorted) y M20 (sin encadenado): eventos DECLARADOS fuera de orden,
        dos kicks al MISMO tick del MISMO nodo (encadenados), nodos distintos el mismo tick,
        y los bordes tick_hija=1 y tick_hija=ticks."""
        specs, _ = _specs_frescos()
        d1 = [0.001 * (k + 1) for k in range(10)]
        d2 = [-0.002 * (k + 1) for k in range(10)]
        eventos = [  # DELIBERADAMENTE fuera de orden
            {"tipo": "kick", "tick_hija": 40, "nodo": 1, "canal": "x", "delta": d1},
            {"tipo": "kick", "tick_hija": 1, "nodo": 0, "canal": "v", "delta": d1},
            {"tipo": "kick", "tick_hija": 40, "nodo": 1, "canal": "x", "delta": d2},
            {"tipo": "kick", "tick_hija": 40, "nodo": 2, "canal": "v", "delta": d1},
            {"tipo": "kick", "tick_hija": 50, "nodo": 0, "canal": "v", "delta": d2},
        ]
        with tempfile.TemporaryDirectory() as td:
            run_dir, _, ejec = hj.correr_hija(specs, self.ck_path, Path(td) / "multi",
                                              dict(self.man_hija), eventos, 50,
                                              chunk_ticks=16)
            ticks_ejec = [e["tick_hija"] for e in ejec]
            self.assertEqual(ticks_ejec, sorted(ticks_ejec),
                             "los eventos no se ejecutaron en orden de reloj")
            hj.verificar_hija(run_dir)          # el verificador banca el encadenado
            # espejo manual del timeline COMPLETO
            wl = load_worldline(run_dir)
            net2 = network_from_checkpoint(_specs_frescos()[0],
                                           load_checkpoint(self.ck_path))
            filas = [[_flat(s).copy() for s in net2.states]]
            for tick in range(1, 51):
                if tick == 1:
                    net2.states[0].v += np.asarray(d1)
                if tick == 40:
                    net2.states[1].x += np.asarray(d1)
                    net2.states[1].x += np.asarray(d2)
                    net2.states[2].v += np.asarray(d1)
                if tick == 50:
                    net2.states[0].v += np.asarray(d2)
                net2.step()
                filas.append([_flat(s).copy() for s in net2.states])
            for j in range(3):
                np.testing.assert_array_equal(
                    wl["estados"][j], np.stack([f[j] for f in filas]),
                    err_msg=f"nodo {j}: el multi-evento no es su espejo")

    # ── 4 · hotcut: espejo + drive + WSUM bajo checkpoint ────────────────────

    def test_gate4_hotcut_espejo_y_drive(self):
        wl = load_worldline(self.dir_hotcut)
        wl_g = load_worldline(self.dir_gemela)
        specs, _ = _specs_frescos()
        net2 = network_from_checkpoint(specs, load_checkpoint(self.ck_path))
        filas = [[_flat(s).copy() for s in net2.states]]
        for tick in range(1, TICKS_HIJA + 1):
            if tick == 40:
                ev = {"tipo": "escala_arista", "tick_hija": 40, "arista": 0,
                      "factor_w_k": 0.0, "factor_w_gamma": 0.0}
                hj._aplicar(ev, net2, TICK_CK)   # el camino REAL (incluye recompute wsum)
            net2.step()
            filas.append([_flat(s).copy() for s in net2.states])
        for j in range(3):
            np.testing.assert_array_equal(wl["estados"][j],
                                          np.stack([f[j] for f in filas]),
                                          err_msg=f"nodo {j}: el hotcut no es su espejo")
        np.testing.assert_array_equal(wl["drive"][:40], wl_g["drive"][:40])
        d_post = float(np.max(np.abs(wl["drive"][41:] - wl_g["drive"][41:])))
        self.assertGreater(d_post, 0.0, "cortar la arista no cambió el drive: corte vacuo")
        ejec = hj.verificar_hija(self.dir_hotcut)
        self.assertEqual(ejec[0]["aplicado"]["w_k_despues"], 0.0)

    def test_gate4b_wsum_cierra_bajo_checkpoint(self):
        """El bug A2 muere acá: hija VIVA post-escala vs checkpoint→restore→continuación,
        BIT-exactas (antes: wsum viejo en la viva ⇒ divergencia silenciosa 4.66e-04)."""
        specs, _ = _specs_frescos()
        viva = network_from_checkpoint(specs, load_checkpoint(self.ck_path))
        ev = {"tipo": "escala_arista", "tick_hija": 40, "arista": 0,
              "factor_w_k": 0.5, "factor_w_gamma": 0.25}
        for tick in range(1, 46):
            if tick == 40:
                hj._aplicar(ev, viva, TICK_CK)
            viva.step()
        with tempfile.TemporaryDirectory() as td:
            ck2 = load_checkpoint(save_checkpoint(Path(td) / "ck.npz", viva, tick=145))
            restaurada = network_from_checkpoint(_specs_frescos()[0], ck2)
        np.testing.assert_array_equal(viva._wsum_k, restaurada._wsum_k,
                                      err_msg="wsum_k viva != restaurada (A2 volvió)")
        np.testing.assert_array_equal(viva._wsum_g, restaurada._wsum_g)
        for _ in range(20):
            viva.step()
            restaurada.step()
        for j in range(3):
            d = float(np.max(np.abs(_flat(viva.states[j]) - _flat(restaurada.states[j]))))
            self.assertEqual(d, 0.0, f"nodo {j}: viva vs restore divergen post-escala "
                                     f"({d:.3e}) — el bug A2 volvió")

    # ── 5 · linaje exigido y verificado ──────────────────────────────────────

    def test_gate5_linaje_exigido_fail_loud(self):
        specs, _ = _specs_frescos()
        net = network_from_checkpoint(specs, load_checkpoint(self.ck_path))
        lin_ok = {"parent_run_id": MAN["run_id"],
                  "parent_worldline_hash": self.wl_madre["worldline_hash"],
                  "parent_checkpoint_sha256": self.ck_sha, "tick_madre": TICK_CK,
                  "eventos_declarados": [], "intervenida": False,
                  "linaje_intervenido": False}
        base = {"run_id": "x", "spec_tipo": "M1",
                "hashes_base_externa": dict(MAN["hashes_base_externa"])}
        with tempfile.TemporaryDirectory() as td:
            # (a) SIN linaje: rechaza
            with self.assertRaisesRegex(ValueError, "linaje"):
                WorldlineRecorder(Path(td) / "a", net, dict(MAN), chunk_ticks=32)
            # (b) POR CLAVE: cada una de las 7 ausente individualmente rechaza (M21)
            for clave in lin_ok:
                man = {**base, **{k: v for k, v in lin_ok.items() if k != clave}}
                with self.assertRaisesRegex(ValueError, "linaje|" + clave,
                                            msg=f"clave {clave} ausente no cazó"):
                    WorldlineRecorder(Path(td) / f"b_{clave}", net, man, chunk_ticks=32)
            # (c) checkpoint equivocado / tick mentido / intervenida inconsistente
            for clave, valor, regex in (("parent_checkpoint_sha256", "0" * 64, "RESTAURADO"),
                                        ("tick_madre", 7, "tick_madre"),
                                        ("intervenida", True, "gemela"),
                                        ("parent_run_id", "OTRO", "no se inventa"),
                                        ("linaje_intervenido", True, "lava")):
                man = {**base, **lin_ok, clave: valor}
                with self.assertRaisesRegex(ValueError, regex, msg=f"{clave}={valor}"):
                    WorldlineRecorder(Path(td) / f"c_{clave}", net, man, chunk_ticks=32)
            # (d) SIMETRÍA: red FRESCA + linaje fabricado ⇒ rechazo (V3b)
            net_fresca, _, _ = _f6_net()
            man = {**base, **lin_ok}
            with self.assertRaisesRegex(ValueError, "FABRICADO"):
                WorldlineRecorder(Path(td) / "d", net_fresca, man, chunk_ticks=32)
            # (e) correr_hija: padre INVENTADO (run_id y worldline_hash vs el padre REAL)
            man = dict(self.man_hija); man["parent_run_id"] = "MADRE_QUE_JAMAS_EXISTIO"
            with self.assertRaisesRegex(RuntimeError, "no se inventa"):
                hj.correr_hija(specs, self.ck_path, Path(td) / "e", man, [], 10)
            man = dict(self.man_hija); man["parent_worldline_hash"] = "deadbeef" * 8
            with self.assertRaisesRegex(RuntimeError, "no se inventa"):
                hj.correr_hija(specs, self.ck_path, Path(td) / "f", man, [], 10)
            # (f) sin porqué (regla M1)
            man = {k: v for k, v in self.man_hija.items() if k != "porque"}
            with self.assertRaisesRegex(RuntimeError, "PORQU"):
                hj.correr_hija(specs, self.ck_path, Path(td) / "g", man, [], 10)
            # (g) checkpoint PRE-ESQUEMA (sin estampar): no sirve de madre
            ck_crudo = save_checkpoint(Path(td) / "crudo.npz", net, tick=100)
            net3 = network_from_checkpoint(_specs_frescos()[0], load_checkpoint(ck_crudo))
            man = {**base, **lin_ok,
                   "parent_checkpoint_sha256":
                       hashlib.sha256(ck_crudo.read_bytes()).hexdigest()}
            with self.assertRaisesRegex(ValueError, "PRE-ESQUEMA"):
                WorldlineRecorder(Path(td) / "h", net3, man, chunk_ticks=32)
            # (h) spec M2 con intervención: no compila
            man = {**base, **lin_ok, "spec_tipo": "M2"}
            with self.assertRaisesRegex(ValueError, "M2"):
                WorldlineRecorder(Path(td) / "i", net, man, chunk_ticks=32)

    # ── 6 · pre-registro fail-loud ───────────────────────────────────────────

    def test_gate6_eventos_invalidos_mueren_antes_de_crear_nada(self):
        specs, _ = _specs_frescos()
        casos = [
            ([{"tipo": "laser", "tick_hija": 5}], "tipo desconocido"),
            ([{"tipo": "kick", "tick_hija": 0, "nodo": 0, "canal": "v",
               "delta": [1.0] * 10}], "fuera de"),
            ([{"tipo": "kick", "tick_hija": 999, "nodo": 0, "canal": "v",
               "delta": [1.0] * 10}], "fuera de"),
            ([{"tipo": "kick", "tick_hija": 5, "nodo": 99, "canal": "v",
               "delta": [1.0] * 10}], "nodo"),
            ([{"tipo": "kick", "tick_hija": 5, "nodo": 0, "canal": "q",
               "delta": [1.0] * 10}], "canal"),
            ([{"tipo": "kick", "tick_hija": 5, "nodo": 0, "canal": "v",
               "delta": [1.0] * 3}], "forma"),
            ([{"tipo": "kick", "tick_hija": 5, "nodo": 0, "canal": "v",
               "delta": [float("inf")] * 10}], "finito"),
            ([{"tipo": "kick", "tick_hija": 5, "nodo": 0, "canal": "v",
               "delta": [0.0] * 10}], "teatro"),
            ([{"tipo": "escala_arista", "tick_hija": 5, "arista": 99,
               "factor_w_k": 0.0}], "arista"),
            ([{"tipo": "escala_arista", "tick_hija": 5, "arista": 0,
               "factor_w_k": float("nan")}], "finito"),
            ([{"tipo": "escala_arista", "tick_hija": 5, "arista": 0,
               "factor_w_k": -1.0}], "negativo"),
            ([{"tipo": "escala_arista", "tick_hija": 5, "arista": 0,
               "factor_w_k": 1.0, "factor_w_gamma": 1.0}], "teatro"),
        ]
        with tempfile.TemporaryDirectory() as td:
            for i, (eventos, regex) in enumerate(casos):
                destino = Path(td) / f"caso{i}"
                with self.assertRaisesRegex(RuntimeError, regex,
                                            msg=f"caso {i} ({eventos[0]['tipo']})"):
                    hj.correr_hija(specs, self.ck_path, destino, dict(self.man_hija),
                                   eventos, 50)
                self.assertFalse(destino.exists(),
                                 f"caso {i}: el pre-registro inválido DEJÓ RASTRO en disco")

    # ── 7 · corrida normal + la vista declara la procedencia ─────────────────

    def test_gate7_la_hija_es_una_corrida_normal_y_la_vista_declara(self):
        wl = api.load_run(self.dir_kick)
        self.assertTrue(wl["manifest"]["intervenida"])
        self.assertTrue(wl["manifest"]["linaje_intervenido"])
        v = phase.run(wl)
        self.assertEqual(v.arrays["theta"].shape, (TICKS_HIJA + 1, 3))
        self.assertTrue(v.manifest["film_intervenida"],
                        "la vista CALLA que el film está intervenido (c4-S6)")
        self.assertTrue(v.manifest["film_linaje_intervenido"])
        ve = energy.run(wl, self.meta6["thetas_embebidos"])
        self.assertTrue(ve.manifest["film_intervenida"])
        self.assertNotEqual(v.manifest["worldline_hash"],
                            self.wl_madre["worldline_hash"])
        # un film NO intervenido lo declara en falso
        v_madre = phase.run(self.wl_madre)
        self.assertFalse(v_madre.manifest["film_intervenida"])

    # ── 8 · events.jsonl: toda adulteración se detecta ───────────────────────

    def test_gate8_events_jsonl_toda_adulteracion_se_detecta(self):
        with tempfile.TemporaryDirectory() as td:
            def copia(origen):
                dst = Path(td) / f"c{len(list(Path(td).iterdir()))}"
                shutil.copytree(origen, dst)
                return dst

            def tamper(d, mutador):
                ev = json.loads((d / "events.jsonl").read_text().splitlines()[0])
                mutador(ev)
                (d / "events.jsonl").write_text(json.dumps(ev) + "\n")
            # kicks (F6 v1)
            d = copia(self.dir_kick)
            tamper(d, lambda e: e.update(delta=[x * 2 for x in e["delta"]]))
            with self.assertRaisesRegex(RuntimeError, "declarado"):
                hj.verificar_hija(d)
            d = copia(self.dir_kick)
            tamper(d, lambda e: e.update(estado_pre_sha256="0" * 64))
            with self.assertRaisesRegex(RuntimeError, "miente"):
                hj.verificar_hija(d)
            d = copia(self.dir_kick)
            tamper(d, lambda e: e.update(estado_post_sha256="0" * 64))
            with self.assertRaisesRegex(RuntimeError, "aplicado no es lo declarado"):
                hj.verificar_hija(d)
            # tick_global adulterado (M19)
            d = copia(self.dir_kick)
            tamper(d, lambda e: e.update(tick_global=e["tick_global"] + 1))
            with self.assertRaisesRegex(RuntimeError, "tick_global"):
                hj.verificar_hija(d)
            # clave EXTRA (V1: campo hackeado)
            d = copia(self.dir_kick)
            tamper(d, lambda e: e.update(hackeado=True))
            with self.assertRaisesRegex(RuntimeError, "EXTRA"):
                hj.verificar_hija(d)
            # línea extra / archivo ausente / no-hija
            d = copia(self.dir_kick)
            texto = (d / "events.jsonl").read_text()
            (d / "events.jsonl").write_text(texto + texto)
            with self.assertRaisesRegex(RuntimeError, "timeline no coincide"):
                hj.verificar_hija(d)
            d = copia(self.dir_kick)
            (d / "events.jsonl").unlink()
            with self.assertRaisesRegex(RuntimeError, "sin events.jsonl"):
                hj.verificar_hija(d)
            with self.assertRaisesRegex(RuntimeError, "no es una hija"):
                hj.verificar_hija(self.madre_dir)
            # ARISTAS (V1/M17/M-D — la rama que era forjable):
            # (g) forja COHERENTE del antes + pre-sha fabricado a juego
            d = copia(self.dir_hotcut)
            def forja(e):
                ap = e["aplicado"]
                ap["w_k_antes"] = 999.0
                ap["w_k_despues"] = 999.0 * e["factor_w_k"]
                e["estado_pre_sha256"] = hashlib.sha256(np.ascontiguousarray(
                    np.array([999.0, ap["w_gamma_antes"]])).tobytes()).hexdigest()
                e["estado_post_sha256"] = hashlib.sha256(np.ascontiguousarray(
                    np.array([ap["w_k_despues"], ap["w_gamma_despues"]])).tobytes()).hexdigest()
            tamper(d, forja)
            with self.assertRaisesRegex(RuntimeError, "CORRIENTES|miente"):
                hj.verificar_hija(d)
            # (h) pre-sha de arista adulterado solo
            d = copia(self.dir_hotcut)
            tamper(d, lambda e: e.update(estado_pre_sha256="0" * 64))
            with self.assertRaisesRegex(RuntimeError, "miente"):
                hj.verificar_hija(d)
            # (i) despues != antes×factor
            d = copia(self.dir_hotcut)
            def despues_mal(e):
                e["aplicado"]["w_k_despues"] = 0.5
                e["estado_post_sha256"] = hashlib.sha256(np.ascontiguousarray(
                    np.array([0.5, e["aplicado"]["w_gamma_despues"]])).tobytes()).hexdigest()
            tamper(d, despues_mal)
            with self.assertRaisesRegex(RuntimeError, "EXACTO"):
                hj.verificar_hija(d)

    # ── 9 · abort: blow-up corto no sella, aborta temprano, deja restos ──────

    def test_gate9_blowup_corto_no_sella_y_aborta_temprano(self):
        specs, _ = _specs_frescos()
        bomba = [{"tipo": "kick", "tick_hija": 1, "nodo": 0, "canal": "v",
                  "delta": [1e155] * 10}]
        with tempfile.TemporaryDirectory() as td:
            destino = Path(td) / "bomba"
            with self.assertRaises(FloatingPointError):
                hj.correr_hija(specs, self.ck_path, destino, dict(self.man_hija),
                               bomba, 64, chunk_ticks=8, finite_check_every=16)
            # V5/A4: JAMÁS COMPLETE
            self.assertFalse((destino / "COMPLETE").exists(),
                             "un blow-up se selló COMPLETE — contrato §8 violado")
            # M11: abortó TEMPRANO (dentro de la ventana de chequeo, no al final)
            chunks = list((destino / "worldline").glob("chunk_*.npz"))
            self.assertLessEqual(len(chunks), 3,
                                 f"{len(chunks)} chunks: el abort no fue temprano — "
                                 "el finite_check del loop no corre")
            # M8: los eventos EJECUTADOS quedaron legibles (escritura incremental)
            lineas = (destino / "events.jsonl").read_text().splitlines()
            self.assertEqual(len(lineas), 1,
                             "el abort se comió los eventos ejecutados (escritura no "
                             "incremental)")
            # y con la ventana MÁS CORTA que el blow-up igual no sella (check final)
            destino2 = Path(td) / "bomba2"
            with self.assertRaises(FloatingPointError):
                hj.correr_hija(specs, self.ck_path, destino2, dict(self.man_hija),
                               bomba, 8, chunk_ticks=8, finite_check_every=999)
            self.assertFalse((destino2 / "COMPLETE").exists())

    # ── 10 · hija de madre COMPUESTA: la procedencia F5 viaja ────────────────

    def test_gate10_hija_de_compuesta_hereda_la_procedencia(self):
        fx8 = np.load(F8, allow_pickle=False)
        m8 = json.loads(str(fx8["meta_json"]))
        caps = [cap6.load_capsule(CAPS_DIR / b) for b in m8["block_ids"]]
        ep = m8["engine_params"]
        net, _, recibo = componer_red(
            [{"theta": t, "capsula": c} for t, c in zip(m8["thetas_embebidos"], caps)],
            m8["edges"], dt=float(m8["dt"]), seed=int(m8["seed"]),
            k_global=float(ep["kappa_global"]), coupling_gamma_c=float(ep["coupling_gamma_c"]))
        base = {c["manifest"]["block_id"]: c["capsule_sha256"] for c in caps}
        with tempfile.TemporaryDirectory() as td:
            man_m = {"run_id": "compuesta", "spec_tipo": "M1",
                     "hashes_base_externa": dict(base), "composicion": recibo}
            rec = WorldlineRecorder(Path(td) / "compuesta", net, man_m, chunk_ticks=32)
            for _ in range(40):
                net.step()
                rec.record_step()
            ckc = rec.save_checkpoint()
            for _ in range(20):
                net.step()
                rec.record_step()
            rec.close()
            wl_c = api.load_run(Path(td) / "compuesta")
            # la hija: el recibo viaja en el checkpoint y las cápsulas quedan citadas
            specs_c = []
            for theta in m8["thetas_embebidos"]:
                sp, _ = parse_theta_v2(theta, emission_scale=1.0 / len(theta["modes"]))
                specs_c.append(sp)
            man_h = {"run_id": "hija_compuesta", "spec_tipo": "M1",
                     "hashes_base_externa": {}, "porque": "gate10: herencia de procedencia",
                     "parent_run_id": "compuesta",
                     "parent_worldline_hash": wl_c["worldline_hash"]}
            dir_h, _, _ = hj.correr_hija(specs_c, ckc, Path(td) / "hija_c", man_h,
                                         [], 30, chunk_ticks=16)
            wl_h = load_worldline(dir_h)
            self.assertEqual(wl_h["manifest"]["composicion"], recibo,
                             "el recibo de composición NO llegó a la hija (V6/A5)")
            citadas = set(wl_h["manifest"]["hashes_base_externa"].values())
            for c in caps:
                self.assertIn(c["capsule_sha256"], citadas,
                              "la hija no cita las cápsulas de su madre compuesta")
            # negativo: red restaurada de compuesta SIN composicion en el manifiesto
            net_r = network_from_checkpoint(specs_c, load_checkpoint(ckc))
            man_mal = {"run_id": "mal", "spec_tipo": "M1", "hashes_base_externa": {},
                       "parent_run_id": "compuesta",
                       "parent_worldline_hash": wl_c["worldline_hash"],
                       "parent_checkpoint_sha256":
                           hashlib.sha256(Path(ckc).read_bytes()).hexdigest(),
                       "tick_madre": 40, "eventos_declarados": [], "intervenida": False,
                       "linaje_intervenido": False}
            with self.assertRaisesRegex(ValueError, "COMPOSICI"):
                WorldlineRecorder(Path(td) / "mal", net_r, man_mal, chunk_ticks=16)

    # ── 11 · nietas: el linaje encadena y la herencia no se lava ─────────────

    def test_gate11_nietas_encadenan_y_heredan(self):
        specs, _ = _specs_frescos()
        ck_hija = self.dir_kick / "checkpoints" / "ck_00000050.npz"
        self.assertTrue(ck_hija.exists(), "la hija kick no checkpointeó (checkpoint_every)")
        wl_kick = load_worldline(self.dir_kick)
        with tempfile.TemporaryDirectory() as td:
            man_n = {"run_id": "nieta", "spec_tipo": "M1",
                     "hashes_base_externa": dict(MAN["hashes_base_externa"]),
                     "porque": "gate11: la nieta de una intervenida hereda el linaje",
                     "parent_run_id": "hija",
                     "parent_worldline_hash": api.worldline_hash(self.dir_kick)}
            dir_n, _, _ = hj.correr_hija(specs, ck_hija, Path(td) / "nieta", man_n,
                                         [], 20, chunk_ticks=16)
            man = load_worldline(dir_n)["manifest"]
            self.assertEqual(man["parent_run_id"], "hija")
            self.assertEqual(man["tick_madre"], 50)
            self.assertFalse(man["intervenida"], "la nieta gemela no interviene")
            self.assertTrue(man["linaje_intervenido"],
                            "la nieta de una INTERVENIDA se lavó (A3 — nieta lavada)")
            # y el intento de LAVARLA a mano muere en el recorder
            net_n = network_from_checkpoint(_specs_frescos()[0], load_checkpoint(ck_hija))
            man_lavada = {"run_id": "lavada", "spec_tipo": "M1",
                          "hashes_base_externa": dict(MAN["hashes_base_externa"]),
                          "parent_run_id": "hija",
                          "parent_worldline_hash": api.worldline_hash(self.dir_kick),
                          "parent_checkpoint_sha256":
                              hashlib.sha256(ck_hija.read_bytes()).hexdigest(),
                          "tick_madre": 50, "eventos_declarados": [],
                          "intervenida": False, "linaje_intervenido": False}
            with self.assertRaisesRegex(ValueError, "lava"):
                WorldlineRecorder(Path(td) / "lavada", net_n, man_lavada, chunk_ticks=16)


if __name__ == "__main__":
    unittest.main()
