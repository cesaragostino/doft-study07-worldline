# DOUBLETAP del marco post-lote-suelto (wf_cfb44e2e) — por pieza
# VEREDICTO DEL JUEZ — double tap del marco de COA (§18), 5 piezas

**Regla de la casa cumplida**: todo VOLTEA/SOSTIENE de pieza central (P1, P3) re-ejecutado por mí con scripts propios en `/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad/tap_marco/juez/` (`jz0_base.py` importa stft_peaks/amp_at/runs_true VERBATIM del lector sellado `tools/leer_suelto120.py`; `jz1`–`jz5` + `jz*_resultados.json`). Repo intacto. El arbitraje par131 y el test de nulidad del escéptico (ambos OBLIGATORIOS) están re-ejecutados abajo. Los desacuerdos entre lentes se arbitraron con código, no con prosa.

---

## P1 — «ρ>1 = cambio de dominancia, no nacimiento; dlnρ/dt pre-captura ≈ |σ| aislado» → **MATIZA**

**Test de nulidad (OBLIGATORIO, jz1) — el ataque de tautología FALLA, punto para COA:**
- par129 Q1 (jamás captura), [14,110]: dlnρ/dt = **−0.0003** (stft) / −0.0005 (demod).
- Fresh par133_f/par134_f, 6 modos Q, [14,56]: |pendiente| ≤ **0.0022**, con dlnA_L ≡ dlnA_S (p.ej. par134_f Q0: −0.019096 vs −0.019096).
El detector NO fabrica la subida: donde no hay física, da cero. La ontología (respuesta forzada preexistente que gana dominancia mientras el tono libre muere) es física medible, no construcción del detector. Coincide con el escéptico y con la medición directa de mecanismo (PLV del componente forzado 0.96–0.996 ya en [20,40], amplitud 4 órdenes sobre mudez).

**La identidad numérica VOLTEA como identidad (jz1 + jz2), cuatro vías:**
1. Reproduce solo en par129 Q2: +0.0167 [60,90], +0.0145 [70,93], +0.0163 [60,93] vs |σ|=0.0147 — y AHÍ la descomposición muestra que es RESTA de dos tasas grandes: dlnA_L = −0.024..−0.029, dlnA_S = −0.041..−0.043 (ambas ≫ σ). No es «tono libre muere a σ bajo forzada constante».
2. par129 Q0 no es log-lineal: +0.0085 [14,52], mitades +0.0232 [14,33] / +0.0050 [33,52].
3. No es específica de captura: par131 Q0/Q1 suben +0.0097/+0.0096 en [14,110] y JAMÁS capturan (ρ_max 0.80/0.87); par134 Q0 post-muerte sube +0.0109 [70,116] (ambas familias) = 5.8×|σ| y jamás recaptura.
4. El drive no es estacionario (ver arbitraje): la corrección por drive deja las tasas positivas pero 1.7–2.8×|σ|.

**ARBITRAJE par131 (OBLIGATORIO, jz2) — RESUELTO: es TRAMO, ambos números correctos, la suposición de régimen log-lineal único es lo que está mal.**
| ventana | dlnρ/dt stft | demod | dlnA_L | dlnA_S |
|---|---|---|---|---|
| [14,52] | **+0.0185** | +0.0180 | −0.0206 | −0.0390 |
| [14,64] | **+0.0130** | +0.0126 | −0.0185 | −0.0315 |
| [70,108] | **−0.0017** | −0.0016 | −0.0321 | −0.0304 |
| [90,110] | −0.0096 | −0.0118 | −0.0357 | −0.0262 |

