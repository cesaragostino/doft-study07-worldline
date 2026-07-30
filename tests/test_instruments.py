"""GATES F4 — el primer instrumento offline (plan §20.9 Fase 4) + refuerzos del double tap.

A.  La vista de FASE reproduce la referencia del oráculo (theta/z/R/J/omega calculados ONLINE
    por el motor de Study06 con SUS funciones) leyendo SÓLO la worldline. Dos niveles.
A2. El VEREDICTO (r_min) sobre el MISMO film con umbral 0.99: ambas ramas pobladas, NaN en la
    banda inválida (el nulo del instrumento se ejercita — F4 A2).
B.  La vista de ENERGÍA reproduce las energías por capa del oráculo; su ventana declarada se
    HONRA (recorte bit-exacto — F4 A5) y su constitución se verifica por huella.
C.  LA DEMO FUNDACIONAL: tres configs sobre la MISMA película, mismo worldline_hash, config_hash
    distinto, SIN re-simular — y las vistas derivadas se comparan EXACTAS canal por canal
    (recorte y decimación de r/j/z/omega/ticks; J estriado contra referencia escalar
    independiente con dt_ef — F4 A1).
D.  Caché EN DISCO: write→load_view reproduce hash y arrays bit-exactos; el hash es estable
    ante write (idempotente); ata el CONTENIDO; el pisado con otro contenido es rechazo (F4 A3).
E.  Canal ausente ⇒ FALLA (phase Y energy); constitución equivocada ⇒ FALLA (F4 A5).
F.  La vista declara TODO: config con defaults resueltos (r_min=0.08 SIN override — mata el
    default mutado), taxonomía dato/inferencia/veredicto, hash del film.
G.  IDENTIDAD del film: worldline_hash = sha256(sha_total ‖ manifest_sha), atado al close()
    del recorder; films distintos ⇒ hashes distintos; editar el manifiesto cambia la
    identidad (F4 A4 — la colisión dt×2 muere acá).
H.  Ventanas malformadas y claves desconocidas ⇒ error de contrato; film INCOMPLETO no se
    observa sin flag explícito declarado en la config (F4 A8).
I.  Film HETEROGÉNEO (2 nodos, layouts distintos): el layout por nodo del manifiesto es el de
    CADA nodo y phase lo usa — deja de testearse vacuamente (F4 A9).
J.  eps_den es LOAD-BEARING en un film sintético con dt=1e-13: la config declarada se USA,
    no sólo se declara (F4/M05b).

La worldline de trabajo se genera UNA vez por clase con el motor de study07 (misma composición
f6, 1500 ticks) — después de eso, el motor no se toca más: todo es lectura.
"""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from study07.artifacts.recorder import WorldlineRecorder, load_worldline
from study07.artifacts.runner import run as run_net
from study07.instruments import api, energy, phase
from test_worldline_checkpoint import MAN, _f6_net

REPO = Path(__file__).resolve().parents[1]
F6 = REPO / "tests/fixtures/study07_f6_regimen_caliente.npz"
F7 = REPO / "tests/fixtures/study07_f7_observables_ref.npz"
# ancla SELLADA de la referencia (patrón f1-f5): regenerar f7 exige re-sellar acá, a la vista
F7_SHA_SELLADA = "f415e3f964b2ca9b1c15cef0a68cf55fdcda3e522f6d6bbb0c2837eee173d844"
TOL = 3.8579e-11


def _pinned(meta7):
    import platform
    return (np.__version__ == meta7.get("numpy") and platform.machine() == meta7.get("machine"))


