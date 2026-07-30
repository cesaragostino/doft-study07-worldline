# DOUBLE TAP F6 — VEREDICTO DEL JUEZ

**Alcance:** 4 lentes (c1 test-del-test, c2 mutación, c3 contrato/oráculo, c4 cobertura) + verificación independiente del juez en sandbox propio (`/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad/judge_f6/`, `git clone` + checkout **9dd1ccd** verificado — no `cp -R`, siguiendo la NOTA de proceso de c3). Baseline reproducida: gates F6 8/8, suite completa 54 passed. Scripts del juez: `veredicto_v1_v6.py` (14/14 sondas OK, cada agujero con CONTROL que murió donde debía) y `mutantes_vivos.py` (8 mutantes re-aplicados uno por vez, restore + purga de `__pycache__`, sandbox `git status` vacío al cierre). Nada heredado sin reproducir: **todo BLOQUEA/ALTO fue re-ejecutado por el juez**; los 14 mutantes MUERTOS de c2 se heredan como declarados (no re-corridos — dicho honesto).

---

## 1. Veredicto único: **F6 NO PASADA** (tal cual está; re-declarable tras arreglos A1–A5 + re-tap dirigido)

La física salió bien —otra vez—: gemela bit-exacta todos los canales/ticks, espejos manuales bit-exactos, semántica de reloj genuinamente anclada (familia M1–M4/M6 muerta por gate3), enforcement de linaje directo pieza por pieza (M12–M16 muertos por gate5). Pero **tres claims sellados del commit están FALSADOS con evidencia ejecutada**, y uno de ellos rompe el gate central de CHECKPOINT_SCHEMA para el artefacto que F6 produce. Los gates nacieron más duros que en F2–F5 (14/21 mutantes muertos vs los 24/5/15/29 vivos históricos), pero **no alcanzó**.

### Bloqueantes (los tres falsan texto sellado en 9dd1ccd)

**A1 — La rama `escala_arista` de `verificar_hija` no está anclada a nada** (convergen c1+c2+c3+c4; juez V1).
`src/study07/artifacts/hija.py:212-224`. Forja coherente ejecutada por el juez: `w_k_antes` real 1.0 → mentido 999.0 + `estado_pre_sha256` fabricado + campo extra `hackeado` ⇒ `verificar_hija` **ACEPTA**. Control: la misma jugada sobre un kick muere con "miente" (la rama kick SÍ ancla al film). Y borrar la rama arista ENTERA del verificador deja 8/8 verdes (M-D re-ejecutado): gate8 no tiene ni un caso arista. El claim "adulterar events.jsonl es detectable sin sellos extra" (docstring :19-21 + WORLDLINE_SCHEMA enmienda F6) es **FALSO para uno de los dos tipos de evento v1**.
*Parche:* pesos corrientes por arista inicializados de `manifest['topologia']['w_k'/'w_gamma'][ar]`, encadenados por factor como los kicks; exigir `antes == corriente` EXACTO y `estado_pre_sha256 == sha(np.array([antes_k, antes_g]))`; rechazar claves extra por tipo. Gate8: casos (g) antes fabricado coherente, (h) pre_sha de arista, (i) campo extra.

**A2 — `escala_arista` no recomputa `_wsum_k/_wsum_g` ⇒ divergencia silenciosa viva-vs-restore** (c3-A; juez V2).
`hija.py:105-106` muta `edge_w_k/edge_w_g`; `engine/network.py:45-49` precomputa wsum en `__init__`; `physics/coupling.py` normaliza con él. Ejecutado: hija post-hotcut, checkpoint al tick 45, continuar viva vs restore→continuar: `wsum_k` viva `[2.0,1.5,1.5]` vs restaurada `[1.0,0.5,1.5]`, **dmax=4.66e-04 sin excepción**; control idéntico sin hotcut: **dmax=0.0 exacto** (wsum es la causa única). Es la clase exacta de divergencia silenciosa que F3-A4 mató. Los gates no lo ven porque el espejo repite la misma mutación in-place y nunca se checkpointea post-evento.
*Parche:* en `_aplicar`, tras escalar, recomputar wsum desde `edge_ij/edge_w_k/edge_w_g` (mismo loop de `__init__`) — la mutación queda cerrada bajo checkpoint y los espejos siguen pasando. Gate nuevo: hija post-escala → ck → restore → continuación bit-exacta.

