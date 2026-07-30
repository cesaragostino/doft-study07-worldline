Verificación completa. Ambos repos quedaron intactos (todo corrió sobre copia en scratchpad; el driver restauró pristine al final). Resultado para la bitácora:

---

# DOUBLE TAP F4 — VEREDICTO DEL JUEZ

Repo auditado: `/Users/cagostino/code/doft-study07-worldline` @ 522683e. Entorno **pinned** confirmado (numpy 2.3.4 / x86_64 == meta7 ⇒ los gates exigen 0.0 exacto). Baseline reproducido: **6 passed (~5s)**. Batería independiente del juez en sandbox: `scratchpad/judge_f4/{driver.py,probes.py}`, una mutación por vez, restore + purga de `__pycache__` entre corridas, con control que DEBE morir (murió: arnés válido).

## 1. Veredicto único: **F4 NO PASADA**

El espejo físico es genuino: el camino anclado (t0=0, t1=full, stride=1) reproduce al oráculo a 0.000e+00 exacto y el control (atan2 invertido) muere en gate A. Pero los gates no protegen el instrumento: **11/11 mutantes construidos por el juez viven con 6/6 verde**, cubriendo los cuatro BLOQUEA_F4 de los lentes, todos verificados por mi cuenta. Tres cláusulas del INSTRUMENT_CONTRACT están incumplidas en código (no en prosa): el caché escrito jamás se relee y `write()` rompe la estabilidad del `view_hash` (verificado: pre-write `e53c5876` == almacenado; post-write recomputado `4fb5e385` ≠ almacenado; segundo write almacena otro hash); la identidad del film no se coteja nunca (hash constante `"f"*64` pasa todo); la constitución de energy no está atada al film (masa×2 aceptada sin error, max|dE|=2.144e-01; nodos permutados aceptados, max|dE|=4.412e+02; el manifiesto del film no lleva `spec_fingerprints` y `hashes_base_externa={'fixture_f6':'local'}` es placeholder). Regla dura de F3: no se declara hasta aplicar los arreglos y **re-matar los mutantes contra el código modificado**. Patrón confirmado: F2=24 vivos, F3=5 vivos, F4=15 vivos únicos (11 verificados por el juez).

### Arreglos requeridos para el próximo tap (file:línea + parche)

