"""[M1-P1] El fuego importado y el lock del par, medidos como vistas — RUNNER del batch.

Ejecuta EXACTAMENTE lo pre-registrado en docs/prereg/M1-P1.json (el prereg es la config:
este runner no decide nada que el prereg no declare). Dos corridas secuenciales
(transported / fresh), films perfil conformidad con checkpoints, vistas offline phase+energy
escritas y RE-VERIFICADAS desde disco (load_view fail-loud), metricas definidas en el prereg,
RESUMEN.json y archivado verificado al disco externo. NADA se borra localmente.
"""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

import sys
STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

from study07.artifacts.composer import componer_red                     # noqa: E402
from study07.artifacts.recorder import WorldlineRecorder                # noqa: E402
from study07.artifacts.runner import run as run_net                     # noqa: E402
from study07.compat import study06_capsule as cap6                      # noqa: E402
from study07.instruments import api, energy, phase                      # noqa: E402

PREREG = STUDY07 / "docs/prereg/M1-P1.json"
F8 = STUDY07 / "tests/fixtures/study07_f8_transporte.npz"
CAPS_DIR = STUDY07 / "tests/fixtures/f8_capsulas"
BASE = STUDY07 / "data/corridas/m1p1"


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log(msg: str) -> None:
    print(f"[m1p1 +{time.time() - T0:8.1f}s] {msg}", flush=True)


T0 = time.time()


