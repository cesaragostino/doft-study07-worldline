Ambos repos intactos (git limpio, cero escrituras fuera del sandbox). Verificación completa. Veredicto para bitácora:

---

# DOUBLE TAP F3 — VEREDICTO DEL JUEZ (repo @ e235d4f, sandbox propio, todo re-ejecutado por mano del juez)

Baseline reproducido en copia bit-idéntica: gates F3 **7/7**, suite completa **17 passed** (F2 intacta). El 7/7 queda **REFUTADO como evidencia suficiente**: 5 mutantes del recorder viven con todos los gates verdes — la misma trampa del F2 (verde por régimen degenerado/cobertura parcial). El código shipped, en cambio, sobrevivió TODAS las sondas dinámicas: kicks rederivados de los 4 chunks (incluido el parcial) desde el rng_state PROPIO con residuo 0.000e+00; canal drive veraz contra re-integración independiente (residuo 0, dtype float64, no-vacuo max|drive|=2.44e-01); continuación bit-exacta; controles de no-vacuidad todos muertos. **El defecto es de los GATES y de la mitad de PROCEDENCIA, no de la dinámica.**

## 1. VEREDICTO ÚNICO: **PASADA CON ARREGLOS** — prohibido declarar F3 hasta aplicar A1–A6 y re-verificar matando

- **A1 [tests — DEMOSTRADO]** `tests/test_worldline_checkpoint.py`: agregar **gate2b** (replay-compare total: 130 ticks, chunk_ticks=16, memoria de estados+drive+kicks, dtype float64 en los 3 canales, guard max|drive[1:]|>0, igualdad EXACTA fila a fila) y **gate5b** (rederivar kicks de TODOS los chunks desde el rng_state PROPIO de cada uno + dtype). Parche listo y verificado: `/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad/juez_f3/repo/tests/test_gates_f3_juez.py` — pristine **9 passed**; los 5 vivos **mueren**. Corregir además el comentario falso de `:182` ("chunk 0 tiene filas 0..16" → 0..15; layout medido: 0..15 / 16..31 / 32..47 / 48..48).
- **A2 [prod]** `src/study07/artifacts/recorder.py:49-60`: manifiesto auto-poblado desde `net` — topología (aristas w_k/w_gamma/τ), k_global/gamma_c/tau_field, por nodo {n_modes, n_z, n_layers}, git commit+dirty, versiones python/numpy, perfil='conformidad'; validación fail-loud de claves obligatorias del caller (run_id, spec [M1|M2], hashes de base externa). Verificado por el juez: el manifiesto real tiene 9 claves y NINGUNO de los campos de WORLDLINE_SCHEMA:56-63.
- **A3 [prod]** `recorder.py:116-120` y `:139-147`: COMPLETE incluye sha256 de manifest.json y el lector lo verifica + cross-check n_nodes/dims contra las formas reales. Verificado: manifest adulterado TRAS COMPLETE (dt=123.456, seed=999999) es aceptado sin error.
- **A4 [prod]** `src/study07/artifacts/checkpoint.py:31-43` y `:67-79`: la meta lleva k_global/gamma_c/tau_field + sha de edges normalizados y de la constitución serializada; `network_from_checkpoint` los APLICA de la meta y verifica el hash de los specs fail-loud (kwargs sólo override explícito registrado). Verificado: sin k_global → aceptado con k_global=0.0, divergencia 3.610e-04 en 10 ticks, cero excepción; constitución gamma×1.5+0.01 → aceptada, divergencia 1.095e-06, silencio.
- **A5 [prod]** `recorder.py:91-92`: chunks con tmp .npz + rename (patrón `checkpoint.py:44-47`, cuidando el append .npz ya cazado); lector `allow_incomplete` captura BadZipFile por chunk y reporta cuál. Verificado: chunk truncado → `BadZipFile: File is not a zip file` crudo, justo en el modo cuyo propósito es auditar restos.
- **A6 [docs]** CHECKPOINT_SCHEMA promovido a v1 sellado (hoy: BORRADOR de 5 líneas que checkpoint.py declara implementar); WORLDLINE_SCHEMA: sellar drive=sub-paso 0, canal t=derivado (no almacenado), events.jsonl=(F6), y que COMPLETE prueba CIERRE no autenticidad (sha_total lo pinea el catálogo externo); bitácora §4: sección NO-CUBIERTO (verificado: §3-F2 la tiene en :64, §4-F3 no tiene ninguna).

**Condición dura:** A2–A5 tocan producción y cambian el formato de los artefactos → re-correr batería reforzada + suite completa (las 17 de F2 deben seguir verdes) TRAS aplicarlos. El double tap no se hereda.

## 2. Tabla de mutantes consolidada (los 11 re-ejecutados por el juez; equivalencias b1/b4 anotadas)

| mutante (dónde) | batería actual 7 gates | batería reforzada 9 gates |
|---|---|---|
| M6 drive=ceros en record_step (=B de b4) | **VIVO 7/7** | MUERTO |
| M4c drive float32 en _flush_chunk | **VIVO 7/7** | MUERTO |
| M3 rng_state estancado en _flush_chunk :99 (≈A de b4) | **VIVO 7/7** | MUERTO |
| M7 kicks basura tick>16 (≈C de b4) | **VIVO 7/7** | MUERTO (2 gates) |
| D estados +1e-9 tick>100 | **VIVO 7/7** | MUERTO |
| M1 e_ref no aplicado (control) | MUERTO (gate1) | MUERTO |
| M2 RNG no restaurado (control) | MUERTO (gate1) | MUERTO |
| M8 buffer no restaurado (control) | MUERTO (gate1) | MUERTO |
| M4 estados float32 (control) | MUERTO (gate2) | MUERTO |
| M4b kicks float32 (control) | MUERTO (gate5) | MUERTO |
| M5 fila0=POST (control) | MUERTO (gate2) | MUERTO |

