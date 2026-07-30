"""Genera la REFERENCIA de observables de F4 corriendo el oráculo read-only (Fase 0.3).

Reproduce EXACTAMENTE la trayectoria del fixture f6 (mismos thetas modificados, mismas
constantes, mismo seed, mismo escalado de IC y rebuild del buffer) y colecta, tick a tick, lo
que el oráculo calcula ONLINE con SUS PROPIAS funciones:
  - theta_q por nodo (NodeOscillator.theta_q_from_state)
  - energías por capa por nodo (NodeOscillator.energies — devueltas por step())
  - Z, R, J, omega_c, omega_valid (atlas.observables.lock_band_observables — importada del
    oráculo, no re-escrita: la referencia es SU aritmética)
Fila 0 = PRE-step (theta y energías del estado inicial; J=0, omega=nan por has_previous=False).

El instrumento offline de study07 debe reproducir ESTA referencia leyendo sólo la worldline —
ésa es la inversión arquitectónica completa: lo que el oráculo calculaba DENTRO del motor,
study07 lo calcula como vista.
"""
import copy
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
sys.path.insert(0, str(ORACLE / "src"))

from paper5.olar.differential_engine import DifferentialNetwork, HistoryBuffer  # noqa: E402
from paper5.olar.physics_core import Layer  # noqa: E402
from atlas.observables import lock_band_observables, EPS_DEN, R_MIN_DEFAULT  # noqa: E402

F6 = STUDY07 / "tests/fixtures/study07_f6_regimen_caliente.npz"


def main():
    fx = np.load(F6, allow_pickle=False)
    meta6 = json.loads(str(fx["meta_json"]))
    thetas = copy.deepcopy(meta6["thetas_embebidos"])   # ya traen las masas modificadas
    params = dict(meta6["engine_params"])
    ticks = int(meta6["ticks"])
    dt = float(meta6["dt"])

    raw = json.load(open(ORACLE / "data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json"))
    blocks = {b["block_id"]: b for b in (raw["blocks"] if "blocks" in raw else raw)}
    omegas = [float(blocks[b]["omega_ref"]) for b in meta6["block_ids"]]

    net = DifferentialNetwork(thetas, omegas, meta6["edges"], params, seed=int(meta6["seed"]))
    for osc in net.oscillators:
        osc.state.x[:] *= float(meta6["ic_scale"])
        osc.state.v[:] *= float(meta6["ic_scale"])
    xv_scaled = np.array([o.xv_total_from_state(o.state) for o in net.oscillators])
    net.history = HistoryBuffer(net.history.delay_steps, len(net.oscillators), xv_scaled)

    # verificación de identidad de trayectoria: el estado inicial DEBE ser el del f6
    for j, o in enumerate(net.oscillators):
        st = o.state
        plano = np.concatenate([st.x, st.v, st.z, st.b, st.e])
        d = float(np.max(np.abs(plano - fx[f"estados_nodo{j}"][0])))
        assert d == 0.0, f"nodo {j}: estado inicial difiere del f6 ({d:.3e})"

    n = len(net.oscillators)
    theta = np.empty((ticks + 1, n))
    e_capa = np.empty((ticks + 1, n, 3))            # (t, nodo, [Q,S1,S2])
    for j, o in enumerate(net.oscillators):
        theta[0, j] = o.theta_q_from_state(o.state)
        en = o.energies(o.state)
        e_capa[0, j] = [float(en.get(Layer.Q, 0.0)), float(en.get(Layer.S1, 0.0)),
                        float(en.get(Layer.S2, 0.0))]
    z = np.empty(ticks + 1, dtype=complex)
    r = np.empty(ticks + 1); jj = np.empty(ticks + 1)
    om = np.empty(ticks + 1); omv = np.empty(ticks + 1, dtype=bool)
    z[0] = complex(np.mean(np.exp(1j * theta[0])))
    jj[0], r[0], om[0], omv[0] = lock_band_observables(z[0], 0j, dt, R_MIN_DEFAULT, False)
    for tick in range(1, ticks + 1):
        th_next, energ = net.step()                 # el oráculo calcula ONLINE
        theta[tick] = th_next
        e_capa[tick] = energ.T                      # step devuelve (3, n) → (n, 3)
        z[tick] = complex(np.mean(np.exp(1j * theta[tick])))
        jj[tick], r[tick], om[tick], omv[tick] = lock_band_observables(
            z[tick], z[tick - 1], dt, R_MIN_DEFAULT, True)
        # identidad de trayectoria POR TICK contra el f6 (double tap F4 A6): una divergencia a
        # mitad de corrida aparecería después como residuo de Gate A atribuido al instrumento
        for j, o in enumerate(net.oscillators):
            st = o.state
            plano = np.concatenate([st.x, st.v, st.z, st.b, st.e])
            d = float(np.max(np.abs(plano - fx[f"estados_nodo{j}"][tick])))
            assert d == 0.0, f"tick {tick} nodo {j}: trayectoria difiere del f6 ({d:.3e})"

    # procedencia MEDIDA, no declarada en prosa (F4 A6: «la metadata miente»)
    oracle_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ORACLE,
                                   capture_output=True, text=True).stdout.strip()
    oracle_dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ORACLE,
                                       capture_output=True, text=True).stdout.strip())
    blocks_path = ORACLE / "data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json"
    payload = {
        "schema": "study07_observables_reference_v1",
        "fuente": "oraculo online (theta_q_from_state + energies + lock_band_observables)",
        "f6_sha256": hashlib.sha256(F6.read_bytes()).hexdigest(),
        "blocks_sha256": hashlib.sha256(blocks_path.read_bytes()).hexdigest(),
        "ticks": ticks, "dt": dt, "n_nodes": n,
        "eps_den": EPS_DEN, "r_min": R_MIN_DEFAULT,
        "oracle_commit": oracle_commit, "oracle_dirty": oracle_dirty,
        "numpy": np.__version__,
        "python": platform.python_version(), "machine": platform.machine(),
        "nota": ("fila 0 = PRE-step; theta[k] = fase Q POST step k; Z=mean(exp(i*theta)); "
                 "J[k]=Im(conj(Z_k)*(Z_k-Z_{k-1})/dt), J[0]=0; omega=J/max(R^2,eps_den) si "
                 "R>=r_min sino nan"),
    }
    out = STUDY07 / "tests/fixtures/study07_f7_observables_ref.npz"
    np.savez_compressed(out, theta=theta, e_capa=e_capa, z=z, r=r, j=jj, omega=om,
                        omega_valid=omv, meta_json=np.array(json.dumps(payload)))
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    (STUDY07 / "tests/fixtures/study07_f7.sha256").write_text(
        f"{sha}  tests/fixtures/{out.name}\n")
    print(f"[f7] {out.name} {out.stat().st_size//1024} KB sha256={sha[:16]}  "
          f"R final={r[-1]:.4f}  omega_valid={int(omv.sum())}/{len(omv)}")


if __name__ == "__main__":
    main()
