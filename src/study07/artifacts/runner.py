"""Runner mínimo — integra y registra. Vive en artifacts (NO en engine: el motor jamás importa
hacia arriba — gate de dependencias unidireccionales).

Guardas de blow-up: ACÁ, fail-loud (PHYSICS_CONTRACT §8) — abortan, jamás alteran trayectoria.
"""
from __future__ import annotations

import numpy as np

from ..engine.network import Network
from .recorder import WorldlineRecorder


def run(net: Network, ticks: int, recorder: WorldlineRecorder | None = None,
        checkpoint_every: int | None = None, finite_check_every: int = 256) -> None:
    for tick in range(1, int(ticks) + 1):
        net.step()
        if recorder is not None:
            recorder.record_step()
        if finite_check_every and tick % finite_check_every == 0:
            for j, st in enumerate(net.states):
                if not (np.all(np.isfinite(st.x)) and np.all(np.isfinite(st.v))
                        and np.all(np.isfinite(st.z)) and np.all(np.isfinite(st.b))
                        and np.all(np.isfinite(st.e))):
                    raise FloatingPointError(
                        f"blow-up: no-finito en nodo {j} al tick {tick} — el runner ABORTA "
                        "fail-loud (contrato §8); la trayectoria no se altera jamás")
        if recorder is not None and checkpoint_every and tick % checkpoint_every == 0:
            recorder.save_checkpoint()
