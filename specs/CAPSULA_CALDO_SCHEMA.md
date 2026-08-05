# CAPSULA_CALDO_SCHEMA v1 — continuación de caldos entre olas

Artefacto NUEVO (no extensión de la cápsula de onion v1). Un caldo continúa a otra ola
con TODO su estado causal. Versionado propio.

## capsula_caldo.npz + manifest_capsula.json

| clave | shape | dtype |
|---|---|---|
| estados | (N, dim) | float64 |
| tau | (n_pairs,) | float64 (U.T.) |
| historia | (W_cap, N, n_S, 2) | float64 |
| historia_tick0 | () | int64 |
| rng_states_json | () | str |
| b_e_incluidos | — | (en estados; la biografía VIAJA — contrato §10 v0/§1 v1) |

manifest_capsula.json: `schema: "CAPSULA_CALDO_v1"`, `run_id_origen`, `worldline_hash`,
`tick_corte` (int64), `fingerprint_extendido`, `ids_onion` (identidades ESTABLES que
persisten entre olas — no se re-sortean, contrato v0 §2 heredado), `genoma_block_id`,
`sha256` de cada array. La hidratación en la ola siguiente verifica fingerprint y
worldline_hash del origen (patrón cápsula v1: pinneada por sha en la spec de la
campaña consumidora). PROHIBIDO: cápsula sin historia suficiente para las consultas
τ actuales (fail-loud al hidratar si max τ > ventana portada).
