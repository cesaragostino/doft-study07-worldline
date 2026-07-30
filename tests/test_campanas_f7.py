"""GATES F7 — campañas y el census [M2] como tipo validado, ENDURECIDOS por el double tap
wf_2f58724b (A1-A9): la reanudación reconstruye filas COMPLETAS verificadas, el ledger jamás
se degrada, una unidad que falla es un DATO, la procedencia no es fabricable, la población
se verifica por GENOMA, y los papeles (spec_sha canónico, atomicidad, spawn, archivado
verificado) tienen spec-pins con kill-test.

1.  VALIDADOR rama por rama (~22 casos, incl. A5/A9: sha-sin-dir, es_poblacion sin block_id,
    duplicados, genoma vs inventario, hz<1, claves filtro).
2.  END-TO-END: filas ENTERAS del ledger verificadas — view_hashes contra load_view
    RECOMPUTADO y métricas RECOMPUTADAS de los arrays (un ledger mentiroso no compila).
3.  DETERMINISMO: workers=3 == workers=1 en FILAS ENTERAS (física + papeles + métricas).
4.  REANUDACIÓN: reusadas VERIFICADAS (load_worldline) con fila COMPLETA, orden de la spec,
    chunk corrupto con COMPLETE intacto ⇒ REHECHA (restos, jamás borrada), ledger previo
    apartado (jamás degradado).
5.  Una campaña NO PISA otra.
6.  CONTENCIÓN: la unidad con cápsula adulterada = fila 'fallida' con el error como DATO;
    el census sigue, el ledger existe, completa=False; la reanudación la reintenta.
7.  ARCHIVADO atómico verificado: fault-injection (byte corrupto ⇒ raise), sin tmp huérfano,
    destino ocupado no se pisa.
8.  SPEC-PINS + GOLDEN: sha_json invariante al orden (M17), _sha_file >1MB (M19), atomicidad
    del ledger (M14), spawn pinneado (M21), metricas_basicas_v1 con valores golden
    sintéticos (M18: cruce breve ⇒ None) y n=1 ⇒ None declarado, preflight de disco.
"""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        cls.inventario = {
            "sha256": "inv_mini_" + cp.sha_json(cls.bids)[:16],
            "block_ids": list(cls.bids),
            "genome_hash_por_block": {b: cap6.genome_sha256(t)
                                      for b, t in zip(cls.bids, cls.thetas)}}
        cls.base_hashes = {"mini_inv": cls.inventario["sha256"]}
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _unidad(self, run_id, origenes, seed=2026, ticks=TICKS, poblacion=None):
        cons = []
        for k, (bid, origen) in enumerate(zip(self.bids, origenes)):
            c = {"block_id": bid, "theta": self.thetas[self.bids.index(bid)]}
            if origen == "capsula":
                c["capsula_dir"] = str(CAPS_DIR / bid)
                c["capsule_sha256"] = self.caps_sha[bid]
            if poblacion and k in poblacion:
                c["es_poblacion"] = True
            cons.append(c)
        return {"run_id": run_id, "constituyentes": cons, "edges": self.edges,
                "engine_params": dict(self.ep), "seed": seed, "ticks": ticks}

    def _spec(self):
        return {"campana": "mini_f7", "spec_tipo": "M2",
                "porque": "gates F7: la máquina de campañas, medida",
                "poblacion_inventario_sha256": self.inventario["sha256"],
                "unidades": [
                    self._unidad("u1_transported", ["capsula", "capsula"],
                                 poblacion=(0, 1)),
                    self._unidad("u2_fresh", ["nacimiento", "nacimiento"]),
                    self._unidad("u3_mixta", ["capsula", "nacimiento"]),
                ],
                "retencion": {"perfil": "conformidad_completa", "chunk_ticks": 64},
                "horizonte_emergencia_ticks": TICKS,
                "reglas_clasificacion": {"basicas_v1": "t_lock/t_half/E segun prereg"},
                "probeta_gold_block_id": self.bids[0],
                "seed_politica": "seed unica declarada por unidad"}

    def _correr(self, base, spec=None, **kw):
        kw.setdefault("inventario", self.inventario)
        kw.setdefault("hashes_base", self.base_hashes)
        kw.setdefault("workers", 1)
        return cp.correr_campana(spec or self._spec(), base, **kw)

    # ── 1 · validador rama por rama ──────────────────────────────────────────

    def test_gate1_validador_m2_rama_por_rama(self):
        cp.validar_campana(self._spec(), self.inventario)     # la sana PASA
        casos = []
        s = self._spec(); del s["unidades"][0]["constituyentes"][0]["es_poblacion"]
        casos.append((s, self.inventario, "inventario COMPLETO"))
        s = self._spec()
        s["unidades"][1]["constituyentes"][0]["block_id"] = "f" * 40
        s["unidades"][1]["constituyentes"][0]["es_poblacion"] = True
        casos.append((s, self.inventario, "sobran|inventario COMPLETO"))
        casos.append((self._spec(), None, "sin inventario"))
        s = self._spec(); s["poblacion_inventario_sha256"] = "x" * 16
        casos.append((s, self.inventario, "poblacion_inventario_sha256"))
        s = self._spec(); s["unidades"][1]["eventos"] = [{"tipo": "kick"}]
        casos.append((s, self.inventario, "intervenciones"))
        s = self._spec(); s["unidades"][0]["ticks"] = TICKS - 1
        casos.append((s, self.inventario, "horizonte"))
        s = self._spec(); s["horizonte_emergencia_ticks"] = 0
        casos.append((s, self.inventario, "piso"))
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
        # A5: hash sin artefacto = procedencia fabricada
        s = self._spec()
        s["unidades"][1]["constituyentes"][0]["capsule_sha256"] = "sha256:" + "0" * 64
        casos.append((s, self.inventario, "FABRICADA"))
        # A9: es_poblacion sin block_id
        s = self._spec(); del s["unidades"][0]["constituyentes"][0]["block_id"]
        casos.append((s, self.inventario, "insinúa|insinua"))
        # A9: población duplicada entre unidades
        s = self._spec(); s["unidades"][2]["constituyentes"][0]["es_poblacion"] = True
        casos.append((s, self.inventario, "DUPLICADOS"))
        # A9/J4: theta trocado en un individuo de la población
        s = self._spec()
        s["unidades"][0]["constituyentes"][0]["theta"] = \
            s["unidades"][0]["constituyentes"][1]["theta"]
        casos.append((s, self.inventario, "GENOMA"))
        # A9: inventario sin mapa de genomas
        inv_pobre = {k: v for k, v in self.inventario.items()
                     if k != "genome_hash_por_block"}
        casos.append((self._spec(), inv_pobre, "genome_hash_por_block"))
        # gate-portero: claves de filtro no compilan
        s = self._spec(); s["filtro_instrumento"] = {"solo_interesantes": True}
        casos.append((s, self.inventario, "FILTRO"))
        s = self._spec(); del s["porque"]
        casos.append((s, self.inventario, "sin claves"))
        s = self._spec(); s["spec_tipo"] = "M3"
        casos.append((s, self.inventario, "M1 o M2"))
        s = self._spec(); s["unidades"] = []
        casos.append((s, self.inventario, "sin unidades"))
        for i, (spec, inv, regex) in enumerate(casos):
            with self.assertRaisesRegex(RuntimeError, regex, msg=f"caso {i}"):
                cp.validar_campana(spec, inv)
        s = self._spec(); s["spec_tipo"] = "M1"
        cp.validar_campana(s, None)                           # M1 laxa: pasa

    # ── 2 · end-to-end con filas VERIFICADAS ─────────────────────────────────

    def test_gate2_ledger_de_filas_enteras_verificadas(self):
        from study07.instruments import api
        base = self.tmp / "c_base"
        ledger = self._correr(base)
        self.assertEqual(ledger["n_unidades"], 3)
        self.assertTrue(ledger["completa"])
        self.assertEqual(ledger["fallidas"], [])
        self.assertEqual([u["run_id"] for u in ledger["unidades"]],
                         ["u1_transported", "u2_fresh", "u3_mixta"])
        self.assertEqual(len({u["worldline_hash"] for u in ledger["unidades"]}), 3)
        for u in ledger["unidades"]:
            self.assertEqual(u["estado"], "completa")
            run_dir = base / "unidades" / u["run_id"]
            self.assertTrue((run_dir / "COMPLETE").exists())
            # los view_hashes del ledger se RECOMPUTAN desde disco (A7: no son decorado)
            wl_hash = u["worldline_hash"]
            for instr, clave in (("layer_energy", "view_hash_energy"),
                                 ("phase_lock", "view_hash_phase")):
                candidatos = list((base / "views" / wl_hash[:16] / instr).glob("*"))
                self.assertEqual(len(candidatos), 1)
                lv = api.load_view(candidatos[0])             # recompute fail-loud
                self.assertEqual(lv["view_hash"], u[clave],
                                 f"{u['run_id']}: {clave} del ledger no es el del disco")
            # una métrica RECOMPUTADA de los arrays (A7: métricas de aire no compilan)
            lv_e = api.load_view(list((base / "views" / wl_hash[:16]
                                       / "layer_energy").glob("*"))[0])
            e_tot = lv_e["arrays"]["e_capa"].sum(axis=2)
            self.assertEqual(u["metricas"]["E0_nodo0"], float(e_tot[0, 0]),
                             f"{u['run_id']}: E0_nodo0 del ledger no sale de la vista")
        m1 = ledger["unidades"][0]["metricas"]; m2 = ledger["unidades"][1]["metricas"]
        self.assertGreater(m1["E0_nodo0"], 1e3 * max(m2["E0_nodo0"], 1e-12))
        cuerpo = (base / "LEDGER.json").read_text()
        self.assertEqual(hashlib.sha256(cuerpo.encode()).hexdigest(),
                         (base / "LEDGER.sha256").read_text().split()[0])
        # la SPEC quedó PERSISTIDA y sellada (re-ejecutable desde los papeles)
        self.assertEqual(cp.sha_json(json.loads((base / "SPEC.json").read_text())),
                         (base / "SPEC.sha256").read_text().split()[0])
        self.assertEqual(ledger["spec_sha256"],
                         (base / "SPEC.sha256").read_text().split()[0])
        type(self).ledger_base = ledger

    # ── 3 · determinismo: filas ENTERAS ──────────────────────────────────────

    def test_gate3_workers_3_bit_identico_en_filas_enteras(self):
        base = self.tmp / "c_par"
        ledger = self._correr(base, workers=3)
        self.assertEqual(ledger["unidades"], self.ledger_base["unidades"],
                         "el paralelismo cambió ALGO (física, vistas o métricas) — "
                         "PROHIBIDO")

    # ── 4 · reanudación verificada, ordenada, sin degradar ───────────────────

    def test_gate4_reanudacion_verifica_reconstruye_y_no_degrada(self):
        base = self.tmp / "c_resume"
        l1 = self._correr(base)
        # (a) interrupción simple: COMPLETE ausente en u2
        (base / "unidades" / "u2_fresh" / "COMPLETE").unlink()
        l2 = self._correr(base)
        estados = {u["run_id"]: u["estado"] for u in l2["unidades"]}
        self.assertEqual(estados, {"u1_transported": "reusada", "u2_fresh": "completa",
                                   "u3_mixta": "reusada"})
        self.assertEqual([u["run_id"] for u in l2["unidades"]],
                         ["u1_transported", "u2_fresh", "u3_mixta"],
                         "el reporte reanudado no respeta el ORDEN de la spec (M13b)")
        for u1, u2 in zip(l1["unidades"], l2["unidades"]):
            self.assertEqual(u1["worldline_hash"], u2["worldline_hash"])
            self.assertEqual(u1["metricas"], u2["metricas"],
                             f"{u1['run_id']}: la fila reanudada PERDIÓ métricas (J1)")
            self.assertEqual(u1["view_hash_energy"], u2["view_hash_energy"])
        self.assertEqual(len(list((base / "unidades").glob("restos_u2_fresh_*"))), 1)
        # (b) el LEDGER previo NO se degradó: quedó apartado (A2)
        self.assertEqual(len(list(base.glob("restos_LEDGER_*.json"))), 1)
        # (c) chunk corrupto con COMPLETE intacto ⇒ la reusa lo CAZA y se rehace (J2)
        chunk = sorted((base / "unidades" / "u1_transported" / "worldline")
                       .glob("chunk_*.npz"))[1]
        datos = bytearray(chunk.read_bytes()); datos[len(datos) // 2] ^= 0xFF
        chunk.write_bytes(bytes(datos))
        l3 = self._correr(base)
        fila1 = next(u for u in l3["unidades"] if u["run_id"] == "u1_transported")
        self.assertEqual(fila1["estado"], "completa",
                         "el film corrupto con COMPLETE intacto fue REUSADO (J2)")
        self.assertEqual(fila1["worldline_hash"], l1["unidades"][0]["worldline_hash"],
                         "la unidad rehecha no reprodujo el film (determinismo)")
        self.assertEqual(len(list((base / "unidades").glob("restos_u1_transported_*"))), 1)

    # ── 5 · una campaña no pisa otra ─────────────────────────────────────────

    def test_gate5_spec_distinta_sobre_mismo_base_rechaza(self):
        base = self.tmp / "c_pisa"
        self._correr(base)
        otra = self._spec(); otra["porque"] = "OTRA campaña con otro porqué"
        with self.assertRaisesRegex(RuntimeError, "no pisa"):
            self._correr(base, spec=otra)

    # ── 6 · contención: la unidad que falla es un DATO ───────────────────────

    def test_gate6_unidad_fallida_no_mata_el_census(self):
        base = self.tmp / "c_falla"
        s = self._spec()
        s["unidades"][2]["constituyentes"][0]["capsule_sha256"] = \
            "sha256:" + "e" * 64                              # pin equivocado: falla al cargar
        ledger = self._correr(base, spec=s)
        self.assertFalse(ledger["completa"])
        self.assertEqual(ledger["fallidas"], ["u3_mixta"])
        fila = next(u for u in ledger["unidades"] if u["run_id"] == "u3_mixta")
        self.assertEqual(fila["estado"], "fallida")
        self.assertIn("PINNEADA", fila["error"])
        self.assertEqual(fila["error_clase"], "RuntimeError")
        # las otras DOS corrieron y el LEDGER existe (J5: nada se brickea)
        for rid in ("u1_transported", "u2_fresh"):
            self.assertEqual(next(u for u in ledger["unidades"]
                                  if u["run_id"] == rid)["estado"], "completa")
        self.assertTrue((base / "LEDGER.json").exists())
        # reanudación: reintenta la fallida (falla otra vez — determinista), reusa el resto
        l2 = self._correr(base, spec=s)
        self.assertEqual({u["run_id"]: u["estado"] for u in l2["unidades"]},
                         {"u1_transported": "reusada", "u2_fresh": "reusada",
                          "u3_mixta": "fallida"})
        # ATRIBUCIÓN mentida en un NO-población (A6/J4): theta y cápsula consistentes entre
        # sí pero block_id etiquetado con OTRO bloque — A9 no aplica (no es población), el
        # único guardián es el worker: debe caer como fallida con el error declarado
        s2 = self._spec()
        s2["unidades"][2]["constituyentes"][0]["block_id"] = self.bids[1]   # miente
        ledger2 = self._correr(self.tmp / "c_swap", spec=s2)
        fila_sw = next(u for u in ledger2["unidades"] if u["run_id"] == "u3_mixta")
        self.assertEqual(fila_sw["estado"], "fallida")
        self.assertIn("swapeada", fila_sw["error"],
                      "la atribución mentida de un no-población pasó sin ruido (A6/J4)")

    # ── 7 · archivado atómico verificado ─────────────────────────────────────

    def test_gate7_archivado_atomico_fault_injection_y_no_pisa(self):
        base = self.tmp / "c_arch"
        destino = self.tmp / "externo" / "c_arch"
        self._correr(base, archivar_en=destino)
        self.assertTrue((destino / "ARCHIVADO.json").exists())
        self.assertTrue((destino / "LEDGER.json").exists())
        self.assertTrue((destino / "SPEC.json").exists())
        self.assertFalse(destino.with_name(destino.name + ".tmp_archivo").exists(),
                         "quedó un tmp huérfano tras archivar")
        with self.assertRaisesRegex(RuntimeError, "no se pisa"):
            cp._archivar(base, destino)
        # fault-injection (A8): la copia se corrompe ⇒ la verificación DEBE reventar
        destino2 = self.tmp / "externo" / "c_arch2"
        real_copytree = shutil.copytree

        def copytree_corrupto(src, dst, *args, **kw):
            r = real_copytree(src, dst, *args, **kw)
            # copytree recursa por el nombre del módulo: corromper SOLO en el top-level
            if str(dst).endswith(".tmp_archivo"):
                victima = sorted(Path(dst).rglob("chunk_*.npz"))[0]
                datos = bytearray(victima.read_bytes()); datos[0] ^= 0xFF
                victima.write_bytes(bytes(datos))
            return r
        with mock.patch.object(shutil, "copytree", side_effect=copytree_corrupto):
            with self.assertRaisesRegex(RuntimeError, "FALLÓ la verificación"):
                cp._archivar(base, destino2)

    # ── 8 · spec-pins y golden values ────────────────────────────────────────

    def test_gate8a_sha_json_invariante_al_orden(self):
        self.assertEqual(cp.sha_json({"a": 1, "b": 2}), cp.sha_json({"b": 2, "a": 1}))
        self.assertEqual(cp.sha_json({"x": {"b": 1, "a": 2}, "y": [1, 2]}),
                         cp.sha_json({"y": [1, 2], "x": {"a": 2, "b": 1}}))
        self.assertNotEqual(cp.sha_json({"a": 1}), cp.sha_json({"a": 2}))

    def test_gate8b_sha_file_mas_alla_del_primer_MB(self):
        a = self.tmp / "a.bin"; b = self.tmp / "b.bin"
        cuerpo = bytearray(2 * (1 << 20))
        a.write_bytes(bytes(cuerpo))
        cuerpo[(1 << 20) + 7] = 0xFF                          # difiere SOLO tras el MB 1
        b.write_bytes(bytes(cuerpo))
        self.assertNotEqual(cp._sha_file(a), cp._sha_file(b),
                            "_sha_file no ve más allá del primer MB (M19)")
        self.assertEqual(cp._sha_file(a),
                         hashlib.sha256(a.read_bytes()).hexdigest())

    def test_gate8c_metricas_golden_sinteticas(self):
        dt = 1e-3
        n = 3000
        e = np.zeros((n, 2, 3)); e[:, 0, 0] = np.linspace(100.0, 0.0, n)
        r = np.zeros(n); ov = np.zeros(n, dtype=bool)
        # cruce BREVE (999 < ventana 1000) ⇒ t_lock None (M18: primer-cruce simple no vale)
        r[100:1099] = 0.995
        met = cp.metricas_basicas_v1(e, r, ov, dt)
        self.assertIsNone(met["t_lock_tick"], "un cruce de 999 ticks NO es lock sostenido")
        # cruce SOSTENIDO (1000 exactos) ⇒ t_lock en el arranque del cruce
        r2 = np.zeros(n); r2[500:1500] = 0.999
        met2 = cp.metricas_basicas_v1(e, r2, ov, dt)
        self.assertEqual(met2["t_lock_tick"], 500)
        # decaimiento lineal 100→0: t_half exacto en el primer tick ≤ 50
        esperado = int(np.where(e[:, 0, 0] <= 50.0)[0][0])
        self.assertEqual(met2["t_half_tick"], esperado)
        # n=1 ⇒ R identidad por construcción: None DECLARADO (F4 NO-CUBIERTO 4)
        met1 = cp.metricas_basicas_v1(e[:, :1, :], r2, ov, dt)
        self.assertIsNone(met1["t_lock_tick"])
        self.assertIsNone(met1["R_max"])
        self.assertIn("identidad", met1["nota_n1"])

    def test_gate8d_atomicidad_y_spawn_pinneados(self):
        base = self.tmp / "c_pins"
        with mock.patch.object(cp, "_escribir_atomico",
                               wraps=cp._escribir_atomico) as escr, \
             mock.patch.object(cp.mp, "get_context",
                               wraps=cp.mp.get_context) as ctx:
            self._correr(base, workers=2)
        destinos = {Path(c.args[0]).name for c in escr.call_args_list}
        self.assertIn("LEDGER.json", destinos,
                      "el LEDGER no pasó por la escritura atómica (M14)")
        self.assertIn("SPEC.json", destinos)
        self.assertEqual([c.args for c in ctx.call_args_list], [("spawn",)],
                         "el pool no pinnea spawn (M21: fork hereda estado)")
        self.assertFalse(list(base.glob("*.tmp")), "tmp huérfano tras la campaña")

    def test_gate8f_cache_de_vistas_corrupto_muere_en_el_worker(self):
        """El worker RE-verifica las vistas desde disco (load_view): si el caché se corrompe
        entre write y verificación, la unidad FALLA — sin load_view (M10) esto pasa verde."""
        from study07.instruments.api import View
        real_write = View.write

        def write_corrupto(self_v, views_root):
            p = real_write(self_v, views_root)
            datos = bytearray((p / "data.npz").read_bytes())
            datos[len(datos) // 2] ^= 0xFF
            (p / "data.npz").write_bytes(bytes(datos))
            return p
        with mock.patch.object(View, "write", write_corrupto):
            ledger = self._correr(self.tmp / "c_vistas")
        self.assertEqual(len(ledger["fallidas"]), 3,
                         "vistas corruptas en disco NO mataron a las unidades (M10: "
                         "el caché no se re-verifica)")
        # el fallo viene del camino load_view (hash recomputado o npz ilegible)
        self.assertRegex(ledger["unidades"][0]["error"], "view_hash|CRC|no se puede")

    def test_gate8e_preflight_de_disco(self):
        Uso = type("Uso", (), {})
        falso = Uso(); falso.free = 100 * 1024; falso.total = 0; falso.used = 0
        with mock.patch.object(cp.shutil, "disk_usage", return_value=falso):
            with self.assertRaisesRegex(RuntimeError, "preflight de DISCO"):
                self._correr(self.tmp / "c_disco")


if __name__ == "__main__":
    unittest.main()
