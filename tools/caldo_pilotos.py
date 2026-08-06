"""PILOTOS del caldo τ [paso 8-9 del plan; PREREG audit/PREREG_PILOTO_CALDO_I.md].

Piloto i (N=2): screen del grid K×λ a 10 u.t. (16 procesos) → candidatos → fase
COMPLETA 120 u.t. con estabilidad dt vs dt/2 y τ_final contra las CONCHAS predichas
(0.0351, 0.1793, 0.3219, ... ± τ_s). Piloto ii (N=25 × 5 u.t.): ventana génesis
(escape ESTADÍSTICO desde τ=0: coherentes escapan, anticoherentes en capa).
Constantes declaradas del piloto (van al registro): T_pulso=13.0 (e_Q≈3·T≈39 > 38 —
CRUZA la frontera H2 predicha dw_∞=0.0073·ΔE vs lengua 0.275), ticks_pulso=1250
(0.1 u.t.), T_rem=0.05, ticks_rem=2500 (0.2 u.t. — el remanente débil «muerto de forma,
ruido activo»). Techo de K (spec §12.7): K ≤ 3/((N−1)·n_S·κ·A_pulso), κ=3.5,
A_pulso = sqrt(Σ_S T_pulso/(m·ω²)).
Criterios SELLADOS (prereg): (K,λ) declarados = deriva de τ observable en ≤600 u.t.
sin violar la semántica causal; τ clavado en TODO el barrido = resultado falsable.
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
OUT = STUDY07 / "data/caldo"

T_PULSO, TICKS_PULSO = 13.0, 1250
T_REM, TICKS_REM = 0.05, 2500
TAU_S = 8e-4
DT = 8e-5
CONCHAS = [0.0351, 0.1793, 0.3219, 0.4636, 0.6061, 0.7498]
KS = [1e-2, 1e-1, 0.3, 1.0]
LAMS = [30.0, 100.0, 300.0, 1000.0]   # RONDA 2 (§13: lambda~106 del S²dt medido)


def _spec():
    from study07.compat.study06_v4 import parse_theta_v2
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    u = [x for x in spec_j["unidades"] if x["run_id"].startswith("s120_par134")][0]
    spec, _ = parse_theta_v2(u["constituyentes"][0]["theta"], emission_scale=0.1)
    return spec


def a_pulso(spec):
    from study07.physics.state import Layer
    idx = [i for i, m in enumerate(spec.modes) if m.layer in (Layer.S1, Layer.S2)]
    return float(np.sqrt(sum(T_PULSO / (spec.modes[i].mass * spec.modes[i].omega0 ** 2)
                             for i in idx)))


def _correr(args):
    K, lam, n, ut, dt, seed = args
    from study07.engine.caldo import RedCaldo
    spec = _spec()
    c = RedCaldo(spec, n, dt=dt, seed=seed, K=K, lam=lam, tau_s=TAU_S,
                 T_pulso=T_PULSO, ticks_pulso=int(TICKS_PULSO * (DT / dt)),
                 T_rem=T_REM, ticks_rem=int(TICKS_REM * (DT / dt)))
    ticks = int(round(ut / dt))
    tau_serie = []
    fmax = 0.0
    paso_muestra = max(1, ticks // 400)
    for k in range(ticks):
        c.step()
        if c.n_pairs and k % paso_muestra == 0:
            tau_serie.append([k * dt, float(c.tau.mean()), float(c.tau.max())])
            # F̂ por par (proxy declarado): K·(|S_ret| + n_S·|x_S|_max)
            fmax = max(fmax, float(np.abs(c.last_fS_sub0).max()) * K * 1.0)
    return {"K": K, "lam": lam, "n": n, "ut": ut, "dt": dt,
            "tau_final_mean": float(c.tau.mean()) if c.n_pairs else 0.0,
            "tau_final_max": float(c.tau.max()) if c.n_pairs else 0.0,
            "tau_final_por_par": [float(t) for t in c.tau],
            "max_abs_dtau": c.max_abs_dtau, "clamp_count": c.clamp_count,
            "min_margen_causal": (None if not np.isfinite(c.min_margen_causal)
                                  else float(c.min_margen_causal)),
            "high_water_ut": c.historia.high_water * dt,
            "F_proxy_max": fmax,
            "tau_serie": tau_serie[-50:]}


def screen():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = _spec()
    A = a_pulso(spec)
    techo = 3.0 / (1 * 7 * 3.5 * A)
    print(f"[piloto-i] A_pulso={A:.4f}  techo K(N=2)={techo:.3f}", flush=True)
    combos = [(K, lam, 2, 10.0, DT, 20260805) for K in KS for lam in LAMS
              if K <= techo * 1.05]
    print(f"[piloto-i] screen: {len(combos)} combos × 10 u.t. (16 procesos)", flush=True)
    t0 = time.time()
    res = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for r in ex.map(_correr, combos):
            res.append(r)
            print(f"  K={r['K']:.0e} λ={r['lam']:.0e}: τ_max={r['tau_final_max']:.5f} "
                  f"dτ_max={r['max_abs_dtau']:.3f} clamp={r['clamp_count']} "
                  f"F̂={r['F_proxy_max']:.3f}", flush=True)
    (OUT / "PILOTO_I_SCREEN.json").write_text(json.dumps(
        {"A_pulso": A, "techo_K_N2": techo, "constantes": {
            "T_pulso": T_PULSO, "ticks_pulso": TICKS_PULSO, "T_rem": T_REM,
            "ticks_rem": TICKS_REM, "tau_s": TAU_S}, "resultados": res}, indent=1))
    print(f"[piloto-i] screen listo en {(time.time()-t0)/60:.1f} min "
          f"→ PILOTO_I_SCREEN.json", flush=True)


def completo():
    """Fase completa: los candidatos del screen (criterio sellado: deriva observable
    τ_max ∈ (τ_s, 1] a 10 u.t. sin clamp desbocado) × 120 u.t. + dt/2 para EL mejor."""
    scr = json.loads((OUT / "PILOTO_I_SCREEN.json").read_text())
    cand = [r for r in scr["resultados"]
            if TAU_S < r["tau_final_max"] <= 1.0 and r["clamp_count"] < 1000]
    cand.sort(key=lambda r: abs(np.log10(r["tau_final_max"] / 0.18)))  # cerca de concha 2
    cand = cand[:3]
    if not cand:
        print("[piloto-i] SIN candidatos: τ clavado o desbocado en TODO el barrido — "
              "RESULTADO FALSABLE, se reporta (prereg)", flush=True)
        (OUT / "PILOTO_I_COMPLETO.json").write_text(json.dumps(
            {"veredicto": "SIN_CANDIDATOS_RESULTADO_FALSABLE"}, indent=1))
        return
    print(f"[piloto-i] fase completa: {[(r['K'], r['lam']) for r in cand]}", flush=True)
    trabajos = [(r["K"], r["lam"], 2, 120.0, DT, 20260805) for r in cand]
    trabajos.append((cand[0]["K"], cand[0]["lam"], 2, 120.0, DT / 2, 20260805))
    res = []
    with ProcessPoolExecutor(max_workers=4) as ex:
        for r in ex.map(_correr, trabajos):
            res.append(r)
            print(f"  K={r['K']:.0e} λ={r['lam']:.0e} dt={r['dt']:.0e}: "
                  f"τ_final={r['tau_final_por_par']} dτ_max={r['max_abs_dtau']:.3f}",
                  flush=True)
    # conchas: ¿τ_final cae en alguna ± τ_s? (criterio H3-piloto)
    for r in res:
        r["concha_mas_cercana"] = min(CONCHAS, key=lambda c: abs(c - r["tau_final_max"]))
        r["en_concha"] = bool(min(abs(c - r["tau_final_max"]) for c in CONCHAS)
                              <= 10 * TAU_S)
    (OUT / "PILOTO_I_COMPLETO.json").write_text(json.dumps(
        {"candidatos": res, "conchas_prereg": CONCHAS}, indent=1))
    print("[piloto-i] completo → PILOTO_I_COMPLETO.json", flush=True)


def piloto_ii():
    """N=25 × 5 u.t.: la ventana del génesis con el (K,λ) declarado."""
    comp = json.loads((OUT / "PILOTO_I_COMPLETO.json").read_text())
    if "candidatos" not in comp:
        print("[piloto-ii] sin (K,λ) — el piloto i no declaró", flush=True)
        return
    mejor = comp["candidatos"][0]
    r = _correr((mejor["K"], mejor["lam"], 25, 5.0, DT, 20260805))
    taus = np.array(r["tau_final_por_par"])
    r["frac_escapados"] = float(np.mean(taus > TAU_S))
    r["frac_en_capa"] = float(np.mean(taus <= TAU_S))
    (OUT / "PILOTO_II_GENESIS.json").write_text(json.dumps(r, indent=1))
    print(f"[piloto-ii] N=25 génesis: escapados={r['frac_escapados']:.2f} "
          f"en_capa={r['frac_en_capa']:.2f} τ_max={r['tau_final_max']:.4f} "
          f"→ PILOTO_II_GENESIS.json", flush=True)


if __name__ == "__main__":
    {"screen": screen, "completo": completo, "ii": piloto_ii}[sys.argv[1]]()
