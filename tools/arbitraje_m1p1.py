"""ARBITRAJE de M1-P1 contra el ORÁCULO (Fase 0.3: «cualquier duda se arbitra corriendo el
oráculo» — STUDY06_ORACLE.md).

Pregunta de COA: ¿lo que generó study07 en M1-P1 es la MISMA física que haría Study06?
Respuesta por la vía más dura: el oráculo (DifferentialNetwork congelado @ 39f8df6) corre los
DOS brazos COMPLETOS de M1-P1 — transported (restore_specimen_capsules topology_quench sobre
las mismas 2 cápsulas reales) y fresh (nacimiento con la misma semilla) — los 250.000 ticks,
y se compara TICK POR TICK, nodo por nodo, contra los films archivados de study07.

En esta máquina (el entorno del generador) la exigencia es 0.0 EXACTO — el mismo bit en
las 500.002 filas de estado. Cualquier residuo se reporta con su primer tick de divergencia.
Read-only sobre el oráculo; los films de study07 no se tocan (solo lectura).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
sys.path.insert(0, str(ORACLE / "src"))
sys.path.insert(0, str(STUDY07 / "src"))

from paper5.olar.differential_engine import DifferentialNetwork          # noqa: E402
from paper5.olar.specimen_capsule import (load_specimen_capsule,         # noqa: E402
                                          restore_specimen_capsules)
from study07.artifacts.recorder import load_worldline                    # noqa: E402

F8 = STUDY07 / "tests/fixtures/study07_f8_transporte.npz"
CAPS = STUDY07 / "tests/fixtures/f8_capsulas"
M1P1 = STUDY07 / "data/corridas/m1p1"
T0 = time.time()


def log(msg):
    print(f"[arbitraje +{time.time() - T0:7.1f}s] {msg}", flush=True)


def flat(osc):
    st = osc.state
    return np.concatenate([np.asarray(st.x, float), np.asarray(st.v, float),
                           np.asarray(st.z, float), np.asarray(st.b, float),
                           np.asarray(st.e, float)])


def armar_oraculo(m8, transported: bool):
    thetas = m8["thetas_embebidos"]
    net = DifferentialNetwork(thetas, [float(o) for o in m8["omegas_ref"]],
                              m8["edges"],
                              {"dt": m8["dt"], "T_ticks": 250000, "temperature": 0.0,
                               "kappa_global": 0.7, "coupling_gamma_c": 0.15,
                               "emission_norm": "mean", "tau_field": 0.0},
                              seed=int(m8["seed"]))
    if transported:
        caps = [load_specimen_capsule(CAPS / b) for b in m8["block_ids"]]
        restore_specimen_capsules(net, caps, node_indices=[0, 1], mode="topology_quench")
    return net


def arbitrar(brazo: str, m8) -> dict:
    log(f"── BRAZO {brazo}: cargando film de study07 ──")
    wl = load_worldline(M1P1 / brazo)          # verifica COMPLETE + chunks + manifiesto
    estados = wl["estados"]
    ticks = len(wl["ticks"]) - 1
    log(f"{brazo}: film verificado, {ticks} ticks, {len(estados)} nodos")
    net = armar_oraculo(m8, transported=(brazo == "transported"))
    # fila 0: el estado inicial del oráculo DEBE ser la fila 0 del film
    peor, primer_div = 0.0, None
    for j, osc in enumerate(net.oscillators):
        d = float(np.max(np.abs(flat(osc) - estados[j][0])))
        peor = max(peor, d)
    if peor > 0.0:
        return {"brazo": brazo, "max_abs_d": peor, "primer_tick_divergente": 0}
    log(f"{brazo}: fila 0 IDÉNTICA — el oráculo arranca del mismo bit; corriendo "
        f"{ticks} ticks…")
    for tick in range(1, ticks + 1):
        net.step()
        for j, osc in enumerate(net.oscillators):
            d = float(np.max(np.abs(flat(osc) - estados[j][tick])))
            if d > peor:
                peor = d
                if primer_div is None and d > 0.0:
                    primer_div = tick
        if tick % 50000 == 0:
            log(f"{brazo}: tick {tick}/{ticks} — max|d| acumulado = {peor:.3e}")
    return {"brazo": brazo, "max_abs_d": peor, "primer_tick_divergente": primer_div,
            "ticks_comparados": ticks, "filas_comparadas": (ticks + 1) * len(estados)}


def main():
    fx = np.load(F8, allow_pickle=False)
    m8 = json.loads(str(fx["meta_json"]))
    resultados = [arbitrar(b, m8) for b in ("transported", "fresh")]
    print()
    veredicto = {"arbitraje": "M1-P1 vs oraculo @ 39f8df6 (250k ticks por brazo)",
                 "resultados": resultados,
                 "duracion_s": round(time.time() - T0, 1)}
    out = STUDY07 / "docs/corridas/M1-P1_ARBITRAJE.json"
    out.write_text(json.dumps(veredicto, indent=1))
    for r in resultados:
        estado = ("IDENTICO AL ORACULO (0.0 exacto, el mismo bit)"
                  if r["max_abs_d"] == 0.0 else
                  f"DIVERGE: max|d|={r['max_abs_d']:.3e} desde tick "
                  f"{r['primer_tick_divergente']}")
        log(f"VEREDICTO {r['brazo']}: {estado}")
    log(f"escrito {out.name}")


if __name__ == "__main__":
    main()
