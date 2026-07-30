"""Recorder de worldline — WORLDLINE_SCHEMA v1 (chunked, float64, COMPLETE atómico).

La película ES la fuente primaria de observación. Fila 0 = estado PRE-step; estados[tick] =
estado POST step número tick (la misma semántica de los fixtures de conformidad). Un film sin
COMPLETE no es un artefacto: no entra a ningún catálogo.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

import numpy as np

from ..engine.network import Network

# Claves que el CALLER debe aportar (PROVENANCE_CONTRACT): sin ellas el artefacto nace huérfano.
CLAVES_OBLIGATORIAS = ("run_id", "spec_tipo", "hashes_base_externa")


def _git_info(repo_root: Path) -> Dict:
    """git commit + dirty del código que corre — parte del manifiesto (A2). Sin git: declarado."""
    import subprocess
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root,
                                capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=repo_root,
                                    capture_output=True, text=True, timeout=10).stdout.strip())
        return {"commit": commit or "desconocido", "dirty": dirty}
    except Exception:
        return {"commit": "sin_git", "dirty": None}


def _flat(state) -> np.ndarray:
    return np.concatenate([state.x, state.v, state.z, state.b, state.e])


class WorldlineRecorder:
    """Escribe la worldline por chunks al nivel caliente (disco local). El archivado al nivel
    externo (copy-at-close + verificación + poda declarada) es responsabilidad de campañas —
    este recorder garantiza el artefacto local íntegro y verificable."""

    def __init__(self, out_dir: Path, net: Network, manifest: Dict, chunk_ticks: int = 4096):
        if chunk_ticks < 1:
            raise ValueError("chunk_ticks >= 1")
        self.dir = Path(out_dir)
        (self.dir / "worldline").mkdir(parents=True, exist_ok=False)   # corrida nueva SIEMPRE
        (self.dir / "checkpoints").mkdir(exist_ok=True)
        self.net = net
        self.chunk_ticks = int(chunk_ticks)
        self.n_nodes = len(net.specs)
        self.dims = [_flat(s).size for s in net.states]
        self._chunk_idx = 0
        self._rows: List[List[np.ndarray]] = [[] for _ in range(self.n_nodes)]
        self._drive: List[np.ndarray] = []
        self._kicks: List[List[np.ndarray]] = [[] for _ in range(self.n_nodes)]
        self._ticks_en_chunk: List[int] = []
        self._chunk_shas: List[str] = []
        self._closed = False
        self._tick_actual = 0
        # el estado del RNG al INICIO del chunk (replay/continuación por chunk)
        self._rng_state_chunk = json.dumps(net.noise_rng.bit_generator.state, default=str)

        faltan = [k for k in CLAVES_OBLIGATORIAS if k not in manifest]
        if faltan:
            raise ValueError(f"manifiesto sin claves obligatorias {faltan} — un artefacto sin "
                             "run_id/spec_tipo/hashes_base_externa nace huérfano "
                             "(PROVENANCE_CONTRACT; double tap F3 A2)")
        if manifest["spec_tipo"] not in ("M1", "M2"):
            raise ValueError(f"spec_tipo={manifest['spec_tipo']!r}: debe ser M1 o M2")
        import platform
        manifest = dict(manifest)
        manifest.update({
            "schema": "study07_worldline_v1",
            "n_nodes": self.n_nodes, "dims": self.dims,
            "por_nodo": [{"n_modes": sp.n_modes, "n_z": sp.n_z, "n_layers": sp.n_layers}
                         for sp in net.specs],
            "dt": net.dt, "seed": net.seed, "temperature": net.temperature,
            "k_global": net.k_global, "gamma_c": net.gamma_c,
            "topologia": {"edges_ij": net.edge_ij.tolist(), "w_k": net.edge_w_k.tolist(),
                          "w_gamma": net.edge_w_g.tolist(), "tau": net.edge_tau.tolist()},
            "perfil": manifest.get("perfil", "conformidad"),
            "entorno": {"python": platform.python_version(), "numpy": np.__version__,
                        "machine": platform.machine()},
            "git": _git_info(Path(__file__).resolve().parents[3]),
            "chunk_ticks": self.chunk_ticks,
            "semantica": ("fila 0 del chunk 0 = estado PRE-step; estados[tick] = POST step "
                          "numero tick; drive[k] = fuerza KV del sub-paso 0 del step k; "
                          "noise_kick[k] = incremento estocastico aplicado en el step k; "
                          "rng_state = estado del generator al INICIO del chunk; "
                          "t = tick * dt (derivado, no almacenado)"),
        })
        cuerpo = json.dumps(manifest, indent=1, default=str)
        (self.dir / "manifest.json").write_text(cuerpo)
        self._manifest_sha = hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()
        # fila 0: PRE-step
        for j, st in enumerate(net.states):
            self._rows[j].append(_flat(st).copy())
        self._drive.append(np.zeros(self.n_nodes))
        for j in range(self.n_nodes):
            self._kicks[j].append(np.zeros(net.specs[j].n_modes))
        self._ticks_en_chunk.append(0)

    def record_step(self) -> None:
        """Llamar DESPUÉS de net.step(): registra estado POST-step + info causal del paso."""
        if self._closed:
            raise RuntimeError("recorder cerrado")
        self._tick_actual += 1
        for j, st in enumerate(self.net.states):
            self._rows[j].append(_flat(st).copy())
            self._kicks[j].append(self.net.last_noise_kicks[j].copy())
        self._drive.append(self.net.last_drive0.copy())
        self._ticks_en_chunk.append(self._tick_actual)
        if len(self._ticks_en_chunk) >= self.chunk_ticks:
            self._flush_chunk()

    def _flush_chunk(self) -> None:
        if not self._ticks_en_chunk:
            return
        arrays = {"ticks": np.asarray(self._ticks_en_chunk, dtype=np.int64),
                  "drive": np.stack(self._drive),
                  "rng_state_json": np.array(self._rng_state_chunk)}
        for j in range(self.n_nodes):
            arrays[f"estados_nodo{j}"] = np.stack(self._rows[j])
            arrays[f"kicks_nodo{j}"] = np.stack(self._kicks[j])
        path = self.dir / "worldline" / f"chunk_{self._chunk_idx:05d}.npz"
        tmp = path.with_name(path.stem + ".tmp.npz")   # savez appendea .npz: el tmp lo trae
        np.savez_compressed(tmp, **arrays)
        tmp.rename(path)                               # rename atómico: nunca un chunk a medias
        self._chunk_shas.append(hashlib.sha256(path.read_bytes()).hexdigest())
        self._chunk_idx += 1
        self._rows = [[] for _ in range(self.n_nodes)]
        self._drive = []
        self._kicks = [[] for _ in range(self.n_nodes)]
        self._ticks_en_chunk = []
        self._rng_state_chunk = json.dumps(self.net.noise_rng.bit_generator.state, default=str)

    def save_checkpoint(self) -> Path:
        from .checkpoint import save_checkpoint
        return save_checkpoint(self.dir / "checkpoints" / f"ck_{self._tick_actual:08d}.npz",
                               self.net, self._tick_actual)

    def close(self) -> str:
        """Cierre ATÓMICO: flush del último chunk + COMPLETE con el hash del conjunto.
        Si el proceso muere antes, NO hay COMPLETE y el film no es un artefacto."""
        if self._closed:
            raise RuntimeError("ya cerrado")
        self._flush_chunk()
        agregado = hashlib.sha256()
        for sha in self._chunk_shas:
            agregado.update(bytes.fromhex(sha))
        total = agregado.hexdigest()
        cuerpo = json.dumps({"ticks": self._tick_actual, "chunks": len(self._chunk_shas),
                             "chunk_shas": self._chunk_shas, "sha_total": total,
                             "manifest_sha": self._manifest_sha}, indent=1)
        tmp = self.dir / "COMPLETE.tmp"
        tmp.write_text(cuerpo)
        tmp.rename(self.dir / "COMPLETE")          # rename atómico en el mismo filesystem
        self._closed = True
        return total


def load_worldline(run_dir: Path, allow_incomplete: bool = False) -> Dict:
    """Lector: verifica COMPLETE + hashes de cada chunk, reensambla sin pérdida ni duplicado.
    Un film sin COMPLETE levanta fail-loud salvo pedido EXPLÍCITO (auditoría de restos)."""
    run_dir = Path(run_dir)
    manifest_txt = (run_dir / "manifest.json").read_text()
    manifest = json.loads(manifest_txt)
    complete = run_dir / "COMPLETE"
    if not complete.exists():
        if not allow_incomplete:
            raise RuntimeError(f"{run_dir}: SIN COMPLETE — no es un artefacto "
                               "(interrupción o corrida viva); allow_incomplete=True sólo "
                               "para auditoría de restos")
        marca = None
    else:
        marca = json.loads(complete.read_text())
        sha_man = hashlib.sha256(manifest_txt.encode("utf-8")).hexdigest()
        if marca.get("manifest_sha") != sha_man:
            raise RuntimeError("manifest.json fue ALTERADO después del COMPLETE (inmutabilidad "
                               "post-cierre, WORLDLINE_SCHEMA regla 2 / double tap F3 A3)")
    chunks = sorted((run_dir / "worldline").glob("chunk_*.npz"))
    if marca is not None:
        if len(chunks) != marca["chunks"]:
            raise RuntimeError(f"chunks en disco {len(chunks)} != COMPLETE {marca['chunks']}")
        for path, sha_esp in zip(chunks, marca["chunk_shas"]):
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if sha != sha_esp:
                raise RuntimeError(f"{path.name}: sha {sha[:12]} != COMPLETE {sha_esp[:12]}")
    n = int(manifest["n_nodes"])
    estados = [[] for _ in range(n)]
    drive, ticks = [], []
    kicks = [[] for _ in range(n)]
    rng_states = []
    chunks_malos = []
    for path in chunks:
        try:
            fx = np.load(path, allow_pickle=False)
        except Exception as exc:                       # A5: restos legibles hasta el chunk roto
            if marca is not None:
                raise
            chunks_malos.append((path.name, repr(exc)))
            break
        ticks.append(np.asarray(fx["ticks"]))
        drive.append(np.asarray(fx["drive"]))
        rng_states.append(str(fx["rng_state_json"]))
        for j in range(n):
            estados[j].append(np.asarray(fx[f"estados_nodo{j}"]))
            kicks[j].append(np.asarray(fx[f"kicks_nodo{j}"]))
    ticks = np.concatenate(ticks) if ticks else np.zeros(0, dtype=np.int64)
    esperado = np.arange(len(ticks))
    if not np.array_equal(ticks, esperado):
        raise RuntimeError("ticks no consecutivos: pérdida o duplicado entre chunks")
    # A3: el manifiesto declarado debe corresponder a las formas reales
    if len(estados) != int(manifest["n_nodes"]):
        raise RuntimeError("n_nodes del manifiesto no coincide con los canales del film")
    for j, e in enumerate(estados):
        if e and e[0].shape[1] != manifest["dims"][j]:
            raise RuntimeError(f"dims[{j}] del manifiesto no coincide con el film")
    return {"manifest": manifest, "ticks": ticks, "chunks_malos": chunks_malos,
            "estados": [np.concatenate(e) for e in estados],
            "drive": np.concatenate(drive) if drive else np.zeros((0, n)),
            "kicks": [np.concatenate(k) for k in kicks],
            "rng_states_chunk": rng_states,
            "complete": marca is not None}
