# DOUBLE TAP DISEÑO OLA B — VEREDICTO
**Juez del tap de diseño — todo BLOQUEA/ALTO re-ejecutado de forma independiente en sandbox propio** (`scratchpad/juez_diseno/`: `j_eje.py`, `j_sint.py`, `j_eje_w.json` + corridas inline sobre `aristas_juez.json`, `SPEC_lote1.json`, `dw_fino_seleccion.json`, `carriers_fina.json`, las 26 unidades COMPLETE de lote 1, `census_arnold_correr.py` y `campana.py`). Mi implementación de `w_fina` reproduce el sellado bit-exacto (max|dif|=0 sobre 150 rings). Lock C1 = `rw_corr≥0.95` sobre 288 aristas reproduce los cuartiles 88.9/58.3/27.8/9.7 exactos. Repos intactos (git status limpio en ambos), census vivo (PID 79786, sin REPORTE aún), lote1 no tocado.

## 1. Veredicto: **COINCIDE CON CAMBIOS**

Los tres lentes coinciden en lo esencial y **todo BLOQUEA/ALTO se confirmó bajo re-ejecución independiente** — ninguno se cayó. El núcleo del diseño (concentrar el remanente en [0,2] sobre `dw_fina`, pooling A∪B, contraste t−f apareado) sobrevive; el sello queda **condicionado a C1..C9**. Se avanza sobre la versión del DISENO_OLA_B.md con estos cambios exactos:

- **C1 — CENTINELAS EN LA COLA (operativo, con reloj: antes de que caiga `lote1/REPORTE.json`, hoy).** La sesión dueña crea `data/census_arnold/lote2/REPORTE.json` y `lote3/REPORTE.json` con `{"estado":"SUPERSEDIDO por DISENO_OLA_B"}`. *Re-verificado: el runner vivo itera `for n in (1,2,3)` y saltea SOLO si existe REPORTE; `lote2/` y `lote3/` no existen; el lote 2 supersedido (150 u. ≈ 11 h) arranca solo al cerrar lote 1.* Declararlo como paso operativo 0 del diseño.
- **C2 — Corregir el bloque Contexto con los números REALES de ola A = lote 1 (75 pares).** Medido: **2** pares <0.05 (no 6), 12 en [0.05,0.275), 27 en [0.275,1.5), 34 en [1.5,60); **30** en [3,60) (no 45 — el 45 no cuadra con ninguna población: sel-150 da 60); cola: [2,3):2, [3,5.1):13, **[5.1,10): 2**, [10,19.8):15, **nada sobre 19.77**; reuso máx **6×** (83 nodos), no 9×; «161 disponibles» → **159**.
- **C3 — Horizonte y outcome del corazón.** Re-medido en las 26 COMPLETE con view (13 pares, dw 0.014–0.31): FIRME W=4 sostenido 2W = **1/26**; **9/26 siguen subiendo** (+>0.01/u.t.) al corte, extrapolando cruce de 0.95 a **+1..+27 u.t.** después de 60. Sellar 60 y leer frac-lock fabricaría una punta de lengua invertida. Cambio: unidades de los bins [0,0.30) corren a **120 u.t.**; el lock se pre-registra ADEMÁS como variable **censurada** (supervivencia, t_lock censurado al horizonte) en TODA la ola; **pulling = outcome primario bajo dw<0.275** (zona_falso_firme W=4 — ahí FIRME no discrimina por construcción).
- **C4 — Rediseño del brazo κ/τ (tal como está es teatro: poder ≈ α).** Re-medido: κ 0.2 vs 0.3 a τ=0.2 = **0/72 discordantes** (media|Δrw|=0.025); lock en dw∈[0.1,0.6] = **0.917 en LAS 4 celdas** (plateau, n=12); frontera p50 (logística mía): 1.47 celda ppal → 2.16 con τ=0.05 (corrimiento hacia afuera); los 6 discordantes de τ viven todos en dw∈[1.18,19.6] — **cero en la ventana [0.1,0.6]**. Cambio: eliminar (0.2,0.2) y (0.2,0.05); **una celda (0.3,0.05) × 25 pares en dw∈[0.8,2.8]** (reusa pares de B, sólo transported, 25 u.), declarando que el brazo es condicional a borde abrupto; las ~20 u. liberadas van al núcleo.
- **C5 — Eje y estratos.** Re-medido exacto: retención del corazón bajo re-medición por columna v / NLS = **55.3% / 64.6%**; [0.05,0.15) 63.5/64.1%; portadora del corazón mediana 7.31 con 90%<9 (la banda mala: fina p90 sintético 0.13 en w<7 vs <0.01 en w>9). Cambios: (a) bins de selección quedan, pero **inferencia primaria = dw continuo con σ_dw por par declarada** (tabla σ(w̄)×√2 en el archivo sellado) y estrato-corazón fusionado **[0,0.15)** (retención 79/86%; ojo: [0.15,0.30) queda en 66–71% — otro motivo para el análisis continuo, matiz mío sobre d1); (b) pools de los bins <0.15 = **intersección dw_fina∩dw_nls** (medido: 104 pares/106 nodos — alcanza); (c) **veto de eje blando** en bins <0.30: nodos con |w_fina(x)−w_fina(v)|>0.15 (6) o residuo NLS>0.3 (8) — los 3 saltadores de modo (41410e9c, 9611ef40, 00585fa8; |wx−wv| 192.6/106.9/6.8) están en el top-8 de reuso del corazón (7×,6×,6×): la selección por dw chico enriquece error; (d) **borrar la cláusula de relajación del tope** (tope 3 duro); (e) **retirar w_hilbert como validador** (sesgo re-medido +0.6..+0.8 con 2º armónico; 31/150 rings con razón ≥0.1) — queda como chequeo de octava; no citar 0.065 como error del eje; (f) dw medido <0.02 se reporta «<piso del eje».
- **C6 — Reasignación del presupuesto (tabla en §2).** Re-medido el contraste t−f por cuartil C1: **+0.222 / +0.375 / +0.194 / −0.083** — la ventaja sigue viva en Q3 [2.36,5.1] y muere/invierte en Q4 (>5.1), o sea la transición está en dw≈2–10, exactamente donde el borrador pone **cero pares nuevos** y A∪B tiene 2 pares en [5.1,10). Corazón baja de 20→10 (censurado + falso-firme + contraste C1 invertido ahí: es brazo exploratorio de pulling), y 13 pares van a [2,10).
- **C7 — 5 self-pairs** (bloque×clon de sí mismo) como ancla dw=0 estructural (los gemelos constitucionales no existen: coincidencias entre familias distintas).
- **C8 — Cuentas honestas + sub-lotes.** Re-medido: tandas de 8 cada ~33–39 min → **~4.6 min/u** (no ~3.2); preflight `FACTOR_DISCO=2.2` proyecta 0.871 GB/u → un solo SPEC de ~225 u. exige ≥245 GB libres y el máximo observado es 189 → **PARO LIMPIO garantizado**; el consumo real (373+69=442 MB/u) sí entra. Cambio: ola B = **3–5 sub-lotes** con la cadena archivo→liberación entre ellos (los sub-lotes largos de 120 u.t. en tandas de ~37 u.), presupuesto declarado **~22–23 h**, ~130 GB reales con liberación.
- **C9 — Tres cláusulas de prereg (baratas):** término de ola e interacción ola×dw sólo sobre el soporte común [0.05,2.0); sensibilidad excluyendo los 8 pares del vistazo diagnóstico; claims poblacionales reponderados por la distribución dw de los 11175; declarar n_eff esperado (~133/175 curva; contraste apareado inmune al reuso) y el ancho mínimo resoluble del borde (s se reporta como cota superior, ~0.05–0.1 dec en dw≈1).

