"""GATES F7 — campañas y el census [M2] como tipo validado (plan §20.9 Fase 7).

Nacidos endurecidos (lección de 5 double taps): regex por rama del validador, anclas
bit-exactas del determinismo, reanudación medida, restos jamás borrados.

1. VALIDADOR [M2] rama por rama: población parcial/sobrante, catálogo por hash,
   intervenciones, horizonte de emergencia, reglas sin sellar, probeta GOLD, retención no
   implementada, spec malformada — cada una RECHAZA con su mensaje (el 67/150 de §84 no
   compila).
2. CAMPAÑA end-to-end: ledger completo EN ORDEN (los aburridos son datos), films COMPLETE,
   vistas re-verificadas, métricas basicas_v1, GOLD en el ledger.
3. DETERMINISMO BAJO PARALELISMO: workers=3 == workers=1 BIT-exacto (worldline_hashes).
4. REANUDACIÓN: unidades COMPLETE se reusan idénticas (verificado por hash); una unidad
   rota va a restos_*/ (JAMÁS se borra) y se rehace al MISMO hash.
5. Una campaña NO PISA otra (spec distinta sobre el mismo base = rechazo).
6. Cápsula no-pinneada o adulterada: la unidad muere fail-loud.
7. ARCHIVADO verificado sha-por-sha; el destino ocupado no se pisa.
"""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from study07.artifacts import campana as cp
from study07.compat import study06_capsule as cap6

REPO = Path(__file__).resolve().parents[1]
F8 = REPO / "tests/fixtures/study07_f8_transporte.npz"
CAPS_DIR = REPO / "tests/fixtures/f8_capsulas"
TICKS = 400


