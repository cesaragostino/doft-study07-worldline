"""JUEZ — re-ejecucion independiente de sigma/estabilidad y bandas colectivas.

DOS vias independientes para el Jacobiano (x,v,z) en el punto frio:
 (A) construccion ANALITICA directa de la ley (transcripcion propia de rhs.py)
 (B) diferencias finitas centrales sobre study07.physics.rhs.derivatives (la ley real)
Control: max|J_A - J_B| debe ser ~error de FD. Bandas = eig del sub-bloque (x,v) (b=0).
Cubre 2 lideres + 9 receptores (3 focales + 6 del lider debil).
"""
import json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, "/Users/cagostino/code/doft-study07-worldline/src")
from study07.compat.study06_v4 import parse_theta_v2
from study07.physics import rhs
from study07.physics.state import NodeState, Layer, EPS_OMEGA, MEM_FORCE_SCALE

BLOCKS = Path("/Users/cagostino/code/doft-study06-fundamental-lock-dynamics/data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json")
OUT = Path(__file__).parent

PREFIXES = ["1bc9dcccf3bd", "108114f666e3",           # lideres
            "34b5ab50a85c", "46b339f16f33", "61b484288817",  # focales
            "401ff8728f63", "74b23f765604", "956fba96c70c",  # lider debil
            "9c2256bc8e73", "b053ff4d163b", "e58e88925b4d"]

blocks = json.load(open(BLOCKS))
by_prefix = {}
for b in blocks:
    for p in PREFIXES:
        if b["block_id"].startswith(p):
            by_prefix[p] = b

def build_analytic(spec):
    n, nz = spec.n_modes, spec.n_z
    m = np.array([md.mass for md in spec.modes])
    # K: dv = -K x  (rigidez efectiva/masa) ; G: friccion diag ; Z: dv/dz ; Zx: dz/dx
    K = np.zeros((n, n))
    for p, md in enumerate(spec.modes):
        K[p, p] += md.omega0 ** 2          # sin dividir por masa (ley §1.1)
    for pr in spec.intra_pairs:
        K[pr.i_idx, pr.i_idx] += pr.k0 / m[pr.i_idx]
        K[pr.i_idx, pr.j_idx] -= pr.k0 / m[pr.i_idx]
        K[pr.j_idx, pr.j_idx] += pr.k0 / m[pr.j_idx]
        K[pr.j_idx, pr.i_idx] -= pr.k0 / m[pr.j_idx]
    for lk in spec.direct_links:
        s, d = lk.shallow_idx, lk.deep_idx
        K[s, s] += lk.g0 / m[s]; K[s, d] -= lk.g0 / m[s]
        K[d, d] += lk.g0 / m[d]; K[d, s] -= lk.g0 / m[d]
    G = np.diag([md.gamma for md in spec.modes])
    # memoria: dv[idx] += -g_k z_k / m_idx (por capa) ; dz = -z/tau0 + a*beta*input_layer
    Dvz = np.zeros((n, nz))
    Dzx = np.zeros((nz, n))
    Dzz = np.zeros((nz, nz))
    lorder = list(spec.mem_layer_order)
    for (layer, k), iz in spec.mem_index.items():
        par = spec.layer_mem[layer]
        for idx in spec.layer_indices.get(layer, ()):
            Dvz[idx, iz] += -MEM_FORCE_SCALE * par.g[k] / m[idx]
        Dzz[iz, iz] = -1.0 / par.tau0[k]
        r = lorder.index(layer)
        for c, lc in enumerate(lorder):
            if lc in spec.layer_indices:
                w = spec.W[r, c] / len(spec.layer_indices[lc])
                for xi in spec.layer_indices[lc]:
                    Dzx[iz, xi] += par.a[k] * par.beta[k] * w
    dim = 2 * n + nz
    A = np.zeros((dim, dim))
    A[:n, n:2 * n] = np.eye(n)
    A[n:2 * n, :n] = -K
    A[n:2 * n, n:2 * n] = -G
    A[n:2 * n, 2 * n:] = Dvz
    A[2 * n:, :n] = Dzx
    A[2 * n:, 2 * n:] = Dzz
    return A, K, G

