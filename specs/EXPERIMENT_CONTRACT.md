# EXPERIMENT_CONTRACT — M1 y M2 como tipos FORMALES + el explorer [BORRADOR — Fase 1]

**Origen**: doctrina METODO de Study06 (COA), vuelta EJECUTABLE — "ese tema de M1 y M2 cambia el
soft" (COA 2026-07-29). El validador de specs hace imposibles-en-silencio las violaciones que
Study06 descubrió por panel.

## Spec [M1] — el microscopio
- `composicion`: elementos EXPLÍCITOS por hash (block_ids / checkpoint de grumo) — "elegir la
  entrada". Componer a cualquier nivel = "separar por olas" (1 onion; N+aristas; etc.).
- `intervenciones`: timeline declarado (kick/twin/hotcut/cirugía) ⇒ worldlines HIJAS.
- horizontes libres, instrumentos zoom. PORQUÉ declarado antes de correr (regla M1 heredada).

## Spec [M2] — obligatorio, validado
El validador RECHAZA una spec [M2] si: población ≠ inventario COMPLETO del nivel anterior (hash
del catálogo; el 67/150 de §84 sería ERROR DE VALIDACIÓN, no hallazgo de panel) · hay
intervenciones (M2 = aristas ON desde t=0, evolución libre) · hay filtro de instrumento
decidiendo quién cuenta (gate-portero no compila) · horizonte < horizonte de emergencia
declarado · reglas de clasificación sin sellar en el prereg · reporte ≠ población completa
(los "aburridos" son datos).

## El explorer — cliente del motor, iterador de M2 entre niveles
Propone constituciones (ola1: genomas; ola2+: composiciones naturales sobre el inventario
completo del nivel anterior) → emite specs [M2] → corre → COSECHA checkpoints+pasaportes al
inventario del nivel siguiente. Recursivo: inventario_N → explorer → M2 → inventario_N+1.
Nunca vive dentro del integrador. La probeta GOLD acompaña toda corrida M2 (regla heredada).
