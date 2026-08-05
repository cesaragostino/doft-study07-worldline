"""Paso 7: artefactos del caldo — recorder, checkpoint (gate a caballo), cápsula."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

from study07.artifacts.caldo_artifacts import (RecorderCaldo, guardar_capsula,
                                               guardar_checkpoint, hidratar_capsula,
                                               restaurar_checkpoint)
from study07.engine.caldo import RedCaldo


def _spec():
    from study07.compat.study06_v4 import parse_theta_v2
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    u = [x for x in spec_j["unidades"] if x["run_id"].startswith("s120_par134")][0]
    spec, _ = parse_theta_v2(u["constituyentes"][0]["theta"], emission_scale=0.1)
    return spec


KW = dict(dt=8e-5, seed=13, K=1e-3, lam=1e-2, tau_s=8e-4,
          T_pulso=0.05, ticks_pulso=200, T_rem=0.05, ticks_rem=100)


def test_recorder_roundtrip(tmp_path):
    spec = _spec()
    c = RedCaldo(spec, 3, **KW)
    rec = RecorderCaldo(tmp_path / "run", c, {"run_id": "test"}, chunk_ticks=64,
                        dec_factor=8, n_caja=32)
    for _ in range(150):
        x_pre, v_pre = c.x.copy(), c.v.copy()
        c.step()
        rec.registrar_paso(x_pre, v_pre)
    wl_hash = rec.close()
    assert len(wl_hash) == 64
    chunks = sorted((tmp_path / "run/worldline").glob("chunk_*.npz"))
    assert len(chunks) >= 2
    f0 = np.load(chunks[0], allow_pickle=False)
    assert f0["ticks"][0] == 0                       # fila 0 = PRE-step (remanente)
    assert f0["estados"].shape[1:] == (3, 33)
    assert f0["tau"].shape[1] == 3
    comp = json.loads((tmp_path / "run/COMPLETE").read_text())
    assert comp["ticks_totales"] == 150 and len(comp["chunk_shas"]) == len(chunks)


def test_checkpoint_gate_a_caballo(tmp_path):
    """El gate del schema v2: checkpoint A CABALLO del pulso; directa vs restore
    BIT-EXACTA hasta 2·ticks_pulso."""
    spec = _spec()
    a = RedCaldo(spec, 2, **KW)
    for _ in range(100):                             # mitad del pulso (200 ticks)
        a.step()
    ck = guardar_checkpoint(a, tmp_path / "ck.npz", seed=13, genoma_id="61b48428",
                            run_id="t", manifest_sha="m")
    b = restaurar_checkpoint(spec, ck, seed=13, genoma_id="61b48428",
                             K=KW["K"], lam=KW["lam"], tau_s=KW["tau_s"],
                             T_pulso=KW["T_pulso"], ticks_pulso=KW["ticks_pulso"])
    for _ in range(300):                             # cruza el fin del pulso (a caballo)
        a.step(); b.step()
    for m_, s_, n_ in ((a.x, b.x, "x"), (a.v, b.v, "v"), (a.z, b.z, "z"),
                       (a.b, b.b, "b"), (a.e, b.e, "e"), (a.tau, b.tau, "tau")):
        assert np.array_equal(m_, s_), f"gate a caballo: canal {n_} difiere (no bit-exacto)"


def test_checkpoint_fingerprint_fail_loud(tmp_path):
    spec = _spec()
    a = RedCaldo(spec, 2, **KW)
    for _ in range(20):
        a.step()
    ck = guardar_checkpoint(a, tmp_path / "ck.npz", seed=13, genoma_id="61b48428",
                            run_id="t", manifest_sha="m")
    with pytest.raises(RuntimeError, match="fingerprint"):
        restaurar_checkpoint(spec, ck, seed=13, genoma_id="61b48428",
                             K=0.999, lam=KW["lam"], tau_s=KW["tau_s"],
                             T_pulso=KW["T_pulso"], ticks_pulso=KW["ticks_pulso"])


def test_capsula_roundtrip_y_fail_loud(tmp_path):
    spec = _spec()
    a = RedCaldo(spec, 2, **KW)
    for _ in range(50):
        a.step()
    cap = guardar_capsula(a, tmp_path / "cap", seed=13, genoma_id="61b48428",
                          run_id_origen="t", worldline_hash="w" * 64)
    b = hidratar_capsula(spec, cap, seed=13, genoma_id="61b48428",
                         K=KW["K"], lam=KW["lam"], tau_s=KW["tau_s"],
                         T_pulso=KW["T_pulso"], ticks_pulso=KW["ticks_pulso"])
    assert b.tick == a.tick and np.array_equal(b.tau, a.tau)
    # adulteración → fail-loud por sha
    npz = Path(cap) / "capsula_caldo.npz"
    datos = bytearray(npz.read_bytes()); datos[-1] ^= 0xFF
    npz.write_bytes(bytes(datos))
    with pytest.raises(RuntimeError, match="sha"):
        hidratar_capsula(spec, cap, seed=13, genoma_id="61b48428",
                         K=KW["K"], lam=KW["lam"], tau_s=KW["tau_s"],
                         T_pulso=KW["T_pulso"], ticks_pulso=KW["ticks_pulso"])
