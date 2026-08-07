"""CAMPAÑA M2 «CALDO CENSAL 1» [PREREG §43 bitácora 2026-08-07 — SELLADO, GO COA].

Un caldo N=150 heterogéneo (census SPEC_lote1 EN SU ORDEN), 120 u.t., ley completa.
argv: calendario {frio|frontera|caliente} + seed. Retención mínima declarada por
calendario; τ dec ×8; checkpoints c/10 u.t.; recorder a ExternalDisk.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

CAL = {"frio": (5.0, 10.0), "frontera": (12.7, 60.0), "caliente": (13.0, 80.0)}
K, LAM, TAU_S, DT, UT = 0.3, 30.0, 8e-4, 8e-5, 120.0
TICKS_PULSO, T_REM, TICKS_REM = 1250, 0.05, 2500
CK_CADA_UT, DEC_TAU = 10.0, 8


def poblacion():
    from study07.compat.study06_v4 import parse_theta_v2
    j = json.loads((STUDY07 / "data/census_arnold/SPEC_lote1.json").read_text())
    specs, gids = [], []
    for u in j["unidades"]:
        s, _ = parse_theta_v2(u["constituyentes"][0]["theta"], emission_scale=0.1)
        specs.append(s); gids.append(u["run_id"])
    assert len(specs) == 150, f"población: {len(specs)} != 150 (prereg §43)"
    return specs, gids


def main():
    from study07.artifacts.caldo_artifacts import RecorderCaldo, guardar_checkpoint
    from study07.engine.caldo import RedCaldo
    calendario, seed = sys.argv[1], int(sys.argv[2])
    t_pulso, ret_ut = CAL[calendario]
    run_id = f"m2censal1_{calendario}_s{seed}"
    dest = Path("/Volumes/ExternalDisk/doft-study07/m2_censal") / run_id
    git_hash = subprocess.run(["git", "rev-parse", "HEAD"], cwd=STUDY07,
                              capture_output=True, text=True).stdout.strip()
    specs, gids = poblacion()
    c = RedCaldo(specs, 150, genoma_ids=gids, dt=DT, seed=seed, K=K, lam=LAM,
                 tau_s=TAU_S, T_pulso=t_pulso, ticks_pulso=TICKS_PULSO,
                 T_rem=T_REM, ticks_rem=TICKS_REM,
                 w_ticks_max=int(round(ret_ut / DT)))
    rec = RecorderCaldo(dest, c, {
        "run_id": run_id, "seed": seed, "genoma_id": "census_lote1_150",
        "git_hash": git_hash, "prereg": "§43 bitácora 2026-08-07"},
        chunk_ticks=4096, dec_factor=32, n_caja=2500,
        segmentos_full=((0.0, 5.0),), dec_tau=DEC_TAU)
    ticks = int(round(UT / DT))
    ck_cada = int(round(CK_CADA_UT / DT))
    t0 = time.time()
    print(f"[censal] {run_id} git={git_hash[:8]} ret={ret_ut}ut → {dest}", flush=True)
    for k in range(ticks):
        xp, vp = c.x.copy(), c.v.copy()
        c.step()
        rec.registrar_paso(xp, vp)
        if (k + 1) % ck_cada == 0:
            guardar_checkpoint(c, dest / "checkpoints" / f"ck_{int((k+1)*DT):04d}ut.npz",
                               seed=seed, genoma_id="census_lote1_150",
                               run_id=run_id, manifest_sha=rec.manifest_sha)
        if (k + 1) % int(round(1.0 / DT)) == 0:
            ut = (k + 1) * DT
            print(f"[censal] {calendario} s{seed} t={ut:6.1f} "
                  f"τ:{c.tau.mean():.5f}/{c.tau.max():.5f} τ̇max={c.max_abs_dtau:.3f} "
                  f"clamp={c.clamp_count} hw={c.historia.high_water} "
                  f"{(time.time()-t0)/3600:.2f}h", flush=True)
    wl = rec.close()
    resumen = {"run_id": run_id, "git_hash": git_hash, "worldline_hash": wl,
               "horas": (time.time() - t0) / 3600, "clamp": c.clamp_count,
               "tau_stats": {"mean": float(c.tau.mean()), "max": float(c.tau.max())}}
    (dest / "RESUMEN.json").write_text(json.dumps(resumen, indent=1))
    print(f"[censal] {run_id} COMPLETO wl={wl[:12]} {resumen['horas']:.1f}h", flush=True)


if __name__ == "__main__":
    main()
