"""PROBETA GOLD [M2-build 2; contrato §35 punto 4]: motor + instrumentos JUNTOS
contra un fixture SELLADO — el gate de entrada de toda campaña M2.

Corrida chica de respuesta conocida: N=3 heterogéneo (2 genomas distintos del
gimnasio, arquitectura compartida), 2500 ticks con pulso — motor het completo
(pares, τ, kicks, historia) + recorder + TODOS los instrumentos de la librería.
Modo `sellar`: genera el fixture (UNA vez, se commitea). Modo `verificar`: re-corre
y compara BIT-EXACTO (hashes y arrays) + tolerancia declarada 1e-12 en lecturas
flotantes. Cualquier deriva del motor, del recorder o de un estimador ROMPE la
probeta ANTES de quemar una campaña. PYTHONPATH=src; corre en ~30 s.
"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
FIXTURE = STUDY07 / "tests/fixtures/PROBETA_GOLD_V1.json"

TICKS = 2500
KW = dict(dt=8e-5, seed=20260807, K=0.3, lam=30.0, tau_s=8e-4,
          T_pulso=5.0, ticks_pulso=1250, T_rem=0.05, ticks_rem=500)


def correr():
    from study07.artifacts.caldo_artifacts import RecorderCaldo, fingerprint_extendido
    from study07.compat.study06_v4 import parse_theta_v2
    from study07.engine.caldo import RedCaldo
    from study07.instruments.caldo_lecturas import (fases_banda, grafo_afinidad,
                                                    grafo_lock, matriz_tau,
                                                    mds_espectro, slips_en_lock)
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    specs, gids = [], []
    for u in spec_j["unidades"][:2]:
        s, _ = parse_theta_v2(u["constituyentes"][0]["theta"], emission_scale=0.1)
        specs.append(s); gids.append(u["run_id"][:12])
    specs = [specs[0], specs[1], specs[0]]           # het real: 2 genomas, N=3
    gids3 = [gids[0], gids[1], gids[0]]
    c = RedCaldo(specs, 3, genoma_ids=gids3, **KW)
    with tempfile.TemporaryDirectory() as td:
        rec = RecorderCaldo(Path(td) / "run", c, {"run_id": "probeta_gold_v1"},
                            chunk_ticks=1024, dec_factor=8)
        sig = np.empty((TICKS, 3))
        bq = np.empty((TICKS, 3))
        for k in range(TICKS):
            xp, vp = c.x.copy(), c.v.copy()
            c.step()
            rec.registrar_paso(xp, vp)
            sig[k] = c.x[:, 0:3].sum(1)
            bq[k] = c.b[:, 0]
        wl_hash = rec.close()
        W_total = rec.W_acc.copy()
    ph = fases_banda(sig, KW["dt"], lo=2.0, hi=60.0)
    A_lock, frac, grado = grafo_lock(ph, KW["dt"], caja_ut=0.05)
    slips, locked = slips_en_lock(ph, KW["dt"], caja_ut=0.05)
    A_af, dw = grafo_afinidad(bq[-1])
    ev, dstar, no_eucl = mds_espectro(matriz_tau(c.tau, 3))
    return {
        "fingerprint": fingerprint_extendido(c, KW["seed"], "gold_lote"),
        "worldline_hash": wl_hash,
        "tau_final": [float(t) for t in c.tau],
        "x_sha_bits": float(np.abs(c.x).sum()),          # suma L1 exacta en float64
        "clamp": int(c.clamp_count),
        "frac_lock": [float(f) for f in frac],
        "grado": [int(g) for g in grado],
        "slips": [int(slips), int(locked)],
        "dw_afinidad": [float(d) for d in dw],
        "mds": {"ev": [float(x) for x in ev], "dstar": int(dstar),
                "no_eucl": float(no_eucl)},
        "W_total": [float(w) for w in W_total],
    }


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "verificar"
    res = correr()
    if modo == "sellar":
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps(res, indent=1))
        print(f"[gold] fixture SELLADO → {FIXTURE.name}")
        return
    fix = json.loads(FIXTURE.read_text())
    fallas = []
    for k in ("fingerprint", "worldline_hash", "clamp", "grado", "slips"):
        if res[k] != fix[k]:
            fallas.append(f"{k}: {res[k]} != {fix[k]}")
    for k in ("tau_final", "frac_lock", "dw_afinidad", "W_total"):
        if not np.allclose(res[k], fix[k], rtol=0, atol=1e-12):
            fallas.append(f"{k}: deriva > 1e-12")
    if not np.allclose(res["mds"]["ev"], fix["mds"]["ev"], rtol=0, atol=1e-12) or \
       res["mds"]["dstar"] != fix["mds"]["dstar"]:
        fallas.append("mds: deriva")
    if abs(res["x_sha_bits"] - fix["x_sha_bits"]) != 0.0:
        fallas.append("x: estado final no bit-exacto")
    if fallas:
        print("[gold] ROTA:\n  " + "\n  ".join(fallas))
        sys.exit(1)
    print("[gold] PROBETA GOLD VERDE — motor+recorder+instrumentos = fixture sellado")


if __name__ == "__main__":
    main()