def fd_jacobian(spec, h=1e-6):
    n, nz, nl = spec.n_modes, spec.n_z, spec.n_layers
    dim = 2 * n + nz  # solo (x,v,z); b=e=0 fijo (desacople verificado aparte)
    def f(vec):
        x = vec[:n]; v = vec[n:2 * n]; z = vec[2 * n:]
        st = NodeState(x=x.copy(), v=v.copy(), z=z.copy(),
                       b=np.zeros(nl), e=np.zeros(nl))
        d = rhs.derivatives(spec, st, drive_ext=0.0)
        return np.concatenate([d.x, d.v, d.z])
    J = np.zeros((dim, dim))
    for j in range(dim):
        dv = np.zeros(dim); dv[j] = h
        J[:, j] = (f(dv) - f(-dv)) / (2 * h)
    return J

res = {}
for p in PREFIXES:
    theta = by_prefix[p]["theta_internal"]
    spec, _ = parse_theta_v2(theta, emission_scale=1.0)
    n = spec.n_modes
    A, K, G = build_analytic(spec)
    Jfd = fd_jacobian(spec)
    diff = float(np.max(np.abs(A - Jfd)))
    ew, V = np.linalg.eig(A)
    imax = int(np.argmax(ew.real))
    sigma = float(ew[imax].real); om = float(abs(ew[imax].imag))
    # participacion por capa del modo max (componentes x)
    part = {}
    vx = V[:n, imax]
    tot = float(np.sum(np.abs(vx) ** 2)) or 1.0
    for layer, idxs in spec.layer_indices.items():
        part[layer.name] = round(float(np.sum(np.abs(vx[list(idxs)]) ** 2)) / tot, 4)
    # bandas x-solo (b=0, sin memoria): eig de [[0,I],[-K,-G]]
    dimx = 2 * n
    Ax = np.zeros((dimx, dimx)); Ax[:n, n:] = np.eye(n); Ax[n:, :n] = -K; Ax[n:, n:] = -G
    ex, Vx = np.linalg.eig(Ax)
    freqs = []
    for i in range(len(ex)):
        if ex[i].imag > 1e-9:
            vxx = Vx[:n, i]
            t = float(np.sum(np.abs(vxx) ** 2)) or 1.0
            pp = {L.name: float(np.sum(np.abs(vxx[list(ix)]) ** 2)) / t
                  for L, ix in spec.layer_indices.items()}
            dom = max(pp, key=pp.get)
            freqs.append((float(ex[i].imag), dom, round(pp[dom], 3), float(ex[i].real)))
    freqs.sort()
    banda = {}
    for L in ("Q", "S1", "S2"):
        fs = [f for f in freqs if f[1] == L]
        if fs:
            banda[L] = [round(fs[0][0], 4), round(fs[-1][0], 4)]
    # sigma tambien del FD (control de la via B)
    ewf = np.linalg.eigvals(Jfd)
    sigf = float(np.max(ewf.real))
    res[p] = {"sigma_analitico": sigma, "omega_modo_max": om, "particip": part,
              "sigma_fd": sigf, "max_dJ_analitico_vs_fd": diff,
              "max_re_x_solo": float(np.max(ex.real)),
              "bandas_x_solo": banda,
              "freqs_x_solo": [[round(f[0], 4), f[1]] for f in freqs],
              "gammas_Q": [float(spec.modes[i].gamma) for i in spec.layer_indices[Layer.Q]]}
    print(f"{p}: sigma={sigma:+.6f} @ w={om:.3f} {part} | fd={sigf:+.6f} "
          f"dJ={diff:.1e} | maxRe(x-solo)={res[p]['max_re_x_solo']:+.5f} | bandas {banda}")

OUT.joinpath("j2_resultados.json").write_text(json.dumps(res, indent=1))
print("OK")
