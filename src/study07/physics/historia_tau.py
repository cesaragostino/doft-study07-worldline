"""Historia causal del caldo τ [SPEC_MOTOR_TAU_V1 §3 + §12.11 — guarda 4].

UN array (W_ticks, N, n_S, 2) float64 contiguo, indexado por TICK int64 módulo W_ticks
(«por onion» es la vista, no el almacenamiento). PROHIBIDO pre-llenar con t=0: la
historia arranca con la ÚNICA fila del estado remanente en tick 0 (t_pulso ≡ 0, burn-in
FUERA del calendario — spec §12.6). Timestamps = tick·dt DERIVADO, jamás float
acumulado. Consulta más vieja que la ventana retenida = EXCEPCIÓN (fail-loud); la
consulta pre-pulso (t_src < 0) NO llega acá: el motor aplica J≡0 antes (cero causal).
Crecimiento amortizado ×2 hasta el tope declarado; recién al tope se vuelve ring y
descarta lo más viejo; high-water registrado.
Interpolación: HERMITE CÚBICA en x con el v almacenado (error O(dt⁴), consistente con
RK4 — spec §2.3); v retardada = derivada del Hermite (O(dt³); solo va al registro,
ℬ no la usa). La rama solapada (t_src > último tick) NO es de este módulo: el motor la
sirve con Hermite DE ETAPA (spec §12.4).
"""
from __future__ import annotations

import numpy as np


class HistoriaCaldo:
    def __init__(self, n_onions: int, n_s: int, dt: float,
                 w_ticks_ini: int = 1 << 17, w_ticks_max: int = 1 << 21) -> None:
        if w_ticks_ini < 2 or w_ticks_max < w_ticks_ini:
            raise ValueError("ventana: se exige 2 <= w_ini <= w_max")
        self.n = int(n_onions)
        self.n_s = int(n_s)
        self.dt = float(dt)
        self.w_max = int(w_ticks_max)
        self.buf = np.zeros((int(w_ticks_ini), self.n, self.n_s, 2), dtype=np.float64)
        self.tick_min = 0            # tick más viejo retenido
        self.tick_next = 0           # próximo tick a escribir (= filas escritas)
        self.high_water = 0          # máximo span retenido (ticks)

    @property
    def capacidad(self) -> int:
        return self.buf.shape[0]

    def _crecer(self) -> None:
        nueva_cap = min(self.capacidad * 2, self.w_max)
        nuevo = np.zeros((nueva_cap, self.n, self.n_s, 2), dtype=np.float64)
        span = self.tick_next - self.tick_min
        idx = (np.arange(self.tick_min, self.tick_next) % self.capacidad)
        nuevo[np.arange(self.tick_min, self.tick_next) % nueva_cap] = self.buf[idx]
        self.buf = nuevo

    def push(self, x_s: np.ndarray, v_s: np.ndarray) -> None:
        """Escribe la fila del tick_next (POST-kick — spec §2.4). x_s/v_s: (N, n_S)."""
        if x_s.shape != (self.n, self.n_s) or v_s.shape != (self.n, self.n_s):
            raise ValueError(f"push: shapes {x_s.shape}/{v_s.shape} != ({self.n},{self.n_s})")
        span = self.tick_next - self.tick_min
        if span >= self.capacidad:
            if self.capacidad < self.w_max:
                self._crecer()
            else:
                self.tick_min += 1            # ring: descarta lo más viejo (al tope)
        fila = self.tick_next % self.capacidad
        self.buf[fila, :, :, 0] = x_s
        self.buf[fila, :, :, 1] = v_s
        self.tick_next += 1
        self.high_water = max(self.high_water, self.tick_next - self.tick_min)

    def consulta(self, onions: np.ndarray, t_src: np.ndarray):
        """(x, v) retardados por HERMITE para cada (onion_k, t_src_k). Devuelve
        (M, n_S) × 2. EXIGE tick_min·dt ≤ t_src ≤ (tick_next−1)·dt — lo anterior a la
        ventana es EXCEPCIÓN; lo posterior (rama solapada) no es de este módulo."""
        if self.tick_next == 0:
            raise RuntimeError("historia vacía: no hay fila de remanente (guarda 4)")
        t_src = np.asarray(t_src, dtype=np.float64)
        onions = np.asarray(onions, dtype=np.int64)
        if self.tick_next < 2:
            # una sola fila (génesis exacto): t_src solo puede ser el tick 0
            if np.any(t_src < 0.0) or np.any(t_src > 0.0):
                raise RuntimeError("historia de una fila: solo t_src=0 es consultable")
            x0 = self.buf[0 % self.capacidad, onions]
            return x0[:, :, 0], x0[:, :, 1]
        k = np.floor(t_src / self.dt).astype(np.int64)
        theta = t_src / self.dt - k                       # ∈ [0,1)
        # borde derecho exacto: t_src == último tick
        tope = self.tick_next - 1
        en_tope = k >= tope
        k = np.where(en_tope, tope - 1, k)
        theta = np.where(en_tope, 1.0, theta)
        if np.any(k < self.tick_min):
            raise RuntimeError(
                f"consulta pre-ventana: tick {int(k.min())} < retenido {self.tick_min} "
                "— sub-retención del buffer (fail-loud, spec §1.3)")
        f0 = self.buf[k % self.capacidad, onions]         # (M, n_S, 2)
        f1 = self.buf[(k + 1) % self.capacidad, onions]
        x0, v0 = f0[:, :, 0], f0[:, :, 1]
        x1, v1 = f1[:, :, 0], f1[:, :, 1]
        th = theta[:, None]
        h = self.dt
        h00 = 2 * th ** 3 - 3 * th ** 2 + 1
        h10 = th ** 3 - 2 * th ** 2 + th
        h01 = -2 * th ** 3 + 3 * th ** 2
        h11 = th ** 3 - th ** 2
        x = h00 * x0 + h10 * h * v0 + h01 * x1 + h11 * h * v1
        d00 = 6 * th ** 2 - 6 * th
        d10 = 3 * th ** 2 - 4 * th + 1
        d01 = -6 * th ** 2 + 6 * th
        d11 = 3 * th ** 2 - 2 * th
        v = (d00 * x0 / h + d10 * v0 + d01 * x1 / h + d11 * v1)
        return x, v