def _j_omega_espejo(z_arr, r_arr, dt_ef, eps_den, r_min):
    """Referencia escalar INDEPENDIENTE del instrumento (misma aritmética del oráculo):
    J[k]=Im(conj(z_k)·(z_k−z_{k−1})/max(dt_ef,eps)), J[0]=0; omega=J/max(r²,eps) si válido."""
    n = len(z_arr)
    j_ref = np.empty(n); om_ref = np.empty(n); val_ref = np.empty(n, dtype=bool)
    for k in range(n):
        z_val = z_arr[k]
        last = z_arr[k - 1] if k > 0 else 0j
        dz = (z_val - last) / max(float(dt_ef), eps_den) if k > 0 else 0.0 + 0.0j
        jv = float(np.imag(np.conj(z_val) * dz))
        rv = float(r_arr[k])
        ok = bool(np.isfinite(rv) and rv >= float(r_min))
        j_ref[k], val_ref[k] = jv, ok
        om_ref[k] = (jv / max(rv * rv, eps_den)) if ok else float("nan")
    return j_ref, om_ref, val_ref


class TestInstrumentos(unittest.TestCase):
    """La worldline se graba UNA vez (setUpClass); los gates son todos lecturas."""

    @classmethod
    def setUpClass(cls):
        # ANCLAS DE PROCEDENCIA (F4 A6): la cadena f6→f7 se VERIFICA, no se asume
        sha_f7 = hashlib.sha256(F7.read_bytes()).hexdigest()
        sidecar = (REPO / "tests/fixtures/study07_f7.sha256").read_text().split()[0]
        if not (sha_f7 == sidecar == F7_SHA_SELLADA):
            raise RuntimeError(f"f7 no coincide con su sello: disco={sha_f7[:12]} "
                               f"sidecar={sidecar[:12]} sellado={F7_SHA_SELLADA[:12]} — "
                               "referencia stale o adulterada (fail-loud de procedencia)")
        cls.ref = np.load(F7, allow_pickle=False)
        cls.meta7 = json.loads(str(cls.ref["meta_json"]))
        sha_f6 = hashlib.sha256(F6.read_bytes()).hexdigest()
        if cls.meta7["f6_sha256"] != sha_f6:
            raise RuntimeError("el f6 en disco NO es el que generó la referencia f7 — "
                               "regenerar f7 o restaurar f6 (fail-loud de procedencia)")
        cls.tmp = Path(tempfile.mkdtemp())
        net, specs, meta6 = _f6_net()
        cls.meta6 = meta6
        rec = WorldlineRecorder(cls.tmp / "run", net, dict(MAN), chunk_ticks=256)
        run_net(net, int(cls.meta7["ticks"]), recorder=rec)
        cls.sha_total = rec.close()
        cls.wl = api.load_run(cls.tmp / "run")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _assert_nivel(self, d, nombre):
        if _pinned(self.meta7):
            self.assertEqual(d, 0.0, f"{nombre}: en el entorno del generador debe ser 0.0 "
                                     f"exacto (midió {d:.3e})")
        else:
            print(f"[F4] ENTORNO NO PINEADO (numpy/machine != generador de f7): gate de "
                  f"{nombre} degradado de 0.0-exacto a TOL={TOL:.3e} — DECLARADO, no silencioso")
            self.assertLessEqual(d, TOL, nombre)

    def test_gateA_fase_reproduce_al_oraculo(self):
        v = phase.run(self.wl)
        for canal, ref in (("theta", self.ref["theta"]), ("z", self.ref["z"]),
                           ("r", self.ref["r"]), ("j", self.ref["j"])):
            d = float(np.max(np.abs(v.arrays[canal] - ref)))
            print(f"[F4:fase] {canal}: max|d|={d:.3e}")
            self._assert_nivel(d, canal)
        # omega tiene NaN donde no es válido: comparar validez + valores válidos
        np.testing.assert_array_equal(v.arrays["omega_valid"], self.ref["omega_valid"])
        m = self.ref["omega_valid"]
        d = float(np.max(np.abs(v.arrays["omega"][m] - self.ref["omega"][m]))) if m.any() else 0.0
        print(f"[F4:fase] omega(valida): max|d|={d:.3e} ({int(m.sum())}/{len(m)})")
        self._assert_nivel(d, "omega")

    def test_gateA2_veredicto_r_min_ambas_ramas(self):
        """El NULO del instrumento (F4 A2): r∈[0.60,1.00] en este film ⇒ r_min=0.99 puebla las
        DOS ramas del veredicto. omega_valid conmuta con el umbral y la banda inválida es NaN."""
        v = phase.run(self.wl, {"r_min": 0.99})
        esperado = self.ref["r"] >= 0.99
        n_val, n_inv = int(esperado.sum()), int((~esperado).sum())
        print(f"[F4:fase] r_min=0.99: validos={n_val} invalidos={n_inv}")
        self.assertGreater(n_val, 0, "escenario vacuo: ningún tick válido con r_min=0.99")
        self.assertGreater(n_inv, 0, "escenario vacuo: ningún tick inválido con r_min=0.99 — "
                                     "el veredicto no se ejercita")
        np.testing.assert_array_equal(v.arrays["omega_valid"], esperado)
        self.assertTrue(np.isnan(v.arrays["omega"][~esperado]).all(),
                        "la banda inválida debe ser NaN, no un número disfrazado")
        d = float(np.max(np.abs(v.arrays["omega"][esperado] - self.ref["omega"][esperado])))
        self._assert_nivel(d, "omega@r_min=0.99")

    def test_gateB_energia_reproduce_al_oraculo(self):
        v = energy.run(self.wl, self.meta6["thetas_embebidos"])
        d = float(np.max(np.abs(v.arrays["e_capa"] - self.ref["e_capa"])))
        print(f"[F4:energia] e_capa: max|d|={d:.3e}")
        self._assert_nivel(d, "e_capa")

    def test_gateB2_energia_honra_su_ventana(self):
        """F4 A5: la ventana DECLARADA se USA — recorte+decimación bit-exactos del canal."""
        full = energy.run(self.wl, self.meta6["thetas_embebidos"])
        ve = energy.run(self.wl, self.meta6["thetas_embebidos"],
                        {"t0_tick": 500, "t1_tick": 1000, "stride": 5})
        np.testing.assert_array_equal(ve.arrays["e_capa"], full.arrays["e_capa"][500:1001:5])
        np.testing.assert_array_equal(ve.arrays["ticks"], full.arrays["ticks"][500:1001:5])

    def test_gateC_demo_fundacional_tres_ventanas_sin_resimular(self):
        """Lo que en Study06 costaba re-integrar 4.8h: acá son LECTURAS. Y las vistas derivadas
        se comparan EXACTAS canal por canal (F4 A1) — no sólo theta."""
        dt = float(self.meta7["dt"])
        va = phase.run(self.wl)                                        # ventana completa
        vb = phase.run(self.wl, {"t0_tick": 500, "t1_tick": 1000})     # sub-ventana
        vc = phase.run(self.wl, {"stride": 5})                         # otra cadencia
        self.assertEqual(va.manifest["worldline_hash"], vb.manifest["worldline_hash"])
        self.assertEqual(va.manifest["worldline_hash"], vc.manifest["worldline_hash"])
        self.assertNotEqual(va.manifest["config_hash"], vb.manifest["config_hash"])
        self.assertNotEqual(va.manifest["config_hash"], vc.manifest["config_hash"])
        # SUB-VENTANA: recorte bit-exacto de dato e inferencia (no sólo theta)
        for canal, corte in (("theta", np.s_[500:1001]), ("z", np.s_[500:1001]),
                             ("r", np.s_[500:1001]), ("ticks", np.s_[500:1001])):
            np.testing.assert_array_equal(vb.arrays[canal], va.arrays[canal][corte],
                                          err_msg=f"sub-ventana: {canal} no es recorte exacto")
        # J en el borde de ventana: J[0]=0 por construcción; del tick 1 en adelante = recorte
        self.assertEqual(float(vb.arrays["j"][0]), 0.0)
        np.testing.assert_array_equal(vb.arrays["j"][1:], va.arrays["j"][501:1001])
        np.testing.assert_array_equal(vb.arrays["omega_valid"], va.arrays["omega_valid"][500:1001])
        mask = vb.arrays["omega_valid"][1:]
        np.testing.assert_array_equal(vb.arrays["omega"][1:][mask],
                                      va.arrays["omega"][501:1001][mask])
        self.assertTrue(np.isnan(vb.arrays["omega"][1:][~mask]).all())
        # DECIMACIÓN: dato decimado exacto; J/omega estriados = OTRO estimador (dt_ef=5·dt),
        # comparados contra una referencia escalar INDEPENDIENTE construida en el test
        for canal in ("theta", "z", "r", "ticks"):
            np.testing.assert_array_equal(vc.arrays[canal], va.arrays[canal][::5],
                                          err_msg=f"decimación: {canal} no es va[::5]")
        j_ref, om_ref, val_ref = _j_omega_espejo(va.arrays["z"][::5], va.arrays["r"][::5],
                                                 5 * dt, 1e-12, 0.08)
        np.testing.assert_array_equal(vc.arrays["j"], j_ref,
                                      err_msg="J estriado != referencia escalar con dt_ef=5·dt")
        np.testing.assert_array_equal(vc.arrays["omega_valid"], val_ref)
        np.testing.assert_array_equal(vc.arrays["omega"][val_ref], om_ref[val_ref])
        self.assertTrue(np.isnan(vc.arrays["omega"][~val_ref]).all() if (~val_ref).any()
                        else True)
        # y las tres se escriben bajo el MISMO árbol del film
        with tempfile.TemporaryDirectory() as td:
            pa = va.write(Path(td)); pb = vb.write(Path(td)); pc = vc.write(Path(td))
            self.assertEqual(pa.parent.parent, pb.parent.parent)
            self.assertEqual(len({pa, pb, pc}), 3)

    def test_gateD_cache_en_disco_reproduce_y_no_se_pisa(self):
        """F4 A3: el caché ESCRITO se relee y verifica — no recompute-vs-recompute en RAM."""
        v1 = phase.run(self.wl, {"stride": 3})
        h1 = v1.view_hash()
        self.assertEqual(h1, phase.run(self.wl, {"stride": 3}).view_hash(),
                         "recomputar una vista debe reproducir su hash")
        # el hash ata el CONTENIDO: mutar un array lo cambia
        v_mut = phase.run(self.wl, {"stride": 3})
        v_mut.arrays["theta"][0, 0] += 1e-9
        self.assertNotEqual(v_mut.view_hash(), h1, "view_hash ignora los arrays: no ata contenido")
        with tempfile.TemporaryDirectory() as td:
            p = v1.write(Path(td))
            # write NO muta el hash base (idempotencia — antes el hash se hasheaba a sí mismo)
            self.assertEqual(v1.view_hash(), h1, "write() mutó el view_hash del objeto")
            p2 = v1.write(Path(td))                       # re-write mismo contenido: OK
            self.assertEqual(p, p2)
            en_disco = json.loads((p / "manifest.json").read_text())["view_hash"]
            self.assertEqual(en_disco, h1, "el hash sellado en disco difiere del recompute")
            # LECTOR-VERIFICADOR: arrays bit-exactos, dtypes intactos, hash recomputado de DISCO
            lv = api.load_view(p)
            self.assertEqual(lv["view_hash"], h1)
            for k, arr in v1.arrays.items():
                self.assertEqual(lv["arrays"][k].dtype, arr.dtype, f"{k}: dtype degradado")
                np.testing.assert_array_equal(lv["arrays"][k], arr,
                                              err_msg=f"{k}: el caché no reproduce la vista")
            # adulterar el data.npz ⇒ load_view FALLA fuerte
            np.savez_compressed(p / "data.tmp.npz",
                                **{k: a.astype(np.float32) if a.dtype == np.float64 else a
                                   for k, a in v1.arrays.items()})
            (p / "data.tmp.npz").rename(p / "data.npz")
            with self.assertRaises(RuntimeError):
                api.load_view(p)
            # restaurar y verificar que el pisado con OTRO contenido es rechazo
            np.savez_compressed(p / "data.tmp.npz", **v1.arrays)
            (p / "data.tmp.npz").rename(p / "data.npz")
            with self.assertRaises(RuntimeError):
                v_mut.write(Path(td))                     # misma config, otro contenido

    def test_gateE_canal_ausente_y_constitucion_equivocada_fallan(self):
        wl_mutilada = dict(self.wl)
        wl_mutilada["estados"] = []
        with self.assertRaises(RuntimeError):
            phase.run(wl_mutilada)
        with self.assertRaises(RuntimeError):
            energy.run(wl_mutilada, self.meta6["thetas_embebidos"])
        # constitución: cantidad equivocada
        with self.assertRaises(RuntimeError):
            energy.run(self.wl, self.meta6["thetas_embebidos"][:2])
        # constitución con OTRA física (masa×2): fail-loud por huella, jamás silencioso (A5)
        thetas_mal = copy.deepcopy(self.meta6["thetas_embebidos"])
        thetas_mal[0]["modes"][0]["mass"] *= 2.0
        with self.assertRaises(RuntimeError):
            energy.run(self.wl, thetas_mal)
        # nodos PERMUTADOS: fail-loud (los nodos del f6 tienen masas distintas)
        t = self.meta6["thetas_embebidos"]
        with self.assertRaises(RuntimeError):
            energy.run(self.wl, [t[1], t[0], t[2]])

    def test_gateF_config_en_el_manifiesto_de_la_vista(self):
        """La vista declara TODO: config completa (con defaults resueltos), hash del film,
        instrumento+versión, taxonomía de canales — nada implícito."""
        v = phase.run(self.wl, {"r_min": 0.10})
        self.assertEqual(v.manifest["observation_config"]["r_min"], 0.10)
        self.assertEqual(v.manifest["observation_config"]["eps_den"], 1e-12)
        self.assertEqual(v.manifest["instrument_id"], "phase_lock")
        self.assertIn("worldline_hash", v.manifest)
        # los DEFAULTS sin override son los del oráculo (mata el default mutado — F4/M04)
        v0 = phase.run(self.wl)
        self.assertEqual(v0.manifest["observation_config"]["r_min"], 0.08)
        self.assertEqual(v0.manifest["observation_config"]["eps_den"], 1e-12)
        self.assertEqual(v0.manifest["observation_config"]["stride"], 1)
        # taxonomía dato/inferencia/veredicto (INSTRUMENT_CONTRACT, forma ejecutable)
        self.assertTrue(v0.manifest["canales"]["omega_valid"].startswith("veredicto"))
        self.assertTrue(v0.manifest["canales"]["theta"].startswith("dato"))
        self.assertTrue(v0.manifest["canales"]["j"].startswith("inferencia"))
        ve = energy.run(self.wl, self.meta6["thetas_embebidos"])
        self.assertTrue(ve.manifest["canales"]["e_capa"].startswith("inferencia"))

    def test_gateG_identidad_del_film(self):
        """F4 A4: la identidad se MIDE — atada al close() del recorder y al manifiesto que los
        instrumentos leen. La colisión dt×2 (mismos chunks, otro manifiesto) muere acá."""
        marca = json.loads((self.tmp / "run" / "COMPLETE").read_text())
        self.assertEqual(marca["sha_total"], self.sha_total,
                         "el COMPLETE no registra lo que close() devolvió")
        esperado = hashlib.sha256(
            (marca["sha_total"] + marca["manifest_sha"]).encode("utf-8")).hexdigest()
        self.assertEqual(self.wl["worldline_hash"], esperado,
                         "worldline_hash no es sha256(sha_total ‖ manifest_sha)")
        with tempfile.TemporaryDirectory() as td:
            # film DISTINTO (menos ticks) ⇒ identidad distinta
            net2, _, _ = _f6_net()
            rec2 = WorldlineRecorder(Path(td) / "corto", net2, dict(MAN), chunk_ticks=16)
            run_net(net2, 30, recorder=rec2)
            rec2.close()
            self.assertNotEqual(api.worldline_hash(Path(td) / "corto"),
                                self.wl["worldline_hash"])
            # MISMOS chunks, manifiesto editado coherentemente ⇒ OTRA identidad (no colisión)
            runb = Path(td) / "runB"
            shutil.copytree(self.tmp / "run", runb)
            man = json.loads((runb / "manifest.json").read_text())
            man["dt"] = 2.0 * float(man["dt"])
            cuerpo = json.dumps(man, indent=1, default=str)
            (runb / "manifest.json").write_text(cuerpo)
            marca_b = json.loads((runb / "COMPLETE").read_text())
            marca_b["manifest_sha"] = hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()
            (runb / "COMPLETE").write_text(json.dumps(marca_b, indent=1))
            wl_b = api.load_run(runb)                      # coherente: carga
            self.assertEqual(marca_b["sha_total"], marca["sha_total"], "chunks idénticos")
            self.assertNotEqual(wl_b["worldline_hash"], self.wl["worldline_hash"],
                                "dt×2 con los mismos chunks NO puede compartir identidad")

    def test_gateH_ventanas_malformadas_y_film_incompleto(self):
        """F4 A8: la ventana es parte de la interfaz — se valida, no se wrapea."""
        for cfg_mala in ({"t0_tick": -1}, {"t0_tick": 50, "t1_tick": 10},
                         {"t1_tick": 99999}, {"stride": 0}, {"stride": -1}):
            with self.assertRaises(RuntimeError, msg=f"config {cfg_mala} debía fallar"):
                phase.run(self.wl, cfg_mala)
            with self.assertRaises(RuntimeError, msg=f"config {cfg_mala} debía fallar"):
                energy.run(self.wl, self.meta6["thetas_embebidos"], cfg_mala)
        # clave desconocida (typo) = error de contrato, jamás una config declarada
        with self.assertRaises(RuntimeError):
            phase.run(self.wl, {"r_mim": 0.99})
        with self.assertRaises(RuntimeError):
            energy.run(self.wl, self.meta6["thetas_embebidos"], {"strid": 5})
        # film INCOMPLETO: no se observa por defecto; auditoría de restos = flag DECLARADO
        with tempfile.TemporaryDirectory() as td:
            net3, _, _ = _f6_net()
            rec3 = WorldlineRecorder(Path(td) / "trunco", net3, dict(MAN), chunk_ticks=8)
            for _ in range(20):
                net3.step()
                rec3.record_step()
            # SIN close(): interrupción
            wl_t = load_worldline(Path(td) / "trunco", allow_incomplete=True)
            wl_t["worldline_hash"] = "a" * 64
            with self.assertRaises(RuntimeError):
                phase.run(wl_t)
            v = phase.run(wl_t, {"permitir_incompleto": True})
            self.assertTrue(v.manifest["observation_config"]["permitir_incompleto"])
            self.assertEqual(v.arrays["theta"].shape[0], 16,     # 2 chunks flusheados de 8
                             "la auditoría de restos ve SOLO lo flusheado, declarado")

    def test_gateI_film_heterogeneo_layout_por_nodo(self):
        """F4 A9: dos nodos con layouts DISTINTOS — el manifiesto lleva el layout de CADA nodo
        y phase lo usa. Con población homogénea este gate era vacuo (mutante nodo-0 vivía)."""
        from study07.compat.study06_v4 import birth_state, parse_theta_v2
        from study07.engine.network import Network
        th_a = copy.deepcopy(self.meta6["thetas_embebidos"][0])
        th_b = copy.deepcopy(self.meta6["thetas_embebidos"][1])
        # heterogeneidad REAL: el orden de los modos define el layout del estado; mover el
        # último modo (S2) al frente cambia capas_por_modo sin tocar la física declarada
        # (las referencias intra/inter van por (layer, index), no por posición)
        th_b["modes"] = [th_b["modes"][-1]] + th_b["modes"][:-1]
        specs, states = [], []
        for idx, th in enumerate((th_a, th_b)):
            sp, _ = parse_theta_v2(th, emission_scale=1.0 / max(len(th["modes"]), 1))
            specs.append(sp)
            states.append(birth_state(sp, seed=99, idx=idx))
        layouts = [[m.layer.name for m in sp.modes] for sp in specs]
        self.assertNotEqual(layouts[0], layouts[1],
                            "escenario vacuo: los layouts no difieren — el gate no protege nada")
        ep = self.meta6["engine_params"]
        net = Network(specs, states,
                      [{"i": 0, "j": 1, "w_k": 1.0, "w_gamma": 0.5, "tau": 0.02}],
                      dt=float(self.meta6["dt"]), seed=99,
                      k_global=float(ep["kappa_global"]),
                      coupling_gamma_c=float(ep["coupling_gamma_c"]))
        with tempfile.TemporaryDirectory() as td:
            rec = WorldlineRecorder(Path(td) / "het", net, dict(MAN), chunk_ticks=16)
            run_net(net, 40, recorder=rec)
            rec.close()
            wl = api.load_run(Path(td) / "het")
        for j, sp in enumerate(specs):
            self.assertEqual(wl["manifest"]["por_nodo"][j]["capas_por_modo"], layouts[j],
                             f"nodo {j}: el manifiesto no lleva SU layout (film no "
                             "auto-suficiente — el hallazgo del juez F3 sigue abierto)")
        v = phase.run(wl)
        # referencia directa desde los SPECS (no desde el manifiesto): theta por nodo
        for j, sp in enumerate(specs):
            qi = np.array([k for k, m in enumerate(sp.modes) if m.layer.name == "Q"], dtype=int)
            n = sp.n_modes
            est = wl["estados"][j]
            esperada = np.arctan2(est[:, n + qi].sum(axis=1), est[:, qi].sum(axis=1))
            np.testing.assert_array_equal(v.arrays["theta"][:, j], esperada,
                                          err_msg=f"nodo {j}: theta no sale de SU layout")

    def test_gateJ_eps_den_es_load_bearing(self):
        """F4/M05b: con dt=1e-13 el divisor de dZ/dt es max(dt_ef, eps_den)=eps_den — el valor
        DECLARADO en la config decide J. Un eps_den hardcodeado distinto cambia J en órdenes."""
        t = np.arange(6, dtype=np.float64)
        x = np.cos(0.3 * t); vv = np.sin(0.3 * t)
        est = np.stack([x, vv], axis=1)                    # 1 nodo, 1 modo Q: [x, v]
        wl_sint = {"manifest": {"dt": 1e-13, "n_nodes": 1,
                                "por_nodo": [{"n_modes": 1, "capas_por_modo": ["Q"]}]},
                   "ticks": np.arange(6), "estados": [est],
                   "worldline_hash": "b" * 64, "complete": True}
        v = phase.run(wl_sint)
        theta = np.arctan2(vv, x)
        z = np.empty(6, dtype=complex)
        for k in range(6):
            z[k] = complex(np.mean(np.exp(1j * np.array([theta[k]]))))
        r = np.array([float(abs(z[k])) for k in range(6)])
        j_ref, om_ref, val_ref = _j_omega_espejo(z, r, 1e-13, 1e-12, 0.08)
        self.assertGreater(float(np.max(np.abs(j_ref))), 1e10,
                           "escenario vacuo: J no está en el régimen donde eps_den decide")
        np.testing.assert_array_equal(v.arrays["j"], j_ref,
                                      err_msg="J no usa el eps_den DECLARADO (config≠cómputo)")
        np.testing.assert_array_equal(v.arrays["omega"][val_ref], om_ref[val_ref])


if __name__ == "__main__":
    unittest.main()
