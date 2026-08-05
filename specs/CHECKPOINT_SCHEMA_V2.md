# CHECKPOINT_SCHEMA_V2 — checkpoints del motor τ (caldo)

Extiende CHECKPOINT_SCHEMA v1 SOLO para redes caldo (v1 intocado para v1-KV).
Gate permanente: **directa-vs-restore BIT-EXACTA con pulso a caballo** — checkpoint en
tick_ck ∈ (0, ticks_pulso), comparación exacta de X, τ, RNG y worldline hasta
2·ticks_pulso.

## ck_XXXXXXXX.npz

| clave | shape | dtype | semántica |
|---|---|---|---|
| tick | () | int64 | tick del checkpoint (estado POST step tick) |
| estados | (N, dim) | float64 | X exacto |
| tau | (n_pairs,) | float64 | τ exacto, orden p, U.T. |
| historia | (W_ck, N, n_S, 2) | float64 | ventana de historia causal suficiente para continuar: (x_ν, v_ν) de modos S |
| historia_tick0 | () | int64 | tick de la fila 0 de historia (timestamps = tick0+k, DERIVADOS) |
| rng_states_json | () | str | N estados de bit_generator por id_onion |
| meta_json | () | str | ver abajo |

## meta_json (claves obligatorias)

`schema: "CHECKPOINT_CALDO_v2"`, `run_id`, `manifest_sha`, `N`, `n_pairs`,
`convencion_pares`, `ids_onion`, `fingerprint_extendido` = sha256 canónico de
{constitución del genoma} ∪ {K, lambda, tau_s_ut, kappa_pico, calendario_pulso,
seed_campaña} (bug-class kappa_global/K_global cerrado), `pulso_consumido_hasta_tick`
(int64 — cuántos ticks de kicks se consumieron; T(t) por tramos se re-deriva del
calendario + este tick), `dt`, `intervenida_linaje` (heredado v1).
Continuación: EXIGE fingerprint_extendido idéntico; RedCaldo.desde_checkpoint rehidrata
historia+RNG+τ y el primer paso post-restore es bit-idéntico al directo (gate).