- El +0.0152 de COA vive en las ventanas tempranas ([14,52]/[14,64] lo bracketean); el −0.0018 de t1/§18 reproduce exacto en [70,108]. Ninguno está «mal».
- Pendiente local (ventana 10 u.t., paso 1, [14,112]): oscila entre **−0.019 y +0.047 con 8 cambios de signo** — coincide con la oscilación de mecanismo.
- CAUSA del tramo tardío (verificación del hallazgo de biografía): el líder débil SE APAGA — dlnF/dt(RMS 2 u.t.) = **−0.0310** en [70,108] (par129, mismo líder: −0.0311) y A_L lo copia (−0.0321, 3.7% de diferencia) mientras A_S decae igual (−0.0304): ahí NO hay crossover diferencial. Corrigiendo por drive: +0.0293 (par131 [70,108]), +0.0264 (par129 Q0 [14,52]), +0.0417 (par129 Q2 [70,93]) — todas positivas (la dirección de COA sobrevive) pero **1.7–2.8×|σ|** (la magnitud no).
- Y «pre-captura» está mal definido en par131 Q2 (punto del escéptico, verificado): ρ>0.95 hoverea **[65.25,102.25]** (37 u.t.), episodios ρ>1 desde 66.75, fracción ρ>0.9 en [60,110] = 0.95 — la consolidación de 110.25 no tiene un «antes» limpio.

**Qué degenera**: «dlnρ/dt de ventana única pre-captura» como firma citable de σ — puede dar ±cualquier cosa según [a,b]. **Qué sobrevive**: la lectura cualitativa de dominancia (apoyada por nulos limpios, cruces suaves y hovering) y σ como co-ordenador direccional (4/4 en el lote), no como número del mecanismo.

---

## P2 — relevo modal con solape (par129 Q0→Q2) → **MATIZA**

Arbitraje escéptico-SOSTIENE vs grumo-MATIZA, con código (jz5):
- **El hecho SOSTIENE**: solape positivo en 6/6 variantes umbral×familia — stft 13.5/9.0/4.5, demod 10.0/7.5/5.5 u.t. (thr 0.95/1.0/1.05; mi regla: primera corrida de Q2 que llega al fin; la variante demod-0.95=16.0 del escéptico usa otra regla de selección de corrida — los BORDES son regla-dependientes ±2–6 u.t., el solape no). No hay hueco de canal en el relevo.
- **El observable de coherencia degenera** (grumo verificado): Δψ(Q0−Q2) da PLV5 = **0.9998** (std detr 0.020 rad) en [60,90] PRE-relevo — más coherente que DURANTE el relevo (0.9991, std 0.042) — y 0.978 ya en [30,54], antes de toda captura. El R=0.9991 es el basal del receptor (modos casi degenerados encadenados), no firma del traspaso.

**Cita honesta**: «relevo por dominancia con solape 9 [4.5,13.5] u.t., robusto a umbral y familia». R/PLV del relevo: no citable como física del traspaso.

---

## P3 — «link sano = existencia continua de ≥1 canal modal coherente con relevos; AND-3Q incorrecto» → **MATIZA** (núcleo SOSTIENE y entra al sello v2; las dos evidencias auxiliares de §18 VOLTEADAS)

**Núcleo SOSTENIDO** (hechos §17 + jz4/jz5): par134 = filtro por modo con link vivo (Q0 muere, Q1 cicatriz+recaptura, Q2 continuo); par132 Q1 recaptura y consolida; relevo par129 6/6; y mis w_final {36.000, 35.998} están sobre la **línea MEDIDA** del líder (36.012 en [116,118.5]), no sobre la fórmula (36.261). El AND-3Q es físicamente incorrecto: se reemplaza (prescripción 2).

**Evidencia auxiliar 1 («canal enterrado» por PLV) — VOLTEADA (jz3, OBLIGATORIO):**
| modo, hueco [63.5,80] | PLV5 suavizada | PLV5 instantánea | A_L media | ρ_max |
|---|---|---|---|---|
| par132 Q1 (enterrado) | 0.9906 | 0.520 | 1.798 | **1.005** |
| par132 Q0 (jamás capt.) | 0.9747 | 0.169 | 1.831 | 0.423 |
| par132 Q2 (jamás capt.) | 0.9895 | 0.417 | 1.873 | 0.805 |
| par129 Q1 (jamás capt.) | **0.9994** | 0.255 | 1.124 | 0.496 |