**A3 — El linaje al run es declarativo y el estado intervenido se NATURALIZA en una generación** (c1-E1/E2, c3-B, c4; juez V3a/V3b/V4).
Ejecutado: (i) `parent_run_id='MADRE_QUE_JAMAS_EXISTIO'` + hash `deadbeef*8` ⇒ hija COMPLETE, `verificar_hija` la acepta (`recorder.py:95-115` sólo verifica ck-sha+tick); (ii) red FRESCA sin `origen_checkpoint` + linaje completo fabricado ⇒ el recorder salta TODO el bloque y sella (camino inverso al que gate5 prueba); (iii) el checkpoint de una hija intervenida lleva meta `[dt, e_ref, edges, ..., tick]` — **cero rastro** — y una "nieta lavada" se selló COMPLETE con `intervenida=False` y padre inventado. El oráculo rehúsa exactamente esto ("only a natural, unintervened network can be sealed"). Controles que murieron: restaurada sin linaje ⇒ `ValueError linaje`; ck-sha mentido ⇒ `ValueError RESTAURADO` (el vínculo físico SÍ se verifica).
*Parche:* `recorder.save_checkpoint` (`recorder.py:189-192`) estampa `extra_meta` = {run_id, manifest_sha, intervenida-hasta-el-tick, linaje propio} (`checkpoint.py` ya soporta `extra_meta`); `network_from_checkpoint` lo adhiere a `origen_checkpoint`; el recorder exige `parent_run_id == meta.run_id` y linaje-intervenido heredado; simetría: manifiesto con claves `parent_*` y red sin origen ⇒ `ValueError`. Gate5: ramas (f) fresca-con-linaje, (g) padre inventado, (h) nieta de intervenida.

### Altos (arreglo exigido antes de declarar)

**A4 — Blow-up < 256 ticks se sella COMPLETE** (c2-M11; juez V5): `hija.py:116,150-155` — hija de 64 ticks con delta=1e155 (finito: pasa pre-registro) ⇒ `COMPLETE=True`, film no-finito, violando el contrato §8 que el propio mensaje de error cita. Control: `finite_check_every=16` ⇒ FloatingPointError sin COMPLETE. *Parche:* check incondicional tras el loop, antes de `rec.close()` + gate con ticks cortos.

**A5 — La procedencia F5 muere en la primera generación** (c3-C, c4; juez V6): `composicion_recibo` no viaja en el checkpoint (`checkpoint.py:54-72`) ⇒ hija de madre compuesta (cápsulas f8 reales) sellada COMPLETE con `hashes_base_externa={'nada_que_ver': '0'*64}`, sin `composicion` ni un solo `capsule_sha256` citado. Control gen 0: el recorder SÍ rechaza film compuesto sin recibo. *Parche:* persistir el recibo en la meta (mismo vehículo que A3), re-adherir en restore — el enforcement F5-A5 existente dispara solo.

### Medios/bajos (a bitácora + arreglos en el mismo pase, no bloquean por sí solos)
Pin externo = `worldline_hash`, no `sha_total` (c1-E4, enmienda de una línea) · re-medición de la madre en `tearDownClass` (c1 M-E: gate6 la ensució 9 veces con 8/8 verdes) · rng de hijas sin ancla (c1 M-B: 54/54 con rng corrupto) · cobertura multi-evento (M5/M20: mutantes rechazan hijas legítimas con todo verde) · gate de abort (M8) · caso `tick_global` en gate8 (M19) · omisión por-clave de linaje (M21) · validaciones antes del `mkdir` (c1-E5) · cruce `spec_tipo=M2`×intervención (c3-E1) · factor negativo ⇒ ck irrestaurable (c3-F) · eventos vacuos (c4-S7) · `tick_global` relativo al padre desde la 2ª generación (c4) · nietas sin API ni gate (c4-S4) · colisión de nombre `hotcut` study07≠oráculo sin declarar (c3) · campo `porque` M1 (c3-E2, contrato en borrador) · vistas agnósticas a la intervención: decidir y escribir (c4-S6).

