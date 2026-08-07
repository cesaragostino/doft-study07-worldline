"""VIZ 3D del caldo [pedido COA 2026-08-07]: película navegable del mapa τ.

Escanea los run-dirs disponibles (m2_censal/* y caldo1/*), precalcula frames de
1 u.t. (posición = MDS-3D de log1p(τ/τ_s) alineado por Procrustes; tamaño = rms del
líder Q; color = log e_Q; aristas = lock de fase por caja) y genera UN html
autocontenido con combo de corridas, órbita 3D, slider temporal y MEDIDOR DE
FIDELIDAD (fracción de varianza del mapa capturada por el 3D — la honestidad del
embedding en pantalla). Transformación radial log DECLARADA en pantalla.
Uso: python3 tools/viz_caldo.py  →  docs/viz/caldo_3d.html
"""
import json
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
RAICES = [Path("/Volumes/ExternalDisk/doft-study07/m2_censal"),
          Path("/Volumes/ExternalDisk/doft-study07/caldo1")]
OUT = STUDY07 / "docs/viz/caldo_3d.html"
DEC = 8
TAU_S = 8e-4
LENGUA = 0.275
MAX_ARISTAS = 4000


def cargar(dirw):
    """STREAMING: acumula medias de τ por caja de 1 u.t. chunk a chunk — jamás
    concatena la matriz τ entera (5+ GB a N=150 con la máquina cargada)."""
    chunks = sorted((dirw / "worldline").glob("chunk_*.npz"))
    if not chunks:
        return None
    man = json.loads((dirw / "manifest.json").read_text())
    dt = float(man["dt"])
    sig, bq, eq = [], [], []
    tau_sum, tau_cnt = {}, {}
    for ch in chunks:
        f = np.load(ch, allow_pickle=False)
        E = f["estados"][::DEC]
        sig.append(E[:, :, 0:3].sum(2)); bq.append(E[:, :, 27]); eq.append(E[:, :, 30])
        tt = (f["tau_ticks"] if "tau_ticks" in f.files else f["ticks"]) * dt
        tau = f["tau"]
        for caja in np.unique(tt.astype(np.int64)):
            m = (tt >= caja) & (tt < caja + 1)
            if not m.any():
                continue
            k = int(caja)
            tau_sum[k] = tau_sum.get(k, 0.0) + tau[m].sum(0)
            tau_cnt[k] = tau_cnt.get(k, 0) + int(m.sum())
    tau_medias = {k: tau_sum[k] / tau_cnt[k] for k in tau_sum}
    return (np.concatenate(sig), np.concatenate(bq), np.concatenate(eq),
            tau_medias, dt, man)


def mds3(D):
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    idx = np.argsort(w)[::-1]
    w, V = w[idx], V[:, idx]
    pos = V[:, :3] * np.sqrt(np.maximum(w[:3], 0.0))
    fid = float(np.maximum(w[:3], 0).sum() / np.abs(w).sum()) if np.abs(w).sum() else 0.0
    return pos, fid


def procrustes(P, Q):
    """Rota/refleja Q para alinearlo a P (sin escala — la escala es la expansión)."""
    A = Q.T @ P
    U, _, Vt = np.linalg.svd(A)
    return Q @ (U @ Vt)


def frames_de(run):
    sig, bq, eq, tau_medias, dt, man = run
    n = sig.shape[1]
    dtd = dt * DEC
    span = sig.shape[0] * dtd
    iu = np.triu_indices(n, 1)
    nfr = int(span) - 1
    fr = []
    prev = None
    for a in range(nfr):
        t0, t1 = a + 0.0, a + 1.0
        s0, s1 = int(t0 / dtd), int(t1 / dtd)
        seg = sig[s0:s1]
        rms = np.sqrt((seg ** 2).mean(0))
        e_m = eq[s0:s1].mean(0)
        if a not in tau_medias:
            continue
        tau_m = tau_medias[a]
        D = np.log1p(tau_m / TAU_S)
        M = np.zeros((n, n)); M[iu] = D; M += M.T
        pos, fid = mds3(M)
        if prev is not None:
            pos = procrustes(prev, pos)
        prev = pos
        # aristas: lock de fase por pendiente de fase en la caja (proxy rápido:
        # pendiente de fase ≈ frecuencia media por diferencias de la señal analítica
        # — acá usamos diferencia de fase de FFT de la caja, suficiente para viz)
        F = np.fft.rfft(seg * np.hanning(seg.shape[0])[:, None], axis=0)
        k = np.abs(F[1:]).argmax(0) + 1
        frecs = 2 * np.pi * k / (seg.shape[0] * dtd)
        A = np.abs(frecs[:, None] - frecs[None, :])[iu] < LENGUA
        idxs = np.where(A)[0]
        if len(idxs) > MAX_ARISTAS:
            idxs = idxs[np.linspace(0, len(idxs) - 1, MAX_ARISTAS).astype(int)]
        aristas = [[int(iu[0][k_]), int(iu[1][k_])] for k_ in idxs]
        fr.append({"t": round(t0 + 0.5, 1),
                   "pos": np.round(pos, 4).tolist(),
                   "rms": np.round(rms, 4).tolist(),
                   "e": np.round(np.log10(np.maximum(e_m, 1e-6)), 3).tolist(),
                   "b": np.round(bq[s0:s1].mean(0), 3).tolist(),
                   "fid": round(fid, 3), "aristas": aristas})
    return {"run_id": man.get("run_id", "?"), "N": n, "frames": fr}


def main():
    runs = {}
    for raiz in RAICES:
        if not raiz.exists():
            continue
        for d in sorted(raiz.iterdir()):
            if (d / "worldline").exists():
                print(f"[viz] cargando {d.name} …", flush=True)
                r = cargar(d)
                if r is None:
                    continue
                try:
                    runs[d.name] = frames_de(r)
                    print(f"[viz]   {len(runs[d.name]['frames'])} frames", flush=True)
                except Exception as ex:
                    print(f"[viz]   salteada ({ex})", flush=True)
    plantilla = (STUDY07 / "tools/viz_caldo_plantilla.html").read_text()
    html = plantilla.replace("/*DATOS*/", "const DATOS = " +
                             json.dumps(runs, separators=(",", ":")) + ";")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"[viz] → {OUT} ({OUT.stat().st_size/1e6:.1f} MB, {len(runs)} corridas)")


if __name__ == "__main__":
    main()
