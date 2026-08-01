"""GATES del instrumento de PAR (etapa 0 del norte del link) — nacidos endurecidos.

La referencia acá es ANALÍTICA (films sintéticos con física conocida de antemano — no hay
oráculo de pares) + el film REAL f8 + coherencia con el instrumento de fase:

1. LOCK CON DESFASE (la lección §16): dos nodos a la MISMA ω con desfase π/2 — la fase
   cruda es elíptica y castigaría el lock (rw≈0.43 medía el panel); el instrumento con
   corrección debe dar FIRME con rw_final ≥ 0.999. KILL del mutante sin-corrección.
2. DERIVA PURA: Δω conocido ≫ punto ciego ⇒ MUERTO, 0 episodios, y rw_final ≈
   |sinc(Δω·W/2)| ANALÍTICO (ancla la mecánica de ventana, tolerancia declarada).
3. COQUETEO: lock por tramos construido ⇒ estado coqueteo, episodios contados bien
   (kill de off-by-one del contador de rachas).
4. t_lock: deriva → lock en t* conocido ⇒ t_lock ∈ [t*, t* + sostén + resolución].
5. PULLING: convergencia de ω construida ⇒ dw_tardia < dw_temprana/2.
6. PORTADORA_FFT: coseno puro a ω conocida ⇒ pico a ±resolución; y NO el punto fijo
   −2ω²/(1+ω²) del estimador viejo (kill del regreso del artefacto §15).
7. FILM REAL f8: theta del par == theta de fase BIT-exacto (un solo camino de extracción);
   flags coherentes con los umbrales declarados; vista se escribe/relee.
8. CONTRATO: stride=1 exigido, film corto rechazado, config whitelist, umbrales default
   con procedencia, punto ciego declarado en el manifiesto.
"""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from study07.instruments import api, par, phase

REPO = Path(__file__).resolve().parents[1]
F8 = REPO / "tests/fixtures/study07_f8_transporte.npz"
CAPS_DIR = REPO / "tests/fixtures/f8_capsulas"

DT = 8e-5


def _wl_sintetico(thetas_deseadas, dt=DT):
    """Film sintético de nodos 1-modo-Q: estados [x, v] = [cos θ, −sin θ] genera la fase
    ELÍPTICA real atan2(v·(−ω̂ implícito)...) — acá construimos x=cos(θ), v=d/dt cos(θ)
    para que atan2(v, x) tenga la distorsión REAL del estimador (la que la corrección
    §16 debe planchar)."""
    n_t = len(thetas_deseadas[0])
    estados = []
    for th in thetas_deseadas:
        x = np.cos(th)
        v = np.gradient(x, dt)               # v físico ⇒ atan2(v,x) elíptico de verdad
        estados.append(np.stack([x, v], axis=1))
    man = {"dt": dt, "n_nodes": len(estados),
           "por_nodo": [{"n_modes": 1, "capas_por_modo": ["Q"]}] * len(estados)}
    return {"manifest": man, "ticks": np.arange(n_t), "estados": estados,
            "worldline_hash": "s" * 64, "complete": True}