- **A1** `tests/test_instruments.py:83-98` (gateC): asserts exactos de recorte/decimación para `r`, `j`, `z`, `omega`, `ticks` en `vb` y `vc` (no sólo `theta`), + referencia escalar independiente para `vc.j` con `dt_ef=5·dt` (c1 la verificó a residuo 0.0). Mata J-M1/J-M2/J-M5.
- **A2** `tests/test_instruments.py:63-75` (gateA): comparar `v.arrays['z']` contra `ref['z']`; sub-gate con `r_min=0.99` sobre el MISMO film (r∈[0.6008,0.9998] ⇒ ambas ramas pobladas): `omega_valid==(ref['r']>=0.99)` y `isnan(omega[~valid])`. Mata J-Mz/J-Mo/J-Mr.
- **A3** `src/study07/instruments/api.py:45-52,54-63`: `view_hash()` hashea el manifiesto EXCLUYENDO la clave `view_hash`; `write()` no muta el hash base, escribe `data.npz` primero y el manifiesto al final como marca de cierre, rechaza overwrite con `view_hash` distinto; agregar `load_view()` que relee y recomputa fail-loud; gate D pasa a comparar recompute vs **DISCO**. Mata J-M3/J-M13 y sella idempotencia.
- **A4** identidad: gate `wl['worldline_hash'] == json.loads(COMPLETE)['sha_total'] == rec.close()` + dos films distintos ⇒ hashes distintos; `api.py:20-23`: `worldline_hash = sha256(sha_total || manifest_sha)` (el manifiesto que phase/energy LEEN debe estar dentro de la identidad — colisión dt×2 confirmada por lectura de `recorder.py:152-158`). Mata J-M15/J-M6.
- **A5** energy: gate con ventana `{'t0_tick':500,'t1_tick':1000,'stride':5}` vs recorte bit-exacto + clon de gateE para energy. Mata J-M4. `recorder.py:74-95`: `spec_fingerprints` en el manifiesto del film (la función ya existe en `checkpoint.py:20`); `energy.py:31`: verificar por nodo contra `man['spec_fingerprints']`, fail-loud; `MAN` con sha real de f6, no `'local'`.
- **A6** anclas f7: en `setUpClass` assert `sha256(F6)==meta7['f6_sha256']` y `sha256(F7)==sidecar` (hoy coinciden — verificado — pero ningún test los mira: grep `sha256` en `test_instruments.py` = 0 hits); `tools/gen_f7_observables.py:75-81`: assert por-tick contra f6 dentro del loop (hoy sólo fila 0); `:89` oracle_commit medido con git, no prosa.
- **A7** `recorder.py:16`: mover `Network` a `TYPE_CHECKING` + gate de subproceso limpio (verificado: `import study07.instruments.api` carga `study07.engine.network` transitivamente — "sin re-simular" es sintáctico, no invariante de proceso).
- **A8** validación de ventana compartida en api: `0<=t0<=t1<len(ticks)`, `stride>=1`, `sel.size>0`; whitelist de claves (`set(obs)-set(DEFAULTS)` ⇒ error de contrato); agregar `'ticks'` a `exigir_canales` y exigir `wl['complete'] is True` por defecto.
- **A9** fixture heterogéneo (2 nodos, layouts distintos) para que `capas_por_modo` deje de testearse vacuamente (c2-M16 sobrevivió la suite COMPLETA).
- **A10** condición dura F3: re-matar los 15 vivos contra el código arreglado antes de declarar F4.

## 2. Tabla de mutantes

Batería del juez (independiente, verificada): **12 probados / 1 detectado / 11 vivos**.

| Mutante | Toca | Gate que debía cazarlo | Resultado |
|---|---|---|---|
| J-M1 dt_ef=dt (ignora stride) | phase.py:52 | C/D | **VIVO** 6/6 |
| J-M2 subsample arranca t0+stride−1 | phase.py:30 | C/D | **VIVO** |
| J-M5 J=0 si t0>0 | phase.py:65 | C | **VIVO** |
| J-M15 worldline_hash="f"×64 | api.py:20-23 | C/F | **VIVO** |
| J-M6 worldline_hash=manifest_sha | api.py:23 | C/F | **VIVO** |
| J-Mz z con signo invertido | phase.py:56 | A | **VIVO** |
| J-Mo omega inválido→0.0 (no NaN) | phase.py:69 | A | **VIVO** |
| J-Mr r_min ignorado (ok=isfinite) | phase.py:67 | A/F | **VIVO** |
| J-M3 write() guarda npz sin arrays | api.py:61 | C/D | **VIVO** |
| J-M13 view_hash ignora arrays | api.py:49-51 | D | **VIVO** |
| J-M4 energy ignora su ventana | energy.py:34 | B | **VIVO** |
| CONTROL atan2(X,V) | phase.py:45 | A | MUERTO (gate A) |

Corroboración lente c2 (no re-corrida por el juez): 17 probados / 12 muertos / 5 vivos — los 12 muertos son la física del espejo (θ/J/ω/E), márgenes 4.8e-05…3.2e+02; sus vivos adicionales: M16 capas_por_modo nodo-0 (suite completa verde), M04 r_min default 0.5, M05b eps_den hardcodeado, y el float32-cache de c3. **Vivos únicos consolidados: 15** (11 verificados por el juez, 4 reportados por lentes con evidencia consistente).

## 3. INSTRUMENT_CONTRACT por cláusula

