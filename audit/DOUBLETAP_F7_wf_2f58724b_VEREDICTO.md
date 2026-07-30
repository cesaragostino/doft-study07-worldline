Todo verificado. Cierro con el veredicto.

# DOUBLE TAP F7 — VEREDICTO DEL JUEZ

Clon del juez: `scratchpad/judge_f7/repo` — `git clone` + `checkout ada062e` verificado (`git log -1` = ada062e). Baseline: gates 7/7, suite 66/66. Arnés con mutante CONTROL que MURIÓ (quitar el raise de población → `1 failed` en 0.16s): el arnés detecta kills. Cada mutación una por vez, `git checkout` + purga de `__pycache__` entre corridas (0 diffs al cierre). Sondas del juez: `scratchpad/judge_f7/sondas_judge.py` + `sonda_j6_pool.py`.

**Ambos repos reales INTACTOS, verificado al cierre**: study07 @ ada062e porcelain vacío; oráculo study06 @ 39f8df6 porcelain vacío; ningún archivo R_f leído; cero procesos colgados de las sondas.

## 1. Veredicto único: **F7 NO PASADA**

El patrón F2-F6 se repite por sexta vez: la mecánica central es sólida (determinismo BIT bajo pool, validador M2 rama por rama, restos jamás borrados, no-pisa, composer fail-loud — todo re-confirmado), pero los gates no protegen los claims de PAPELES del commit ada062e, y tres de esos claims son hoy **falsos en ejecución**. Verifiqué por mi cuenta, con evidencia ejecutada y controles vivos:

- **"Reanudación por unidad sin pérdida" — FALSO (BLOQUEA, J1 confirmado)**: tras reanudar, el LEDGER.json EN DISCO quedó con `u1_transported`/`u3_mixta` = `{estado, run_id, worldline_hash}` — sin métricas ni view_hashes — pisando el LEDGER previo que tenía 3/3 con métricas. Convergencia de 3 lentes + juez.
- **"COMPLETE se reusa verificada por hash" — FALSO (ALTO, J2 confirmado)**: chunk bit-flippeado con COMPLETE intacto → `estado=reusada`, hash heredado==original `True`. CONTROL vivo: `api.load_run` detecta `chunk_00000.npz: sha d5cb9e72aa3b != COMPLETE f97aae5f3076` — la maquinaria existe, nadie la llama.
- **Una unidad que falla mata el census (BLOQUEA, J5 confirmado)**: unidad con sha adulterado → campaña ABORTA, `LEDGER.json existe: False` con 2/3 COMPLETE en disco; re-correr con la spec corregida → `COMPLETE de OTRA spec (1c2a88b1 != 8766d8a0)` — base_dir brickeado, N-1 unidades inutilizables. CONTROL: campaña sana escribe LEDGER.
- **Procedencia fabricable (ALTO, J3 confirmado)**: `capsule_sha256` sin `capsula_dir` pasa el validador y el manifest queda `hashes_base_externa={capsula_nodo0: sha256:2e4aad25...}` con `origen='nacimiento'`. CONTROL vivo: sha adulterado con `capsula_dir` sí muere.
- **Atribución swapeable (ALTO, J4 confirmado)**: block_id swapeados entre cápsulas → validador PASA, campaña VERDE, spec nodo0 `92466fe3` vs cápsula real `1bc9dccc` sellado en los papeles. CONTROL vivo: theta trocado muere en composer (`genoma no coincide`).
- **Worker muerto = cuelgue (ALTO, J6 confirmado a nivel patrón)**: patrón idéntico a campana.py:244-246, worker SIGKILLeado → 25s sin resultado ni excepción; con `.map()` a secas el bloqueo es indefinido. CONTROL: sin kill termina. (El cuelgue de campaña real 180s lo ejecutó c4; no lo repetí — corroborado a nivel patrón.)

### Arreglos requeridos (A1-A9) — condición dura: re-matar TODOS los mutantes vivos y re-correr las sondas J1-J6 contra el código arreglado antes de declarar

