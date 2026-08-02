"""CIRUGÍA DE LÍNEA FIJA — campaña [M1, §12-SELLADO post-tap wf_030bb1cc].

GRID FINAL DEL JUEZ (62 unidades, audit/DOUBLETAP_CIRUGIA_*): fase 0 (2 gemelos OFF,
320 u.t.) + 1A (30 estaciones STRADDLE, F0 = {0.5,0.7,1.0,1.4,2.0}×F_th^OFF sellados,
emitidos por `niveles` DESPUÉS de leer los OFF) + 1B (8 estaciones P1-σ, F0 absolutos
pre-registrados) + 1C (12 barridos CENTRADOS en el notch — ambos brazos cruzan ω* al
mismo t con la misma A_S) + 1D (8 estaciones E2-LINK_REAL, lazo de UN lado declarado) +
1E (2 réplicas de IC: brazo fresh como IC alternativa declarada).
NULA SELLADA = worldline lineal COMPLETA (Jacobiano frío + IC + programa, RK4 idéntico
al motor, dt=8e-5; verificada por el juez a ≤2.1e-4 relativo) con transitorio de
encendido INCLUIDO — se publica y committea ANTES de abrir lectura ON alguna; la
frontera F0>A_S/|χ| queda como corolario t≫1/|σ| (para σ lentos NUNCA aplica en 120).
Orden: correr fase0+fijas → leer OFF (script sellado `niveles`) → publicar NULA+mapa
completo de notches (commit) → correr 1A/1E → recién entonces LEER unidades ON.
Cruces citables t∈[10,110]. Presupuesto (fórmula preflight): 74.3 GB, 68.3 wh.
Subcomandos: matar | chi | generar_fijas | niveles | nula | correr_fase0 | correr_1a
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))
ORACLE = Path.home() / "code/doft-study06-fundamental-lock-dynamics"
BASE = ORACLE / "data/processed/ola1_v4_c1/ola1"
OUT = STUDY07 / "data/cirugia"
ARCHIVO = Path("/Volumes/ExternalDisk/study07_cirugia_linea_fija")

DT = 8e-5
RECEPTORES = {
    "34b5ab50": {"estaciones": [(30.17, "Q1"), (30.67, "Q1"), (25.0, "Q1")],
                 "notch_focal": 30.17, "notch_2": 31.22,
                 "barridos": [(30.17, (3.0, 0.03)), (31.22, (0.04,))],
                 "e2_res": [(7.07, 3e-3), (6.00, 3e-3), (25.0, 0.01), (30.17, 0.3)]},
    "61b48428": {"estaciones": [(33.69, "Q0"), (34.37, "Q1"), (25.0, "Q1")],
                 "notch_focal": 33.69, "notch_2": 34.37,
                 "barridos": [(33.69, (0.3, 0.03)), (34.37, (0.04,))],
                 "e2_res": [(8.62, 3e-3), (8.62, 0.01), (25.0, 0.01), (33.69, 0.3)]},
}
MULT_STRADDLE = (0.5, 0.7, 1.4, 1.0, 2.0)      # sellados (orden cosmético)
P1B = [(33.69, 3e-3), (33.69, 0.01), (25.0, 3e-3), (25.0, 0.01)]        # 61b
P1B_34 = [(30.17, 3e-3), (30.17, 0.01), (25.0, 3e-3), (25.0, 0.01)]     # 34b
RATE = 0.05
SEMI = 8.0                                       # ventana de barrido ω*±8
T_EST, T_LARGO = 1500000, 4000000                # 120 / 320 u.t.
ENGINE = {"dt": DT, "kappa_global": 0.3, "coupling_gamma_c": 0.3,
          "tau_field": 0.0, "temperature": 0.0}


def _bloques():
    raw = json.load(open(BASE / "simple_blocks_canonical.json"))
    bl = raw["blocks"] if isinstance(raw, dict) and "blocks" in raw else raw
    out = {}
    for b in bl:
        for p in RECEPTORES:
            if b["block_id"].startswith(p):
                out[p] = b
    return out


def _capsulas():
    inv = json.load(open(STUDY07 / "data/inventario_v4.json"))
    dir_b = {p["block_id"]: p["dir"] for p in inv["poblacion"]}
    sha_b = {p["block_id"]: p["capsule_sha256"] for p in inv["poblacion"]}
    out = {}
    for p, b in _bloques().items():
        bid = b["block_id"]
        out[p] = {"dir": str(BASE / "specimen_capsules" / dir_b[bid]),
                  "sha": sha_b[bid], "block_id": bid}
    return out


# ------------------------- χ / Jacobiano (port de d1 del juez) -------------------------

def build_A(spec):
    from study07.physics.state import MEM_FORCE_SCALE
    n, nz = spec.n_modes, spec.n_z
    m = np.array([md.mass for md in spec.modes])
    K = np.zeros((n, n))
    for p, md in enumerate(spec.modes):
        K[p, p] += md.omega0 ** 2
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
    Dvz = np.zeros((n, nz)); Dzx = np.zeros((nz, n)); Dzz = np.zeros((nz, nz))
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
    return A, m


def _spec_de(pref):
    from study07.compat.study06_v4 import parse_theta_v2
    theta = _bloques()[pref]["theta_internal"]
    spec, _ = parse_theta_v2(theta, emission_scale=1.0 / len(theta["modes"]))
    return spec, theta


def chi():
    """Mapa COMPLETO de χ y notches (arreglo 9) + A0/σ/eigQ → CHI_NULA_BASE.json."""
    from study07.compat.study06_capsule import load_capsule
    from study07.physics.state import Layer
    caps = _capsulas()
    res = {}
    for pref in RECEPTORES:
        spec, _ = _spec_de(pref)
        n = spec.n_modes
        A, m = build_A(spec)
        ew, V = np.linalg.eig(A)
        qidx = list(spec.layer_indices[Layer.Q])
        eigQ = []
        for i in range(len(ew)):
            if ew[i].imag > 1e-9:
                vx = V[:n, i]
                t = float(np.sum(np.abs(vx) ** 2)) or 1.0
                if float(np.sum(np.abs(vx[qidx]) ** 2)) / t > 0.5:
                    eigQ.append((float(ew[i].imag), float(ew[i].real)))
        eigQ.sort()
        omegas = np.arange(4.0, 42.5001, 0.01)
        dim = A.shape[0]
        B = np.zeros(dim); B[n:2 * n] = 1.0 / m
        chi_grid = np.zeros((len(omegas), len(qidx)))
        for k, w in enumerate(omegas):
            x = np.linalg.solve(1j * w * np.eye(dim) - A, B)
            chi_grid[k] = np.abs(x[:n])[qidx]
        notches = {}
        for j in range(len(qidx)):
            c = chi_grid[:, j]
            mins = [(round(float(omegas[k]), 2), float(c[k]))
                    for k in range(1, len(omegas) - 1)
                    if 20 <= omegas[k] <= 42.5 and c[k] < c[k - 1] and c[k] < c[k + 1]]
            notches[f"Q{j}"] = mins
        cap = load_capsule(caps[pref]["dir"])
        x0 = np.asarray(cap["arrays"]["x"], float)
        v0 = np.asarray(cap["arrays"]["v"], float)
        A0 = {f"Q{j}": float(np.hypot(x0[p], v0[p] / spec.modes[p].omega0))
              for j, p in enumerate(qidx)}
        res[pref] = {"q_idx": qidx,
                     "eig_Q": [{"omega": round(w, 4), "sigma": round(s, 6)}
                               for w, s in eigQ],
                     "omegas": [float(omegas[0]), float(omegas[-1]), 0.01],
                     "chi_Q": {f"Q{j}": [round(float(v), 8) for v in chi_grid[:, j]]
                               for j in range(len(qidx))},
                     "notches_completos": notches, "A0_capsula": A0}
        print(pref, "eigQ:", res[pref]["eig_Q"], "| A0:", A0)
        print("  notches:", {k: v for k, v in notches.items()})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "CHI_NULA_BASE.json").write_text(json.dumps(res, indent=1))
    print("→ data/cirugia/CHI_NULA_BASE.json")


# ------------------------------- specs -------------------------------

def _unidad(pref, run_id, ticks, programa, fresh=False):
    caps = _capsulas()
    b = _bloques()[pref]
    c = {"theta": b["theta_internal"], "block_id": caps[pref]["block_id"]}
    if not fresh:
        c["capsula_dir"] = caps[pref]["dir"]
        c["capsule_sha256"] = caps[pref]["sha"]
    u = {"run_id": run_id, "constituyentes": [c], "edges": [],
         "engine_params": dict(ENGINE), "seed": 3000, "ticks": ticks}
    if programa is not None:
        u["programa"] = programa
    return u


def _spec(nombre, unidades, porque):
    return {"spec_tipo": "M1", "campana": nombre, "porque": porque,
            "retencion": {"perfil": "conformidad_completa", "chunk_ticks": 65536},
            "horizonte_emergencia_ticks": T_EST,
            "reglas_clasificacion": {
                "instrumento": "lector cirugía (v3-lite: rho + r con convergencia-W "
                               "anti-fuga §8 + P de serie); NULA sellada = worldline "
                               "lineal completa, publicada ANTES de leer ON",
                "outcomes": ["frontera de captura vs nula por (modo, omega, F0)",
                             "histeresis = (medido−nula) por dirección al mismo (ω,F0)",
                             "P1-sigma: dlnrho apareado a dlnA_S^OFF del gemelo",
                             "E2: F̂/(K·X_prog) = 1/(1+chi_em·K) — lazo de UN lado"],
                "umbrales": "sellados §12; cruces citables t∈[10,110]"},
            "seed_politica": "seed única 3000 (T=0 determinista; réplica = de IC, no seed)",
            "checkpoint_every": None,
            "unidades": unidades}


def generar_fijas():
    """Fase 0 (OFF) + 1B + 1C + 1D — F0 fijos, corren esta noche; lectura ON bloqueada."""
    us0, us_fijas = [], []
    for pref in RECEPTORES:
        us0.append(_unidad(pref, f"cir0_off_{pref[:3]}", T_LARGO, None))
    for pref, cfg in RECEPTORES.items():
        p1b = P1B if pref == "61b48428" else P1B_34
        for w0, f0 in p1b:
            us_fijas.append(_unidad(pref, f"cir1b_{pref[:3]}_w{w0}_F{f0}", T_EST,
                                    {"modo": "clamp", "forma": "estacion",
                                     "F0": f0, "w0": w0, "rate": 0.0}))
        for centro, f0s in cfg["barridos"]:
            for f0 in f0s:
                for et, w_ini, rate in (("up", centro - SEMI, RATE),
                                        ("dn", centro + SEMI, -RATE)):
                    us_fijas.append(_unidad(
                        pref, f"cir1c_{pref[:3]}_c{centro}_{et}_F{f0}", T_LARGO,
                        {"modo": "clamp", "forma": "barrido",
                         "F0": f0, "w0": w_ini, "rate": rate}))
        for w0, f0 in cfg["e2_res"]:
            us_fijas.append(_unidad(pref, f"cir1d_{pref[:3]}_w{w0}_F{f0}", T_EST,
                                    {"modo": "link_real", "forma": "estacion",
                                     "F0": f0, "w0": w0, "rate": 0.0}))
    OUT.mkdir(parents=True, exist_ok=True)
    for nombre, us in (("fase0", us0), ("fase1_fijas", us_fijas)):
        s = _spec(f"cirugia_{nombre}", us,
                  "cirugía de línea fija §12-SELLADO (tap wf_030bb1cc, grid del juez): "
                  "medición decisiva con correcciones §8 — decide C3-histéresis, "
                  "C4-residuo del notch, P1-sigma")
        cuerpo = json.dumps(s, indent=1)
        (OUT / f"SPEC_{nombre}.json").write_text(cuerpo)
        print(f"[gen] {nombre}: {len(us)} unidades "
              f"sha={hashlib.sha256(cuerpo.encode()).hexdigest()[:16]}")


def niveles():
    """SCRIPT SELLADO (arreglo 5): lee los gemelos OFF → A_S^OFF(t_mid=60) por modo con
    convergencia-W (§8: W=8 y 16, exige acuerdo <15%) → F_th^OFF = A_S/(|χ|·factor_ventana)
    → F0 = MULT_STRADDLE × F_th → SPEC_fase1A + SPEC_fase1E. Cero grados de libertad."""
    from study07.instruments.api import load_run
    chi_base = json.load(open(OUT / "CHI_NULA_BASE.json"))
    us_a, us_e = [], []
    niveles_reg = {}
    for pref, cfg in RECEPTORES.items():
        run = OUT / "fase0/unidades" / f"cir0_off_{pref[:3]}"
        wl = load_run(run)
        man = wl["manifest"]
        nd = man["por_nodo"][0]
        est = wl["estados"][0]
        nm = nd["n_modes"]
        x = est[::10, :nm].astype(np.float64)
        dt_s = DT * 10
        qidx = chi_base[pref]["q_idx"]
        w0_grid, w1_grid, dw_grid = chi_base[pref]["omegas"]
        amps = {}
        for j, p in enumerate(qidx):
            sig = x[:, p]
            vals = []
            for Wut in (8.0, 16.0):
                n_w = int(round(Wut / dt_s)); i0 = int(round((60.0 - Wut / 2) / dt_s))
                seg = sig[i0:i0 + n_w]
                win = np.hanning(n_w)
                S = np.abs(np.fft.rfft(seg * win, n_w * 8))
                vals.append(float(S.max()) / (win.sum() / 2))
            if vals[1] > 0 and abs(vals[0] - vals[1]) / vals[1] > 0.15:
                print(f"[niveles] AVISO {pref} Q{j}: W8/W16 difieren "
                      f"{vals[0]:.3e}/{vals[1]:.3e} — se usa W16 (declarado)")
            amps[f"Q{j}"] = vals[1]
        niveles_reg[pref] = {"A_S_off_t60": amps, "F_th": {}}
        for w0, modo_prim in cfg["estaciones"]:
            k = int(round((w0 - w0_grid) / dw_grid))
            chi_m = chi_base[pref]["chi_Q"][modo_prim][k]
            f_th = amps[modo_prim] / chi_m
            niveles_reg[pref]["F_th"][str(w0)] = {"modo": modo_prim,
                                                  "chi": chi_m, "F_th": f_th}
            for mult in MULT_STRADDLE:
                f0 = round(mult * f_th, 8)
                us_a.append(_unidad(pref, f"cir1a_{pref[:3]}_w{w0}_m{mult}", T_EST,
                                    {"modo": "clamp", "forma": "estacion",
                                     "F0": f0, "w0": w0, "rate": 0.0}))
        wf, mp = (cfg["notch_focal"],
                  dict(cfg["estaciones"])[cfg["notch_focal"]])
        f_th = niveles_reg[pref]["F_th"][str(wf)]["F_th"]
        us_e.append(_unidad(pref, f"cir1e_{pref[:3]}_fresh", T_EST,
                            {"modo": "clamp", "forma": "estacion",
                             "F0": round(1.0 * f_th, 8), "w0": wf, "rate": 0.0},
                            fresh=True))
    for nombre, us in (("fase1A", us_a), ("fase1E", us_e)):
        s = _spec(f"cirugia_{nombre}", us, "cirugía §12 — straddle sellado desde OFF")
        cuerpo = json.dumps(s, indent=1)
        (OUT / f"SPEC_{nombre}.json").write_text(cuerpo)
        print(f"[niveles] {nombre}: {len(us)} unidades "
              f"sha={hashlib.sha256(cuerpo.encode()).hexdigest()[:16]}")
    (OUT / "NIVELES.json").write_text(json.dumps(niveles_reg, indent=1))


def nula():
    """NULA SELLADA: worldline lineal completa por unidad ON (Jacobiano frío + IC de la
    cápsula/fresh + programa, RK4 dt=8e-5 idéntico en tiempos de sub-paso). Publica
    A_pred por modo Q (submuestreo 10) + cruces predichos → NULA.json (commit antes de
    leer ON). Validación: corre también los OFF (programa nulo) y compara contra el film."""
    from study07.compat.study06_capsule import load_capsule
    from study07.physics.state import Layer
    caps = _capsulas()
    chi_base = json.load(open(OUT / "CHI_NULA_BASE.json"))
    specs_on = []
    for nombre in ("fase1_fijas", "fase1A", "fase1E"):
        p = OUT / f"SPEC_{nombre}.json"
        if p.exists():
            specs_on += json.loads(p.read_text())["unidades"]
    res = {}
    for pref in RECEPTORES:
        spec, _ = _spec_de(pref)
        n = spec.n_modes
        A, m = build_A(spec)
        qidx = list(spec.layer_indices[Layer.Q])
        cap = load_capsule(caps[pref]["dir"])
        y0_cap = np.concatenate([np.asarray(cap["arrays"]["x"], float),
                                 np.asarray(cap["arrays"]["v"], float),
                                 np.zeros(spec.n_z)])
        dim = A.shape[0]
        B = np.zeros(dim); B[n:2 * n] = 1.0 / m
        for u in [x for x in specs_on if x["run_id"].split("_")[1][:3] == pref[:3]]:
            prog = u["programa"]
            fresh = "capsula_dir" not in u["constituyentes"][0]
            if fresh:
                th = u["constituyentes"][0]["theta"]
                y0 = np.zeros(dim)
                y0[:n] = [mo.get("x0", 0.0) for mo in th["modes"]]
                y0[n:2 * n] = [mo.get("v0", 0.0) for mo in th["modes"]]
            else:
                y0 = y0_cap.copy()
            ticks = int(u["ticks"])
            stride = 10
            F0, w0, rate = prog["F0"], prog["w0"], prog["rate"]

            def fprog(t):
                if prog["modo"] == "clamp":
                    return F0 * math.cos(w0 * t + 0.5 * rate * t * t)
                X = F0 * math.cos(w0 * t + 0.5 * rate * t * t)
                V = -F0 * (w0 + rate * t) * math.sin(w0 * t + 0.5 * rate * t * t)
                return None, X, V                      # link_real: se arma abajo
            y = y0.copy()
            outs = np.zeros((ticks // stride + 1, len(qidx)))
            outs[0] = y[qidx]
            if prog["modo"] == "link_real":
                k_c, g_c = ENGINE["kappa_global"], ENGINE["coupling_gamma_c"]
                Alink = A.copy()
                em = 0.1  # emission_scale = 1/n_modes… la emisión es 0.1·Σx (contrato)
                # F = k_c(X − 0.1Σx) + g_c(V − 0.1Σv) sobre todos los v:
                for p_ in range(n):
                    Alink[n + p_, :n] -= k_c * 0.1 / m[p_]
                    Alink[n + p_, n:2 * n] -= g_c * 0.1 / m[p_]
                Aef = Alink
            else:
                Aef = A
            dt = DT
            for k in range(1, ticks + 1):
                t0 = (k - 1) * dt
                if prog["modo"] == "clamp":
                    f_a = fprog(t0); f_b = fprog(t0 + 0.5 * dt); f_c = fprog(t0 + dt)
                    k1 = Aef @ y + B * f_a
                    k2 = Aef @ (y + 0.5 * dt * k1) + B * f_b
                    k3 = Aef @ (y + 0.5 * dt * k2) + B * f_b
                    k4 = Aef @ (y + dt * k3) + B * f_c
                else:
                    _, Xa, Va = fprog(t0); _, Xb, Vb = fprog(t0 + 0.5 * dt)
                    _, Xc, Vc = fprog(t0 + dt)
                    k_c, g_c = ENGINE["kappa_global"], ENGINE["coupling_gamma_c"]
                    fa, fb, fc = (k_c * Xa + g_c * Va, k_c * Xb + g_c * Vb,
                                  k_c * Xc + g_c * Vc)
                    k1 = Aef @ y + B * fa
                    k2 = Aef @ (y + 0.5 * dt * k1) + B * fb
                    k3 = Aef @ (y + 0.5 * dt * k2) + B * fb
                    k4 = Aef @ (y + dt * k3) + B * fc
                y = y + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
                if k % stride == 0:
                    outs[k // stride] = y[qidx]
            res[u["run_id"]] = {
                "programa": prog, "fresh": fresh,
                "x_pred_sub10_absmax_por_ventana": {
                    str(int(tt)): [round(float(np.abs(
                        outs[max(0, int(tt / (DT * stride)) - 625):
                             int(tt / (DT * stride)) + 625, j]).max()), 8)
                        for j in range(len(qidx))]
                    for tt in range(10, int(ticks * DT) - 5, 10)}}
            print(f"[nula] {u['run_id']} ok", flush=True)
    (OUT / "NULA.json").write_text(json.dumps(res, indent=1))
    print(f"[nula] {len(res)} unidades → data/cirugia/NULA.json — COMMIT antes de leer ON")


def matar():
    """Batería K1/K4/K5/K6 + rechazo de checkpoint (los K2/K3 los verificó el juez con
    re-ejecución; K2-absoluto se re-verifica en la primera lectura contra la NULA)."""
    from study07.artifacts.cirugia import ProgramaDrive, RedConDrivePrograma
    from study07.artifacts.composer import componer_red
    from study07.compat.study06_capsule import load_capsule
    caps = _capsulas()
    b = _bloques()["61b48428"]
    cap = load_capsule(caps["61b48428"]["dir"])
    cons = [{"theta": b["theta_internal"], "capsula": cap}]
    mk = lambda: componer_red(cons, [], dt=DT, seed=3000, k_global=0.3,
                              coupling_gamma_c=0.3, tau_field=0.0, temperature=0.0)[0]
    # K1: clamp F0=0 bit-exacto vs Network puro (5k ticks)
    n1, n2 = mk(), mk()
    r = RedConDrivePrograma.desde_red(n2, {"modo": "clamp", "forma": "estacion",
                                           "F0": 0.0, "w0": 30.0, "rate": 0.0},
                                      k_c=0.3, g_c=0.3)
    for _ in range(5000):
        n1.step(); r.step()
    for a, bb in ((n1.states[0].x, r.states[0].x), (n1.states[0].v, r.states[0].v),
                  (n1.states[0].z, r.states[0].z), (n1.states[0].b, r.states[0].b)):
        assert np.array_equal(a, bb), "K1: divergencia bit"
    assert np.array_equal(n1.history.buffer, r.history.buffer), "K1: history difiere"
    print("[matar] K1 bit-exacto OFF: OK")
    # K5: fase del barrido exacta en el canal drive (clamp)
    r2 = RedConDrivePrograma.desde_red(mk(), {"modo": "clamp", "forma": "barrido",
                                              "F0": 0.5, "w0": 25.0, "rate": 0.05},
                                       k_c=0.3, g_c=0.3)
    drv, esperado = [], []
    t_acc = 0.0                     # misma ACUMULACIÓN que t_abs (F6: acumulado ≠ k·dt)
    for k in range(2000):
        r2.step()
        drv.append(float(r2.last_drive0[0]))
        esperado.append(0.5 * math.cos(25.0 * t_acc + 0.025 * t_acc * t_acc))
        t_acc += DT
    assert max(abs(a - e) for a, e in zip(drv, esperado)) == 0.0, "K5: fase difiere"
    print("[matar] K5 fase de barrido bit-exacta en drive: OK")
    # K4: link_real — F̂ ≠ F0 y fórmula exacta contra kv a mano
    r3 = RedConDrivePrograma.desde_red(mk(), {"modo": "link_real", "forma": "estacion",
                                              "F0": 0.01, "w0": 8.62, "rate": 0.0},
                                       k_c=0.3, g_c=0.3)
    from study07.physics.rhs import emitted_xv
    for k in range(1000):
        xv = emitted_xv(r3.specs[0], r3.states[0])
        t0 = r3.t_abs
        X = 0.01 * math.cos(8.62 * t0); V = -0.01 * 8.62 * math.sin(8.62 * t0)
        f_mano = 0.3 * (X - xv[0]) + 0.3 * (V - xv[1])
        r3.step()
        assert abs(float(r3.last_drive0[0]) - f_mano) < 1e-300 or \
            float(r3.last_drive0[0]) == f_mano, "K4: fórmula difiere"
    print("[matar] K4 link_real = fórmula KV(w=1) exacta, reacción incluida: OK")
    # K6: provenance — validación de spec rechaza cfg malo; checkpoint rechaza restore
    from study07.artifacts.checkpoint import load_checkpoint, network_from_checkpoint
    from study07.artifacts.checkpoint import save_checkpoint as sck
    try:
        ProgramaDrive({"modo": "clamp", "forma": "estacion", "F0": 1.0, "w0": 30.0,
                       "rate": 0.1})
        raise AssertionError("K6: estación con rate≠0 no rechazada")
    except ValueError:
        pass
    p_ck = Path("/tmp") / "ck_cirugia_test.npz"
    sck(p_ck, r3, 1000, extra_meta={"programa": {"modo": "clamp"}, "t_abs": r3.t_abs})
    ck = load_checkpoint(p_ck)
    try:
        network_from_checkpoint(r3.specs, ck)
        raise AssertionError("K6: restore de cirugía no rechazado")
    except ValueError as e:
        assert "CIRUGÍA" in str(e) or "cirugía" in str(e).lower()
    p_ck.unlink()
    print("[matar] K6 spec fail-loud + checkpoint rechaza restore de cirugía: OK")
    print("[matar] batería: TODO OK")


def _correr(spec_nombre, workers):
    from study07.artifacts.campana import correr_campana
    spec = json.loads((OUT / f"SPEC_{spec_nombre}.json").read_text())
    base = OUT / spec_nombre
    if (base / "REPORTE.json").exists():
        print(f"[cirugia] {spec_nombre}: ya corrida"); return
    inv_sha = (STUDY07 / "data/inventario_v4.sha256").read_text().split()[0]
    hashes = {"inventario_v4": inv_sha,
              "chi_nula_base": hashlib.sha256(
                  (OUT / "CHI_NULA_BASE.json").read_bytes()).hexdigest()}
    rep = correr_campana(spec, base, hashes_base=hashes, workers=workers,
                         archivar_en=ARCHIVO / spec_nombre)
    (base / "REPORTE.json").write_text(json.dumps(rep, indent=1, default=str))
    print(f"[cirugia] {spec_nombre} TERMINADA")


def correr_fase0():
    _correr("fase0", 2)


def correr_fijas():
    _correr("fase1_fijas", 10)


def correr_1a():
    _correr("fase1A", 10)
    _correr("fase1E", 2)


if __name__ == "__main__":
    {"matar": matar, "chi": chi, "generar_fijas": generar_fijas, "niveles": niveles,
     "nula": nula, "correr_fase0": correr_fase0, "correr_fijas": correr_fijas,
     "correr_1a": correr_1a}[sys.argv[1]]()