El PLV suavizado NO discrimina (un control da MÁS que el canal enterrado); la media móvil de 1 u.t. es un pasabanda en ω_L que da fase lenta a cualquier respuesta forzada lineal. A_L tampoco discrimina. **Lo que SÍ discrimina es ρ**: el canal enterrado de Q1 hoverea en ρ_max≈1.0 mientras los controles quedan en 0.42–0.81. El «canal estaba enterrado» es REAL, pero su definición operativa es por DOMINANCIA, no por fase.

**Evidencia auxiliar 2 («grumo»: coherencia colectiva > obediencia al drive) — VOLTEADA (jz4, OBLIGATORIO):**
- ψ_LÍDER vs fórmula en [83.5,118]: deriva **−0.03152 c/u.t.** — la «deriva conjunta» de Q1/Q2 (−0.03197/−0.03287) ES el sesgo de la fórmula.
- Contra la línea medida: ψ_Q1−ψ_L = −0.00045, ψ_Q2−ψ_L = −0.00135 c/u.t. — mismo orden que Δ(Q1−Q2)=+0.00090. Obedecen al drive real tan bien como entre sí; el «26×» muere.
- Varianzas highpass 2 u.t.: var(Δψ)/[var(ψ1)+var(ψ2)] = **0.72** (no 1/26); cov implícita / var(ψ_L) = **0.964** — la fluctuación compartida es el jitter del líder, sin residuo para acople mutuo.
- Control letal confirmado: el modo MUERTO Q0 da Δψ(Q0−Q1)=−0.00073 y Δψ(Q0−Q2)=+0.00017 — tan «trabado» como el par capturado.

**Muerte par134 Q0 (evidencia SOSTIENE de mecanismo) — números confirmados, lectura acotada (jz3):** |zm| mínimo 2.5e-4 en [63,70] → 3.5e-4 [67,68] → recuperación 8.7e-4 [77,78], fase estable (0.12 rad/u.t. absoluta, 0.18 relativa al líder, vs beat −25.2 = 0.5–0.7%). Real — pero por los controles esto es respuesta forzada genérica: apoya la ontología de P1 («enterrado, no destruido»), NO certifica salud del link por sí mismo.

**Qué degenera**: «PLV/R contra la línea» como detector de canal (vacuo: todo link sería sano siempre); «deriva conjunta vs fórmula» → «error de fórmula».

---

## P4 — dos escalas: entrainment frío vs plasticidad lenta → **MATIZA**

Mi re-lectura de raws (jz5) reproduce todo exacto: b_S1 par132 = **0.00456/0.0791/0.1292/0.2007** (t=30/60/80/120); par134 = 0.00348 final pese a lock fuerte 2/3; par129 = 6.2e-5, par131 = 2.9e-6 (sin cruce de banda no hay depósito); b_Q max ≤ 1.16e-4 en los cuatro (entrainment sin re-escritura). La separabilidad fenomenológica SOSTIENE.

El MARCO causal se corrige con el hallazgo de biografía (P4 no es pieza central — no lo re-ejecuté; es identidad-por-construcción de rhs.py DECLARADA, con reconstrucción R=1.000 contra el canal independiente x1 y parámetros del ajuste que calzan con τ_e/α_b/τ_b al 0.8–4.3%): **b_S1 es un filtro pasabajos de dos polos de la energía on-site de S1**, no «plasticidad de la pelea». Consecuencias: el onset es el CRUCE (37% de b acumulado antes de la primera captura — la captura no puede causarlo); el 58× entre genomas = 9.3 (ganancia α_b/τ_b) × 6.2 (física); el predictor es cruce de resonancia × Q del modo S1 barrido × amplitud del drive (Q²=8.4 vs 9.3 medido), no σ (ranking se separa en par131) ni tiempo-en-banda (falsado: par134 2.1× más tiempo, 9.3× menos depósito).

**Qué degenera**: «b_S1 comparado entre genomas» (moneda invariante: ∫(e−e_ref)dt) y «b_S1 = memoria de la pelea». **Queda pendiente falsable**: b_S1 par132 pica ≈0.293 @t≈281 y DECAE (τ_b≈330) — ver medición decisiva.

---

## P5 — lag pico-S1 +4.10/+4.15 → **MATIZA**