| # | Dónde | Parche |
|---|-------|--------|
| A1 | campana.py:221-228 | Reusa: `api.load_run(run_dir)` (verifica chunks+manifest) en vez de `worldline_hash`; si falla → restos + rehacer. Recuperar fila COMPLETA: `load_view` de views_root + recomputar `metricas_basicas_v1` |
| A2 | campana.py:262-267 | LEDGER jamás degradado: mover el previo a `restos_LEDGER_<n>.json` antes del rename (o merge verificado); sidecar sha con tmp+rename junto al json |
| A3 | campana.py:240-248 | Contención por unidad: try/except en `_correr_unidad` → `estado='fallida'` con error+tick como DATO del reporte; distinguir falla-dato (blow-up) de aborto-integridad (cápsula adulterada); reanudación rehace solo fallidas |
| A4 | campana.py:244-246 | `concurrent.futures.ProcessPoolExecutor(mp_context=spawn)` — `BrokenProcessPool` fail-loud ante worker muerto |
| A5 | campana.py:84-85, 175-177 | Rechazar `capsule_sha256` sin `capsula_dir`; citar `capsula_nodo{idx}` SOLO si la cápsula se cargó |
| A6 | campana.py:160-167 | `if c.get('block_id') and cap['manifest']['block_id'] != c['block_id']: raise` |
| A7 | tests gate2/3/4 | Comparar filas ENTERAS del ledger (no solo hashes); view_hashes contra `load_view` recomputado; caso reanudación exige métricas en TODAS; caso chunk corrupto exige rehacer |
| A8 | tests gate7 + metricas | Kill-test de archivado con fault-injection (corromper 1 byte post-copytree → debe raise); golden values de `metricas_basicas_v1` con arrays sintéticos (cruce breve ⇒ None, sostenido ⇒ k) y valores pinneados del fixture |
| A9 | campana.py:95-109 | Validador M2: `hz >= 1`; población como lista sin duplicados; `genome_sha256(theta) == inventario.genome_hash[block_id]` para todo `es_poblacion` (el inventario_v4 ya lo tiene); RuntimeError tipado para `es_poblacion` sin block_id |

## 2. Tabla de mutantes

**Re-corridos por el juez** (independientes, restore+purga entre cada uno):

| Mutante | Origen | Mi corrida | Veredicto |
|---|---|---|---|
| CTRL: quitar raise de población | juez | **1 failed, 0.16s** | MUERE — arnés válido |
| M15: archivado sin verificación (sello intacto) | c2 | **7 passed** | VIVO — CONFIRMADO |
| M18: t_lock primer-cruce sin ventana | c2 | **7 passed** + divergencia ejecutada: mutante=10, original=None | VIVO — CONFIRMADO |
| M10: sin `load_view`, todo desde memoria | c2 | **7 passed** | VIVO — CONFIRMADO |
| Ledger mentiroso: view_hashes basura + met ×1e6 | c1 | **7 passed** | VIVO — CONFIRMADO |

Grep verificado: solo `tests/test_campanas_f7.py` consume `campana` — los veredictos valen para la suite de 66.

**De los lentes, no re-corridos por mí** (evidencia ejecutada declarada por el lente; los acepto como PLAUSIBLES de alta confianza, mismo patrón): M13b orden en reanudación, M14 LEDGER sin tmp+rename, M17 `sort_keys` (riesgo: rehacer census entero), M19 `_sha_file` 1MB, M21 fork/spawn. **Muertos (crédito, c2)**: 14/22 — gate1 mata las 6 ramas del validador + borde or→and; M8 muere por defensa en profundidad del recorder (PROVENANCE F5-A5); M9 por el ancla física de gate2.

## 3. Contratos por cláusula (EXPERIMENT_CONTRACT vs código)