**Condición dura para re-declarar F6:** aplicar A1–A5 y **re-matar contra el código arreglado**: los 7 mutantes vivos (M5, M8, M11, M17, M19, M20, M21) + M-D + los 6 ataques del juez (V1 forja arista, V2 wsum, V3a/V3b linaje, V4 nieta lavada, V5 blow-up, V6 recibo) — cada uno debe pasar de VIVO/ACEPTADO a MUERTO/RECHAZADO, y la suite + fixtures F3/F5 deben seguir bit-exactos (ninguno de los parches toca la física; V2-control lo garantiza si el recompute de wsum replica el loop de `__init__`).

---

## 2. Tabla de mutantes

| Mutante | Qué muta | Lente | Juez (re-corrido) | Estado |
|---|---|---|---|---|
| M1 evento post-step | hija.py `_aplicar` orden | c2 | no re-corrido | MUERTO (gate3) — heredado |
| M2 canal opuesto | kick x↔v | c2 | no re-corrido | MUERTO (gate3) — heredado |
| M3 signo invertido | delta negado | c2 | no re-corrido | MUERTO (gate3) — heredado |
| M4 tick_global−1 | reloj | c2 | no re-corrido | MUERTO (gate3) — heredado |
| M6 pre-sha post-aplicar | orden sha | c2 | no re-corrido | MUERTO (gate3) — heredado |
| M7 ignora factor_w_gamma | física del corte | c2 | no re-corrido | MUERTO (gate4) — heredado |
| M18 corte vacuo | reporta sin aplicar | c2 | no re-corrido | MUERTO (gate4) — heredado |
| M12–M16 linaje (ck-sha/tick/intervenida/enforcement/adhesión) | recorder+checkpoint | c2 | no re-corridos | MUERTOS (gate5, 1f/53p c/u) — heredados |
| M9/M10 campo-por-campo / pre-vs-film | verificador kick | c2 | no re-corridos | MUERTOS (gate8) — heredados |
| **M-D borrar rama arista entera del verificador** | hija.py:212-224 | c1 | **8 passed** | **VIVO — confirma A1** |
| **M5 sin sorted** | validar_eventos:87 | c2 | **8 passed** | **VIVO confirmado** |
| **M8 events.jsonl al final** | hija.py:142-147 | c2 | **8 passed** | **VIVO confirmado** |
| **M11 sin finite_check** | hija.py:150-155 | c2 | **8 passed** | **VIVO confirmado** (+V5: agujero en el ORIGINAL) |
| **M17 aplicado/shas de arista fabricados** | _aplicar:107-110 | c2 | **8 passed** | **VIVO confirmado** (+V1: forja en el ORIGINAL) |
| **M19 sin check tick_global** | hija.py:190-191 | c1+c2 | **8 passed** | **VIVO confirmado** |
| **M20 sin encadenado** | hija.py:195-200 | c2 | **8 passed** | **VIVO confirmado** |
| **M21 sin eventos_declarados en faltan_lin** | recorder.py:97-100 | c2 | **8 passed + suite 54 passed** | **VIVO confirmado** |

Score independiente del juez: **8/8 vivos re-confirmados** (siete de c2 + M-D de c1), restauración bit-exacta entre cada uno (sandbox `git status` vacío).

## 3. Contratos por cláusula

