"""Genera el fixture f6 (régimen caliente, NO degenerado) CORRIENDO EL ORÁCULO read-only.

Exigido por el double tap del gate F2 (§3 bitácora study07): los 5 fixtures heredados viven en
régimen frío y degenerado (masas≡1.0, emission='sum', kappa=1.0, b~1e-8) y dejan 24 mutantes de
ley en verde. f6 los cierra de un golpe: masas ≠ 1 POR NODO, kappa_global=0.7,
coupling_gamma_c EXPLÍCITO, emission_norm='mean' (el modo de PRODUCCIÓN v1), temperature=0.05
con MÚLTIPLES nodos y aristas mixtas (dict con w_gamma≠w_k y τ fraccional + tupla legacy),
estado CALIENTE (IC×100 ⇒ b crece ⇒ eps_omega/eps_k/clamp/tau_eff se enganchan), y el ruido
corre con el STREAM PROPIO del motor (pinea la derivación de semilla §6 — el replay NO inyecta).

SELF-CONTAINED: los theta modificados van EMBEBIDOS en el npz ⇒ este fixture corre sin el
oráculo presente (el gate mínimo local que exigió el juez). Permitido por la Fase 0.3 del plan
(Study06 como oráculo para exportar fixtures): CERO escrituras en el repo congelado.

Es una HERRAMIENTA de study07 (tools/), no motor: puede importar el oráculo. physics/ y engine/
jamás lo hacen (gate de arquitectura).
"""
import copy
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
sys.path.insert(0, str(ORACLE / "src"))

from paper5.olar.differential_engine import DifferentialNetwork, HistoryBuffer  # noqa: E402

GOLD = "01a53ee2550de1cb5639de63041329a449a902bd"
RAMPA = "2c674414e77c0526f34e33f50a055e1fdbb23d8e"
MEMORIA = "5d2dab0c1b6b83fcbac560440576fe554b3f62ae"
MASS_FACTORS = [1.7, 0.6, 1.0]     # por nodo — mata el mutante on-site÷masa (JM1)
IC_SCALE = 100.0                    # régimen caliente: b sale del piso 1e-8
TICKS = 1500
SEED = 42


def flat(osc):
    st = osc.state
    return np.concatenate([np.asarray(st.x, float), np.asarray(st.v, float),
                           np.asarray(st.z, float), np.asarray(st.b, float),
                           np.asarray(st.e, float)])


def main():
    raw = json.load(open(ORACLE / "data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json"))
    blocks = {b["block_id"]: b for b in (raw["blocks"] if "blocks" in raw else raw)}
    cap_dirs = sorted((ORACLE / "data/processed/ola1_v4_c1/ola1/specimen_capsules").glob("*"))
    cap = json.load(open(next(d for d in cap_dirs if GOLD[:12] in d.name) / "capsule.json"))
    dt = float(cap["engine_contract"]["dt"])

    thetas = []
    for bid, mf in zip([GOLD, RAMPA, MEMORIA], MASS_FACTORS):
        th = copy.deepcopy(blocks[bid]["theta_internal"])
        for m in th["modes"]:
            m["mass"] = float(m.get("mass", 1.0)) * mf
        thetas.append(th)

    frac = 1.25 * dt
    edges = [
        {"i": 0, "j": 1, "w_k": 1.0, "w_gamma": 0.8, "tau": frac},   # w_gamma ≠ w_k
        {"i": 1, "j": 2, "w_k": 0.5, "w_gamma": 0.5, "tau": 2.5 * dt},
        [0, 2],                                                       # tupla LEGACY (tau=tau_field)
    ]
    params = {"dt": dt, "T_ticks": TICKS, "temperature": 0.05,
              "kappa_global": 0.7, "coupling_gamma_c": 0.15,          # explícito, NO ratio
              "emission_norm": "mean", "tau_field": 0.0}
    omegas = [float(blocks[b]["omega_ref"]) for b in [GOLD, RAMPA, MEMORIA]]
    net = DifferentialNetwork(thetas, omegas, edges, params, seed=SEED)

    # régimen caliente: escalar ICs y RECONSTRUIR la historia con el xv escalado
    for osc in net.oscillators:
        osc.state.x[:] *= IC_SCALE
        osc.state.v[:] *= IC_SCALE
    xv_scaled = np.array([o.xv_total_from_state(o.state) for o in net.oscillators])
    net.history = HistoryBuffer(net.history.delay_steps, len(net.oscillators), xv_scaled)

    e_ref = [{layer.name: float(osc.struct_params.e_ref[layer])
              for layer in osc.struct_params.e_ref} for osc in net.oscillators]
    rng_state0 = json.dumps(net.noise_rng.bit_generator.state)

    dims = [flat(o).size for o in net.oscillators]
    estados = [np.empty((TICKS + 1, d)) for d in dims]
    for j, o in enumerate(net.oscillators):
        estados[j][0] = flat(o)
    buffer0 = np.array(net.history.buffer, copy=True)
    head0 = int(net.history.head_idx)
    for tick in range(1, TICKS + 1):
        net.step()                      # stream PROPIO: nada se inyecta
        for j, o in enumerate(net.oscillators):
            estados[j][tick] = flat(o)

    b_max = max(float(np.max(np.abs(e[:, :]))) for e in estados)
    b_final = [float(np.max(np.abs(o.state.b))) for o in net.oscillators]
    print(f"[f6] max|estado|={b_max:.3e}  max|b| final por nodo={b_final}")
    assert max(b_final) > 1e-6, "el régimen no calentó: b sigue en el piso — subir IC_SCALE"

    payload = {
        "schema": "study07_conformance_fixture_v1_selfcontained",
        "nombre": "f6_regimen_caliente",
        "block_ids": [GOLD, RAMPA, MEMORIA], "mass_factors": MASS_FACTORS,
        "ic_scale": IC_SCALE, "seed": SEED, "dt": dt, "ticks": TICKS,
        "engine_params": params, "edges": edges, "emission_norm": "mean",
        "e_ref_policy": net.e_ref_policy, "e_ref_por_nodo": e_ref,
        "rng_state0": rng_state0,
        "thetas_embebidos": thetas,
        "oracle_commit": "39f8df6", "numpy": np.__version__,
        "python": platform.python_version(), "machine": platform.machine(),
        "nota": ("estados[0]=PRE-step (ya escalado); buffer reconstruido con xv escalado; "
                 "el ruido corre con el stream propio (seed*1000003+99991) — el replay NO inyecta"),
    }
    arrays = {f"estados_nodo{j}": estados[j] for j in range(3)}
    arrays["buffer0"] = buffer0
    arrays["head0"] = np.int64(head0)
    arrays["meta_json"] = np.array(json.dumps(payload, default=str))
    out = STUDY07 / "tests/fixtures/study07_f6_regimen_caliente.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **arrays)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    (STUDY07 / "tests/fixtures/study07_f6.sha256").write_text(
        f"{sha}  tests/fixtures/{out.name}\n")
    print(f"[f6] {out.name} {out.stat().st_size//1024} KB sha256={sha[:16]}")


if __name__ == "__main__":
    main()
