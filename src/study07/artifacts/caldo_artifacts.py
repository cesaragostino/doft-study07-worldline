"""Artefactos del caldo τ: recorder + checkpoint + cápsula [paso 7 del plan;
specs/WORLDLINE_CALDO_SCHEMA.md, CHECKPOINT_SCHEMA_V2.md, CAPSULA_CALDO_SCHEMA.md].

Convenciones selladas: tick int64 (t ≡ tick·dt DERIVADO); índice de par p lexicográfico
compartido por TODOS los canales; canales causales del sub-paso 0 (convención drive[n]);
W_ij integrado A TASA COMPLETA desde lo emitido (un solo RHS — consumo, no re-cálculo);
fingerprint EXTENDIDO = constitución ∪ {K, λ, τ_s, calendario_pulso, seed} (bug-class
kappa_global cerrado). Gate permanente del checkpoint: directa-vs-restore BIT-EXACTA
con pulso a caballo (test en la batería).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ..engine.caldo import RedCaldo


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fingerprint_extendido(caldo: RedCaldo, seed: int, genoma_id: str) -> str:
    """Constitución ∪ constantes de campaña — canónico, orden de claves fijo."""
    if getattr(caldo, "het", False):
        # población heterogénea: la constitución cubre TODOS los genomas por onion
        # (bug-class kappa_global — un solo spec de referencia NO alcanza)
        modos = [[(m.omega0, m.gamma, m.mass, str(m.layer)) for m in s.modes]
                 for s in caldo.lote.specs]
        genoma_id = f"{genoma_id}|het:" + ",".join(caldo.genoma_ids)
    else:
        modos = [(m.omega0, m.gamma, m.mass, str(m.layer)) for m in caldo.spec.modes]
    doc = {"genoma": genoma_id, "modos": modos, "N": caldo.n,
           "K": caldo.K, "lambda": caldo.lam, "tau_s_ut": caldo.tau_s,
           "calendario_pulso": {"T_pulso": caldo.T_pulso,
                                "ticks_pulso": caldo.ticks_pulso},
           "seed": int(seed), "dt": caldo.dt,
           "convencion_pares": "p=i*N-i*(i+1)/2+(j-i-1)"}
    return _sha(json.dumps(doc, sort_keys=True, default=float).encode())


# ─────────────────────────────── recorder ───────────────────────────────

class RecorderCaldo:
    def __init__(self, out_dir, caldo: RedCaldo, manifest: dict, *,
                 chunk_ticks: int = 16384, dec_factor: int = 32,
                 n_caja: int = 2500, segmentos_full=((0.0, 5.0),)) -> None:
        self.dir = Path(out_dir)
        (self.dir / "worldline").mkdir(parents=True, exist_ok=False)
        (self.dir / "checkpoints").mkdir(exist_ok=True)
        self.caldo = caldo
        self.chunk_ticks = int(chunk_ticks)
        self.dec = int(dec_factor)
        self.n_caja = int(n_caja)
        self.segmentos_full = [(float(a), float(b)) for a, b in segmentos_full]
        dim = (caldo.spec.n_modes * 2 + caldo.spec.n_z + caldo.spec.n_layers * 2)
        self.dim = dim
        manifest = dict(manifest)
        manifest.update({
            "schema": "WORLDLINE_CALDO_v1", "N": caldo.n, "n_pairs": caldo.n_pairs,
            "convencion_pares": "p=i*N-i*(i+1)/2+(j-i-1)",
            "ids_onion": [int(i) for i in caldo.ids],
            "K": caldo.K, "lambda": caldo.lam, "tau_s_ut": caldo.tau_s,
            "kappa_pico": 3.5,
            "calendario_pulso": {"T_pulso": caldo.T_pulso,
                                 "ticks_pulso": caldo.ticks_pulso},
            "dt": caldo.dt, "chunk_ticks": self.chunk_ticks,
            "dec_factor": self.dec, "N_caja": self.n_caja,
            "segmentos_full": self.segmentos_full,
            "semantica": ("fila 0 = estado PRE-step (remanente, t=0); estados/tau[k] = "
                          "POST step tick k; fS_sub0/B_sub0 = consumido/emitido en el "
                          "sub-paso 0 del step k (convencion drive[n]); t = tick*dt "
                          "DERIVADO; W_cajas integrado a tasa completa desde lo emitido; "
                          "burn-in del remanente FUERA del calendario (descartado)"),
        })
        cuerpo = json.dumps(manifest, indent=1, default=str)
        (self.dir / "manifest.json").write_text(cuerpo)
        self.manifest_sha = _sha(cuerpo.encode())
        self._reset_chunk()
        self.chunk_idx = 0
        self.chunk_shas = []
        self.W_acc = np.zeros(caldo.n_pairs)
        self.W_cajas = []
        self._fila(pre_step=True)              # fila 0 = PRE-step (remanente)

    def _reset_chunk(self):
        self.rows = {"ticks": [], "estados": [], "tau": [], "kicks": [],
                     "fS_sub0": [], "B_sub0": [], "dec_ticks": [],
                     "trending": [], "clamp": []}

    def _flat(self):
        c = self.caldo
        return np.concatenate([c.x, c.v, c.z, c.b, c.e], axis=1)   # (N, dim)

    def _en_segmento_full(self, t):
        return any(a <= t <= b for a, b in self.segmentos_full)

    def _fila(self, pre_step=False):
        c = self.caldo
        self.rows["ticks"].append(c.tick)
        self.rows["estados"].append(self._flat().astype(np.float64))
        self.rows["tau"].append(c.tau.copy())
        self.rows["kicks"].append(c.last_kicks.copy())
        t = c.tick * c.dt
        if pre_step or c.tick % self.dec == 0 or self._en_segmento_full(t):
            self.rows["fS_sub0"].append(c.last_fS_sub0.copy())
            self.rows["B_sub0"].append(c.last_B_sub0.copy())
            self.rows["dec_ticks"].append(c.tick)
            self.rows["trending"].append([
                c.min_margen_causal if np.isfinite(c.min_margen_causal) else 0.0,
                c.max_abs_dtau, float(c.historia.high_water)])
            self.rows["clamp"].append(c.clamp_count)

    def registrar_paso(self, x_pre: np.ndarray, v_pre: np.ndarray) -> None:
        """Llamar DESPUÉS de caldo.step(), con (x, v) PRE-step (para el ledger W del
        sub-paso 0: f consumida en el estado del sub-paso 0)."""
        c = self.caldo
        if c.n_pairs:
            # W_ij += dt·(Σ_μ f_{i←j,μ}·v_iμ + Σ_ν f_{j←i,ν}·v_jν), f del sub-paso 0
            xs = x_pre[:, c.S_idx]; vs = v_pre[:, c.S_idx]
            i_idx, j_idx = c.pares[:, 0], c.pares[:, 1]
            n_s = float(c.n_s)
            # masas del RECEPTOR: (n_S,) homogéneo (ops selladas) ó fila por onion (het)
            mS_i = c.masa_S[None, :] if c.masa_S.ndim == 1 else c.masa_S[i_idx]
            mS_j = c.masa_S[None, :] if c.masa_S.ndim == 1 else c.masa_S[j_idx]
            f_i = (c.K / mS_i) * (c.last_fS_sub0[:, 0][:, None] - n_s * xs[i_idx])
            f_j = (c.K / mS_j) * (c.last_fS_sub0[:, 1][:, None] - n_s * xs[j_idx])
            self.W_acc += c.dt * ((f_i * vs[i_idx]).sum(1) + (f_j * vs[j_idx]).sum(1))
            if c.tick % self.n_caja == 0:
                self.W_cajas.append((c.tick, self.W_acc.copy()))
        self._fila()
        if len(self.rows["ticks"]) >= self.chunk_ticks:
            self._flush()

    def _flush(self):
        if not self.rows["ticks"]:
            return
        nombre = self.dir / "worldline" / f"chunk_{self.chunk_idx:05d}.npz"
        wc_t = np.array([t for t, _ in self.W_cajas], dtype=np.int64)
        wc_v = (np.stack([v for _, v in self.W_cajas])
                if self.W_cajas else np.zeros((0, self.caldo.n_pairs)))
        np.savez_compressed(
            nombre,
            ticks=np.array(self.rows["ticks"], dtype=np.int64),
            estados=np.stack(self.rows["estados"]),
            tau=np.stack(self.rows["tau"]),
            kicks=np.stack(self.rows["kicks"]),
            fS_sub0=(np.stack(self.rows["fS_sub0"])
                     if self.rows["fS_sub0"] else np.zeros((0, self.caldo.n_pairs, 2))),
            B_sub0=(np.stack(self.rows["B_sub0"])
                    if self.rows["B_sub0"] else np.zeros((0, self.caldo.n_pairs))),
            dec_ticks=np.array(self.rows["dec_ticks"], dtype=np.int64),
            trending_causal=(np.array(self.rows["trending"])
                             if self.rows["trending"] else np.zeros((0, 3))),
            clamp_count=np.array(self.rows["clamp"], dtype=np.int64),
            W_cajas_ticks=wc_t, W_cajas=wc_v,
            rng_states_json=json.dumps([str(r.bit_generator.state)
                                        for r in self.caldo.rngs]))
        self.chunk_shas.append(_sha(nombre.read_bytes()))
        self.W_cajas = []
        self.chunk_idx += 1
        self._reset_chunk()

    def close(self) -> str:
        self._flush()
        sha_total = _sha("".join(self.chunk_shas).encode())
        (self.dir / "COMPLETE").write_text(json.dumps(
            {"chunk_shas": self.chunk_shas, "sha_total": sha_total,
             "manifest_sha": self.manifest_sha,
             "ticks_totales": int(self.caldo.tick)}, indent=1))
        return _sha((sha_total + self.manifest_sha).encode())   # worldline_hash


# ─────────────────────────────── checkpoint ───────────────────────────────

def guardar_checkpoint(caldo: RedCaldo, path, *, seed: int, genoma_id: str,
                       run_id: str, manifest_sha: str) -> Path:
    h = caldo.historia
    span = h.tick_next - h.tick_min
    filas = (np.arange(h.tick_min, h.tick_next) % h.capacidad)
    meta = {"schema": "CHECKPOINT_CALDO_v2", "run_id": run_id,
            "manifest_sha": manifest_sha, "N": caldo.n, "n_pairs": caldo.n_pairs,
            "convencion_pares": "p=i*N-i*(i+1)/2+(j-i-1)",
            "ids_onion": [int(i) for i in caldo.ids],
            "fingerprint_extendido": fingerprint_extendido(caldo, seed, genoma_id),
            "pulso_consumido_hasta_tick": int(min(caldo.tick, caldo.ticks_pulso)),
            "dt": caldo.dt, "intervenida_linaje": False}
    path = Path(path)
    np.savez_compressed(
        path, tick=np.int64(caldo.tick),
        estados=np.concatenate([caldo.x, caldo.v, caldo.z, caldo.b, caldo.e], axis=1),
        tau=caldo.tau.copy(),
        historia=h.buf[filas].copy(),
        historia_tick0=np.int64(h.tick_min),
        rng_states_json=json.dumps([str(r.bit_generator.state) for r in caldo.rngs]),
        meta_json=json.dumps(meta, default=float))
    return path


def restaurar_checkpoint(spec, path, *, seed: int, genoma_id: str,
                         K: float, lam: float, tau_s: float,
                         T_pulso: float, ticks_pulso: int,
                         genoma_ids=None) -> RedCaldo:
    """Rehidrata un RedCaldo EXACTO. EXIGE fingerprint idéntico (fail-loud).
    spec: NodeSpec (homogéneo) o lista de NodeSpecs + genoma_ids (het, M2-build 1)."""
    import ast
    f = np.load(path, allow_pickle=False)
    meta = json.loads(str(f["meta_json"]))
    n = int(meta["N"])
    caldo = RedCaldo(spec, n, dt=float(meta["dt"]), seed=seed, K=K, lam=lam,
                     tau_s=tau_s, T_pulso=T_pulso, ticks_pulso=ticks_pulso,
                     T_rem=0.0, ticks_rem=0, ids=meta["ids_onion"],
                     genoma_ids=genoma_ids)
    fp = fingerprint_extendido(caldo, seed, genoma_id)
    if fp != meta["fingerprint_extendido"]:
        raise RuntimeError("checkpoint caldo: fingerprint extendido difiere — "
                           "constitución o constantes de campaña cambiadas (fail-loud)")
    est = f["estados"]
    ref = caldo.spec                       # het: arquitectura de referencia del lote
    nm, nz, nl = ref.n_modes, ref.n_z, ref.n_layers
    caldo.x = est[:, :nm].copy(); caldo.v = est[:, nm:2 * nm].copy()
    caldo.z = est[:, 2 * nm:2 * nm + nz].copy()
    caldo.b = est[:, 2 * nm + nz:2 * nm + nz + nl].copy()
    caldo.e = est[:, 2 * nm + nz + nl:].copy()
    caldo.tau = f["tau"].copy()
    caldo.tick = int(f["tick"])
    h = caldo.historia
    hist = f["historia"]
    tick0 = int(f["historia_tick0"])
    while h.capacidad < len(hist):
        h._crecer()
    h.tick_min = tick0
    h.tick_next = tick0 + len(hist)
    h.buf[(np.arange(tick0, h.tick_next) % h.capacidad)] = hist
    h.high_water = len(hist)
    estados_rng = json.loads(str(f["rng_states_json"]))
    for r, s in zip(caldo.rngs, estados_rng):
        r.bit_generator.state = ast.literal_eval(s)
    return caldo


# ─────────────────────────────── cápsula ───────────────────────────────

def guardar_capsula(caldo: RedCaldo, out_dir, *, seed: int, genoma_id: str,
                    run_id_origen: str, worldline_hash: str) -> Path:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    p = guardar_checkpoint(caldo, out / "capsula_caldo.npz", seed=seed,
                           genoma_id=genoma_id, run_id=run_id_origen,
                           manifest_sha="")
    man = {"schema": "CAPSULA_CALDO_v1", "run_id_origen": run_id_origen,
           "worldline_hash": worldline_hash, "tick_corte": int(caldo.tick),
           "fingerprint_extendido": fingerprint_extendido(caldo, seed, genoma_id),
           "ids_onion": [int(i) for i in caldo.ids], "genoma_block_id": genoma_id,
           "sha256_npz": _sha(p.read_bytes())}
    (out / "manifest_capsula.json").write_text(json.dumps(man, indent=1))
    return out


def hidratar_capsula(spec, cap_dir, **kw) -> RedCaldo:
    cap_dir = Path(cap_dir)
    man = json.loads((cap_dir / "manifest_capsula.json").read_text())
    npz = cap_dir / "capsula_caldo.npz"
    if _sha(npz.read_bytes()) != man["sha256_npz"]:
        raise RuntimeError("cápsula caldo: sha del npz difiere del manifiesto")
    caldo = restaurar_checkpoint(spec, npz, **kw)
    ventana = (caldo.historia.tick_next - caldo.historia.tick_min) * caldo.dt
    if caldo.n_pairs and float(caldo.tau.max()) > ventana:
        raise RuntimeError("cápsula caldo: max τ excede la ventana de historia portada "
                           "(fail-loud, CAPSULA_CALDO_SCHEMA)")
    return caldo
