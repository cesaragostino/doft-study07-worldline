# WORLDLINE_CALDO_SCHEMA v1 — worldline del motor τ (caldo)

Versión propia: NADA re-significa worldlines v1-KV (WORLDLINE_SCHEMA.md intocado).
Convenciones globales: **tick int64; t ≡ tick·dt DERIVADO** (jamás float acumulado).
Pares: orden lexicográfico (i<j), **índice p = i·N − i·(i+1)/2 + (j−i−1)** — el MISMO p
ordena TODOS los canales de par (tau, fS, B, W_cajas) y los artefactos (checkpoint,
cápsula). Onions: eje 0..N−1 en orden de id_onion (identidad estable del génesis).

## Chunks (worldline/chunk_XXXXX.npz), chunk_ticks=16384 declarado en manifiesto

| clave | shape | dtype | semántica |
|---|---|---|---|
| ticks | (T,) | int64 | ticks absolutos del chunk (fila 0 chunk 0 = estado PRE-step t=0) |
| estados | (T, N, dim) | float64 | X apilado por onion (layout de state._flat, dim=33 genoma canónico); estados[k] = POST step tick k |
| tau | (T, n_pairs) | float64 | τ_ij en U.T., orden p; tau[k] = POST step |
| fS_sub0 | (T_dec, 2, n_pairs) | float64 | sumas retardadas colapsadas CONSUMIDAS en sub-paso 0: [0]=S_j(t_src) (→i), [1]=S_i(t_src) (→j); DECIMADO ×32 (ticks_dec en meta) |
| B_sub0 | (T_dec, n_pairs) | float64 | ℬ_ij del sub-paso 0, decimado ×32 |
| W_cajas | (T_caja, n_pairs) | float64 | ledger W_ij integrado A TASA COMPLETA por el recorder, volcado por cajas de N_caja ticks |
| kicks | (T, N, n_modes) | float64 | kicks FDT por onion (0 fuera del pulso) |
| rng_states_json | () | str | N estados de bit_generator al INICIO del chunk (json list por id_onion) |
| trending_causal | (T_dec, 3) | float64 | [min_p(t−τ−0), max_p|dτ/dt|, high_water_ret] |
| clamp_count | (T_dec,) | int64 | activaciones del clamp de respaldo τ←max(τ,0) |

Segmentos FULL declarados en manifiesto (génesis [0, 5 u.t.] + ventanas de eventos):
chunks con fS_sub0/B_sub0 SIN decimar, flag `full_rate=true` en el nombre del chunk.

## Manifiesto (manifest.json) — claves adicionales a las heredadas de v1

`schema: "WORLDLINE_CALDO_v1"`, `N`, `n_pairs`, `convencion_pares: "p=i*N-i*(i+1)/2+(j-i-1)"`,
`ids_onion: [0..N-1]`, `genoma_block_id`, `K`, `lambda`, `tau_s_ut`, `kappa_pico: 3.5`,
`A_pulso_formula`, `calendario_pulso: {T_pulso, ticks_pulso, T_rem, ticks_rem}`,
`dt`, `chunk_ticks`, `dec_factor: 32`, `N_caja`, `segmentos_full: [[t0,t1],...]`,
`orden_integrador_medido`, `semantica`: «fila 0 = PRE-step; estados/tau[k] = POST step k;
fS_sub0/B_sub0 = consumido/emitido en el sub-paso 0 del step k (convención drive[n]);
t ≡ tick·dt; burn-in del remanente FUERA del calendario (trayectoria descartada)».