No re-ejecutado (no central; tres lentes concurren sin conflicto entre sí). El pico es real y el lag estable ante ventana RMS (±0.05), pero: sistemático de borde de banda ±0.1 rad ⇒ **±0.9–1.2 u.t. por film**; el pico de ENERGÍA da +4.62/+5.14 (difiere del RMS en el mismo film — parte del «4.10≈4.15» es suerte del estimador); el ring-up 1/|Re| (6.72 vs 2.11 u.t.) descarta el mecanismo más simple; 3 anclas probadas con n=2 y solo «entrada» coincide. **Cita honesta: lag ≈ +4 ± 1 u.t. tras entrada a banda, n=2, mismo líder, sin mecanismo.** Prohibido el decimal y prohibido usarlo como reloj.

---

## PRESCRIPCIONES (sello v2 del canal)

1. **Canal modal coherente (definición operativa v2)**: episodio de DOMINANCIA — corrida ρ>u de ≥2 u.t. en ambas familias (stft+demod), curva t(u) con u∈{0.8,1.0,1.5}, A_L sobre el piso de mudez, w del modo sobre la línea MEDIDA del líder. PLV/R no definen canal (vacuo: controles 0.975–0.999).
2. **Agregación por unidad (reemplaza AND-3Q)**: link sano = cobertura continua por episodios de dominancia de ≥1 modo Q; transiciones solo por relevo solapado (solape>0 ambas familias, citado como rango por umbral) o hueco ≤ h_max pre-registrado (propuesta 8 u.t. = cicatriz par134 Q1) con re-captura consolidada. Citable: fracción de cobertura + lista de relevos/huecos. AND-3Q prohibido como criterio de salud.
3. **(b) release v2 condicionado a captura previa** (corrige el vacuo de §17).
4. **dlnρ/dt**: prohibida la ventana única; publicar perfil local 10 u.t. + descomposición A_L/A_S + corrección por drive (dlnF); «pre-captura» indefinido bajo hovering (ρ>0.95 sostenido).
5. **Fase contra la línea MEDIDA del líder**, fórmula solo para extremos de ω_L; deriva conjunta vs fórmula = sesgo de fórmula, prohibida como «coherencia colectiva».
6. **PLV/R entre modos del mismo receptor**: prohibido sin control jamás-capturado + versión instantánea + referencia a ψ_L medida.
7. **b**: prohibido rankear por b_S1 crudo entre genomas; invariante ∫(e−e_ref)dt; b_S1 = lectura filtrada de energía, no memoria de la pelea.
8. **Lag S1**: citar +4±1 u.t. (n=2, mismo líder); prohibido el decimal.

## MEDICIÓN DECISIVA

**Film largo 300–600 u.t. de par132 y par134** (transported, lector v2): (1) mata o confirma la predicción de biografía (b_S1 pica ≈0.29 @t≈281 y decae — filtro-que-olvida vs acumulador); (2) da ventanas con drive estacionario para decidir si la tasa corregida converge a |σ| o queda en 1.7–2.8×; (3) des-censura outcomes tardíos (par131 capturó a 110 — 120 u.t. probablemente censura). Complementarias a pre-registrar: **cirugía M1 con b_S1 congelado** (¿el corrimiento dinámico de banda causa las re-capturas? retro-efecto +4.3% no decidible por observación) y, para P5, **pares con dω_L/dt distinto** (¿lag ∝ 1/velocidad de barrido? rompe el confound mismo-líder).

**Archivos del juez**: `.../scratchpad/tap_marco/juez/{jz0_base.py, jz1_p1_null_tasas.py, jz2_p1_arb131.py, jz3_p3_canal.py, jz4_p3_grumo.py, jz5_p2p4.py, jz1..jz5_resultados.json}`.

## Por pieza (estructurado)