class TestParSintetico(unittest.TestCase):

    def test_gate1_lock_con_desfase_es_FIRME(self):
        """Dos nodos a la MISMA ω, desfase π/2, 30 u.t. — el caso que el estimador viejo
        castigaba (rw≈0.43, §16). Con corrección: FIRME, rw≥0.999."""
        t = np.arange(int(30 / DT)) * DT
        w = 6.2
        wl = _wl_sintetico([w * t, w * t - np.pi / 2])
        v = par.run(wl)
        self.assertEqual(int(v.arrays["estado"][0]), 2, "lock con desfase NO dio firme")
        self.assertGreaterEqual(float(v.arrays["rw_final"][0]), 0.999,
                                f"rw_final={v.arrays['rw_final'][0]:.4f}: la corrección "
                                "de fase §16 no plancha el desfase (¿volvió el artefacto?)")
        self.assertAlmostEqual(abs(float(v.arrays["dphi_final"][0])), np.pi / 2, places=2)
        self.assertFalse(np.isnan(v.arrays["t_lock_ut"][0]))

    def test_gate2_deriva_pura_es_MUERTO_y_sinc(self):
        """Δω=3 rad/u.t. ≫ punto ciego (2π/4≈1.57): MUERTO, 0 episodios, y la mecánica de
        ventana es la ANALÍTICA: rw ≈ |sinc(Δω·W/2π·π)| (tolerancia 0.05 declarada por la
        distorsión elíptica residual)."""
        t = np.arange(int(30 / DT)) * DT
        dw = 3.0
        wl = _wl_sintetico([6.2 * t, (6.2 + dw) * t])
        v = par.run(wl)
        self.assertEqual(int(v.arrays["estado"][0]), 0, "deriva pura no dio muerto")
        self.assertEqual(int(v.arrays["episodios"][0]), 0)
        self.assertTrue(np.isnan(float(v.arrays["t_lock_ut"][0])))
        w_ut = 4.0
        esperado = abs(np.sinc(dw * w_ut / (2 * np.pi)))
        self.assertLess(abs(float(v.arrays["rw_final"][0]) - esperado), 0.05,
                        f"rw={v.arrays['rw_final'][0]:.3f} vs sinc={esperado:.3f}: la "
                        "mecánica de ventana no es la declarada")
        # pulling nulo: las portadoras no convergen
        self.assertGreater(float(v.arrays["dw_tardia"][0]),
                           0.5 * float(v.arrays["dw_temprana"][0]))

    def test_gate3_coqueteo_episodios_contados(self):
        """Tres tramos de lock de 10 u.t. separados por derivas de 4 u.t. (W=4: cada tramo
        da ~6 u.t. de rw alto ≥ 1 ventana = episodio; termina en deriva ⇒ sin firmeza
        final): estado COQUETEO, episodios en [2,4] (declarado — la rampa difumina bordes).
        Mata al contador borrado (0) y al que pega rachas (1)."""
        w = 6.2
        tramos = []
        fase_acum = 0.0
        for ciclo in range(3):
            t_lock = np.arange(int(10 / DT)) * DT
            tramos.append(fase_acum + w * t_lock)
            fase_acum = tramos[-1][-1]
            t_der = np.arange(int(4 / DT)) * DT
            tramos.append(fase_acum + (w + 4.0) * t_der)
            fase_acum = tramos[-1][-1]
        th2 = np.concatenate(tramos)
        n_t = th2.size
        th1 = w * np.arange(n_t) * DT
        # nodo 2 = th1 + (th2 − su propia envolvente w·t) ⇒ mismo carrier, desfase por tramos
        wl = _wl_sintetico([th1, th2])
        v = par.run(wl)
        self.assertEqual(int(v.arrays["estado"][0]), 1,
                         f"estado={v.arrays['estado'][0]}: el lock por tramos no es coqueteo")
        self.assertGreaterEqual(int(v.arrays["episodios"][0]), 2)
        self.assertLessEqual(int(v.arrays["episodios"][0]), 4)
        self.assertGreater(float(v.arrays["dur_max_ut"][0]), 1.0)

    def test_gate4_t_lock_donde_corresponde(self):
        """Deriva 10 u.t. → lock 20 u.t.: t_lock en [10, 10+2W+resolución]."""
        w = 6.2
        n_der = int(10 / DT); n_lock = int(20 / DT)
        th1 = w * np.arange(n_der + n_lock) * DT
        th2_der = (w + 3.0) * np.arange(n_der) * DT
        th2_lock = th2_der[-1] + w * (np.arange(n_lock) + 1) * DT
        wl = _wl_sintetico([th1, np.concatenate([th2_der, th2_lock])])
        v = par.run(wl)
        self.assertEqual(int(v.arrays["estado"][0]), 2)
        t_lock = float(v.arrays["t_lock_ut"][0])
        self.assertGreaterEqual(t_lock, 9.0, f"t_lock={t_lock}: antes de que exista el lock")
        self.assertLessEqual(t_lock, 10.0 + 2 * 4.0 + 0.5,
                             f"t_lock={t_lock}: el sostén no puede tardar más de 2W+res")

    def test_gate5_pulling_convergencia(self):
        """ω2 converge linealmente a ω1 en 30 u.t.: dw_tardia < dw_temprana/2."""
        n_t = int(30 / DT)
        t = np.arange(n_t) * DT
        w1 = 6.2
        w2_t = 6.2 + 1.0 * np.maximum(0.0, 1.0 - t / 20.0)       # 1.0 → 0 en 20 u.t.
        th2 = np.cumsum(w2_t) * DT
        wl = _wl_sintetico([w1 * t, th2])
        v = par.run(wl)
        self.assertLess(float(v.arrays["dw_tardia"][0]),
                        0.5 * float(v.arrays["dw_temprana"][0]),
                        "la convergencia construida no se ve en el pulling")

    def test_gate6_portadora_fft_y_no_el_artefacto(self):
        """Coseno puro a ω=6.168: el pico ±resolución — y NUNCA el punto fijo del
        estimador viejo (−2ω²/(1+ω²) ≈ −1.95, §15/§16)."""
        w = 6.168
        t = np.arange(25001) * DT
        y = np.cos(w * t + 0.7)
        medido = par.portadora_fft(y, DT)
        resol = 2 * np.pi / (8 * 25001 * DT)
        self.assertLess(abs(medido - w), 3 * resol,
                        f"portadora {medido:.4f} != {w} (resol {resol:.4f})")
        artefacto = 2 * w * w / (1 + w * w)
        self.assertGreater(abs(medido - artefacto), 1.0,
                           "la portadora medida ES el punto fijo del estimador viejo")
        with self.assertRaises(RuntimeError):
            par.portadora_fft(np.ones(4), DT)

    def test_gate7_punto_ciego_declarado_y_w_configurable(self):
        t = np.arange(int(30 / DT)) * DT
        wl = _wl_sintetico([6.2 * t, 6.4 * t])
        v = par.run(wl)
        self.assertAlmostEqual(v.manifest["punto_ciego_dw"], 2 * np.pi / 4.0, places=3)
        v8 = par.run(wl, {"w_ut": 8.0})
        self.assertAlmostEqual(v8.manifest["punto_ciego_dw"], 2 * np.pi / 8.0, places=3)
        self.assertNotEqual(v.manifest["config_hash"], v8.manifest["config_hash"])


