"""Genera el fixture f8 (TRANSPORTE + composición todo-cápsulas) CORRIENDO EL ORÁCULO.

La referencia de F5: el oráculo restaura 2 cápsulas v4 REALES con SU restore_specimen_capsules
(mode=topology_quench — el modo de transporte certificado en §93-b con 80 sondas a residuo 0)
en una red par nueva (tau=0.02 ⇒ delay 250: el quench TRUNCA el ring de 25000) y corre 1500
ticks. study07 debe reproducir: (a) el buffer post-quench BIT-exacto por su propio camino
(compat.quench_column), (b) el estado post-restore, (c) la trayectoria completa.

Selección ESTRATIFICADA por energía mecánica de cápsula (el discriminador que la campaña
OLA2-C1 §59-§60 encontró: el fuego es importado y viaja con E mecánica): el espécimen de E
máxima (ignitor) + el de E mediana (callado). Las cápsulas se copian VERBATIM a
tests/fixtures/f8_capsulas/<block_id>/ (capsule.json + state.npz) — el lector de study07 se
gatea contra el formato REAL, no contra una imitación.

SELF-CONTAINED: thetas embebidos en el npz. Fase 0.3: cero escrituras en el repo congelado.
"""
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
ORACLE = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
sys.path.insert(0, str(ORACLE / "src"))

from paper5.olar.differential_engine import DifferentialNetwork  # noqa: E402
from paper5.olar.specimen_capsule import (load_specimen_capsule,  # noqa: E402
                                          restore_specimen_capsules)

BASE = ORACLE / "data/processed/ola1_v4_c1/ola1"
TICKS = 1500
SEED = 2026
TAU = 0.02          # 250 pasos a dt=8e-5: el quench trunca 25000 -> 250


def flat(osc):
    st = osc.state
    return np.concatenate([np.asarray(st.x, float), np.asarray(st.v, float),
                           np.asarray(st.z, float), np.asarray(st.b, float),
                           np.asarray(st.e, float)])


