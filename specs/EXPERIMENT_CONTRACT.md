# EXPERIMENT_CONTRACT — M1 y M2 como tipos FORMALES + el explorer

**Estado**: sección [M2]/campañas SELLADA en F7 (ejecutable en `artifacts/campana.py`);
explorer sigue BORRADOR.

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

## Cláusulas EJECUTABLES (selladas F7, double tap wf_2f58724b)

`validar_campana` RECHAZA (jamás corrige en silencio): población ≠ inventario COMPLETO
(identidad por hash del catálogo Y por GENOMA individuo por individuo — block_id swapeado o
theta trocado no compilan) · población duplicada · intervenciones en unidades · horizonte <
emergencia declarada (piso ≥1) · reglas de clasificación sin sellar · probeta GOLD ausente ·
claves de filtro (gate-portero estructuralmente imposible: el reporte ES la población entera,
en el orden de la spec) · retención no implementada (v1: `conformidad_completa`; poda = F7.2
fail-loud) · procedencia fabricada (capsule_sha256 sin artefacto). La spec es AUTO-CONTENIDA
(thetas embebidos, cápsulas pinneadas, chunk_ticks en retención: los bytes del film son
función de la spec), se PERSISTE (SPEC.json + sha canónico invariante al orden) y toda unidad
sella `campana_spec_sha256` en su manifiesto. Ejecución: spawn pinneado, worker muerto =
fail-loud, unidad que falla = DATO del reporte (estado `fallida` + error), reanudación por
unidad VERIFICADA (film completo re-leído, fila reconstruida entera), ledger jamás degradado,
restos jamás borrados, archivado atómico verificado sha-por-sha, preflight de disco.

## El explorer — cliente del motor, iterador de M2 entre niveles [BORRADOR]
Propone constituciones (ola1: genomas; ola2+: composiciones naturales sobre el inventario
completo del nivel anterior) → emite specs [M2] → corre → COSECHA checkpoints+pasaportes al
inventario del nivel siguiente. Recursivo: inventario_N → explorer → M2 → inventario_N+1.
Nunca vive dentro del integrador. La probeta GOLD acompaña toda corrida M2 (regla heredada).