## 2. Asignación FINAL recomendada

| Región (dw_fina) | Pares nuevos | Nota |
|---|---|---|
| [0, 0.05) | 10 | pool doble fina∩nls, veto eje blando, horizonte 120, brazo EXPLORATORIO de pulling |
| self-pairs (dw=0) | 5 | ancla estructural de la asíntota, horizonte 120 |
| [0.05, 0.15) | 10 | pool doble, horizonte 120 |
| [0.15, 0.30) | 12 | horizonte 120 |
| [0.30, 0.60) | 15 | |
| [0.60, 1.0) | 18 | alimenta ventana κ/τ |
| [1.0, 2.0) | 17 | alimenta ventana κ/τ |
| [2.0, 3.5) | 6 | Q3: ventaja t−f aún +0.19 |
| [3.5, 5.1) | 4 | borde de la muerte de la ventaja |
| [5.1, 10) | 3 | lado muerto (A tiene 2) |
| **Total** | **100** | × 2 brazos (t/f) = 200 u. |

**Parámetros:** estratos de inferencia = dw continuo con σ_dw por par (fusión [0,0.15) para tablas); tope de reuso **3 duro, sin cláusula de relajación**; brazo κ/τ = **SÍ pero una sola celda (0.3,0.05) × 25 pares en dw∈[0.8,2.8]**, transported, 25 u. (condicional a borde abrupto, declarado); horizonte **120 u.t. en [0,0.30) / 60 en el resto**, lock censurado declarado en toda la ola, pulling primario bajo 0.275; estimador del eje = `w_fina` (validado: error mediano global ~0.003; se declara σ(w) — w_hilbert retirado de validador, columna v = canal de veto, 2col prohibido). Total **225 u. ≈ 22–23 h** en 3–5 sub-lotes con liberación intermedia, ~130 GB reales.

## 3. Abierto para la ola C (sin bloquear la B)

1. **Hipótesis de bandas por familia/DNA (COA):** en B sólo se registra `familia_i/familia_j` como covariable (costo cero); la estratificación misma-vs-distinta familia a igual dw se pre-registra en C si la covariable muestra señal.
2. **La inversión de Q4** (lock_f 0.181 > lock_t 0.097 en dw>5.1, Δ=−0.083): ¿la biografía ESTORBA lejos de la lengua? Pregunta nueva, no cabe en B.
3. **¿Dónde termina exactamente la lengua (dw>10)?** B llega a 10; la cola [10,60) queda con los 15 pares de A.
4. **Mejor estimador del eje** (multi-modo consciente) para bajar el piso ~0.02 y convertir la cota superior de s en s puntual; eventualmente W=16 para el corazón.
5. **Claims poblacionales reponderados** sobre los 11175 — sólo después de que A∪B esté completo.
6. **Horizonte >120** si la supervivencia censurada de B muestra masa de cruces más allá de 120 en el corazón.

**Higiene verificada:** `git status` limpio en study06 y study07; census lote 1 intacto y corriendo (PID 79786, elapsed 2:29 h, sin REPORTE.json todavía — la ventana para C1 sigue abierta); ningún archivo escrito fuera de `scratchpad/juez_diseno/`. R_f no leído.