def main():
    raw = json.load(open(BASE / "simple_blocks_canonical.json"))
    blocks = {b["block_id"]: b for b in (raw["blocks"] if "blocks" in raw else raw)}

    # seleccion estratificada por E mecanica de capsula (masas=1.0 en los 150)
    energias = []
    for d in sorted((BASE / "specimen_capsules").glob("run_*")):
        bid = d.name.split("_", 2)[2]
        with np.load(d / "state.npz", allow_pickle=False) as st:
            x, v = st["x"], st["v"]
        om = np.array([m["omega0"] for m in blocks[bid]["theta_internal"]["modes"]])
        e_mec = 0.5 * float(np.sum(v ** 2)) + 0.5 * float(np.sum((om * x) ** 2))
        energias.append((e_mec, bid, d))
    energias.sort(key=lambda t: t[0])
    ignitor = energias[-1]
    mediana = energias[len(energias) // 2]
    print(f"[f8] ignitor  E={ignitor[0]:.1f}  {ignitor[1][:12]} ({ignitor[2].name})")
    print(f"[f8] mediana  E={mediana[0]:.4f}  {mediana[1][:12]} ({mediana[2].name})")

    # copiar las capsulas VERBATIM al arbol de fixtures (formato real, hashes intactos)
    fx_caps = STUDY07 / "tests/fixtures/f8_capsulas"
    if fx_caps.exists():
        shutil.rmtree(fx_caps)
    shas = {}
    for _, bid, d in (ignitor, mediana):
        dest = fx_caps / bid
        dest.mkdir(parents=True)
        for nombre in ("capsule.json", "state.npz"):
            shutil.copy2(d / nombre, dest / nombre)
            shas[f"{bid}/{nombre}"] = hashlib.sha256((dest / nombre).read_bytes()).hexdigest()

    bids = [ignitor[1], mediana[1]]
    thetas = [blocks[b]["theta_internal"] for b in bids]     # VERBATIM: el genoma debe calzar
    omegas = [float(blocks[b]["omega_ref"]) for b in bids]
    caps = [load_specimen_capsule(fx_caps / b) for b in bids]  # desde el fixture copiado
    dt = float(caps[0].manifest["engine_contract"]["dt"])
    edges = [{"i": 0, "j": 1, "w_k": 1.0, "w_gamma": 1.0, "tau": TAU}]
    params = {"dt": dt, "T_ticks": TICKS, "temperature": 0.0,
              "kappa_global": 0.7, "coupling_gamma_c": 0.15,
              "emission_norm": "mean", "tau_field": 0.0}
    net = DifferentialNetwork(thetas, omegas, edges, params, seed=SEED)
    receipt = restore_specimen_capsules(net, caps, node_indices=[0, 1],
                                        mode="topology_quench")
    buffer_post = np.array(net.history.buffer, dtype=np.float64, copy=True)
    head_post = int(net.history.head_idx)
    assert head_post == 0, "quench debe dejar head=0"

    n = len(net.oscillators)
    dims = [flat(o).size for o in net.oscillators]
    estados = [np.empty((TICKS + 1, d)) for d in dims]
    for j, o in enumerate(net.oscillators):
        estados[j][0] = flat(o)                              # fila 0 = POST-restore, PRE-step
    for tick in range(1, TICKS + 1):
        net.step()
        for j, o in enumerate(net.oscillators):
            estados[j][tick] = flat(o)

    def _git(repo, *args):
        return subprocess.run(["git", *args], cwd=repo,
                              capture_output=True, text=True).stdout.strip()
    oracle_commit = _git(ORACLE, "rev-parse", "--short", "HEAD")
    oracle_dirty = bool(_git(ORACLE, "status", "--porcelain"))
    study07_commit = _git(STUDY07, "rev-parse", "--short", "HEAD")
    study07_dirty = bool(_git(STUDY07, "status", "--porcelain"))
    meta = {
        "schema": "study07_transporte_referencia_v1",
        "fuente": ("oraculo: DifferentialNetwork + restore_specimen_capsules("
                   "mode=topology_quench) — el camino certificado en §93-b"),
        "block_ids": bids,
        "capsulas_sha256": shas,
        "seleccion": {"criterio": "E mecanica de capsula (max + mediana)",
                      "ignitor": {"block_id": ignitor[1], "e_mecanica": ignitor[0]},
                      "mediana": {"block_id": mediana[1], "e_mecanica": mediana[0]}},
        "thetas_embebidos": thetas, "omegas_ref": omegas,
        "edges": edges, "engine_params": params, "seed": SEED,
        "dt": dt, "ticks": TICKS, "n_nodes": n, "dims": dims,
        "head_post_restore": head_post,
        "receipt_transfer": {k: v for k, v in receipt.items() if k != "nodes"},
        "receipt_nodos": receipt.get("nodes", receipt.get("node_receipts")),
        "blocks_sha256": hashlib.sha256(
            (BASE / "simple_blocks_canonical.json").read_bytes()).hexdigest(),
        "oracle_commit": oracle_commit, "oracle_dirty": oracle_dirty,
        "study07_commit": study07_commit, "study07_dirty": study07_dirty,
        "numpy": np.__version__, "python": platform.python_version(),
        "machine": platform.machine(),
        "nota": ("fila 0 = estado POST-restore PRE-step; buffer_post_restore = ring del "
                 "receptor tras el quench (study07 debe reproducirlo con quench_column); "
                 "capsulas verbatim en f8_capsulas/<block_id>/"),
    }
    arrays = {"buffer_post_restore": buffer_post,
              "meta_json": np.array(json.dumps(meta, default=str))}
    for j in range(n):
        arrays[f"estados_nodo{j}"] = estados[j]
    out = STUDY07 / "tests/fixtures/study07_f8_transporte.npz"
    np.savez_compressed(out, **arrays)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    (STUDY07 / "tests/fixtures/study07_f8.sha256").write_text(
        f"{sha}  tests/fixtures/{out.name}\n")
    print(f"[f8] {out.name} {out.stat().st_size // 1024} KB sha256={sha[:16]}")
    print(f"[f8] oracle {oracle_commit} dirty={oracle_dirty}  x_final_n0 max="
          f"{float(np.max(np.abs(estados[0][-1]))):.4g}")


if __name__ == "__main__":
    main()
