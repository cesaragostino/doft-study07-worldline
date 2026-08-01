Both repos are clean and everything re-executed. Final verdict:

# PANEL ESCÉPTICO ARNOLD-C1 — VEREDICTO
**Juez [M1-análisis], 2026-07-31.** Regla aplicada: descreer, medir solo el número. Todo hallazgo VOLTEA/DEBILITA fue **re-ejecutado en sandbox propio** (código nuevo, no heredado): `j1_tabla.py` (tabla+clusters), `j2_sintetico.py` (patologías de estimador), `j3_films.py` (repaso de los 144 films, read-only, con sanidad bit-exacta: max|rw_pipe recalc − tabla| = 0.00e+00), `j3b_stats.py` + `j4_adjudica.py` (adjudicación), en `/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad/juez_arnold/`.

**Hecho estructural que gobierna TODA la inferencia de C1 (confirmado):** las 288 aristas son exactamente **72 pares-de-bloques únicos × 4 celdas κ×τ**, con compat y Δω idénticos en las 4 réplicas (multiplicidad `{4:72}`, 0 pares con compat no-constante). El n efectivo para cualquier predictor de par es 72. Toda p citada abajo es de permutación por cluster de par (10k), salvo indicación.

## Estado de cada claim tras el ataque

### (a) "NO hay lengua de Arnold" — **VOLTEADO**
El claim muere por doble artefacto de estimador, ambos reproducidos por mí desde cero:
1. **ω_llegada es un punto fijo del estimador, no física.** La mediana del gradiente de `atan2(v,x)` sin normalizar satura en −2ω²/(1+ω²)≈−2 para cualquier portadora (derivación analítica + numérica: ω=6.168 → medido −1.944, predicho −1.949; la MEDIA sí da −ω exacto). El eje "de llegada" del pipeline (mediana −1.95) medía la constante del artefacto. Carriers reales (FFT hann+zeropad del ring de cápsula, validado contra Hilbert, ρ=+0.959): Δω_llegada real mediana **2.16 rad/u.t.**, solo 19.4% ≤0.4.
2. **rw_final sin normalizar castiga el desfase del lock:** par perfectamente trabado con δ=π/2 mide rw=0.431 (sintético propio).

Con fase normalizada + eje de llegada real: **rw_corr~Δω_fft ρ=−0.637, p_cluster=0.0001** (sobrevive el clustering n=72 que mata a las bandas), monotónica: lock final ≥0.95 por cuartil **88.9% → 58.3% → 33.3% → 8.3%**; robusta a la cola (Δω≤10: −0.653; ≤5: −0.473; ≤1: −0.359) y con el outcome viejo también (−0.459, p_cluster=0.0001).

**Disciplina sobre la lectura positiva (mi aporte de juez):** parte de esa pendiente es mecánica de ventana, no interacción — un par NO interactuante da rw = |sinc(Δω·W/2)| exacto (verificado), rw_corr~sinc(Δω_late)=+0.90, y el **fresh muestra casi la misma pendiente (−0.525, p_cluster=0.0001)**. La evidencia de interacción genuina es diferencial: **transported traba MÁS que fresh apareado por film en Q1–Q3 (Δlock +0.22/+0.38/+0.23, Wilcoxon global p<1e-4, Q1 p=0.0035) y la ventaja desaparece en Q4 (−0.07 n.s.)** — la biografía ayuda a trabar solo a detuning chico/medio, forma de lengua. Sub-claim que SÍ sobrevive: el eje **constitucional** es genuinamente ciego (rw_corr~Δω_const: +0.040, p=0.50). Y el adorno "el bin mayor traba MÁS / signo contrario": no reproducible — con terciles del eje viejo da 15.6/15.6/15.6 (plano), p_cluster=0.35.

