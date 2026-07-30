Todo verificado. Consolido el veredicto.

---

# VEREDICTO DEL JUEZ — DOUBLE TAP GATE F2 (motor mínimo Study07 vs oráculo Study06)

Auditado: study07 @ e0e565a (el HEAD actual 7e81632 sólo tocó `specs/WORLDLINE_SCHEMA.md`; el código bajo gate es idéntico). Ambos repos intactos; toda mutación ocurrió en `/private/tmp/claude-501/.../scratchpad/juez/` (driver: `juez/driver.py`, resultados: `juez/resultados_mutantes_juez.json`, inspector: `juez/inspect_fixtures.py`). Entorno del juez: numpy 2.3.4, x86_64 — coincide con el meta de los fixtures (que registra `numpy=2.3.4, machine=x86_64, python=3.13.9`).

## 1. Veredicto único: **GATE F2 PASADO CON ARREGLOS**

- **El resultado de conformidad SE SOSTIENE**: reproduje el suite completo (7 passed, 50s) y el residuo pristino es `max|d|=0.000e+00` exacto, con `d0=0` y `buffer0=0`. Verifiqué además que f5 SIN inyección de estados del RNG también da 0.0 y que la semilla derivada `(42·1000003+99991)&0xFFFFFFFF` produce exactamente `rng_states[0]` del fixture — el cero incluye el camino del ruido. Tres lentes lo triangularon por vías independientes del gate (lectura operación-por-operación, diferenciales contra el oráculo VIVO en los caminos no cubiertos, censo 150/150 genomas bit-exactos).
- **El GATE como escudo NO se sostiene todavía**: certifica la transcripción sólo en el régimen frío y degenerado de los 5 fixtures. Re-verifiqué yo mismo 6 mutantes de ley y 4 de arquitectura: los 10 VIVOS con gate verde, con números idénticos a los reportados por los lentes. F2 se declara únicamente con los arreglos 1–5 de §5 aplicados y con la lista NO-CUBIERTO de §4 pegada al lado del claim.

## 2. El residuo cero, en una frase citable

**El 0.0 es diseño, no casualidad: el motor es una transcripción operación-por-operación de la misma aritmética IEEE-754 del oráculo (mismo orden de acumulación, mismo RK4, mismo RNG con la misma semilla derivada), corrida en el mismo entorno que generó los fixtures (numpy 2.3.4, x86_64) — y deja de estar garantizado si cambia numpy o la máquina, que es exactamente por qué el gate formal es ≤3.86e-11 y el cero es un hecho observado, no una propiedad exigida por ningún assert.**

## 3. Tabla de mutantes (consolidada entre los 5 lentes + re-verificación del juez)

| | probados | detectados (rojos) | vivos verdes |
|---|---|---|---|
| a2 (batería principal) | 27 | 13 | 14 (3 equivalentes + 11 agujeros de ley) |
| a1 (nuevos: orden nodos FDT, push-antes-del-ruido) | +2 | 0 | 2 |
| a3 (nuevos: g_eff b_deep, orden W, intra capa-j) | +3 | 0 | 3 |
| a4 (nuevos: gamma_c, preserve, orden KV, rama tuple) | +4 | 0 | 4 |
| a5 (arquitectura + 2 sanity) | +6 | 2 (sanity) | 4 |
| **TOTAL sin duplicados** | **42** | **15** | **27 = 3 equivalentes benignos + 24 agujeros reales** |

Equivalentes benignos (no son agujeros): `sa<0`, push-al-inicio-del-step (bit-idéntico por alineación del ring), reorden memoria/intra (~1 ulp, bajo el piso).

**Re-verificados independientemente por el juez (13/13 coinciden con los lentes, cero discrepancias):**