**Totales: batería actual 11 probados / 6 detectados / 5 VIVOS. Batería reforzada: 11/11/0, pristine 9 passed.** El claim de b2 no existe (agente muerto); los claims de mutación de b1 y b4 quedaron CONFIRMADOS por re-ejecución independiente. La no-vacuidad del camino e_ref confirmada aparte: 9/9 pares (nodo,capa) del meta difieren del theta fresco.

## 3. Cumplimiento de schemas por cláusula — PARCIAL-silenciosos al frente

**WORLDLINE_SCHEMA v1 (sellado COA):**

| cláusula | estado | evidencia del juez |
|---|---|---|
| Manifiesto PROVENANCE (:56-63) | **NO CUMPLE — silencioso** | 9 claves; cero de: topología, engine params, git+dirty, entorno, hashes base externa, perfil, [M1|M2], parent, finalización. Sin events.jsonl |
| Canales x,v,z,b,e recuperables del artefacto (:47) | **PARCIAL — silencioso** | dims=33; resto 13 = n_z+2·n_layers ambiguo; partición sólo con el fixture externo — el film NO es auto-suficiente |
| Perfil por corrida (:13-16,:62) | **NO — silencioso** | campo inexistente |
| Regla 2 inmutabilidad post-COMPLETE (:70) | **PARCIAL — silencioso** | manifest adulterado aceptado; truncación + COMPLETE reescrito coherente aceptada (48 filas, complete=True) — tamper, no accidente |
| Regla 1 interrupción/reanudación (:67-69) | **PARCIAL — silencioso** | chunks sin tmp+rename (:92) → BadZipFile en restos; reanudación sin API (mkdir exist_ok=False :32) |
| Canal t (:46) | NO (sólo ticks; derivable — enmendar) | inspección |
| drive sub-paso (:48) | PARCIAL — declarado en manifest, no en el doc normativo | semantica del manifest |
| Fila 0 PRE-step | **CUMPLE** | gate2; M5 muere |
| float64 primario | **CUMPLE en producción** | dtypes verificados; drive sin gate hasta A1 |
| rng_state por chunk | **CUMPLE y CORRECTO 4/4 chunks** | residuo 0.000e+00 incluido el parcial — el gate cubría sólo el chunk 0 |
| noise_kick / chunks con hash / COMPLETE atómico / lector verificador | **CUMPLE** (corrupción accidental) | gates 3/3b + sondas |

**CHECKPOINT_SCHEMA ([BORRADOR] de 5 líneas):** parámetros activos **PARCIAL-silencioso** (e_ref sí, no-vacuo; k_global/gamma_c/tau_field/edges NO viajan — default silencioso 0.0, divergencia 3.61e-04); linaje por hash **NO** (constitución mutada aceptada en silencio); reloj **PARCIAL-silencioso** (tick viaja en meta pero la continuación lo descarta, hija renumera desde 0); estado float64 completo / buffer no-uniforme / RNG **CUMPLEN** (bit-exacto).

## 4. NO-CUBIERTO consolidado para bitácora

1. Reanudar-GRABANDO tras interrupción: sin API (hija renumera desde 0, sin parent_run_id automático, empalme manual; física del empalme medida exacta por b4, residuo 0).
2. Worldline HIJA: parent_run_id / parent_checkpoint_hash / events.jsonl inexistentes en código — F6.
3. Ingesta del FORMATO cápsula v4 real (orden nodos/modos, head, layout): gate4 cubre el mecanismo no-uniforme, no el formato; la guarda de history_init es sólo de FORMA (network.py:68-70).
4. Perfil campaña + retención declarada — F7.
5. gate1 sólo T>0: restore con T=0 sin gate permanente (sondado bit-exacto por b4; parametrizar en T∈{0, 0.05}).
6. Bordes de chunking (chunk_ticks=1, >ticks, frontera exacta, 0 ticks) y runner con checkpoint_every: sin gate (sondados sanos por b4, residuo 0).
7. meta['seed'] del checkpoint sin verificación: un seed mentiroso continúa bit-exacto igual (procedencia, no dinámica).
8. Durabilidad: sin fsync antes de los rename (corte de energía; el lector lo ataja fail-loud).
9. Recorder apuntado al dir PADRE aceptado (contamina layout); tmp del checkpoint matchea el glob ck_*.npz (riesgo para un descubridor futuro de "último checkpoint").
10. Truncación con COMPLETE reescrito coherente ACEPTADA: la inmutabilidad real exige pineo externo del sha_total en el catálogo — declararlo en el schema, no dejarlo implícito.

**Reproducibilidad del juez** (todo en sandbox, repos read-only respetados): `/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad/juez_f3/harness_mutantes.py` (11 mutantes), `.../juez_f3/sondas_juez.py` (sondas S1–S9), `.../juez_f3/repo/tests/test_gates_f3_juez.py` (los 2 gates del arreglo A1, listos para copiar), `.../juez_f3/suite_completa_baseline.txt` (17 passed).