| Cláusula | Estado | Evidencia |
|---|---|---|
| instrument_id+versión | CUMPLE | gate F |
| required_channels: falla, jamás sustituye | PARCIAL | gate E sólo phase/estados=[]; predicado sólo listas vacías; `ticks` y `complete` sin declarar; energy sin gate equivalente |
| observation_config DECLARADA (ventana/stride/umbral) | INCUMPLE en efecto | declara pero no valida ni honra verificadamente: J-M1/M2/M5/M4/Mr vivos; t0 negativo wrapea; typo entra al config_hash |
| worldline_hash → vista con hash y procedencia | INCUMPLE | J-M15/J-M6 vivos; identidad excluye el manifiesto que los instrumentos leen; procedencia placeholder; constitución sin contraparte (verificado: masa×2 y permutación aceptadas) |
| NO muta ni ejecuta el motor | PARCIAL | no ejecuta (cierto hoy), pero engine CARGADO transitivamente (verificado en subproceso); gate AST sólo imports directos |
| Recalculable y comparable contra su caché | INCUMPLE | no existe lector de vistas (grep src/: 0 hits); gate D compara RAM-vs-RAM; J-M3/J-M13 vivos; view_hash inestable post-write (verificado) |
| Distingue dato/inferencia/veredicto | INCUMPLE | sin forma ejecutable; api.py:6 la reescribe debilitada ("dato de configuración") |
| Vistas POR NIVEL (cláusula 2 COA) | NO EVALUADA | F4 sólo cubre nivel red — declarar fuera de alcance, no cumplida |
| Migración con fixture del oráculo | CUMPLE SÓLO en el camino default | 0.0 exacto verificado en (t0=0, t1=full, stride=1); resto del espacio sin fixture |

## 4. NO-CUBIERTO consolidado

1. Espacio de `observation_config` fuera del default: stride>1 y sub-ventanas sin referencia para r/j/z/omega; energy jamás corrida con ventana en tests.
2. Canal `z` y slots inválidos de `omega` jamás comparados contra referencia.
3. El NULO del instrumento (r_min/omega_valid) nunca ejercitado: f7 tiene 0/1501 ticks en [0.08, 0.5), omega_valid=1501/1501 (medido) — la clase exacta de deriva de Study06.
4. `eps_den` inalcanzable en films físicos (constante-guardia no auditable); declaración≠uso sin gate.
5. Caché en disco: sin lector, sin marca de cierre (manifest antes que data), overwrite silencioso del mismo path, hash inestable en re-write.
6. Identidad del film excluye el manifiesto (colisión dt por construcción); `hashes_base_externa` acepta placeholders.
7. Constitución↔film sin huella verificable (sin `spec_fingerprints`).
8. Anclas f7 no verificadas por tests (hoy válidas, verificado a mano); degradación `_pinned`→TOL silenciosa, y TOL=3.86e-11 admite trayectorias a distancia ≲5e-12 en estado (medido por c1, régimen contractivo); gen_f7 verifica sólo tick 0; oracle_commit hardcodeado.
9. "Sin re-simular" es sintáctico: motor cargado transitivamente en el proceso.
10. Ventanas malformadas: wrap negativo, vista vacía escrita, IndexError crudo, stride 0/negativo; sin whitelist de claves.
11. Films incompletos observables por puerta lateral (`allow_incomplete` + hash inventado) y publicables.
12. Población de fixtures homogénea: layout por nodo testeado vacuamente (mutante nodo-0 sobrevive la suite completa).
13. n=1 ⇒ R≡1 identidad-por-construcción sin declarar; T=0 y film de 0 ticks cubiertos de facto sin gate propio.
14. Stride de grabación protegido por accidente (loader exige ticks consecutivos); instrumentos asumen índice==tick y no leen `perfil`.
15. J estriado es OTRO estimador (max|d|=8.4e+01 vs decimado) declarado sólo en nota prosa; borde de ventana redefine J[0]/omega[0]; no existe VIEW_SCHEMA; WORLDLINE_SCHEMA sin enmienda `por_nodo`; `views/<hash>` vs truncado `[:16]`.

Reproducción: `python3 scratchpad/judge_f4/driver.py` (batería) y `python3 scratchpad/judge_f4/probes.py` (P1-P6). Repos read-only respetados; sandbox restaurado a pristine.