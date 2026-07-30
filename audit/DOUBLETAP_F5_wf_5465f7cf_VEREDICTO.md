Verification complete. All work ran in the sandbox copy; both real repos verified clean. Final verdict follows.

# DOUBLE TAP F5 — VEREDICTO DEL JUEZ

Candidata @ 3792ff6 · entorno pinned verificado (numpy 2.3.4 / x86_64) · baseline reproducido: 41 passed · todo el trabajo en copia `scratchpad/judge_f5/repo`.

## 1. Veredicto único: **F5 PASADA CON ARREGLOS — NO DECLARAR todavía**

La FÍSICA del transporte está bien y lo verifiqué por vía independiente: composición desde las 2 cápsulas reales == oráculo con d=0.0 exacto (mi arnés sombra de J1 reproduce la trayectoria limpia contra el fixture; c1 re-midió los 1500 ticks completos: max|d| global = 0.000e+00). El claim nuclear ("las 150 cápsulas entran al motor nuevo") queda EN PIE. Pero el patrón F2/F3/F4 se repite por cuarta vez consecutiva: los gates están verdes sin custodiar lo que declaran. Verifiqué por re-ejecución propia (con controles que debían morir y murieron) los 2 hallazgos clase BLOQUEA y los 7 ALTO; **ninguno se degradó — todos reproducidos, varios con números bit-idénticos a los de los lentes**. Por el estándar de la casa (F4: cero mutantes vivos antes de declarar), F5 no se declara hasta ejecutar A1–A10 y re-matar TODA la población de mutantes vivos contra el código arreglado.

**Arreglos requeridos (A1–A6 bloquean la declaración; A7–A10 pre-declaración):**

