# PHYSICS_CONTRACT — la ley y sus decisiones de contorno [BORRADOR — Fase 1]

**Estado**: esqueleto con lo SELLADO el 2026-07-29; la transcripción término a término se hace
LEYENDO el oráculo (rangos en docs/STUDY06_ORACLE.md), no de memoria.

## Sellado (COA 2026-07-29)
1. **Ley v1 = `direct-only`** (la de la población v4): resortes directos g0 + memoria activa por
   capa (z/W) + feedback b/e + acople KV retardado entre onions. El kernel histórico
   `inter_couplings.taus0/amps0` queda **DIFERIDO con medición citada**: perturbativo en
   trayectoria real (0.2%-4.4% de F_direct, panel de 4, §93-C5 de Study06); si se evalúa, será
   por experimento on/off M1 en este motor — jamás "transportado por implicación".
2. **dt configurado explícito** (la población v4 nació `require_configured_dt`, sin cap). El dt
   SIEMPRE se lee del contrato/cápsula, jamás se re-infiere de un eje temporal (causa raíz del
   bug del kernel de §90).
3. **Guardas de blow-up**: en el RUNNER como fail-loud (abortan, JAMÁS alteran trayectoria).
   El motor no guarda; el recorder valida finitud por chunk.
4. **Ruido FDT**: un solo Generator con semilla derivada declarada; los incrementos y el estado
   del RNG son parte del contrato de worldline (reproducibles con numpy pineado).
5. **e_ref_policy**: se DECLARA por corrida (`receiver_initial_energy` | `preserve_serialized`),
   default el de la cápsula; nunca implícito.
6. **Las 8 perillas** (audit Study06 §21.2) se transcriben una por una con su semántica:
   mem_force_scale · b_omega/b_kcoup · máscaras de hotcut (fuera del motor: son intervenciones)
   · e_ref_policy · emission_norm/emission_scale · derivación de semillas (x0/v0 en runtime) ·
   eps_omega/eps_k/clamp_tanh_arg · convención de sub-paso del delay.
7. **Una sola implementación de la fuerza**: el RHS puede devolver contribuciones nombradas;
   PROHIBIDA una segunda copia de las ecuaciones (la lección del force_ledger).
8. Cláusula 1 de COA: `physics/` es agnóstico de nivel — la palabra "ola" no existe acá.

## Por transcribir en Fase 1 (contra el oráculo)
- [ ] RHS x,v,z,b,e término a término con orden de acumulación (self→intra→direct→memoria→b/e)
- [ ] RK4 (orden exacto de los 4 sub-pasos) + kick FDT post-RK4
- [ ] Delay: buffer, head, interpolación fraccional, offsets por sub-paso
- [ ] KV por arista + normalización wsum + la cláusula grado≤7
- [ ] Inicialización v4 (memoria serializada exacta, struct_params, x0/v0 por _node_seed)
- [ ] Energías por capa