### P1 — MATIZA
Ontología SOSTENIDA por mi re-ejecución del test de nulidad (jz1: par129 Q1 jamás-capturado [14,110] dlnρ/dt=−0.0003; fresh par133_f/par134_f 6 modos [14,56] |pendiente|≤0.0022 con dlnA_L≡dlnA_S) — el detector NO fabrica la subida: ρ>1 = cambio de dominancia es física, no construcción. La identidad numérica «dlnρ/dt pre-captura ≈ |σ| aislado» VOLTEADA como identidad por cuatro vías re-ejecutadas: (i) reproduce solo en par129 Q2 (+0.0167 [60,90], +0.0145 [70,93] vs σ=0.0147) y ahí es RESTA de dos tasas grandes (A_L −0.024/A_S −0.041, ambas ≫σ); (ii) par129 Q0 no es log-lineal (+0.0085 [14,52]; mitades +0.0232/+0.0050); (iii) no es específica: par131 Q0/Q1 suben +0.0097 en [14,110] sin capturar jamás (ρ_max 0.80/0.87) y par134 Q0 post-muerte sube +0.0109 [70,116] = 5.8×σ sin recapturar; (iv) el drive no es estacionario (ver arbitraje). ARBITRAJE par131 RESUELTO CON MI CÓDIGO (jz2): ambos números son correctos y son TRAMOS — +0.0185 [14,52] / +0.0130 [14,64] (bracket del +0.0152 de COA) vs −0.0017 [70,108] (el de t1, ambas familias); la pendiente local 10 u.t. oscila −0.019..+0.047 con 8 cambios de signo; la causa del tramo tardío es que el líder débil SE APAGA (dlnF/dt=−0.0310 en [70,108]) y A_L lo copia (−0.0321) mientras A_S decae igual (−0.0304): no hay crossover diferencial ahí. Corrigiendo por drive las tasas quedan todas positivas (+0.0293 par131 [70,108]; +0.0264/+0.0417 par129) pero 1.7–2.8×|σ|: la dirección sobrevive, la magnitud no. Además «pre-captura» está mal definido en par131: ρ>0.95 hoverea [65.25,102.25] (37 u.t.) antes de consolidar en 110.25. DEGENERA: «dlnρ/dt de ventana única» como firma de σ.

### P2 — MATIZA
El HECHO del relevo con solape SOSTIENE robusto (jz5: solape Q0→Q2 positivo en 6/6 variantes umbral×familia: stft 13.5/9.0/4.5, demod 10.0/7.5/5.5 u.t. con mi regla primera-corrida-que-llega-al-fin; la variante 16.0 del escéptico es otra regla de selección de corrida — los BORDES son regla-dependientes, el solape no). Pero el observable de coherencia degenera: Δψ(Q0−Q2) da PLV5=0.9998 (std 0.020 rad) en [60,90] PRE-relevo — MÁS coherente que durante el relevo (0.9991, std 0.042) — y 0.978 en [30,54] antes de TODA captura. El R=0.9991 es el basal del receptor, no firma del traspaso. Se cita: «relevo por dominancia con solape 9 [4.5,13.5] u.t.»; NO se cita R/PLV como evidencia de traspaso coherente.

### P3 — MATIZA
El NÚCLEO de la corrección SOSTIENE y entra al sello v2: el AND-3Q es físicamente incorrecto (hechos §17 intactos: par134 = 1 muere/1 cicatriz+recaptura/1 continuo con link vivo; par132 Q1 recaptura y consolida w_final=35.999; relevo par129 6/6) y mi jz4 agrega que los w_final {36.000,35.998} están sobre la línea MEDIDA (36.012 en [116,118.5]), no la fórmula (36.261). Pero las DOS evidencias auxiliares de §18 caen bajo MI re-ejecución: (1) «canal enterrado» por PLV: PLV5 suavizada en el hueco [63.5,80] = 0.9906 vs controles jamás-capturados 0.9747/0.9895 (par132 Q0/Q2) y 0.9994 (par129 Q1) — NO discriminativo (la media móvil 1 u.t. es un pasabanda en ω_L; instantánea: 0.52 vs 0.17–0.42, tampoco limpio); A_L en el hueco indistinguible (1.798 vs 1.831/1.873). Lo que SÍ discrimina en el hueco es ρ: Q1 ρ_max=1.005 vs controles 0.42/0.81/0.50 — el canal enterrado es real pero se define por DOMINANCIA, no por fase. (2) «grumo 26×» VOLTEADO: la fase del LÍDER medida contra la fórmula deriva −0.03152 c/u.t. en [83.5,118]; contra la línea medida los seguidores derivan −0.00045/−0.00135 (mismo orden que Δ(Q1−Q2)=+0.00090); varianzas hp-2ut: obs/indep=0.72 (no 1/26) y cov/var_L=0.964 — la fluctuación compartida ES el jitter del líder, sin residuo para acople; control letal confirmado: el modo MUERTO Q0 da Δψ −0.00073/+0.00017, tan «trabado» como el par capturado. La muerte de par134 Q0 (jz3): |zm| 2.5e-4 mín → 8.7e-4 [77,78] con fase estable (0.12 rad/u.t. vs beat −25.2) — números de mecanismo exactos, pero por los controles es respuesta forzada genérica: apoya la ontología de P1, no certifica salud del link. DEGENERAN: «PLV contra la línea» como detector de canal; «deriva conjunta vs fórmula» como coherencia colectiva.