- **A1 [BLOQUEA]** `tests/test_capsulas_f5.py:187-195` — gate4 compara 7/1500 ticks. VERIFICADO POR MÍ: corrupción x+=1.0 en tick 12 curada bit-exacto en tick 90 ⇒ divergencia real 4.159e+02 en [12,90) y los 7 muestreados dan 0.0 ⇒ gate VERDE. Control válido: sin curar, d=1.605e+02 cazada en tick 100. Parche: sacar la comparación del `if tick in (...)` y comparar CADA tick 1..1500 (el fixture ya trae los 1501 estados; costo segundos).
- **A2 [BLOQUEA→ALTO]** `tests/test_capsulas_f5.py:92-116` + `src/study07/compat/study06_capsule.py` — 8 ramas del lector borrables con suite verde (causa raíz: tampers de gate1 rompen specimen_id de paso + assertRaises sin regex). VERIFICADO POR MÍ con 3 mutantes representativos, cada uno 41 passed + forjador re-sellado que CARGA OK bajo el mutante y RECHAZA con el mensaje de SU rama con código intacto: JM1 contenido (z adulterado, solo file-sha reparado), JM2 naturalidad (temperature=0.5 + specimen_id recomputado), JM3 esquema v1 (harvest_tick borrado + specimen_id recomputado). Parche: por rama, tamper RE-SELLADO (patrón gate1b) + assertRaisesRegex('natural'|'esquema v1'|'CONTENIDO'|'history_head difiere'|'fields'|...); incluir el caso re-serialización (savez_compressed, mismos arrays) para separar file-sha de content-sha (c2-M1).
- **A3 [BLOQUEA]** `src/study07/artifacts/composer.py:111-125` + gate5b — el lado FRESH de la mezcla (LA capacidad nueva de F5) no tiene ningún gate de contenido. VERIFICADO POR MÍ: JM5 (ring del fresh puesto a cero) ⇒ 41 passed con física distinta: max|sana−mutante| = 7.440e-08 en 50 ticks = ~1900× el TOL 3.86e-11 (número idéntico al de c4). JM4 (birth_state con idx=0 fijo) ⇒ 41 passed; estado fresh == birth_state(idx=0) con d=0.0 y difiere del correcto idx=1 en 1.641e-02. Parche: extender la verificación post-copia a nodos fresh (columna == relleno uniforme de la emisión inicial) + ancla bit-exacta del estado fresh en gate5b.
- **A4 [ALTO]** `src/study07/compat/study06_v4.py:118` + `study06_capsule.py:107-121` + `composer.py:47-51` — la rama fresh acepta genomas que el oráculo RECHAZA. VERIFICADO POR MÍ contra el validador REAL del oráculo (import read-only, sin bytecode): theta f8 con S2 en modes pero fuera de memory ⇒ oráculo RECHAZA ('memory.layer_order.missing.S2'), study07 genome_sha256 ACEPTA, parse ACEPTA (n_z 4 vs 7), compone mixto y corre 30 ticks finito. Control: theta sano ACEPTADO por el oráculo (arnés válido). Confirmé leyendo el oráculo que su genome_sha256 llama `validate_theta_internal(require_v2_state=True)` — study07 lo omite. Parche: exigir capas de modes ⊆ layer_order + completitud v2; llamar genome_sha256 en la rama nacimiento (cierra también naturalidad-fresh: _mem_force_scale hoy pasa) y sellar genome_hash en el recibo del fresh.
- **A5 [ALTO]** `src/study07/artifacts/recorder.py:68` + `composer.py:126-129` — procedencia no exigida. VERIFICADO POR MÍ: film desde las 2 cápsulas reales, `hashes_base_externa={}` y SIN 'composicion' ⇒ COMPLETE=True, cero rastro de specimen_id/capsule_sha256 en el artefacto. Control válido: sin run_id el recorder rechaza. Parche: recibo adherido a la red y EXIGIDO por el recorder (composicion + capsule_sha256 de cada nodo-cápsula en hashes_base_externa); enmienda a WORLDLINE_SCHEMA.
- **A6 [ALTO]** gate6/inventario — VERIFICADO POR MÍ: 148/150 filas basura + sidecar recomputado ⇒ gate6 1 passed en 0.15s y los 8 gates verdes; control válido (sin refrescar sidecar: 1 failed). **HALLAZGO NUEVO DEL JUEZ que lo agrava:** `data/inventario_v4.json` NO está versionado (`data/*` en .gitignore; `git ls-files` solo trae el tool) — el artefacto que gate6 audita es un archivo local no rastreado: un clon fresco de 3792ff6 ni siquiera pasa gate6, y el sellado "8/8" no es reproducible desde el repo. Parche: versionar inventario+sidecar como los fixtures (lección §90-g B1), sellar `INVENTARIO_SHA_SELLADO` y `F8_SHA_SELLADA` como constantes en el test (verifiqué: F8_SHA_SELLADA=None es constante muerta; f7 sí cumple el patrón triple en test_instruments.py:50,84), y validar estructura de las 150 filas.
- **A7 [MEDIO]** `tests/test_conformance_oracle.py:230` — OLA_SCOPE excluye `artifacts/` (verificado en el código: tupla sin artifacts), justo donde vive el composer que maneja `source`. Agregar 'artifacts'.
- **A8 [MEDIO]** `tools/inventario_v4.py:101` — oracle_tag HARDCODEADO Y FALSO, VERIFICADO POR MÍ: HEAD del oráculo = 39f8df6, `git tag --points-at HEAD` = vacío, el tag apunta a ca437b7. Medir el tag, no asumirlo ("asumir números es asumir física").
- **A9 [MEDIO]** `composer.py:126-128` — recibo sin `topology_quench` / `stationary_claim_exclusion_ticks` / set_digest (higiene de claims del receipt del oráculo :1025-1056) + enmienda F5 a WORLDLINE_SCHEMA para 'composicion'.
- **A10 [MEDIO]** tests negativos para las verificaciones defensivas del composer (formas/capas e_ref/post-copia — c1-M10/11/12, c2-M16), flags read-only (c2-M22), capas no transportables en genome_sha256 (c2-M24), y sub-caso unitario de quench con head≠0 sintético (c2-M6: las 150 cápsulas tienen head=0 — el re-base nunca se ejercita).

**Condición dura:** tras aplicar A1–A10, re-correr la población COMPLETA de mutantes vivos (11 de c1, 12 reales de c2, 2 sondas de c4, JM1–JM5 del juez) contra el código arreglado: **0 vivos** o F5 no se declara. c2-M14/M17 quedan EXENTOS (equivalentes verificados: head_idx nace 0 en delay.py:20; Network copia estados en network.py:32).

## 2. Tabla de mutantes

| Quién | Probados | Muertos | Vivos | Nota |
|---|---|---|---|---|
| JUEZ (independiente) | 6 código + 2 sondas datos + 3 experimentos | JM6 control quench-flip (2 failed) · control sidecar (1 failed) · 3 controles de arnés (forjador vs intacto, oráculo vs sano, recorder sin run_id) | JM1, JM2, JM3, JM4, JM5 (todos 41 passed) + sonda inventario (8 passed con 148 filas basura) | 5/5 vivos reportados por lentes CONFIRMADOS; todos los controles murieron ⇒ arnés válido |
| c1 | 14 | 3 (M9 quench-flip, M13 e_ref-idx0, M14 head=1) | 11 | mecanismo causal (specimen_id enmascara + assertRaises sin regex) confirmado por el juez |
| c2 | 25 | 11 | 14 (12 agujeros reales + 2 equivalentes M14/M17) | JM1≈M2, JM2≈M8, JM3≈M9, JM4=M18 confirmados |
| c4 | 2 sondas | — | 2 (ring fresh, inventario) | JM5=c4-M1 confirmado con número idéntico (7.440e-08); sonda inventario confirmada |

