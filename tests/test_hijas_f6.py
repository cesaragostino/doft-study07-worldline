"""GATES F6 — worldlines HIJAS: intervenciones como specs de corrida (plan §20.9 Fase 6).

Nacidos con el patrón endurecido por 4 double taps (F2/F3/F4/F5): anclas BIT-exactas sobre
TODOS los ticks, forjadores por rama con regex del mensaje exacto, y verificación de que la
madre no se toca — medida, no asumida.

1. MADRE INMUTABLE: crear hijas no cambia UN byte del run de la madre (hash por archivo).
2. GEMELA (control apareado): hija sin eventos == continuación de la madre BIT-exacta en
   TODOS los canales (estados+drive+kicks, T>0: el RNG viaja) y TODOS los ticks.
3. KICK: pre-evento == madre bit; el evento diverge; el ESPEJO manual (restaurar + operar a
   mano) reproduce la hija bit-exacta tick por tick — lo declarado ES lo aplicado.
4. HOTCUT (escala_arista 0): espejo manual bit-exacto; el drive delata el corte vs la gemela.
5. LINAJE EXIGIDO: una red restaurada no se graba sin su linaje completo y VERIFICADO
   (patrón A5: el origen viaja adherido a la red).
6. PRE-REGISTRO fail-loud: eventos inválidos mueren ANTES de crear nada en disco.
7. La hija es una corrida NORMAL: load_run + vistas de fase y energía la leen.
8. events.jsonl VERIFICABLE desde el film: toda adulteración (delta, sha, línea extra,
   archivo ausente) se detecta sin sellos extra.
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
from study07.artifacts.checkpoint import load_checkpoint, network_from_checkpoint
from study07.artifacts.recorder import WorldlineRecorder, load_worldline
from study07.compat.study06_v4 import parse_theta_v2
from study07.instruments import api, energy, phase
from test_worldline_checkpoint import MAN, _f6_net, _flat

REPO = Path(__file__).resolve().parents[1]
F6 = REPO / "tests/fixtures/study07_f6_regimen_caliente.npz"

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
        # la foto de la madre ANTES de crear ninguna hija (gate 1 la re-mide al final)
        cls.madre_hashes_pre = _hash_dir(cls.madre_dir)
        cls.man_hija = {"run_id": "hija", "spec_tipo": "M1",
                        "hashes_base_externa": dict(MAN["hashes_base_externa"]),
                        "parent_run_id": "madre",
                        "parent_worldline_hash": cls.wl_madre["worldline_hash"]}
        # hijas compartidas: gemela + kick + hotcut
        cls.dir_gemela, _, _ = hj.correr_hija(
            _specs_frescos()[0], cls.ck_path, cls.tmp / "gemela", dict(cls.man_hija),
            [], TICKS_HIJA, chunk_ticks=32)
        cls.ev_kick = [{"tipo": "kick", "tick_hija": 30, "nodo": 0, "canal": "v",
                       "delta": list(DELTA_KICK)}]
        cls.dir_kick, _, cls.ejec_kick = hj.correr_hija(
            _specs_frescos()[0], cls.ck_path, cls.tmp / "kick", dict(cls.man_hija),
            cls.ev_kick, TICKS_HIJA, chunk_ticks=32)
        cls.ev_hotcut = [{"tipo": "escala_arista", "tick_hija": 40, "arista": 0,
                          "factor_w_k": 0.0, "factor_w_gamma": 0.0}]
        cls.dir_hotcut, _, _ = hj.correr_hija(
            _specs_frescos()[0], cls.ck_path, cls.tmp / "hotcut", dict(cls.man_hija),
            cls.ev_hotcut, TICKS_HIJA, chunk_ticks=32)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ── 1 · madre inmutable ──────────────────────────────────────────────────

    def test_gate1_madre_inmutable_medido(self):
        """Tras crear gemela+kick+hotcut: ni UN byte de la madre cambió (medido archivo
        por archivo, no asumido)."""
        post = _hash_dir(self.madre_dir)
        self.assertEqual(post, self.madre_hashes_pre,
                         "crear hijas modificó el run de la madre — PROHIBIDO")
        self.assertTrue((self.madre_dir / "COMPLETE").exists())

    # ── 2 · gemela: el control apareado ──────────────────────────────────────

    def test_gate2_gemela_continua_a_la_madre_bit_exacta(self):
        wl = load_worldline(self.dir_gemela)
        man = wl["manifest"]
        self.assertFalse(man["intervenida"])
        self.assertEqual(man["eventos_declarados"], [])
        self.assertEqual(man["parent_checkpoint_sha256"], self.ck_sha)
        self.assertEqual(man["tick_madre"], TICK_CK)
        self.assertEqual(man["parent_run_id"], "madre")
        self.assertEqual(man["parent_worldline_hash"], self.wl_madre["worldline_hash"])
        # TODOS los canales, TODOS los ticks (T=0.05: si el RNG no viajara, divergiría)
        for j in range(3):
            np.testing.assert_array_equal(
                wl["estados"][j], self.wl_madre["estados"][j][TICK_CK:TICK_CK + TICKS_HIJA + 1],
                err_msg=f"nodo {j}: la gemela no continúa a la madre bit-exacta")
            np.testing.assert_array_equal(
                wl["kicks"][j][1:], self.wl_madre["kicks"][j][TICK_CK + 1:TICK_CK + TICKS_HIJA + 1],
                err_msg=f"nodo {j}: el canal de kicks térmicos difiere (el RNG no viajó)")
        np.testing.assert_array_equal(
            wl["drive"][1:], self.wl_madre["drive"][TICK_CK + 1:TICK_CK + TICKS_HIJA + 1],
            err_msg="el drive de la gemela difiere del de la madre")
        self.assertEqual(hj.verificar_hija(self.dir_gemela), [])
        self.assertEqual((self.dir_gemela / "events.jsonl").read_text(), "")

    # ── 3 · kick: declarado == aplicado, espejo bit-exacto ───────────────────

    def test_gate3_kick_diverge_donde_declara_y_espejo_bit_exacto(self):
        wl = load_worldline(self.dir_kick)
        madre = self.wl_madre
        # pre-evento: fila a fila IGUAL a la madre (0..29)
        for j in range(3):
            np.testing.assert_array_equal(
                wl["estados"][j][:30], madre["estados"][j][TICK_CK:TICK_CK + 30],
                err_msg=f"nodo {j}: la hija difiere ANTES del evento declarado")
        # el evento DIVERGE exactamente donde declara
        d30 = float(np.max(np.abs(wl["estados"][0][30] - madre["estados"][0][TICK_CK + 30])))
        self.assertGreater(d30, 0.0, "el kick declarado no cambió nada")
        # ESPEJO MANUAL: restaurar + 29 steps + cirugía a mano + 71 steps == hija, TODOS
        # los ticks bit-exactos (lo declarado ES lo aplicado, sin intermediarios)
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
                                          err_msg=f"nodo {j}: la hija no es el espejo "
                                                  "manual de su spec")
        # events.jsonl: el pre es LA FILA 29 del film (recomputado acá, independiente)
        ej = self.ejec_kick[0]
        self.assertEqual(ej["estado_pre_sha256"],
                         hashlib.sha256(np.ascontiguousarray(
                             wl["estados"][0][29]).tobytes()).hexdigest())
        self.assertEqual(ej["tick_global"], TICK_CK + 30)
        hj.verificar_hija(self.dir_kick)

    # ── 4 · hotcut: el corte se ve en el drive y el espejo es exacto ─────────

    def test_gate4_hotcut_espejo_y_drive(self):
        wl = load_worldline(self.dir_hotcut)
        wl_g = load_worldline(self.dir_gemela)
        specs, _ = _specs_frescos()
        net2 = network_from_checkpoint(specs, load_checkpoint(self.ck_path))
        filas = [[_flat(s).copy() for s in net2.states]]
        for tick in range(1, TICKS_HIJA + 1):
            if tick == 40:
                net2.edge_w_k[0] *= 0.0
                net2.edge_w_g[0] *= 0.0
            net2.step()
            filas.append([_flat(s).copy() for s in net2.states])
        for j in range(3):
            esperado = np.stack([f[j] for f in filas])
            np.testing.assert_array_equal(wl["estados"][j], esperado,
                                          err_msg=f"nodo {j}: el hotcut no es su espejo")
        # antes del corte: drive idéntico a la gemela; después: difiere (el corte es REAL)
        np.testing.assert_array_equal(wl["drive"][:40], wl_g["drive"][:40])
        d_post = float(np.max(np.abs(wl["drive"][41:] - wl_g["drive"][41:])))
        self.assertGreater(d_post, 0.0, "cortar la arista no cambió el drive: corte vacuo")
        ejec = hj.verificar_hija(self.dir_hotcut)
        self.assertEqual(ejec[0]["aplicado"]["w_k_despues"], 0.0)

    # ── 5 · linaje exigido ───────────────────────────────────────────────────

    def test_gate5_linaje_exigido_fail_loud(self):
        specs, _ = _specs_frescos()
        net = network_from_checkpoint(specs, load_checkpoint(self.ck_path))
        with tempfile.TemporaryDirectory() as td:
            # (a) red restaurada SIN linaje: el recorder rechaza
            with self.assertRaisesRegex(ValueError, "linaje"):
                WorldlineRecorder(Path(td) / "a", net, dict(MAN), chunk_ticks=32)
            # (b) linaje con checkpoint EQUIVOCADO
            man = dict(self.man_hija)
            man.update({"parent_checkpoint_sha256": "0" * 64, "tick_madre": TICK_CK,
                        "eventos_declarados": [], "intervenida": False})
            with self.assertRaisesRegex(ValueError, "RESTAURADO"):
                WorldlineRecorder(Path(td) / "b", net, man, chunk_ticks=32)
            # (c) tick_madre mentido
            man = dict(self.man_hija)
            man.update({"parent_checkpoint_sha256": self.ck_sha, "tick_madre": 7,
                        "eventos_declarados": [], "intervenida": False})
            with self.assertRaisesRegex(ValueError, "tick_madre"):
                WorldlineRecorder(Path(td) / "c", net, man, chunk_ticks=32)
            # (d) intervenida inconsistente con los eventos
            man = dict(self.man_hija)
            man.update({"parent_checkpoint_sha256": self.ck_sha, "tick_madre": TICK_CK,
                        "eventos_declarados": [], "intervenida": True})
            with self.assertRaisesRegex(ValueError, "gemela"):
                WorldlineRecorder(Path(td) / "d", net, man, chunk_ticks=32)
            # (e) correr_hija sin parent_run_id: el linaje se declara al nacer
            man = {k: v for k, v in self.man_hija.items() if k != "parent_run_id"}
            with self.assertRaisesRegex(RuntimeError, "linaje se declara"):
                hj.correr_hija(specs, self.ck_path, Path(td) / "e", man, [], 10)

    # ── 6 · pre-registro fail-loud ───────────────────────────────────────────

    def test_gate6_eventos_invalidos_mueren_antes_de_crear_nada(self):
        specs, _ = _specs_frescos()
        casos = [
            ([{"tipo": "laser", "tick_hija": 5}], "tipo desconocido"),
            ([{"tipo": "kick", "tick_hija": 0, "nodo": 0, "canal": "v",
               "delta": [0.0] * 10}], "fuera de"),
            ([{"tipo": "kick", "tick_hija": 999, "nodo": 0, "canal": "v",
               "delta": [0.0] * 10}], "fuera de"),
            ([{"tipo": "kick", "tick_hija": 5, "nodo": 99, "canal": "v",
               "delta": [0.0] * 10}], "nodo"),
            ([{"tipo": "kick", "tick_hija": 5, "nodo": 0, "canal": "q",
               "delta": [0.0] * 10}], "canal"),
            ([{"tipo": "kick", "tick_hija": 5, "nodo": 0, "canal": "v",
               "delta": [0.0] * 3}], "forma"),
            ([{"tipo": "kick", "tick_hija": 5, "nodo": 0, "canal": "v",
               "delta": [float("inf")] * 10}], "finito"),
            ([{"tipo": "escala_arista", "tick_hija": 5, "arista": 99,
               "factor_w_k": 0.0}], "arista"),
            ([{"tipo": "escala_arista", "tick_hija": 5, "arista": 0,
               "factor_w_k": float("nan")}], "finito"),
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

    # ── 7 · la hija es una corrida normal ────────────────────────────────────

    def test_gate7_la_hija_es_una_corrida_normal(self):
        wl = api.load_run(self.dir_kick)
        self.assertTrue(wl["manifest"]["intervenida"])
        v = phase.run(wl)
        self.assertEqual(v.arrays["theta"].shape, (TICKS_HIJA + 1, 3))
        ve = energy.run(wl, self.meta6["thetas_embebidos"])
        self.assertEqual(ve.arrays["e_capa"].shape, (TICKS_HIJA + 1, 3, 3))
        # la vista lleva el worldline_hash de la HIJA, no el de la madre
        self.assertNotEqual(v.manifest["worldline_hash"],
                            self.wl_madre["worldline_hash"])

    # ── 8 · events.jsonl verificable desde el film ───────────────────────────

    def test_gate8_events_jsonl_toda_adulteracion_se_detecta(self):
        with tempfile.TemporaryDirectory() as td:
            def copia():
                dst = Path(td) / f"c{len(list(Path(td).iterdir()))}"
                shutil.copytree(self.dir_kick, dst)
                return dst
            # (a) delta adulterado en events.jsonl (declarado != ejecutado)
            d = copia()
            lineas = (d / "events.jsonl").read_text().splitlines()
            ev = json.loads(lineas[0]); ev["delta"] = [x * 2 for x in ev["delta"]]
            (d / "events.jsonl").write_text(json.dumps(ev) + "\n")
            with self.assertRaisesRegex(RuntimeError, "declarado"):
                hj.verificar_hija(d)
            # (b) pre-sha adulterado COHERENTE con lo declarado (miente sobre el film)
            d = copia()
            ev = json.loads((d / "events.jsonl").read_text().splitlines()[0])
            ev["estado_pre_sha256"] = "0" * 64
            (d / "events.jsonl").write_text(json.dumps(ev) + "\n")
            with self.assertRaisesRegex(RuntimeError, "miente"):
                hj.verificar_hija(d)
            # (c) post-sha adulterado: lo aplicado no es lo declarado
            d = copia()
            ev = json.loads((d / "events.jsonl").read_text().splitlines()[0])
            ev["estado_post_sha256"] = "0" * 64
            (d / "events.jsonl").write_text(json.dumps(ev) + "\n")
            with self.assertRaisesRegex(RuntimeError, "aplicado no es lo declarado"):
                hj.verificar_hija(d)
            # (d) línea extra: el timeline no coincide
            d = copia()
            texto = (d / "events.jsonl").read_text()
            (d / "events.jsonl").write_text(texto + texto)
            with self.assertRaisesRegex(RuntimeError, "timeline no coincide"):
                hj.verificar_hija(d)
            # (e) events.jsonl ausente en una intervenida
            d = copia()
            (d / "events.jsonl").unlink()
            with self.assertRaisesRegex(RuntimeError, "sin events.jsonl"):
                hj.verificar_hija(d)
            # (f) un run NO-hija no se hace pasar por hija
            with self.assertRaisesRegex(RuntimeError, "no es una hija"):
                hj.verificar_hija(self.madre_dir)


if __name__ == "__main__":
    unittest.main()
