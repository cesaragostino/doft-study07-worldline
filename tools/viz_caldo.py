"""VIZ 3D del caldo v2 [COA 2026-08-07]: película navegable del mapa τ.

v2: frames 0.5 u.t. (pos9 = 9 primeras dimensiones del embedding + norma total por
onion → alpha por-onion = pertenencia a la terna visible; selector de ejes 1-3/4-6/
7-9 en la página) · aristas por u.t. compartidas (resolución de la lengua) · modo
--servir: regeneración desde la página (botón con indicador, thread de fondo).
Uso: python3 tools/viz_caldo.py [--servir 8765]  →  docs/viz/caldo_3d.html
"""
import json
import sys
import threading
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
PASO = 0.5                      # u.t. por frame (pos/tamaño/color); aristas cada 1


def cargar(dirw):
    """STREAMING: medias de τ por caja de PASO chunk a chunk (jamás τ entero)."""
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
        for caja in np.unique((tt / PASO).astype(np.int64)):
            m = (tt >= caja * PASO) & (tt < (caja + 1) * PASO)
            if not m.any():
                continue
            k = int(caja)
            tau_sum[k] = tau_sum.get(k, 0.0) + tau[m].sum(0)
            tau_cnt[k] = tau_cnt.get(k, 0) + int(m.sum())
    tau_medias = {k: tau_sum[k] / tau_cnt[k] for k in tau_sum}
    return (np.concatenate(sig), np.concatenate(bq), np.concatenate(eq),
            tau_medias, dt, man)


def mds9(D):
    """pos9 (N,9), fidelidad global de la terna 1-3, norma total por onion."""
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    idx = np.argsort(w)[::-1]
    w, V = w[idx], V[:, idx]
    k = min(9, n)
    pos9 = V[:, :k] * np.sqrt(np.maximum(w[:k], 0.0))
    if k < 9:
        pos9 = np.pad(pos9, ((0, 0), (0, 9 - k)))
    tot = np.abs(w).sum()
    fid = float(np.maximum(w[:3], 0).sum() / tot) if tot else 0.0
    ntot = np.sqrt(np.maximum(np.diag(B), 1e-30))       # ‖x_i‖ en el embedding pleno
    return pos9, fid, ntot


def procrustes(P, Q):
    A = Q.T @ P
    U, _, Vt = np.linalg.svd(A)
    return Q @ (U @ Vt)


def frames_de(run):
    sig, bq, eq, tau_medias, dt, man = run
    n = sig.shape[1]
    dtd = dt * DEC
    span = sig.shape[0] * dtd
    iu = np.triu_indices(n, 1)
    fr, aristas_ut = [], {}
    prev = None
    nfr = int(span / PASO) - 1
    for a in range(nfr):
        t0 = a * PASO
        s0, s1 = int(t0 / dtd), int((t0 + PASO) / dtd)
        seg = sig[s0:s1]
        if a not in tau_medias or seg.shape[0] < 8:
            continue
        rms = np.sqrt((seg ** 2).mean(0))
        e_m = eq[s0:s1].mean(0)
        D = np.log1p(tau_medias[a] / TAU_S)
        M = np.zeros((n, n)); M[iu] = D; M += M.T
        pos9, fid, ntot = mds9(M)
        if prev is not None:
            pos9 = procrustes(prev, pos9)
        prev = pos9
        ut = int(t0)
        if ut not in aristas_ut:
            u0, u1 = int(ut / dtd), int((ut + 1.0) / dtd)
            segU = sig[u0:min(u1, sig.shape[0])]
            F = np.fft.rfft(segU * np.hanning(segU.shape[0])[:, None], axis=0)
            kk = np.abs(F[1:]).argmax(0) + 1
            frecs = 2 * np.pi * kk / (segU.shape[0] * dtd)
            A = np.abs(frecs[:, None] - frecs[None, :])[iu] < LENGUA
            idxs = np.where(A)[0]
            n_reales = int(len(idxs))
            if len(idxs) > MAX_ARISTAS:
                idxs = idxs[np.linspace(0, len(idxs) - 1, MAX_ARISTAS).astype(int)]
            aristas_ut[ut] = {"n": n_reales,
                              "l": [[int(iu[0][q]), int(iu[1][q])] for q in idxs]}
        fr.append({"t": round(t0 + PASO / 2, 2),
                   "pos9": np.round(pos9, 4).tolist(),
                   "ntot": np.round(ntot, 4).tolist(),
                   "rms": np.round(rms, 4).tolist(),
                   "e": np.round(np.log10(np.maximum(e_m, 1e-6)), 3).tolist(),
                   "b": np.round(bq[s0:s1].mean(0), 3).tolist(),
                   "fid": round(fid, 3), "ut": ut})
    return {"run_id": man.get("run_id", "?"), "N": n, "frames": fr,
            "aristas_ut": {str(k): v for k, v in aristas_ut.items()}}


def construir():
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
    datos = json.dumps(runs, separators=(",", ":"))
    html = plantilla.replace("/*DATOS*/", "const DATOS = " + datos + ";")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    (OUT.parent / "datos.json").write_text(datos)
    print(f"[viz] → {OUT} ({OUT.stat().st_size/1e6:.1f} MB, {len(runs)} corridas)")


ESTADO = {"generando": False}


def servir(puerto):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _txt(self, cuerpo, tipo="application/json"):
            self.send_response(200)
            self.send_header("Content-Type", tipo + "; charset=utf-8")
            self.end_headers()
            self.wfile.write(cuerpo.encode() if isinstance(cuerpo, str) else cuerpo)

        def do_GET(self):
            if self.path in ("/", "/caldo_3d.html"):
                self._txt(OUT.read_text(), "text/html")
            elif self.path == "/datos.json":
                self._txt((OUT.parent / "datos.json").read_text())
            elif self.path == "/estado":
                self._txt(json.dumps(ESTADO))
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            if self.path == "/regenerar" and not ESTADO["generando"]:
                ESTADO["generando"] = True

                def trabajo():
                    try:
                        construir()
                    finally:
                        ESTADO["generando"] = False
                threading.Thread(target=trabajo, daemon=True).start()
                self._txt(json.dumps({"ok": True}))
            else:
                self._txt(json.dumps({"ok": False}))

    print(f"[viz] sirviendo en http://localhost:{puerto} — botón regenerar ACTIVO")
    ThreadingHTTPServer(("127.0.0.1", puerto), H).serve_forever()


if __name__ == "__main__":
    if "--servir" in sys.argv:
        i = sys.argv.index("--servir")
        puerto = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 8765
        if not OUT.exists():
            construir()
        servir(puerto)
    else:
        construir()