| Contrato / cláusula | Veredicto | Evidencia |
|---|---|---|
| WORLDLINE_SCHEMA F6: semántica de reloj (evento sobre POST step k−1; fila 0 = restaurado) | **CUMPLE** | gate3 + M1–M4/M6 muertos; c4-S3c: pre==restaurado por sha |
| F6: gemela = control apareado bit-exacto, RNG viaja | **CUMPLE** | gate2 (T=0.05); c4-S5 (T=0) |
| F6: madre inmutable | **PARCIAL** | medida UNA vez al inicio; gate6 la ensució 9× sin detección (c1 M-E) |
| F6: linaje "se declara al nacer y se VERIFICA" | **INCUMPLE** | V3a/V3b/V4: padre inventado, fresca-con-linaje, nieta lavada — sólo ck-sha+tick se verifican |
| F6: "toda adulteración de events.jsonl detectable sin sellos extra" | **INCUMPLE** | V1 + M-D + M17: rama arista jamás anclada |
| F6: pre-registro fail-loud sin rastro | **PARCIAL** | validar_eventos sí (gate6); recorder-falla-tras-validar deja dir (c1-E5); no-ops y factor negativo pasan |
| F6: τ fuera de contrato v1 (declarado) | **CUMPLE** | c3: constitución fingerprint-locked, cero kwargs — verificado |
| CHECKPOINT_SCHEMA: continuación bit-exacta viva-vs-restore | **INCUMPLE post-escala_arista** | V2: dmax=4.66e-04 silencioso; control 0.0 |
| PROVENANCE_CONTRACT / F5-A5 (cápsulas citadas) | **PARCIAL** | gen 0 CUMPLE (V6-control rechaza); descendencia INCUMPLE (V6) |
| EXPERIMENT_CONTRACT: M2 rechaza intervenciones | **INCUMPLE** | c3-E1: M2+kick sellado (contrato [BORRADOR], pero F6 lo vuelve alcanzable) |
| EXPERIMENT_CONTRACT: porqué M1 en el artefacto | **PARCIAL** | c3-E2: ningún campo; contrato en borrador declarado |
| Contrato §8: blow-up aborta sin COMPLETE | **INCUMPLE** | V5: 64 ticks no-finitos sellados COMPLETE |
| Herencia del oráculo: kick entre-steps = semántica histórica | **CUMPLE** | c3: protocols.py:112-119/:2827-2831, jamás dentro del RK4 |
| Herencia: hotcut study07 ≟ hotcut oráculo | **PARCIAL** | capacidad nueva honesta (oráculo jamás mutó edge_w mid-run) pero colisión de nombre sin declarar |

## 4. NO-CUBIERTO consolidado (declarar en bitácora al re-declarar F6)

1. Adulteración de `escala_arista` — **agujero, no sólo no-cubierto** (A1). 2. Nietas / multi-generación: sin API (`checkpoints/` de hijas nace vacío) y sin gate; máquina probada a mano bit-exacta (c4-S1). 3. Hija de madre compuesta (funciona bit-exacta; procedencia cortada — A5). 4. Multi-evento: mismo tick/mismo nodo, nodos distintos, escalas encadenadas, orden de declaración (M5/M20 vivos; recetas en c4-S3). 5. Abort a mitad de corrida: restos de events.jsonl (M8). 6. Blow-up con ticks < finite_check_every (A4). 7. `rng_state_json` de chunks de hijas (c1 M-B: basura sobrevive 54/54). 8. Re-medición de la madre al final de la clase (c1 M-E). 9. `tick_global` en events.jsonl (M19) y su semántica multi-generación (relativo al padre — misnomer). 10. Bordes tick_hija=1 y =ticks, hija T=0 (funcionan, sin gate — c4-S3/S5). 11. Pin externo `worldline_hash` vs `sha_total` (c1-E4). 12. Eventos vacuos como teatro de intervención (c4-S7). 13. Vistas phase/energy agnósticas a la procedencia (c4-S6, decisión pendiente). 14. Cruce M2×intervención y factor negativo (c3). 15. Regla de tap: verificar `git log -1` de la COPIA contra el commit auditado (c3 capturó F5 por carrera de `cp -R` — el juez usó clone+checkout por eso).

---

**Repos al cierre (verificado por el juez):** study07 `/Users/cagostino/code/doft-study07-worldline` @ **9dd1ccd**, `git status` limpio; oráculo `/Users/cagostino/code/doft-study06-fundamental-lock-dynamics` @ **39f8df6**, `git status` limpio, ningún archivo R_f leído. Todo el trabajo ocurrió en el sandbox del juez (`scratchpad/judge_f6/`: `repo/` clonado, `veredicto_v1_v6.py`, `mutantes_vivos.py`), restaurado bit-exacto tras cada mutación.