class TestCampanasF7(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fx = np.load(F8, allow_pickle=False)
        cls.m8 = json.loads(str(fx["meta_json"]))
        cls.bids = cls.m8["block_ids"]
        cls.thetas = cls.m8["thetas_embebidos"]
        cls.caps_sha = {b: cap6.load_capsule(CAPS_DIR / b)["capsule_sha256"]
                        for b in cls.bids}
        cls.ep = {k: cls.m8["engine_params"][k]
                  for k in ("dt", "temperature", "kappa_global", "coupling_gamma_c",
                            "tau_field")}
        cls.edges = cls.m8["edges"]
        cls.inventario = {"sha256": "inv_mini_" + cp.sha_json(cls.bids)[:16],
                          "block_ids": list(cls.bids)}
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _unidad(self, run_id, origenes, seed=2026, ticks=TICKS, poblacion=False):
        cons = []
        for bid, origen in zip(self.bids, origenes):
            c = {"block_id": bid, "theta": self.thetas[self.bids.index(bid)]}
            if origen == "capsula":
                c["capsula_dir"] = str(CAPS_DIR / bid)
                c["capsule_sha256"] = self.caps_sha[bid]
            if poblacion:
                c["es_poblacion"] = True
            cons.append(c)
        return {"run_id": run_id, "constituyentes": cons, "edges": self.edges,
                "engine_params": dict(self.ep), "seed": seed, "ticks": ticks}

    def _spec(self):
        return {"campana": "mini_f7", "spec_tipo": "M2",
                "porque": "gates F7: la máquina de campañas, medida",
                "poblacion_inventario_sha256": self.inventario["sha256"],
                "unidades": [
                    self._unidad("u1_transported", ["capsula", "capsula"], poblacion=True),
                    self._unidad("u2_fresh", ["nacimiento", "nacimiento"]),
                    self._unidad("u3_mixta", ["capsula", "nacimiento"]),
                ],
                "retencion": {"perfil": "conformidad_completa"},
                "horizonte_emergencia_ticks": TICKS,
                "reglas_clasificacion": {"basicas_v1": "t_lock/t_half/E segun prereg"},
                "probeta_gold_block_id": self.bids[0],
                "seed_politica": "seed unica declarada por unidad"}

    # ── 1 · validador rama por rama ──────────────────────────────────────────

    def test_gate1_validador_m2_rama_por_rama(self):
        cp.validar_campana(self._spec(), self.inventario)     # la sana PASA
        casos = []
        s = self._spec(); del s["unidades"][0]["constituyentes"][0]["es_poblacion"]
        casos.append((s, self.inventario, "inventario COMPLETO"))
        s = self._spec()
        s["unidades"][0]["constituyentes"][0]["es_poblacion"] = True
        s["unidades"][1]["constituyentes"][0]["block_id"] = "f" * 40
        s["unidades"][1]["constituyentes"][0]["es_poblacion"] = True
        casos.append((s, self.inventario, "inventario COMPLETO"))
        casos.append((self._spec(), None, "sin inventario"))
        s = self._spec(); s["poblacion_inventario_sha256"] = "x" * 16
        casos.append((s, self.inventario, "poblacion_inventario_sha256"))
        s = self._spec(); s["unidades"][1]["eventos"] = [{"tipo": "kick"}]
        casos.append((s, self.inventario, "intervenciones"))
        s = self._spec(); s["unidades"][0]["ticks"] = TICKS - 1
        casos.append((s, self.inventario, "horizonte"))
        s = self._spec(); s["reglas_clasificacion"] = {}
        casos.append((s, self.inventario, "clasificaci"))
        s = self._spec(); del s["probeta_gold_block_id"]
        casos.append((s, self.inventario, "GOLD"))
        s = self._spec(); s["probeta_gold_block_id"] = "a" * 40
        casos.append((s, self.inventario, "GOLD"))
        s = self._spec(); s["retencion"] = {"perfil": "downsample_100"}
        casos.append((s, self.inventario, "F7.2"))
        s = self._spec(); s["unidades"][1]["run_id"] = "u1_transported"
        casos.append((s, self.inventario, "duplicado"))
        s = self._spec(); del s["unidades"][0]["constituyentes"][0]["theta"]
        casos.append((s, self.inventario, "EMBEBIDO"))
        s = self._spec(); del s["unidades"][0]["constituyentes"][0]["capsule_sha256"]
        casos.append((s, self.inventario, "PINNEADO"))
        s = self._spec(); del s["porque"]
        casos.append((s, self.inventario, "sin claves"))
        s = self._spec(); s["spec_tipo"] = "M3"
        casos.append((s, self.inventario, "M1 o M2"))
        s = self._spec(); s["unidades"] = []
        casos.append((s, self.inventario, "sin unidades"))
        for i, (spec, inv, regex) in enumerate(casos):
            with self.assertRaisesRegex(RuntimeError, regex, msg=f"caso {i}"):
                cp.validar_campana(spec, inv)
        # M1: sin inventario NI reglas M2 — pasa (el microscopio es libre)
        s = self._spec(); s["spec_tipo"] = "M1"
        cp.validar_campana(s, None)

    # ── 2 · campaña end-to-end ───────────────────────────────────────────────

    def test_gate2_campana_end_to_end_ledger_completo(self):
        base = self.tmp / "c_base"
        ledger = cp.correr_campana(self._spec(), base, inventario=self.inventario,
                                   hashes_base={"mini_inv": self.inventario["sha256"]},
                                   workers=1)
        self.assertEqual(ledger["n_unidades"], 3)
        self.assertEqual([u["run_id"] for u in ledger["unidades"]],
                         ["u1_transported", "u2_fresh", "u3_mixta"],
                         "el reporte no respeta el ORDEN de la spec")
        hashes = [u["worldline_hash"] for u in ledger["unidades"]]
        self.assertEqual(len(set(hashes)), 3, "worldline_hashes no únicos")
        for u in ledger["unidades"]:
            self.assertEqual(u["estado"], "completa")
            self.assertIn("t_lock_tick", u["metricas"])
            self.assertIn("E0_nodo0", u["metricas"])
            self.assertTrue((base / "unidades" / u["run_id"] / "COMPLETE").exists())
        self.assertEqual(ledger["probeta_gold_block_id"], self.bids[0])
        # el LEDGER en disco coincide con su sidecar
        cuerpo = (base / "LEDGER.json").read_text()
        self.assertEqual(hashlib.sha256(cuerpo.encode()).hexdigest(),
                         (base / "LEDGER.sha256").read_text().split()[0])
        # física sanity: el transported arranca con el fuego de la cápsula
        m1 = ledger["unidades"][0]["metricas"]
        m2 = ledger["unidades"][1]["metricas"]
        self.assertGreater(m1["E0_nodo0"], 1e3 * max(m2["E0_nodo0"], 1e-12),
                           "el fuego de la cápsula no está en la unidad transported")
        type(self).ledger_base = ledger

    # ── 3 · determinismo bajo paralelismo ────────────────────────────────────

    def test_gate3_workers_3_bit_identico_a_workers_1(self):
        """TODO idéntico salvo workers: si un solo bit difiere, el paralelismo está roto.
        (worldline_hash = chunks ‖ manifiesto: cubre física Y papeles.)"""
        base = self.tmp / "c_par"
        ledger = cp.correr_campana(self._spec(), base, inventario=self.inventario,
                                   hashes_base={"mini_inv": self.inventario["sha256"]},
                                   workers=3)
        h_par = {u["run_id"]: u["worldline_hash"] for u in ledger["unidades"]}
        h_seq = {u["run_id"]: u["worldline_hash"]
                 for u in self.ledger_base["unidades"]}
        self.assertEqual(h_par, h_seq,
                         "el paralelismo cambió un bit de algún film — PROHIBIDO")

    # ── 4 · reanudación sin pérdida ──────────────────────────────────────────

    def test_gate4_reanudacion_reusa_y_rehace_sin_borrar(self):
        base = self.tmp / "c_resume"
        l1 = cp.correr_campana(self._spec(), base, inventario=self.inventario, workers=1)
        h1 = {u["run_id"]: u["worldline_hash"] for u in l1["unidades"]}
        # romper u2: sacarle el COMPLETE (simula interrupción) — en tmpdir del test
        (base / "unidades" / "u2_fresh" / "COMPLETE").unlink()
        l2 = cp.correr_campana(self._spec(), base, inventario=self.inventario, workers=1)
        estados = {u["run_id"]: u["estado"] for u in l2["unidades"]}
        self.assertEqual(estados["u1_transported"], "reusada")
        self.assertEqual(estados["u3_mixta"], "reusada")
        self.assertEqual(estados["u2_fresh"], "completa")
        h2 = {u["run_id"]: u["worldline_hash"] for u in l2["unidades"]}
        self.assertEqual(h1, h2, "la reanudación cambió algún film")
        restos = list((base / "unidades").glob("restos_u2_fresh_*"))
        self.assertEqual(len(restos), 1, "los restos de la interrupción se BORRARON")
        self.assertEqual(l2["reusadas"], 2)

    # ── 5 · una campaña no pisa otra ─────────────────────────────────────────

    def test_gate5_spec_distinta_sobre_mismo_base_rechaza(self):
        base = self.tmp / "c_pisa"
        cp.correr_campana(self._spec(), base, inventario=self.inventario, workers=1)
        otra = self._spec()
        otra["porque"] = "OTRA campaña con otro porqué"
        with self.assertRaisesRegex(RuntimeError, "no pisa"):
            cp.correr_campana(otra, base, inventario=self.inventario, workers=1)

    # ── 6 · cápsula adulterada muere fail-loud ───────────────────────────────

    def test_gate6_capsula_no_pinneada_muere(self):
        s = self._spec()
        s["unidades"][0]["constituyentes"][0]["capsule_sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(RuntimeError, "PINNEADA"):
            cp.correr_campana(s, self.tmp / "c_mala", inventario=self.inventario,
                              workers=1)

    # ── 7 · archivado verificado, sin pisar ──────────────────────────────────

    def test_gate7_archivado_verificado_y_no_pisa(self):
        base = self.tmp / "c_arch"
        destino = self.tmp / "externo" / "c_arch"
        cp.correr_campana(self._spec(), base, inventario=self.inventario,
                          workers=1, archivar_en=destino)
        self.assertTrue((destino / "ARCHIVADO.json").exists())
        arch = json.loads((destino / "ARCHIVADO.json").read_text())
        self.assertEqual(arch["verificacion"], "sha256 por archivo, 0 discrepancias")
        self.assertTrue((destino / "LEDGER.json").exists())
        with self.assertRaisesRegex(RuntimeError, "no se pisa"):
            cp.correr_campana(self._spec(), base, inventario=self.inventario,
                              workers=1, archivar_en=destino)


if __name__ == "__main__":
    unittest.main()