### P4 — MATIZA
Los números SOSTIENEN exactos bajo mi re-lectura de raws (jz5: b_S1 par132 = 0.00456/0.0791/0.1292/0.2007 en t=30/60/80/120; par134 0.00348 final pese a lock 2/3; par129 6.2e-5 y par131 2.9e-6 — sin cruce de banda no hay depósito; b_Q max ≤1.16e-4 en los 4: entrainment sin re-escritura). La SEPARABILIDAD fenomenológica de las dos escalas sobrevive. El MARCO causal se corrige con el hallazgo de biografía (no re-ejecutado por mí — P4 no es pieza central; es identidad-por-construcción de rhs.py declarada, con reconstrucción R=1.000 contra el canal independiente x1 y parámetros que calzan al 0.8–4.3%): b_S1 = filtro pasabajos de dos polos (τ_e,τ_b) de la energía on-site de S1, NO «plasticidad de la pelea»; el onset es el CRUCE (37% acumulado antes de la primera captura), el 58× entre genomas es 9.3 de ganancia (α_b/τ_b) × 6.2 de física, el predictor es cruce×Q_S1×amplitud (no σ ni tiempo-en-banda, falsado: par134 está 2.1× más en banda y deposita 9.3× menos). DEGENERAN: «b_S1 comparado entre genomas» (usar ∫(e−e_ref)dt) y «b_S1 = memoria de la pelea». Predicción falsable pendiente: b_S1 par132 pica ≈0.29 @t≈281 y decae (τ_b≈330).

### P5 — MATIZA
No re-ejecutado por mí (no central; tres lentes concurren sin conflicto). El pico S1 es real y el lag estable ante ventana RMS (±0.05), pero la precisión citada no sobrevive: sistemático de borde de banda ±0.1 rad ⇒ ±0.9–1.2 u.t. por film; el pico de ENERGÍA da +4.62/+5.14 (difiere del RMS en el mismo film ⇒ parte del 4.10≈4.15 es suerte del estimador); el ring-up 1/|Re| (6.72 vs 2.11 u.t.) descarta el mecanismo más simple; 3 anclas probadas con n=2 y solo «entrada» coincide. Cita honesta que entra al registro: «lag ≈ +4 ± 1 u.t. tras entrada a banda, n=2, mismo líder, sin mecanismo». PROHIBIDO citar 4.10/4.15 al decimal como reproducibilidad. La cautela de COA era correcta; ahora tiene barra de error.

## Prescripciones (sello v2)

