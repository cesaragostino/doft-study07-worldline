"""GATES F1 del double tap de par_link (JUEZ) — kill-tests de los mutantes VIVOS del tap
+ gates nuevos de los hallazgos BLOQUEA/ALTO. Corren sobre par.py ARREGLADO (v1.1).
Films sintéticos con dt=8e-4 (física analítica idéntica, 10× más rápidos)."""
import unittest
import warnings

import numpy as np

from study07.instruments import par

DT = 8e-4


def _wl(estados, dt=DT):
    n_t = estados[0].shape[0]
    man = {"dt": dt, "n_nodes": len(estados),
           "por_nodo": [{"n_modes": 1, "capas_por_modo": ["Q"]}] * len(estados)}
    return {"manifest": man, "ticks": np.arange(n_t), "estados": estados,
            "worldline_hash": "j" * 64, "complete": True}


def _nodo(th, dt=DT):
    x = np.cos(th)
    return np.stack([x, np.gradient(x, dt)], axis=1)


def _wl_thetas(ths, dt=DT):
    return _wl([_nodo(np.asarray(t, dtype=np.float64), dt) for t in ths], dt)


T30 = np.arange(int(30 / DT)) * DT


class TestKillMutantes(unittest.TestCase):
    """Cada test mata un mutante que sobrevivía a los gates F0."""

    def test_kt_m04_banda_discriminante_del_umbral_firme(self):
        # dw=0.35, W=4: rw_final ≈ |sinc| ≈ 0.92 ∈ [0.90, 0.95) ⇒ NO firme (mata 0.90 hardcodeado)
        v = par.run(_wl_thetas([6.2 * T30, (6.2 + 0.35) * T30]))
        rw = float(v.arrays["rw_final"][0])
        self.assertGreaterEqual(rw, 0.88, f"rw={rw}: el ancla analitica se movio")
        self.assertLess(rw, 0.949, f"rw={rw}: el ancla analitica se movio")
        self.assertNotEqual(int(v.arrays["estado"][0]), 2,
                            f"rw={rw}<0.95 y dio FIRME: el umbral no es el declarado")

    def test_kt_m06_t_lock_cerca_del_arranque(self):
        # deriva 10 u.t. (dw=3) → lock 20: t_lock ∈ [t*-W, t*+1] (mata t_lock=FIN del sosten)
        n_der, n_lock = int(10 / DT), int(20 / DT)
        th1 = 6.2 * np.arange(n_der + n_lock) * DT
        th2d = 9.2 * np.arange(n_der) * DT
        th2l = th2d[-1] + 6.2 * (np.arange(n_lock) + 1) * DT
        v = par.run(_wl_thetas([th1, np.concatenate([th2d, th2l])]))
        t_lock = float(v.arrays["t_lock_ut"][0])
        self.assertGreaterEqual(t_lock, 10.0 - 4.0, f"t_lock={t_lock}")
        self.assertLessEqual(t_lock, 11.0, f"t_lock={t_lock}: no es el arranque del sosten")

    def test_kt_m07_lock_que_muere_no_es_firme(self):
        # lock 15 u.t. + deriva 15 u.t.: coqueteo, jamás firme (mata firme-por-sost_firme)
        n_h = int(15 / DT)
        th2 = np.concatenate([6.2 * np.arange(n_h) * DT,
                              6.2 * n_h * DT + 9.2 * (np.arange(n_h) + 1) * DT])
        v = par.run(_wl_thetas([6.2 * np.arange(2 * n_h) * DT, th2]))
        self.assertEqual(int(v.arrays["estado"][0]), 1,
                         f"estado={int(v.arrays['estado'][0])}: lock muerto declarado firme")
        self.assertLess(float(v.arrays["rw_final"][0]), 0.5)
        self.assertFalse(np.isnan(v.arrays["t_lock_ut"][0]))

    def test_kt_m08_transitorio_excluido_de_temprana(self):
        # transitorio brutal en [0, 0.5): la ventana temprana (arranca en 0.5) NO lo ve
        n_tr = int(0.5 / DT); n_t = T30.size
        th2 = np.concatenate([50.0 * np.arange(n_tr) * DT,
                              50.0 * 0.5 + 6.2 * (np.arange(n_t - n_tr) + 1) * DT])
        v = par.run(_wl_thetas([6.2 * T30, th2]))
        self.assertLess(float(v.arrays["dw_temprana"][0]), 0.5,
                        f"dw_temprana={v.arrays['dw_temprana'][0]}: contaminada por [0,0.5)")

    def test_kt_m10_tres_nodos_tres_pares(self):
        v = par.run(_wl_thetas([6.2 * T30, 6.2 * T30 - np.pi / 2, 9.2 * T30]))
        np.testing.assert_array_equal(v.arrays["pares_ij"],
                                      np.array([[0, 1], [0, 2], [1, 2]]))
        self.assertEqual(int(v.arrays["estado"][0]), 2, "(0,1) mismo carrier: firme")
        self.assertEqual(int(v.arrays["estado"][1]), 0, "(0,2) dw=3: muerto")
        self.assertEqual(int(v.arrays["estado"][2]), 0, "(1,2) dw=3: muerto")

    def test_kt_m11_hann_con_tendencia(self):
        # tono + rampa de amplitud 3: sin Hann el error explota (medido: 4.2 vs 0.5 rad)
        dt = 8e-5
        t = np.arange(25001) * dt
        y = np.cos(6.168 * t + 0.7) + 3.0 * (t / t[-1])
        resol = 2 * np.pi / (8 * 25001 * dt)
        self.assertLess(abs(par.portadora_fft(y, dt) - 6.168), 3 * resol)

    def test_kt_m12_zeropad_entre_bins(self):
        # w=4.9 cae ENTRE bins coarse: sin zeropad err≈1.76 > tol (medido)
        dt = 8e-5
        t = np.arange(25001) * dt
        resol = 2 * np.pi / (8 * 25001 * dt)
        self.assertLess(abs(par.portadora_fft(np.cos(4.9 * t), dt) - 4.9), 3 * resol)

    def test_kt_m14_contrato_rw_movil(self):
        # largo n-W+1 y 0 EXACTO para dphi alternante 0,pi con W par
        dphi = np.tile([0.0, np.pi], 6)
        rw = par._rw_movil(dphi, 4)
        self.assertEqual(rw.size, dphi.size - 4 + 1)
        np.testing.assert_allclose(rw, 0.0, atol=1e-12)

    def test_kt_m15_film_sin_capa_q_no_fabrica_firme(self):
        # capas ['X'] (fallback: todos los modos): deriva pura DEBE dar muerto, no theta=0
        wl = _wl_thetas([6.2 * T30, 9.2 * T30])
        for info in wl["manifest"]["por_nodo"]:
            info["capas_por_modo"] = ["X"]
        v = par.run(wl)
        self.assertEqual(int(v.arrays["estado"][0]), 0,
                         "deriva pura firme: theta colapso a 0 (duplicado sin fallback)")

    def test_kt_m17_rw_final_es_media_no_max(self):
        # lock SOLO las ultimas 6 u.t.: rw_max≈1 pero rw_final (media ventana final) <0.95
        n_pre, n_fin = int(24 / DT), int(6 / DT)
        th2 = np.concatenate([9.2 * np.arange(n_pre) * DT,
                              9.2 * n_pre * DT + 6.2 * (np.arange(n_fin) + 1) * DT])
        v = par.run(_wl_thetas([6.2 * np.arange(n_pre + n_fin) * DT, th2]))
        self.assertGreater(float(v.arrays["rw_max"][0]), 0.99)
        self.assertLess(float(v.arrays["rw_final"][0]), 0.95)
        self.assertEqual(int(v.arrays["estado"][0]), 0)

    def test_kt_m18_dphi_final_es_de_la_ventana_final(self):
        # desfase 0 la primera mitad, pi/2 la segunda: dphi_final ≈ pi/2 (no la media pi/4)
        n_h = T30.size // 2
        des = np.concatenate([np.zeros(n_h), np.full(T30.size - n_h, np.pi / 2)])
        v = par.run(_wl_thetas([6.2 * T30, 6.2 * T30 - des]))
        self.assertLess(abs(abs(float(v.arrays["dphi_final"][0])) - np.pi / 2), 0.15,
                        f"dphi_final={v.arrays['dphi_final'][0]}: media historica, no vigente")

    def test_kt_m19_banda_discriminante_del_umbral_coqueteo(self):
        # dw=0.7245 ⇒ rw≈0.69 sostenido: BAJO el hombro 0.80 ⇒ 0 episodios, muerto
        v = par.run(_wl_thetas([6.2 * T30, (6.2 + 0.7245) * T30]))
        rw = float(v.arrays["rw_final"][0])
        self.assertTrue(0.5 < rw < 0.80, f"rw={rw}: el ancla analitica se movio")
        self.assertEqual(int(v.arrays["episodios"][0]), 0)
        self.assertEqual(int(v.arrays["estado"][0]), 0)

    def test_kt_m20_cruce_breve_sin_t_lock(self):
        # lock solo [0, 4.5] u.t. (< sosten 2W=8): t_lock DEBE ser NaN
        n_l, n_d = int(4.5 / DT), int(25.5 / DT)
        th2 = np.concatenate([6.2 * np.arange(n_l) * DT,
                              6.2 * n_l * DT + 9.2 * (np.arange(n_d) + 1) * DT])
        v = par.run(_wl_thetas([6.2 * np.arange(n_l + n_d) * DT, th2]))
        self.assertTrue(np.isnan(float(v.arrays["t_lock_ut"][0])),
                        f"t_lock={v.arrays['t_lock_ut'][0]}: cruce breve fechado")