def main():
    pre = json.loads(PREREG.read_text())
    fx8 = np.load(F8, allow_pickle=False)
    m8 = json.loads(str(fx8["meta_json"]))
    thetas = m8["thetas_embebidos"]
    ticks = int(pre["horizonte"]["ticks"])
    dt = float(pre["horizonte"]["dt"])
    ep = pre["engine_params"]

    # ── verificacion de base EXTERNA contra el prereg (fail-loud antes de gastar CPU) ──
    for rol in ("ignitor", "companero"):
        c = pre["constituyentes"][rol]
        d = CAPS_DIR / c["block_id"]
        assert sha_file(d / "capsule.json") == c["capsule_json_sha256"], f"{rol}: capsule.json"
        assert sha_file(d / "state.npz") == c["state_npz_sha256"], f"{rol}: state.npz"
    assert m8["blocks_sha256"] == pre["hashes_base_externa_declarados"]["blocks_canonical_sha256"]
    inv_sha = (STUDY07 / "data/inventario_v4.sha256").read_text().split()[0]
    assert inv_sha == pre["hashes_base_externa_declarados"]["inventario_v4_sha256"]
    log("base externa VERIFICADA contra el prereg (capsulas + blocks + inventario)")

    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=STUDY07,
                         capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=STUDY07,
                                capture_output=True, text=True).stdout.strip())
    base_hashes = {
        "capsula_ignitor": "sha256:" + pre["constituyentes"]["ignitor"]["capsule_json_sha256"],
        "capsula_companero": "sha256:" + pre["constituyentes"]["companero"]["capsule_json_sha256"],
        "blocks_canonical": pre["hashes_base_externa_declarados"]["blocks_canonical_sha256"],
        "inventario_v4": pre["hashes_base_externa_declarados"]["inventario_v4_sha256"],
    }
    BASE.mkdir(parents=True, exist_ok=True)
    resumen = {"prereg": "M1-P1", "prereg_sha256": sha_file(PREREG),
               "study07_commit": git, "study07_dirty": dirty,
               "entorno": {"numpy": np.__version__}, "corridas": {}}

    for brazo in ("transported", "fresh"):
        log(f"── BRAZO {brazo} ──")
        caps = ([cap6.load_capsule(CAPS_DIR / b) for b in m8["block_ids"]]
                if brazo == "transported" else [None, None])
        net, specs, recibo = componer_red(
            [{"theta": t, "capsula": c} for t, c in zip(thetas, caps)],
            pre["topologia"]["edges"], dt=dt, seed=int(pre["seed"]),
            k_global=float(ep["kappa_global"]),
            coupling_gamma_c=float(ep["coupling_gamma_c"]),
            tau_field=float(ep["tau_field"]), temperature=float(ep["temperature"]))
        man = {"run_id": f"m1p1_{brazo}", "spec_tipo": "M1", "porque": pre["porque"],
               "prereg": "M1-P1", "prereg_sha256": resumen["prereg_sha256"],
               "hashes_base_externa": dict(base_hashes), "composicion": recibo,
               "perfil": pre["perfil"]}
        run_dir = BASE / brazo
        rec = WorldlineRecorder(run_dir, net, man, chunk_ticks=4096)
        t_run = time.time()
        run_net(net, ticks, recorder=rec, checkpoint_every=int(pre["checkpoint_every"]),
                finite_check_every=1024)
        rec.close()
        dur = time.time() - t_run
        log(f"{brazo}: {ticks} ticks en {dur:.0f}s ({dur / ticks * 1000:.2f} ms/tick)")

        wl = api.load_run(run_dir)
        v_e = energy.run(wl, thetas)
        v_f = phase.run(wl)
        views_root = BASE / "views"
        p_e = v_e.write(views_root); p_f = v_f.write(views_root)
        lv_e = api.load_view(p_e); lv_f = api.load_view(p_f)   # cache re-verificado fail-loud
        log(f"{brazo}: vistas escritas y RE-verificadas desde disco "
            f"(energy {lv_e['view_hash'][:12]}, phase {lv_f['view_hash'][:12]})")

        e_tot = lv_e["arrays"]["e_capa"].sum(axis=2)           # (t, nodo)
        R = lv_f["arrays"]["r"]
        valid = lv_f["arrays"]["omega_valid"]
        met = {"worldline_hash": wl["worldline_hash"],
               "view_hash_energy": lv_e["view_hash"], "view_hash_phase": lv_f["view_hash"],
               "duracion_s": round(dur, 1),
               "E0_nodo0": float(e_tot[0, 0]), "E0_nodo1": float(e_tot[0, 1]),
               "E_final_nodo0": float(e_tot[-1, 0]), "E_final_nodo1": float(e_tot[-1, 1]),
               "E_max_nodo1": float(e_tot[:, 1].max()),
               "E_max_nodo1_tick": int(e_tot[:, 1].argmax()),
               "R_final_media_ult10pct": float(R[-ticks // 10:].mean()),
               "R_min": float(R.min()), "R_max": float(R.max()),
               "omega_valid_frac": float(valid.mean())}
        # fuego (definicion del prereg: primera cruzada) — solo tiene sentido con E0 grande
        e0 = e_tot[0, 0]
        for etiqueta, frac in (("fuego_t_half", 0.5), ("fuego_t_dec10", 0.1)):
            debajo = np.where(e_tot[:, 0] <= frac * e0)[0]
            met[etiqueta + "_tick"] = int(debajo[0]) if debajo.size else None
            met[etiqueta + "_ut"] = (float(debajo[0] * dt) if debajo.size else None)
        # t_lock: primer k con R[k:k+1000] >= 0.99 SOSTENIDO (cumsum de la mascara)
        ok = (R >= 0.99).astype(np.int64)
        w = 1000
        if len(ok) >= w:
            ventana = np.convolve(ok, np.ones(w, dtype=np.int64), mode="valid")
            sitios = np.where(ventana == w)[0]
            met["t_lock_tick"] = int(sitios[0]) if sitios.size else None
            met["t_lock_ut"] = float(sitios[0] * dt) if sitios.size else None
        resumen["corridas"][brazo] = met
        log(f"{brazo}: E0=({met['E0_nodo0']:.4g}, {met['E0_nodo1']:.4g})  "
            f"E_fin=({met['E_final_nodo0']:.4g}, {met['E_final_nodo1']:.4g})  "
            f"R_final={met['R_final_media_ult10pct']:.4f}  t_lock={met['t_lock_tick']}")

    tr, fr = resumen["corridas"]["transported"], resumen["corridas"]["fresh"]
    resumen["delta_R_final"] = tr["R_final_media_ult10pct"] - fr["R_final_media_ult10pct"]
    resumen["duracion_total_s"] = round(time.time() - T0, 1)
    (BASE / "RESUMEN.json").write_text(json.dumps(resumen, indent=1))
    log(f"RESUMEN.json escrito · delta_R_final={resumen['delta_R_final']:+.4f}")

    # ── archivado VERIFICADO al disco externo (copiar, jamas borrar) ──
    destino = Path(pre["archivado"]["destino"])
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino = destino.with_name(destino.name + f"_{int(T0)}")
    shutil.copytree(BASE, destino)
    malos = []
    for p in sorted(BASE.rglob("*")):
        if p.is_file():
            rel = p.relative_to(BASE)
            if sha_file(p) != sha_file(destino / rel):
                malos.append(str(rel))
    if malos:
        raise SystemExit(f"ARCHIVADO FALLO la verificacion: {malos}")
    n_arch = sum(1 for p in destino.rglob("*") if p.is_file())
    (destino / "ARCHIVADO.json").write_text(json.dumps(
        {"origen": str(BASE), "archivos_verificados": n_arch,
         "verificacion": "sha256 por archivo, 0 discrepancias",
         "study07_commit": git}, indent=1))
    log(f"ARCHIVADO verificado: {n_arch} archivos en {destino} (0 discrepancias)")
    log("M1-P1 COMPLETA")


if __name__ == "__main__":
    main()