1. SELLO v2 — definición operativa de «canal modal coherente»: episodio de DOMINANCIA, no de fase. Canal activo en [a,b] = corrida ρ>u de ≥2 u.t. en AMBAS familias (stft+demod), publicada como curva t(u) con u∈{0.8,1.0,1.5}, con A_L sobre el piso de mudez y w del modo sobre la LÍNEA MEDIDA del líder. La coherencia de fase (PLV/R) NO define canal: mi jz3 mide PLV5≈0.97–0.999 en modos jamás capturados — con PLV todo link es sano siempre (definición vacua).
2. SELLO v2 — agregación por unidad que REEMPLAZA al AND-3Q: link sano en [t0,t1] = cobertura continua por episodios de dominancia de ≥1 modo Q, con transiciones admitidas solo por (i) relevo solapado (solape>0 en ambas familias, citado como rango por umbral, p.ej. 9 [4.5,13.5] u.t.) o (ii) hueco ≤ h_max pre-registrado (propuesta: 8 u.t., la cicatriz de par134 Q1) seguido de re-captura consolidada. Métrica citable: fracción de cobertura + lista de relevos/huecos. El booleano AND-3Q queda PROHIBIDO como criterio de salud.
3. SELLO v2 — (b) release condicionado a captura previa: release = terminación de un episodio de dominancia ≥2 u.t. preexistente. Corrige el vacuo medido en §17 (Q0/Q2 de par132 disparaban b=True sin haber capturado jamás).
4. PROHIBIDO citar dlnρ/dt de ventana única como firma de σ. Si se usa: publicar perfil local (ventana móvil 10 u.t.), descomposición dlnA_L/dlnA_S, y corrección por drive (dlnF del RMS 2 u.t. del líder — el líder débil se apaga a −0.031 y A_L lo copia). «Pre-captura» solo está definido sin hovering (ρ<0.95 sostenido antes del episodio); par131 Q2 NO lo cumple (ρ>0.95 durante 37 u.t. antes de consolidar).
5. Fase SIEMPRE contra la línea MEDIDA del líder (ψ_L demodulada del propio film); la fórmula C√(1+0.1·b) queda solo para extremos de ω_L (ya sellado). Deriva conjunta vs fórmula = sesgo de fórmula (medido: −0.0315 c/u.t. en par134 [83.5,118], resid 1.38%); PROHIBIDO citarla como coherencia colectiva o «grumo».
6. PROHIBIDO PLV/R entre modos del MISMO receptor como evidencia de acople o traspaso sin los tres controles: (a) modo jamás-capturado del mismo film, (b) versión de fase instantánea (sin media móvil), (c) referencia contra ψ_L medida. El R=0.9991 del relevo par129 es basal (0.9998 PRE-relevo en [60,90]).
7. PROHIBIDO rankear receptores por b_S1 crudo entre genomas (ganancia α_b/τ_b varía 9.3× entre par132 y par134); moneda invariante: ∫(e−e_ref)dt. b_S1 se cita como lectura filtrada (dos polos τ_e/τ_b) de la energía on-site de S1, no como «memoria de la pelea»; b_Q≈1e-4 no es otro mecanismo, es la misma ley sin ganancia de energía (drive a 36 sobre modos propios a ~6).
8. Lag S1: citar «+4 ± 1 u.t. tras entrada a banda, n=2, mismo líder»; prohibido el decimal 4.10/4.15 y prohibido usarlo como reloj hasta tener mecanismo y n.

## Medición decisiva

FILM LARGO 300–600 u.t. de par132 y par134 (mismo brazo transported, lector sellado v2). Decide de un tiro lo no-decidible de las tres piezas abiertas: (1) P4 — la predicción falsable de biografía: b_S1 de par132 PICA en ≈0.293 @t≈281 y DECAE con τ_b≈330 (par134: 0.007 @t≈347); si b sigue subiendo, el modelo filtro-que-olvida muere; si pica y decae, «biografía» queda redefinida como memoria transitoria. (2) P1 — ventanas largas con drive estacionario (líder fuerte ya aterrizado) para medir si la tasa corregida por drive converge a |σ| o queda en 1.7–2.8×: decide si σ es EL número o solo co-ordena. (3) P3/censura — par131 capturó a 110: 120 u.t. probablemente censura outcomes; el film largo des-censura la cobertura de canal y los relevos tardíos. Complementarias (pre-registrar): cirugía M1 con b_S1 CONGELADO (contrafáctico) para decidir si el corrimiento dinámico de banda causa las re-capturas (retro-efecto +4.3% en |χ_S1|, no decidible por observación); y para P5, pares con velocidad de barrido dω_L/dt distinta — si lag∝1/(dω_L/dt) es respuesta retardada de sweep y se rompe el confound mismo-líder n=2.