"""JUEZ — controles finales:
(a) par132 cola de rho_Q1 (censura por horizonte del unico negativo del lider fuerte)
(b) par132 detector restringido-a-banda (la otra mitad de la degeneracion del VOLTEA)
(c) envolvente lineal exacta (expm por autodescomposicion) del 34b5ab aislado:
    pendiente log-envolvente Q por ventana — ventana corta vs clase asintotica
"""
import json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, "/Users/cagostino/code/doft-study07-worldline/src")
OUT = Path(__file__).parent

# --- (a) y (b): par132 ---
f = np.load(OUT / "par132_t_jz.npz")
dt = float(f["dt_s"]); x1 = f["x1"]; b0 = f["b0"]
n = x1.shape[0]; T = n * dt; t = np.arange(n) * dt
W, HOP, PAD = 2.0, 0.5, 4
t_grid = np.arange(W / 2 + 0.25, T - W / 2 - 0.25, HOP)
C = 9.9492
w_L_full = C * np.sqrt(1 + 0.1 * b0[:, 0])
w_L = np.interp(t_grid, t, w_L_full)

n_w = int(round(W / dt)); n_fft = n_w * PAD
win = np.hanning(n_w)
freqs = 2 * np.pi * np.fft.rfftfreq(n_fft, d=dt)

def spec(sig, tc):
    i0 = int(round((tc - W / 2) / dt))
    return np.abs(np.fft.rfft(sig[i0:i0 + n_w] * win, n_fft))

# (a) cola de rho por modo
print("== (a) par132: rho(t) STFT por modo, ultimos 12 puntos ==")
for j, nom in [(0, "Q0"), (1, "Q1"), (2, "Q2")]:
    sig = x1[:, j]
    wself = {0: 7.064, 1: 6.842, 2: 5.951}[j]
    rho = []
    for tc, wl in zip(t_grid, w_L):
        S = spec(sig, tc)
        aL = S[(freqs >= wl - 1) & (freqs <= wl + 1)].max()
        aS = S[(freqs >= wself - 1.5) & (freqs <= wself + 1.5)].max()
        rho.append(aL / aS)
    rho = np.array(rho)
    sup = t_grid[rho > 1.0]
    print(f" {nom}: rho>1 en t={np.round(sup,2).tolist()}")
    print(f"     cola: {[(round(a,2), round(b,2)) for a,b in zip(t_grid[-12:], np.round(rho[-12:],3))]}")

# (b) detector restringido a banda alta [15,45]
print("\n== (b) par132: detector restringido w_dom en [15,45], |w_dom-w_L|<1 ==")
selhi = (freqs >= 15) & (freqs <= 45)
for j, nom in [(0, "Q0"), (1, "Q1"), (2, "Q2")]:
    sig = x1[:, j]
    hits = []
    for tc, wl in zip(t_grid, w_L):
        S = spec(sig, tc)
        wd = freqs[selhi][np.argmax(S[selhi])]
        hits.append(abs(wd - wl) < 1.0)
    frac = np.mean(hits)
    print(f" {nom}: fraccion del film en 'captura' segun detector restringido = {frac:.2f}")

# --- (c) envolvente lineal exacta 34b5ab ---
print("\n== (c) 34b5ab aislado: envolvente lineal exacta (autodescomposicion) ==")
from study07.compat.study06_v4 import parse_theta_v2
import importlib.util
spec_mod = importlib.util.spec_from_file_location("j2mod", OUT / "j2_jacobiano_bandas.py")
# construir A analitica reutilizando la funcion (sin re-ejecutar el main): copiar minimal
blocks = json.load(open("/Users/cagostino/code/doft-study06-fundamental-lock-dynamics/data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json"))
theta = next(b for b in blocks if b["block_id"].startswith("34b5ab50a85c"))["theta_internal"]
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    sp, _ = parse_theta_v2(theta, emission_scale=1.0)
from study07.physics.state import MEM_FORCE_SCALE
nm = sp.n_modes; nz = sp.n_z
m = np.array([md.mass for md in sp.modes])
K = np.zeros((nm, nm))
for p, md in enumerate(sp.modes):
    K[p, p] += md.omega0 ** 2
for pr in sp.intra_pairs:
    K[pr.i_idx, pr.i_idx] += pr.k0 / m[pr.i_idx]; K[pr.i_idx, pr.j_idx] -= pr.k0 / m[pr.i_idx]
    K[pr.j_idx, pr.j_idx] += pr.k0 / m[pr.j_idx]; K[pr.j_idx, pr.i_idx] -= pr.k0 / m[pr.j_idx]
for lk in sp.direct_links:
    s_, d_ = lk.shallow_idx, lk.deep_idx
    K[s_, s_] += lk.g0 / m[s_]; K[s_, d_] -= lk.g0 / m[s_]
    K[d_, d_] += lk.g0 / m[d_]; K[d_, s_] -= lk.g0 / m[d_]
G = np.diag([md.gamma for md in sp.modes])
Dvz = np.zeros((nm, nz)); Dzx = np.zeros((nz, nm)); Dzz = np.zeros((nz, nz))
lorder = list(sp.mem_layer_order)
for (layer, k), iz in sp.mem_index.items():
    par = sp.layer_mem[layer]
    for idx in sp.layer_indices.get(layer, ()):
        Dvz[idx, iz] += -MEM_FORCE_SCALE * par.g[k] / m[idx]
    Dzz[iz, iz] = -1.0 / par.tau0[k]
    r = lorder.index(layer)
    for c, lc in enumerate(lorder):
        if lc in sp.layer_indices:
            w_ = sp.W[r, c] / len(sp.layer_indices[lc])
            for xi in sp.layer_indices[lc]:
                Dzx[iz, xi] += par.a[k] * par.beta[k] * w_
dim = 2 * nm + nz
A = np.zeros((dim, dim))
A[:nm, nm:2 * nm] = np.eye(nm); A[nm:2 * nm, :nm] = -K
A[nm:2 * nm, nm:2 * nm] = -G; A[nm:2 * nm, 2 * nm:] = Dvz
A[2 * nm:, :nm] = Dzx; A[2 * nm:, 2 * nm:] = Dzz
ew, V = np.linalg.eig(A)
Vi = np.linalg.inv(V)
x0v = np.zeros(dim); x0v[:nm] = 1e-3  # IC tipo nacimiento
c0 = Vi @ x0v
iQ = list(sp.layer_indices[list(sp.layer_indices)[0]])  # Layer.Q primero (orden canonico)
def envQ(tt):
    xt = (V * np.exp(ew * tt)) @ c0
    return float(np.sqrt(np.sum(np.abs(xt[:3]) ** 2)))  # modos Q = 0,1,2
for (a, b) in [(0, 20), (0, 60), (60, 200), (500, 1000), (2000, 3000)]:
    ts = np.linspace(a, b, 400)
    ev = np.array([envQ(x) for x in ts])
    # pendiente de log-envolvente por ajuste lineal
    sl = np.polyfit(ts, np.log(ev), 1)[0]
    print(f" ventana [{a},{b}]: pendiente log-envolvente Q = {sl:+.4f} /u.t.")
print(f" sigma asintotico (eig): {ew.real.max():+.6f}, e-fold = {1/ew.real.max():.0f} u.t.")