class TestGatesNuevosF1(unittest.TestCase):
    """Gates de los hallazgos BLOQUEA/ALTO del double tap (codigo arreglado v1.1)."""

    def test_gate_mudo_film_que_muere_jamas_firme(self):
        # BLOQUEA F8: dos nodos apagados (underflow real a 0.0) => MUDO (3), jamas firme
        env = np.exp(-50.0 * T30)
        x1 = env * np.cos(6.2 * T30); x2 = env * np.cos(9.2 * T30)
        wl = _wl([np.stack([x1, np.gradient(x1, DT)], 1),
                  np.stack([x2, np.gradient(x2, DT)], 1)])
        v = par.run(wl)
        self.assertEqual(int(v.arrays["estado"][0]), 3,
                         f"estado={int(v.arrays['estado'][0])}: cadaveres con link")
        self.assertEqual(v.manifest["nodos_mudos"], [0, 1])
        # constantes tambien
        cte = np.stack([0.7 * np.ones(T30.size), np.zeros(T30.size)], 1)
        v2 = par.run(_wl([cte.copy(), cte.copy()]))
        self.assertEqual(int(v2.arrays["estado"][0]), 3)
        # CONTROL: vivos no son mudos
        v3 = par.run(_wl_thetas([6.2 * T30, 6.2 * T30 - np.pi / 2]))
        self.assertEqual(v3.manifest["nodos_mudos"], [])
        self.assertEqual(int(v3.arrays["estado"][0]), 2)

    def test_gate_nan_fail_loud(self):
        wl = _wl_thetas([6.2 * T30, 6.2 * T30 - np.pi / 2])
        wl["estados"][0][20000, 0] = np.nan
        with self.assertRaisesRegex(RuntimeError, "NaN"):
            par.run(wl)

    def test_gate_n1_fail_loud(self):
        with self.assertRaisesRegex(RuntimeError, ">= 2 nodos"):
            par.run(_wl_thetas([6.2 * T30]))

    def test_gate_ventanas_pulling_fail_loud(self):
        wl = _wl_thetas([6.2 * T30, 6.4 * T30])
        with self.assertRaisesRegex(RuntimeError, "temprana"):
            par.run(wl, {"temprana_ut": 0.3})          # fin <= arranque hardcodeado 0.5
        with self.assertRaisesRegex(RuntimeError, "temprana"):
            par.run(wl, {"temprana_ut": 40.0})         # mas larga que el film
        with self.assertRaisesRegex(RuntimeError, "tard"):
            par.run(wl, {"tardia_ut": 0.0})
        with self.assertRaisesRegex(RuntimeError, "tard"):
            par.run(wl, {"tardia_ut": 50.0})

    def test_gate_stride_det_y_sosten_fail_loud(self):
        wl = _wl_thetas([6.2 * T30, 6.4 * T30])
        with self.assertRaisesRegex(RuntimeError, "stride_det"):
            par.run(wl, {"stride_det": 0})
        with self.assertRaisesRegex(RuntimeError, "stride_det"):
            par.run(wl, {"stride_det": -100})
        with self.assertRaisesRegex(RuntimeError, "sosten"):
            par.run(wl, {"sosten_ventanas": 0.0})
        with self.assertRaisesRegex(RuntimeError, "w_ut"):
            par.run(wl, {"w_ut": 0.0})

    def test_gate_armonico_declarado(self):
        # lock verdadero con 2do armonico A=0.5: el veredicto se degrada (conocido) pero
        # el nodo queda DECLARADO como armonico en el manifiesto
        ests = []
        for th0, psi in ((6.2 * T30, 0.3), (6.2 * T30 - np.pi / 2, 2.1)):
            x = np.cos(th0) + 0.5 * np.cos(2 * th0 + psi)
            ests.append(np.stack([x, np.gradient(x, DT)], 1))
        v = par.run(_wl(ests))
        self.assertEqual(v.manifest["nodos_armonico"], [0, 1],
                         "armonico 2x no declarado: veredicto no confiable en silencio")
        # CONTROL tono puro: nadie declarado
        v2 = par.run(_wl_thetas([6.2 * T30, 6.2 * T30 - np.pi / 2]))
        self.assertEqual(v2.manifest["nodos_armonico"], [])

    def test_gate_zona_falso_firme_declarada_y_medida(self):
        wl = _wl_thetas([6.2 * T30, 6.4 * T30])
        v = par.run(wl)
        self.assertAlmostEqual(v.manifest["zona_falso_firme_dw"], 1.1 / 4.0, places=3)
        self.assertAlmostEqual(v.manifest["punto_ciego_dw"], 2 * np.pi / 4.0, places=3)
        # frontera MEDIDA: dw=0.236 falso-firme (declarado), dw=1.0 (bajo 2pi/W) muerto limpio
        v_ff = par.run(_wl_thetas([6.2 * T30, (6.2 + 0.236) * T30]))
        self.assertEqual(int(v_ff.arrays["estado"][0]), 2)      # documentado, no negado
        v_ok = par.run(_wl_thetas([6.2 * T30, (6.2 + 1.0) * T30]))
        self.assertEqual(int(v_ok.arrays["estado"][0]), 0)

    def test_gate_sesgo_t_lock_acotado_y_declarado(self):
        # deriva lenta dw_pre=0.3: el adelanto existe (medido -3.3) pero queda acotado por W
        n_der, n_lock = int(10 / DT), int(20 / DT)
        th1 = 6.2 * np.arange(n_der + n_lock) * DT
        th2d = 6.5 * np.arange(n_der) * DT
        th2l = th2d[-1] + 6.2 * (np.arange(n_lock) + 1) * DT
        v = par.run(_wl_thetas([th1, np.concatenate([th2d, th2l])]))
        t_lock = float(v.arrays["t_lock_ut"][0])
        self.assertGreaterEqual(t_lock, 10.0 - 4.0, f"t_lock={t_lock}: adelanto > W")
        self.assertLessEqual(t_lock, 10.5, f"t_lock={t_lock}")
        self.assertIn("ADELANTA", v.manifest["nota"])

    def test_gate_manifiesto_citable(self):
        v = par.run(_wl_thetas([6.2 * T30, 6.2 * T30 - np.pi / 2]))
        self.assertEqual(v.manifest["dt"], DT)
        self.assertEqual(v.manifest["w_ticks_efectivo"], int(round(4.0 / DT)))
        self.assertEqual(v.manifest["estados_codigo"]["2"], "firme")
        self.assertEqual(v.manifest["estados_codigo"]["3"], "mudo")
        self.assertEqual(par.ESTADOS[0], "muerto")   # orden del codigo, no invertido
        self.assertIn("NO re-ejecutados", v.manifest["procedencia_umbrales"])

    def test_gate_borde_firme_al_final(self):
        # semantica declarada: lock solo al final => firme con t_lock NaN
        n_pre, n_fin = int(20 / DT), int(10 / DT)
        th2 = np.concatenate([9.2 * np.arange(n_pre) * DT,
                              9.2 * n_pre * DT + 6.2 * (np.arange(n_fin) + 1) * DT])
        v = par.run(_wl_thetas([6.2 * np.arange(n_pre + n_fin) * DT, th2]))
        self.assertEqual(int(v.arrays["estado"][0]), 2)
        self.assertTrue(np.isnan(float(v.arrays["t_lock_ut"][0])))
        self.assertIn("no fechable", v.manifest["nota"])


if __name__ == "__main__":
    unittest.main()
