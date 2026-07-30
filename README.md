# DOFT — Study07 (worldline-first)

**Nace 2026-07-29** del congelamiento de Study06 (`study06-freeze-20260729`). Motor diferencial
mínimo → worldline causal completa → instrumentos offline como vistas. La física validada de
Study06 **no se reescribe: se porta por comportamiento** contra fixtures de conformidad, con
Study06 congelado como oráculo ejecutable.

## Las cuatro cláusulas de COA (2026-07-29 — gobiernan la arquitectura)

1. **El motor NO interpreta proxies para transferir fronteras entre olas.** Genera ola1,
   ola1+ola2, ola1+ola2+ola3: integración concurrente de constituyentes COMPLETOS. El motor no
   sabe qué es una ola — las olas son niveles de composición, catálogo e instrumentación, jamás
   fronteras físicas. (Gate de CI: `src/study07/physics/` no contiene la palabra "ola".)
2. **Resultados por ola**: visibilidad de onions (ola1), grumos (ola2) y clusters (ola3/n) como
   VISTAS de instrumentos sobre la misma worldline — incluido medir al individuo EMBEBIDO en la
   red y compararlo con su rama aislada.
3. **Instrumentos separados del motor**, construcción iterativa ola a ola (resultado a
   resultado), con gate por iteración: ola1 contra los fixtures + hechos onion certificados;
   ola2 contra el rerun corregido §88/§89; ola3 con la disciplina ya probada dos veces.
4. **El núcleo de ola1 no cambia**: la ley (verificada idéntica entre los dos integradores de
   Study06) se transcribe; lo que cambia es la ENVOLTURA (recorder, guardas fail-loud, captura
   de RNG, políticas de contorno DECLARADAS).

## Arquitectura

```
INVENTARIO por nivel (onions / grumos / clusters: constitución + checkpoint + pasaporte)
      ↑ cosecha                                  ↓ hidrata
   EXPLORER  ──────→  SPEC DE CORRIDA [M1 | M2]  ──→  MOTOR (agnóstico) ──→ WORLDLINE
                       (validador: una spec M2               │
                        no puede violar la doctrina)         ↓
                                              INSTRUMENTOS offline (vistas por nivel)
                                                             ↓
                                              resultados por ola → catálogo
```

```
physics <- engine <- artifacts
   ^                    |
   +------ instruments -+        (dependencias unidireccionales, verificadas)
```

## Los contratos (se escriben ANTES que el motor)

| Spec | Qué sella |
|---|---|
| `specs/PHYSICS_CONTRACT.md` | la ley x,v,z,b,e + RK4 + delay + acople KV + ruido/RNG + las 8 perillas + decisiones de contorno |
| `specs/WORLDLINE_SCHEMA.md` | la película: fila 0 PRE-step, float64, perfiles conformidad/campaña, COMPLETE atómico, ramas hijas |
| `specs/CHECKPOINT_SCHEMA.md` | continuación exacta: estado + buffers + RNG + reloj + linaje |
| `specs/INSTRUMENT_CONTRACT.md` | vistas read-only con canales declarados, versión y hash; jamás ejecutan el motor |
| `specs/EXPERIMENT_CONTRACT.md` | **M1 y M2 como tipos formales validados** + el explorer como productor de inventario |
| `specs/PROVENANCE_CONTRACT.md` | §92 (modelos) + hashes de base externa en toda salida + manifiestos |

## El oráculo

Study06 congelado: ver `docs/STUDY06_ORACLE.md`. Fixtures de conformidad ya generados y
versionados allá (`tests/fixtures/study07_*.npz`), tolerancia **medida** 3.86e-11, ley núcleo
~374 líneas mapeadas rango por rango, 150 cápsulas v4 verificadas exactas en transporte
(80 sondas, residuo 0).

## Plan de fases (audit Study06 §20.9, con gates)

F0 congelamiento (HECHO en Study06) → F1 specs+fixtures → F2 motor mínimo (gate: fixtures a
3.86e-11 + gate arquitectónico) → F3 film+checkpoint (gate: restore bit-exacto) → F4 primer
instrumento offline (gate: dos ventanas sobre la MISMA película sin re-simular) → F5 inventario
v4 + composición concurrente → F6 intervenciones (worldlines hijas) → F7 campañas.