### (b) "la compatibilidad de bandas SÍ predice" — **DEBILITADO (fuerte)**
- El −0.206 (p=4.3e-04) reproduce exacto, pero es **p_cluster=0.048** / colapso n=72: ρ=−0.244, p=0.039 — borderline, no sobrevive Holm con m≥2 sobre la familia de §13.
- **No predice ningún indicador de lock:** frac95 +0.002 (p_cluster=0.98); episodio≥1 +0.104 signo contrario (p_cluster=0.32); en aristas CON episodio: −0.04 n.s. Todo el efecto vive en las **209 aristas drift-only (−0.403, p_cluster=0.0009)** — predice coherencia de deriva, no trabarse.
- **En conjunto con el detuning de llegada real muere:** outcome corregido β_compat=−0.038, IC95_cluster [−0.22,+0.16]; outcome viejo β=−0.130, IC [−0.29,+0.03] — el predictor principal es Δω_fft (β=−0.63 / −0.44).
- Métrica mal descrita: "17 bandas" es falso (conteos 11–30, solo 3/150 tienen 17) y compat~Σn_bandas = +0.703; parcial en drift-only cae a −0.200.
- Fresh nulo global (−0.020, p=0.73). Hilo rescatable, no citable aún: t_lock95~compat = −0.418 (compatible⇒traba antes, ¡signo pro-bandas!) pero n=13 pares, p_cluster=0.075; y en drift-only conjunto queda β_compat=−0.260 junto a Δω_fft. Estructura fina residual PENDIENTE de census, no titular.

### (c) "τ=0.2 traba más en todos los estratos" — **DEBILITADO**
Con el estimador del pipeline: real pero débil — Δfrac95 pareado por par Wilcoxon **p=0.0047** (28+/14−), Δrw pareado p=0.079, MW global p=0.253. Con el estimador corregido: **muere en rw_corr (pareado p=0.915, mediana Δ=0.0000; MW global con dirección invertida p=0.918)** y queda marginal en frac95_corr (p=0.084). Es un efecto sobre el estadístico sesgado de lock sostenido, no robusto a la corrección de fase. Citable solo como tendencia condicionada al estimador.

### (d) "todos llegan a ~2 ⇒ todos DENTRO de la lengua" — **VOLTEADO**
La premisa es el artefacto de (a): "~2 rad/u.t." es −2ω²/(1+ω²). Con carriers reales: los onions emiten a 1× su ω_ref (mediana del cociente en-film 1.006) pero con armónicos poblados (14 bloques a 2×, 5 a 3–4×, max 4.4×); Δω_llegada real llega a >10 rad/u.t. en 13.9% de aristas. La población NO está comprimida dentro de ninguna lengua — cubre ambos lados y por eso la estructura de (a) es medible. (La "biblioteca angosta p95=0.43" de la lente e3 usaba el mismo eje saturado.) Queda un punto ciego honesto heredado de la ventana: con W=1 u.t., lock y deriva son indistinguibles por debajo de Δω≈1.1 rad/u.t. — "adentro" de esa franja el instrumento no discrimina.

## Qué medición NUEVA decidiría lo que queda abierto
1. **Census Arnold pre-registrado, estratificado por Δω_fft** (el estimador de cápsula es barato: 150 carriers en 8 s): ≥150 **composiciones únicas nuevas** (sin réplicas ×4; las 4 celdas κ×τ solo para el subconjunto τ/κ), cubriendo décadas Δω∈[0.05, 20] con ~30 pares por década. Outcomes primarios pre-registrados: (i) **curva de pulling** Δω_late/Δω_llegada (convergencia de portadoras — inmune a la ventana), (ii) evento de lock con fase normalizada y **ventana W=4–8 u.t.** (baja el punto ciego de ~1.1 a ~0.15–0.3 rad/u.t.), (iii) contraste transported−fresh apareado por film como test de biografía. Costo: ~150 films de 60 u.t. = una corrida C1 (horas de cómputo, un nohup).
2. **Bandas sin confundidos:** métrica de compat con conteo de bandas igualado (remuestreo a n común) y en unidades absolutas de ω, testeada como UNA hipótesis en conjunto con Δω_fft sobre las composiciones nuevas; el hilo t_lock~compat (−0.418, 13 pares) se decide ahí con n_lock decente.
3. **τ:** decidirlo dentro del mismo census con el estimador corregido declarado de antemano (pareado por composición); si solo aparece en el estadístico viejo, es del instrumento.

## Integridad
`git status` limpio en ambos repos (study06 en `39f8df6`, study07 en `f51e194`, sin cambios, sin commits); disco `/Volumes/ExternalDisk` solo leído (films `lock_band_*.npz` del sweep); cápsulas y `runs_full.jsonl` del oráculo solo leídos; ningún archivo `R_f` tocado. Todo lo escrito vive en `scratchpad/juez_arnold/` (scripts + `aristas_juez.json`).