class TestParFilmReal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import shutil
        from study07.artifacts.composer import componer_red
        from study07.artifacts.recorder import WorldlineRecorder
        from study07.artifacts.runner import run as run_net
        from study07.compat import study06_capsule as cap6
        fx = np.load(F8, allow_pickle=False)
        m = json.loads(str(fx["meta_json"]))
        caps = [cap6.load_capsule(CAPS_DIR / b) for b in m["block_ids"]]
        ep = m["engine_params"]
        net, _, recibo = componer_red(
            [{"theta": t, "capsula": c} for t, c in zip(m["thetas_embebidos"], caps)],
            m["edges"], dt=float(m["dt"]), seed=int(m["seed"]),
            k_global=float(ep["kappa_global"]), coupling_gamma_c=float(ep["coupling_gamma_c"]))
        base = {c["manifest"]["block_id"]: c["capsule_sha256"] for c in caps}
        cls.tmp = Path(tempfile.mkdtemp())
        man = {"run_id": "par_f0", "spec_tipo": "M1",
               "hashes_base_externa": base, "composicion": recibo}
        rec = WorldlineRecorder(cls.tmp / "run", net, man, chunk_ticks=4096)
        # 3 ventanas de W=... el gate del instrumento exige >=3W; con W=0.4 u.t. alcanza
        # un film corto (15000 ticks = 1.2 u.t. NO alcanza para W=4 ⇒ usamos w_ut=0.24)
        run_net(net, 15000, recorder=rec)
        rec.close()
        cls.wl = api.load_run(cls.tmp / "run")
        cls._shutil = shutil

    @classmethod
    def tearDownClass(cls):
        cls._shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_gate8_theta_identico_al_de_fase_y_vista_completa(self):
        cfg = {"w_ut": 0.24, "temprana_ut": 0.3, "tardia_ut": 0.3}
        v = par.run(self.wl, cfg)
        vf = phase.run(self.wl)
        np.testing.assert_array_equal(v.arrays["theta"], vf.arrays["theta"],
                                      err_msg="par y fase divergen en la extracción de θ "
                                              "— DEBE ser un solo camino")
        # coherencia flag↔umbral declarado
        for fila, rw in enumerate(v.arrays["rw_final"]):
            if v.arrays["estado"][fila] == 2:
                self.assertGreaterEqual(rw, 0.95)
        self.assertEqual(v.arrays["pares_ij"].shape, (1, 2))     # 2 nodos ⇒ 1 par
        self.assertTrue(v.manifest["canales"]["estado"].startswith("VEREDICTO"))
        self.assertIn("MEDIDOS en C1", v.manifest["procedencia_umbrales"])
        with tempfile.TemporaryDirectory() as td:
            p = v.write(Path(td))
            lv = api.load_view(p)
            self.assertEqual(lv["view_hash"], v.view_hash())

    def test_gate9_contrato_fail_loud(self):
        with self.assertRaisesRegex(RuntimeError, "stride=1"):
            par.run(self.wl, {"stride": 5})
        with self.assertRaisesRegex(RuntimeError, "3 ventanas"):
            par.run(self.wl)          # W=4 u.t. default > film de 1.2 u.t.
        with self.assertRaises(RuntimeError):
            par.run(self.wl, {"umbral_firmeza": 0.9})       # typo ⇒ whitelist
        wl_mut = dict(self.wl); wl_mut["estados"] = []
        with self.assertRaises(RuntimeError):
            par.run(wl_mut, {"w_ut": 0.24})
        # defaults con procedencia (mata umbral mutado)
        t = np.arange(int(30 / DT)) * DT
        wl_s = _wl_sintetico([6.2 * t, 6.2 * t])
        v = par.run(wl_s)
        self.assertEqual(v.manifest["observation_config"]["umbral_firme"], 0.95)
        self.assertEqual(v.manifest["observation_config"]["umbral_coqueteo"], 0.80)
        self.assertEqual(v.manifest["observation_config"]["w_ut"], 4.0)


if __name__ == "__main__":
    unittest.main()
