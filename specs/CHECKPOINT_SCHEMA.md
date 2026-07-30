# CHECKPOINT_SCHEMA — continuación exacta (v1, sellado 2026-07-30 tras double tap F3)

El checkpoint es un artefacto DISTINTO de la película: la película observa; el checkpoint
CONTINÚA o BIFURCA (worldlines hijas). Gate permanente: directa vs restore→continuación
BIT-exactas, con T>0 (el RNG viaja).

## Contenido (implementado en artifacts/checkpoint.py, formato npz + meta_json)
- Estado float64 COMPLETO de todos los nodos: x, v, z, b, e.
- Buffer de historia COMPLETO + head (restauración no-uniforme — la API de las cápsulas).
- Estado del bit_generator (continuación exacta del stream de ruido).
- Reloj: tick (la continuación NO lo renumera hacia el film madre: el empalme lo administra el
  linaje del catálogo — declarado, no implícito).
- **Parámetros del motor VIAJAN**: k_global, gamma_c, temperature, dt, seed + topología completa
  (aristas ij/w_k/w_gamma/τ). Restaurar sin ellos producía k_global=0.0 silencioso con
  divergencia 3.6e-04 (double tap F3 A4) — ya no hay camino silencioso.
- **Huella de constitución por nodo** (`spec_fingerprint`: modos, intra, links, memoria, W,
  struct SIN e_ref): `network_from_checkpoint` la VERIFICA fail-loud — una continuación con otra
  física no puede ser silenciosa (medido: gamma×1.5 divergía 1.1e-06 sin excepción).
- e_ref por nodo/capa (muta por política sólo al nacer; el checkpoint lo transporta y lo aplica).
- Escritura atómica: tmp .npz + rename.

## Reglas
1. `network_from_checkpoint(specs, ck)` NO acepta overrides: otros parámetros = otra corrida
   (Network directo + linaje propio de hija).
2. El cursor de eventos/intervenciones llega con F6 (worldlines hijas) — declarado pendiente.
3. Linaje completo (hash de la constitución de ORIGEN en catálogo) = PROVENANCE_CONTRACT.