Lo que SÍ protege (consenso de los 4 lentes + mis controles): gate1b (re-sellar todo + regex, el patrón a copiar), gate2 (ancla de genoma contra sellos del oráculo — referencia independiente real), gate3 (flip/off-by-one/extrapolación del quench mueren), gate4 contra corrupción PERSISTENTE y e_ref adulterado, el check interno post-copia (mata M13/M16-inyección), rechazos de gate7, la cadena blocks_sha256 inventario==f8==f7, y el entorno pinned en modo 0.0 exacto.

## 3. Transcripción y contratos por cláusula

| Cláusula | Veredicto | Evidencia |
|---|---|---|
| Transcripción del lector (orden/semántica de checks) | CUMPLE | c3 cotejó línea por línea; 9/9 sha de claves de source decodifican exacto; única diferencia declarada (RuntimeError vs SpecimenCapsuleError) |
| Transcripción de genome_sha256 | **PARCIAL** | el oráculo llama validate_theta_internal(require_v2_state=True) (leído por el juez en specimen_capsule.py:99-104); study07 lo omite ⇒ A4 |
| Física del transporte (estado+buffer+1500 ticks) | CUMPLE | 0.000e+00 exacto; re-medición completa de c1 + arnés sombra del juez |
| Cláusula 1 (source OPACO, motor sin niveles) | PARCIAL | mecanismo sellado correcto y gate de palabra mata en compat; pero la rama de esquema es borrable (A2) y artifacts/ fuera del scope (A7) |
| Naturalidad heredada | PARCIAL | cápsula: shipped OK pero rama borrable (A2); fresh: NO gateada (A4) |
| PROVENANCE_CONTRACT | **INCUMPLE** | film huérfano COMPLETE verificado por el juez (A5); inventario no versionado (A6) |
| Quench espejo del restore | CUMPLE (con resto) | bit-exacto vs f8; head≠0 y canonical_ring_exact inejercitados (A10 / NO-CUBIERTO) |
| Mezcla cápsula+fresh declarada | PARCIAL | declarada honestamente, pero su mitad fresh sin ningún ancla (A3) |
| Inventario 150 / cadena | PARCIAL | cadena f7==f8==inventario cierra; 2/150 ancladas en suite; 148 a tiempo-de-herramienta; artefacto fuera de git; oracle_tag falso (A6/A8) |
| Entorno pinned / niveles de gate | CUMPLE | exact-0 activo, degradación a TOL declarada por print |

## 4. NO-CUBIERTO consolidado (va a la bitácora §8 — F5 no tenía lista propia)

1. Lado fresh de la mezcla: ring inicial + acople cápsula→fresh en la ventana del delay — cero gates de contenido hasta A3.
2. 148/150 filas del inventario: contenido verificado solo a tiempo-de-herramienta (declararlo en el docstring de gate6 tras A6).
3. Camino `canonical_ring_exact` (tau=2.0, delay igual) sin test ni fixture; modo `exact_reconstruction/raw_ring_exact` del oráculo NO implementado — declarar fuera de alcance.
4. Quench con head≠0: población real 150/150 con history_head=0 — solo cubrible con unit sintético (A10).
5. `preserve_serialized` inalcanzable desde componer_red (política fresh fija por firma).
6. Bordes: delay-0 descarta 25000 pasos de biografía en silencio; cápsula duplicada legal sin marca (espejo fiel del oráculo, pero doctrina de clones §47 pediría declararla); theta sin Q cae al fallback de phase sin registro en la vista.
7. Termalización futura de composiciones (F6/F7) sin vía declarada (T=0 solo custodiado en la puerta).
8. Passports v4: identidad hasheada en el inventario, contenido fuera de alcance de F5 — entran con el explorer/pasaporte 3 caras.
9. Solo 2/150 cápsulas ejercitan el motor en suite; las 150 solo vía tool.
10. Tools sin study07_commit propio (mitigado: artefactos commiteados… salvo el inventario — ver A6).

## Repos intactos — verificado al cierre

- `/Users/cagostino/code/doft-study07-worldline`: `git status` limpio @ 3792ff6. Cero escrituras.
- `/Users/cagostino/code/doft-study06-fundamental-lock-dynamics` (oráculo): `git status` limpio @ 39f8df6. Mi único acceso fue lectura + import con `PYTHONDONTWRITEBYTECODE=1`; los `__pycache__` presentes (gitignorados) tienen mtime ANTERIOR a esta sesión (00:04 / 11:20) — no son míos. Ningún archivo R_f leído.
- Copia de trabajo restaurada: `git status` limpio, inventario sha `dbb6a1cee91233d4` == repo real, F5 de nuevo 8 passed tras la matanza.
- Artefactos del juez: `scratchpad/judge_f5/{exp_gate4_sampling.py, exp_provenance.py, exp_fresh_genome.py, demo_forjador.py, demo_mezcla.py, mutar.py}`.