| Cláusula | Estado ejecutado |
|---|---|
| Población = inventario COMPLETO por hash | Ejecutada pero a nivel NOMBRE (set de strings): duplicados colapsan, census todo-fresh pasa, thetas trocados pasan, block_id swapeado pasa (J4) |
| Cero intervenciones | EJECUTADA Y GATEADA (gate1, mutantes mueren) |
| Horizonte ≥ emergencia declarada | Ejecutada pero auto-declarada y sin piso (0 y −100 compilan); no existe clave `prereg` en CLAVES_SPEC (leído: campana.py:35-36) |
| Reglas de clasificación "selladas en el prereg" | Dict de texto libre no-vacío; sin prereg_sha nada las sella; las métricas "congeladas" son redefinibles (M18 vivo) |
| Probeta GOLD | EJECUTADA Y GATEADA |
| Reporte = población entera | Ejecutada en el camino feliz; el check interno :252-253 es inalcanzable; en reanudación el reporte pierde métricas (J1) y el orden no se asserta (M13b) |
| "Gate-portero no compila" | Sin forma ejecutable (ningún chequeo de filtro de instrumento) |
| Estado del documento | Sigue **[BORRADOR — Fase 1]** sin NINGUNA semántica F7 (spec auto-contenida, retención, ledger, restos, no-pisa, archivado, horizonte). Al cerrar el tap corresponde enmienda a v1 sellado, como INSTRUMENT_CONTRACT post-F4 |

## 4. NO-CUBIERTO consolidado (escala census real: 150-300 unidades, workers 8-12, overnight)

1. **Disco JUSTO**: films 124 MB/unidad medidos (c3) ⇒ 75-90 GB con archivado vs ~110 Gi libres; sin preflight de espacio; restos_* duplican por cada interrupción.
2. **Generador de specs prometido en tools/ NO existe** (`ls` verificado: solo correr_m1p1, gen_f6/f7/f8, inventario_v4) — census a mano = exactamente la clase de bug que J4/A9 demuestran que nada atrapa.
3. **spec_sha frágil**: sensible al orden de claves (M17) — una spec regenerada rechaza todos los COMPLETE; `chunk_ticks`/entorno/git entran al worldline_hash pero NO al spec_sha (c4-G): misma spec ⇒ films distintos entre corridas del runner.
4. **La spec jamás se persiste** y el LEDGER no lleva git/entorno/timestamp — la campaña archivada no es re-ejecutable desde sus propios papeles (c3).
5. **Corte de energía**: cero `fsync` en src/ (grep) — COMPLETE puede sobrevivir con chunks truncados; sidecar LEDGER.sha256 no atómico como par.
6. **Sin lock de campaña ni guard documentado**: `__main__` sin guard = runaway real (pasó en el tap de c3); huérfanos post-kill del padre siguen escribiendo (c4, la carrera probada convergió limpia — rename-aside + COMPLETE atómico son protección real, pero la ventana existe).
7. **Bordes de física**: n_nodes==1 clasifica t_lock=0 con R≡1 (identidad por construcción, F4 NO-CUBIERTO 4); t_half ancla solo al nodo 0 en campañas heterogéneas; ticks=0 publica film de cero evolución "completa".
8. **Operación**: fork no pinneado (M21), `_sha_file` nunca ejercitado >1MB (M19), chunksize default regala ~1-1.5h de cola (c3), rendimiento/duración no registrados en ningún artefacto (c4).

**Lo que SÍ protege (para el veredicto honesto)**: determinismo BIT bajo pool más allá de lo gateado (6u/3w/9chunks/views compartido: 0 diferencias — c1); validador M2 genuinamente gateado rama por rama (16 casos, 7 mutantes muertos); composer theta↔cápsula fail-loud (mi control J4); recorder PROVENANCE como defensa en profundidad (mató M8); restos jamás borrados y no-pisa funcionan como se declara; `load_worldline`/`load_view` detectan TODA la corrupción que la reusa deja pasar — los arreglos son mayormente llamar maquinaria que ya existe y endurecer 3 gates.