| mutante del juez | qué rompe | residuo medido | gate |
|---|---|---|---|
| JM1 on-site ÷ masa (lo que §1.1 PROHÍBE) | ley | 0.000e+00 (f1,f4) | VERDE — vivo |
| JM2 EPS_K=0.0 (canal b→acoples BORRADO) | ley | 8.8e-13…1.07e-11 (5/5) | VERDE — vivo |
| JM3 emission_scale eliminado | ley (producción 'mean') | 0.000e+00 (f4) | VERDE — vivo |
| JM4 kappa_global omitido | ley | 0.000e+00 (f4) | VERDE — vivo |
| JM5 g_eff con b de capa DEEP (la sutileza que §1.3 sella) | ley | 2.3e-12 (f1), 1.9e-11 (f4) < TOL | VERDE — vivo |
| JM6 semilla ruido 99991→99992 | §6 | 0.000e+00 (f5, inyección lo tapa) | VERDE — vivo |
| JM7a-d: «ola1» en engine / `ola_level` en physics / `from matplotlib import pyplot`+`np.load` en engine / `physics/sub/contrabando.py` con todo lo prohibido | arquitectura | — | 4/4 VERDES — vivos |
| sanity: «ola» y «open(» en la superficie cubierta | — | — | 2 failed (los gates funcionan donde miran) |
| verde-vacío: `STUDY06_ORACLE_PATH=/nonexistent` | proceso | 2 passed, 5 skipped, **exit 0** | confirmado |

Causas raíz medidas por el juez desde los datos (no desde los priors): masas = **{1.0}** en los 1500 modos del JSON canónico; `emission_norm='sum'` en 5/5 fixtures (el contrato §4 sella producción v1 con 'mean'); `kappa_global=1.0`; max|b| ≤ 1.0e-8 y max|z| ≤ 1.3e-4 en todas las trayectorias almacenadas (la dinámica lenta está dormida); T>0 sólo en f5, que es mono-nodo sin aristas; `head0` presente en los 5 npz y jamás leído por el test.

## 4. NO CUBIERTO POR EL GATE (va a bitácora tal cual)

1. Régimen caliente: b,z ~O(1) — canal b→acoples (EPS_K), clamp tanh ±5, piso 1e-9 de tau_eff jamás se enganchan (max|b|≤1e-8 medido en los npz). Contrafáctico de a2: con IC×100, borrar eps_k separa 6.5e-6 — cinco órdenes sobre el gate.
2. Masas ≠ 1.0 — toda división por masa (§1.1, §1.5) es identidad bit-exacta en los 150 genomas.
3. kappa_global ≠ 1.0; `coupling_gamma_c` explícito, su precedencia sobre `damp_ratio`, alias legacy `K_global`.
4. `emission_norm='mean'` — el modo de PRODUCCIÓN v1 (contrato §4); los 5 fixtures son 'sum' (legacy).
5. T>0 con >1 nodo y aristas: orden de consumo del RNG entre nodos y ruido→historia emitida (push tras el kick).
6. Derivación de la semilla del ruido §6 con stream propio: f5 inyecta el estado antes de CADA step (verifiqué que hoy el stream propio coincide — la propiedad existe pero no está pineada).
7. Orden de acumulación KV / grado ≥8 (grado máx de los fixtures = 2; suma de 2 términos es conmutativa bit-exacta).
8. `e_ref_policy='preserve_serialized'` (§7.2 — «física distinta en el punto fijo de b»).
9. Aristas tuple legacy y `tau_field` como default.
10. Restore desde cápsula: NO EXISTE (sólo birth); `HistoryBuffer` no admite historia inicial no-uniforme por API — las `history_column` de las cápsulas v4 hoy no cargan.
11. Dominio de compat: sin check de `schema_version` (el docstring promete el rechazo de V3 que no implementa), capa presente sin memoria → `continue` silencioso, `e_ref` ausente → 0.0 silencioso, links duplicados sin dedup — study07 ACEPTA lo que `validate_theta_internal(require_v2_state=True)` del oráculo RECHAZA.
12. Integridad del gate mismo: `head0` no comparado, `np.__version__`/`machine` no asertados contra el meta, sidecar `study07_fixtures.sha256` jamás verificado, oráculo ausente = verde-vacío con exit 0.
13. Entorno: sin CI (README:13 declara un «Gate de CI» inexistente), sin requirements — el pin numpy==2.3.4 es prosa.
14. El claim «bit-exacto» en sí: el assert de trayectoria es ≤3.86e-11 — el cero es observado, no exigido.
15. Población: 4/150 genomas — MITIGADO: censo de a4 150/150 bit-exactos y población estructuralmente homogénea (una sola clase; los casos raros sólo pueden entrar por compat → punto 11).

## 5. Arreglos exigidos (1–5 bloquean la cita de F2 como gate; 6–8 antes del próximo commit de física)

1. **Gate de dos niveles** — `tests/test_conformance_oracle.py:26,102-104`: si `(np.__version__, platform.machine()) == (meta['numpy'], meta['machine'])` → `assertEqual(r["max_d"], 0.0)`; si no → `assertLessEqual(TOL)` con warning impreso. El meta ya trae ambos campos. Mata JM5 (1.9e-11) y JM2 (1.07e-11) en este entorno, sin romper portabilidad (adjudica la contradicción a1↔a3: exactitud donde es válida, TOL documentado donde no).
2. **Fixture f6 NO-degenerado** (generar con `logs/s93_c4_fixtures.py` del oráculo congelado en ejecución read-only; el npz se versiona en study07 `tests/fixtures/` con sha256): 2-3 nodos, masas≠1, `kappa_global=0.7`, `coupling_gamma_c` explícito, `emission_norm='mean'`, `temperature=0.05` con aristas τ fraccional, estado caliente (IC×100 o cápsula v4) para b≥1e-4. Cierra de un golpe JM1, JM3, JM4, m10, m02b/EPS_K, m05, m20, m07, m08, m22, orden RNG multi-nodo, push-vs-ruido y orden de aristas KV.
3. **Pinear la semilla del ruido** — `tests/test_conformance_oracle.py:74-81`: antes del replay de f5, `self.assertEqual(net.noise_rng.bit_generator.state, json.loads(str(fx["rng_states_json"][0])))` + segunda pasada con `use_rng=False` exigiendo 0 bajo entorno pineado. Mata JM6. (La propiedad ya es verdadera — la verifiqué.)
4. **Gates de arquitectura reales** — `tests/test_conformance_oracle.py:123-141`: regex `r'(?i)(?<![A-Za-z])olas?(?![A-Za-z])'` (caza `ola_level`, `ola1`, `OLA`; no «sola»), alcance `physics/` + `engine/` con `rglob('*.py')` (compat: incluido en el gate ola, excluido del gate IO POR ESCRITO), y denylist por AST (`Import`/`ImportFrom` de {matplotlib, pandas, h5py, PIL}; llamadas {open, load, save, savez, savetxt, read_text, write_text, dump}) en vez de substrings; agregar `paper5` y `olar` al set prohibido de imports. Mata JM7a-d.
5. **Fail-loud del gate** — `tests/test_conformance_oracle.py:61-62`: oráculo ausente = FAIL (skip sólo con `STUDY06_ORACLE_OPTIONAL=1` explícito) + verificar `study07_fixtures.sha256` (sellar los 6 hashes como constantes en el test, con commit del oráculo citado) antes de `np.load` + comparar `head0`. Mata el verde-vacío (medido: 2 passed, 5 skipped, exit 0).
6. **Entorno**: `requirements.txt` con `numpy==2.3.4`; README:13 «Gate de CI» → «gate ejecutable local» hasta que exista CI; `.gitignore:3` `logs/` → `logs/*` (regla de re-inclusión muerta, verificada con `git check-ignore`: la negación de la línea 4 nunca se evalúa — la forma exacta del §90-g).
7. **Enmiendas al contrato** (`specs/PHYSICS_CONTRACT.md`): §1:49 «orden de capas canónico» → «orden SERIALIZADO `memory.layer_order` (coincide con el canónico en toda la población v4)» — el código está bien, el texto no (verificado contra `physics_core.py:545-547`); declarar en §1.5 la equivalencia `drive_ext != 0.0` vs `is not None` (`rhs.py:93` vs `physics_core.py:570`); fijar en §1.2 que la b del intra es la de la capa del extremo i; en §7.1, o portar la validación (`schema_version=='theta_internal_v2'`, cobertura de memoria por capa presente, longitudes iguales, `e_ref` obligatorio, dedup fail-loud de links duplicados — `compat/study06_v4.py:86-94,116,72-77`) o declarar el dominio reducido del lector.
8. **Doctrina**: la lista de §4 se pega en la bitácora junto al claim. El claim citable queda: *«el motor reproduce los 5 fixtures de conformidad del oráculo con residuo 0.0 bit-exacto en el entorno del generador (numpy 2.3.4/x86_64) — conformidad verificada EN EL RÉGIMEN FRÍO de los fixtures; el régimen caliente y los modos de producción quedan cubiertos por f6»* — no «el motor ES la ley».

Lo que SÍ resistió el ataque y merece constar: higiene de dependencias real (cero imports de paper5/olar, verificado también en `sys.modules` post-replay), el estado inicial se RECONSTRUYE por RNG derivado y coincide bit-exacto (no se copia), f4 con pesos heterogéneos y taus fraccionales mata 13 mutantes con márgenes de 4 a 200 órdenes, y el autor no compartió ni una línea con el oráculo. La transcripción es fiel; lo que faltaba era que el gate lo demuestre solo.