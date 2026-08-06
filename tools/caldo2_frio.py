"""CALDO 1 [SPEC_MOTOR_TAU_V1 §4 + §7; gate de entrada §15 bitácora 2026-08-05].

N=25 genomas canónicos 61b48428 idénticos (textura = SOLO el remanente por stream),
600 u.t., constantes DECLARADAS por los pilotos: K=0.3, λ=30 (margen de captura 5×,
deriva observable, atractores por población). Calendario: T_pulso=13, ticks_pulso=1250,
remanente T_rem=0.05 × 2500 ticks (burn-in fuera del calendario).
Registro WORLDLINE_CALDO_v1 a ExternalDisk (X/τ tasa completa; f/ℬ dec ×32 + génesis
[0,5] completa; W_ij ledger a tasa completa desde lo emitido). Checkpoint v2 cada
10 u.t. (gate a caballo certificado). Trending causal cada u.t. al log.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

RUN_ID = "caldo2frio_n25_120ut_Tp5"
DEST = Path("/Volumes/ExternalDisk/doft-study07/caldo1") / RUN_ID
SEED = 20260805
GENOMA = "61b48428"
K, LAM, TAU_S = 0.3, 30.0, 8e-4
DT, UT = 8e-5, 120.0
T_PULSO, TICKS_PULSO = 5.0, 1250   # §22: FRÍO — único cambio vs caldo 1
T_REM, TICKS_REM = 0.05, 2500
CK_CADA_UT = 10.0


def _spec():
    from study07.compat.study06_v4 import parse_theta_v2
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    u = [x for x in spec_j["unidades"] if x["run_id"].startswith("s120_par134")][0]
    spec, _ = parse_theta_v2(u["constituyentes"][0]["theta"], emission_scale=0.1)
    return spec


def main():
    from study07.artifacts.caldo_artifacts import RecorderCaldo, guardar_checkpoint
    from study07.engine.caldo import RedCaldo
    git_hash = subprocess.run(["git", "rev-parse", "HEAD"], cwd=STUDY07,
                              capture_output=True, text=True).stdout.strip()
    spec = _spec()
    c = RedCaldo(spec, 25, dt=DT, seed=SEED, K=K, lam=LAM, tau_s=TAU_S,
                 T_pulso=T_PULSO, ticks_pulso=TICKS_PULSO,
                 T_rem=T_REM, ticks_rem=TICKS_REM, w_ticks_max=1_500_000)  # tope SELLADO caldo 1: 120 u.t. (spec §3)
    rec = RecorderCaldo(DEST, c, {
        "run_id": RUN_ID, "seed": SEED, "genoma_id": GENOMA, "git_hash": git_hash,
        "procedencia": "gate §15 bitácora 2026-08-05 (pilotos i/ii + ronda 2/2b)"},
        chunk_ticks=16384, dec_factor=32, n_caja=2500,
        segmentos_full=((0.0, 5.0),))
    ticks = int(round(UT / DT))
    ck_cada = int(round(CK_CADA_UT / DT))
    t0 = time.time()
    print(f"[caldo1] {RUN_ID} git={git_hash[:8]} → {DEST}", flush=True)
    for k in range(ticks):
        x_pre, v_pre = c.x.copy(), c.v.copy()
        c.step()
        rec.registrar_paso(x_pre, v_pre)
        if (k + 1) % ck_cada == 0:
            ut = (k + 1) * DT
            guardar_checkpoint(c, DEST / "checkpoints" / f"ck_{int(ut):04d}ut.npz",
                               seed=SEED, genoma_id=GENOMA, run_id=RUN_ID,
                               manifest_sha=rec.manifest_sha)
        if (k + 1) % int(round(1.0 / DT)) == 0:
            ut = (k + 1) * DT
            el = (time.time() - t0) / 3600
            marg = c.min_margen_causal if np.isfinite(c.min_margen_causal) else -1
            print(f"[caldo1] t={ut:6.1f}  τ:{c.tau.mean():.5f}/{c.tau.max():.5f}  "
                  f"τ̇max={c.max_abs_dtau:.3f} clamp={c.clamp_count} "
                  f"margen={marg:.2e} hw={c.historia.high_water} "
                  f"{el:.2f}h", flush=True)
    wl_hash = rec.close()
    resumen = {"run_id": RUN_ID, "git_hash": git_hash, "worldline_hash": wl_hash,
               "ticks": ticks, "horas": (time.time() - t0) / 3600,
               "tau_final": [float(x) for x in c.tau],
               "clamp_count": c.clamp_count, "max_abs_dtau": c.max_abs_dtau,
               "high_water": int(c.historia.high_water)}
    (DEST / "RESUMEN.json").write_text(json.dumps(resumen, indent=1))
    (STUDY07 / "data/caldo/CALDO1_RESUMEN.json").write_text(
        json.dumps(resumen, indent=1))
    print(f"[caldo1] COMPLETO wl={wl_hash[:12]} en {resumen['horas']:.1f}h", flush=True)


if __name__ == "__main__":
    main()
