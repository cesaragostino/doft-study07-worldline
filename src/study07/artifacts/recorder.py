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

        manifest = dict(manifest)
        manifest.update({
            "schema": "study07_worldline_v1",
            "n_nodes": self.n_nodes, "dims": self.dims,
            "dt": net.dt, "seed": net.seed, "temperature": net.temperature,
            "chunk_ticks": self.chunk_ticks,
            "semantica": ("fila 0 del chunk 0 = estado PRE-step; estados[tick] = POST step "
                          "numero tick; drive[k] = fuerza KV del sub-paso 0 del step k; "
                          "noise_kick[k] = incremento estocastico aplicado en el step k; "
                          "rng_state = estado del generator al INICIO del chunk"),
        })
        (self.dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
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
        np.savez_compressed(path, **arrays)
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
                             "chunk_shas": self._chunk_shas, "sha_total": total}, indent=1)
        tmp = self.dir / "COMPLETE.tmp"
        tmp.write_text(cuerpo)
        tmp.rename(self.dir / "COMPLETE")          # rename atómico en el mismo filesystem
        self._closed = True
        return total


def load_worldline(run_dir: Path, allow_incomplete: bool = False) -> Dict:
    """Lector: verifica COMPLETE + hashes de cada chunk, reensambla sin pérdida ni duplicado.
    Un film sin COMPLETE levanta fail-loud salvo pedido EXPLÍCITO (auditoría de restos)."""
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    complete = run_dir / "COMPLETE"
    if not complete.exists():
        if not allow_incomplete:
            raise RuntimeError(f"{run_dir}: SIN COMPLETE — no es un artefacto "
                               "(interrupción o corrida viva); allow_incomplete=True sólo "
                               "para auditoría de restos")
        marca = None
    else:
        marca = json.loads(complete.read_text())
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
    for path in chunks:
        fx = np.load(path, allow_pickle=False)
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
    return {"manifest": manifest, "ticks": ticks,
            "estados": [np.concatenate(e) for e in estados],
            "drive": np.concatenate(drive) if drive else np.zeros((0, n)),
            "kicks": [np.concatenate(k) for k in kicks],
            "rng_states_chunk": rng_states,
            "complete": marca is not None}
