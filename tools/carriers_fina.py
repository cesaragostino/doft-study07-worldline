"""Portadoras FINAS [M1-corrección, COA 2026-08-01]: estimación SUB-BIN.

COA detectó (verificado exacto): portadora_fft devuelve el argmax de la grilla FFT —
con ring de 25001 muestras y zeropad ×8, grilla = 2π/(8·25001·8e-5) = 0.392683 rad/u.t.
Las 150 portadoras caían en 30 valores; el «hueco poblacional [0.1,0.3)» del prereg §1 era
EL INSTRUMENTO (claim retirado en §3). Este estimador:
  1. FFT Hann + zeropad ×8 + INTERPOLACIÓN PARABÓLICA sobre ln|S| en el pico (sub-bin).
  2. Validación cruzada: mediana de frecuencia instantánea por Hilbert (continua, sin
     grilla), recorte de bordes.
Produce data/census_arnold/carriers_fina.json + reporte de la distribución REAL de Δω.
NO toca el instrumento declarado (par v1.1): esto es el EJE de análisis del census,
declarado como adenda de prereg ANTES de mirar outcomes.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import hilbert

STUDY07 = Path(__file__).resolve().parents[1]
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
CAPS = ORACLE / "data/processed/ola1_v4_c1/ola1/specimen_capsules"
OUT = STUDY07 / "data/census_arnold"
DT = 8e-5


def portadora_fina(y: np.ndarray, dt: float) -> dict:
    y = np.asarray(y, dtype=np.float64)
    y = y - y.mean()
    n = y.size
    sp = np.abs(np.fft.rfft(y * np.hanning(n), n=8 * n))
    om = np.fft.rfftfreq(8 * n, dt) * 2.0 * np.pi
    k = int(np.argmax(sp))
    grilla = float(om[1] - om[0])
    if 0 < k < sp.size - 1 and sp[k - 1] > 0 and sp[k + 1] > 0:
        a, b, c = np.log(sp[k - 1]), np.log(sp[k]), np.log(sp[k + 1])
        delta = 0.5 * (a - c) / (a - 2 * b + c)
    else:
        delta = 0.0
    w_para = float(om[k] + delta * grilla)
    fase = np.unwrap(np.angle(hilbert(y)))
    fi = np.gradient(fase, dt)
    w_hil = float(np.median(fi[500:-500]))
    return {"w_fina": w_para, "w_grilla": float(om[k]), "delta_bins": float(delta),
            "w_hilbert": w_hil}


def main():
    finas = {}
    for d in sorted(CAPS.glob("run_*")):
        bid = d.name.split("_", 2)[2]
        with np.load(d / "state.npz", allow_pickle=False) as st:
            y = st["history_column"][:, 0]
        finas[bid] = portadora_fina(y, DT)
    (OUT / "carriers_fina.json").write_text(json.dumps(finas, indent=1))

    wf = np.array([v["w_fina"] for v in finas.values()])
    wh = np.array([v["w_hilbert"] for v in finas.values()])
    print(f"[fina] {len(finas)} portadoras · valores distintos: {len(np.unique(wf))} "
          f"(antes: 30) · |delta| mediana: "
          f"{np.median([abs(v['delta_bins']) for v in finas.values()]):.3f} bins")
    print(f"[fina] validación Hilbert: corr={np.corrcoef(np.abs(wf), np.abs(wh))[0,1]:.4f} "
          f"· |w_fina − w_hilbert| mediana="
          f"{np.median(np.abs(np.abs(wf) - np.abs(wh))):.4f} rad/u.t.")

    # los 30 pares del bin-1 del prereg: su Δω REAL
    sel = json.load(open(OUT / "seleccion.json"))
    bin0 = sel["seleccion"][0]["pares"]
    dws0 = sorted(abs(finas[a]["w_fina"] - finas[b]["w_fina"]) for a, b, _ in bin0)
    print(f"[fina] bin-1 del prereg (dw de grilla = 0.0): Δω REAL ∈ "
          f"[{dws0[0]:.4f}, {dws0[-1]:.4f}], mediana {dws0[15]:.4f}")
    # ¿hay hueco REAL cerca de cero en la población completa?
    bids = sorted(finas)
    dws = []
    for i in range(len(bids)):
        for j in range(i + 1, len(bids)):
            dws.append(abs(finas[bids[i]]["w_fina"] - finas[bids[j]]["w_fina"]))
    dws = np.array(dws)
    print("[fina] población 11175 pares — Δω fino cerca de cero:")
    for lo, hi in [(0, 0.01), (0.01, 0.05), (0.05, 0.1), (0.1, 0.3), (0.3, 1.0)]:
        m = (dws >= lo) & (dws < hi)
        print(f"   [{lo},{hi}): {int(m.sum())} pares")
    # Δω fino de las 150 composiciones seleccionadas (el eje del análisis)
    filas = {}
    for s in sel["seleccion"]:
        for a, b, dw_g in s["pares"]:
            filas[f"{a[:12]}|{b[:12]}"] = {
                "block_i": a, "block_j": b, "dw_grilla": dw_g,
                "dw_fina": abs(finas[a]["w_fina"] - finas[b]["w_fina"]),
                "dw_hilbert": abs(finas[a]["w_hilbert"] - finas[b]["w_hilbert"])}
    (OUT / "dw_fino_seleccion.json").write_text(json.dumps(filas, indent=1))
    print(f"[fina] dw_fino_seleccion.json: {len(filas)} pares — el EJE del análisis")


if __name__ == "__main__":
    main()
