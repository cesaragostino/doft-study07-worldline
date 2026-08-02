# DOUBLETAP transferencia (wf_f2afea35)

# DOUBLETAP del marco de COA sobre los films s600 — VEREDICTO DEL JUEZ (tap_chi)

**Regla de la casa cumplida**: C1/C2/C4 (las piezas centrales) re-ejecutadas COMPLETAS con código propio en `/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad/tap_chi/juez/` (`jc0`–`jc5` + `jc*_resultados.json` + series npz). Estimadores del lector sellado importados VERBATIM (`stft_peaks`/`amp_at`/`runs_true` de `tools/leer_suelto120.py`; línea medida con prior transcripta de `leer_largo600.analizar_v2`). Los desacuerdos entre lentes se arbitraron con código. Repo y oráculo intactos (git status limpio; study06 solo lectura).

## Cimiento verificado (jc0)

El canal `drive` del film ES la fuerza KV real: reconstruida desde los estados con `drive[k,1] = 0.3·(X_L[k−1−2500]−X_R[k−1]) + 0.3·(V_L[k−1−2500]−V_R[k−1])`, X=0.1·Σx (contrato §3/§4, `coupling.py`/`network.py:106-107`) — **error 0.0 bit-exacto** en chunks completos de par129 y par134. Mi extracción strided coincide bit-exacta con la de los lentes. Todo lo que sigue descansa en fuerza MEDIDA, no proxy.

## El test fuerte re-ejecutado (jc2): r ≡ 1

χ_m(ω) propio por DOS rutas: (A) Jacobiano FD sobre `rhs.derivatives` con estado (x,v,z), b=e=0 (regresión σ vs j2: ≤7e-12); (B) K,G x-solo directo del genoma. Con F̂ = amplitud del drive real en la línea medida (mismo estimador que A_L ⇒ factores de ventana cancelan):

**r_m(t) = A_L,m/(|χ_m(ω_L(t))|·F̂) = 1.000** — par129: medianas 1.0001/1.0001/0.9999 con p2–p98 ⊂ [0.995,1.007] en los 4 tramos del film; par131 ídem; par134 Q2 = 1.0001 [0.998,1.003]; par132 Q1/Q2 ≈ 1. Sobre 6 décadas de F, sin constante libre. Los 3 A finales de par129: ratios 1:1.0064:0.9915 vs χ 1:1.0061:0.9911 (A/χ igual al 0.04% entre modos). Coincide con lente χ (r=1.000 [0.998,1.002]) y con la ganancia absoluta 1.006 del escéptico — tres códigos, una identidad.

χ_A/χ_B = 1.0004 sobre las líneas de los débiles (la memoria z casi no pesa) pero ∈ [0.83,1.28] cerca de los notches de par134 — **ver arbitraje de la cicatriz**.

## ARBITRAJE DEL PUNTO CRÍTICO — release de par129 Q0 en 102.8 (jc3)

¿Suelta una respuesta lineal pura? SÍ, y el mecanismo queda medido:

- Pre-release [90,102]: **dlnF = −0.0335, dlnA_L = −0.0356** (cierre lineal dlnA_L−(dlnF+dln|χ|) = −0.0001), **dlnA_S = +0.0173** (¡el denominador estaba SUBIENDO — batidos multi-tono, ni siquiera decaía!), dln|χ| = −0.002.
- **par129 NO tiene notch**: |χ_Q0,Q1,Q2(ω)| sin mínimos locales en todo [20.4,28.0] (jc2 scan) — la alternativa antirresonancia queda EXCLUIDA.
- **Contrafactual ejecutado**: con F congelada en t=95, ρ_min en [95,130] = **1.316 — no suelta jamás**. La premisa «lineal + A_libre decayendo ⇒ no suelta» es correcta e INAPLICABLE: F no es constante (y A_S ni decaía).
- Recaptura 483.25: dlnA_S = −0.0263 vs dlnA_L = −0.0192 — denominador-driven, cruce RASANTE (ρ 0.70@460 → 1.00@483; citar con banda).

**Veredicto del punto: el release es real Y lineal-explicable — mecanismo numerador-F. C4 no se matiza por acá; se confirma.** Las dos lentes que lo tocaron (χ: numerador; escéptico: carrera de tasas) coinciden y mi descomposición las une: es la misma cosa medida en dos bases.

## Otros eventos re-ejecutados (jc3)

- **Muerte par134 Q2 (303.75)**: dlnF = −0.0395 con χ PLANO (+0.001); carrera de tasas fiteada en [270,300]: −0.0396 vs −0.0159 ⇒ cruce extrapolado **304.3** vs 303.75 medido. Puro apagado del líder — el mecanismo de C2.
- **Cicatriz par134 Q1 [75.25,83.25]** — desacuerdo apagado («no la reproduce») vs lente χ («notch») ARBITRADO: con la ley completa el notch EXISTE (mín |χ_Q1| en ω=34.37, dip ~2.8×; Q0 en 33.69; Q2 sin notch — por eso sostiene 277 u.t.) y el release/recaptura son notch-driven (dln|χ| = −0.115 dominando dlnF = −0.0146 al entrar; +0.0156 al salir; ω_L 34.17→34.61). El gap aparece en ρ_pred ([77.25,78.25]) pero de 1 u.t. vs 8 medidas: **dentro del notch la precisión cae a ±25%** (r ∈ [0.78,1.29], ρ_pred_min 0.998 vs 0.779 medido, cierre lineal degrada a 0.05–0.10). La χ x-solo estática del apagado no lo ve porque ahí la memoria z pesa (χ_A/χ_B ∈ [0.83,1.28]). Resolución: **notch real, bordes explicados, ancho NO predicho — único residuo cuantitativo del marco, n=1, localizado en el fondo del notch.**
- **Muerte par134 Q0 (62.75)**: ω_L = 33.374 entrando a SU notch (33.69), dln|χ| = −0.135 dominante. Confirma lente χ.

## C2 re-ejecutado (jc4 + jc5)

- Cruce: F(60) = 2.5643/1.1611, t_cruce = 223.75, razón 11.46× a 590 ✓ (§5 exacto).
- **Intrínseco**: par132 vs par134 (mismo líder): F(t) idéntica al 1.02% mediana en [2,300] (max 1.8%; 6.1% recién a t=550 sobre F~1e-7); par129 vs par131: 1.03%. El líder se apaga solo.
- **Swap contrafactual** (el MATIZA del apagado, re-ejecutado con mi código — reproduce EXACTO): par129 con F del fuerte pierde la captura (último episodio 362.25; frac[400,600]=0; ρ_fin 0.19/0.40/0.87); par134 Q2 con F del débil muere igual (432.75, +129 u.t.); par131 retiene 2/3 con cualquier F (ρ_fin 38.7/14.5). Control: par129 con su propia F reproduce sus episodios exactos.
- Sin ventaja de frecuencia: χω² = 1.094 (débil@23.53) vs 1.053 (fuerte@28.61).
- Energía (jc5, full-rate, 15 ventanas/film): el líder JAMÁS recibe energía neta (15/15 × 4 films); receptores débiles sumideros puros (15/15); **par132 receptor EXPORTA por el link desde ~252** — concordante con su r~21.8: el único autónomo es el único exportador. (Menor: el t de inversión de signo de par134 es ventana-dependiente — 339 con cajas de 2 u.t. de la lente vs ≥461 con mis cajas de 5.24; |P|~1e-10 fluctuante; no material.)

**C2 = MATIZA**: núcleo sostenido (apagado intrínseco, sin ventaja del débil, muerte del fuerte = su propio drive); suficiencia parcial — la inversión la fija la carrera F_L(t)/A_libre,m(t), DOS apagados.

## VEREDICTOS POR PIEZA

- **C1 — SOSTIENE (reforzado)**: seguimiento forzado pasivo espectralmente puro = identidad r≡1 sub-porcentual, no factor <2; pata energética verificada (sumidero puro); «plana» se retira (estructura χ ×1.33 determinista — refuerza, no debilita); excepción declarada par132 Q0 (autónomo, r~21.8, exporta).
- **C2 — MATIZA**: el apagado diferencial es necesario, intrínseco y direccionalmente dominante; no suficiente solo (swap 4/4 monótono pero par134 muere con cualquier F y par131 retiene con cualquiera).
- **C3 — SOSTIENE**: plano de control no re-visitado (razón 1.2–1.6e-7 según convención — FIJARLA antes de citar; re-cruce de notch 2e-5). Diseño decisor abajo.
- **C4 — MATIZA (ontología SOSTIENE, letra corregida)**: sin bifurcación no lineal en NINGÚN evento (cierre lineal ≤1e-4 fuera de notch; contrafactual del release ejecutado); la forma fuerte del denominador VOLTEA (extrapolar A_libre exponencial borra releases/capturas/muertes: eps_extr de jc2); A_libre = línea propia MEDIDA, multi-tono, con batidos, puede SUBIR; dominio de validez: ±25% dentro de los notches (ancho de cicatriz no predicho); semi-circularidad de la reconstrucción de episodios DECLARADA (el contenido es r≡1 + mecanismos). **El cambio ontológico queda confirmado: el «lock» de estos films = respuesta lineal congelada + biografías de decaimiento diferencial.**
- **C5 — SOSTIENE (reformulado más fuerte)**: b_S1 = eco filtrado del burst de ENTRADA (2 polos, τ propios, picos exactos), CIEGO a la muerte del canal (contrafáctico: cortar energía en t=80 mueve el pico 0.2/1.8 u.t.); muerte→pico = coincidencia de escalas. No re-ejecutado (no central, lentes concordantes).
- **C6 — SOSTIENE (adoptar y ampliar)**: P validado y necesario (ρ es ciego al signo del transporte); r(t) entra como canal nuevo; ver prescripciones.

## PRESCRIPCIONES LECTOR v3 (resumen; lista completa en el campo estructurado)

1. Tres canales por episodio: ρ (dominancia) + g (transmisión) + P (transporte, spec energía con cierre <1e-5); cobertura = «dominancia espectral condicionada al drive existente» + década de F̂.
2. Canal r(t) sellado con χ del Jacobiano frío (c=1, tres códigos): r≈1 seguimiento / r≫1 autonomía (bandera de física nueva); máscara de validez + dominio notch (±25%).
3. Mapa de notches pre-calculado por genoma con la ley COMPLETA (x-solo los corre/pierde) antes de leer episodios.
4. Mecanismo por evento obligatorio (numerador-F / notch-χ / denominador-A_S) con descomposición y residuo de cierre publicados.
5. Denominador declarado: autotono dominante, pendiente con signo (puede subir), batidos; PROHIBIDO extrapolar A_S exponencial.
6. Cruces rasantes con banda de incertidumbre.
7. Correcciones de registro: Σhann/2=624.75 (A_phys 2×), «plana ±8%» retirada, convención t_captura fijada, «captura total»→«seguimiento forzado total», mudez local.
8. «Atractores móviles transitorios» = solución particular forzada; vocabulario de bifurcación prohibido para estos episodios.

## MEDICIÓN DECISIVA

**Cirugía de línea FIJA + campaña 2×9 con nula pre-calculada sin parámetro libre**: F constante por construcción, 9 niveles log F∈[3e-3,3] × barridos up/down ω∈[22,38] apareados en tiempo-desde-init, + estaciones dentro de los notches (33.69/34.37/30.17). Frontera nula publicada ANTES: captura ⇔ F̂ > A_S,m(t)/|χ_m(ω)| con c=1. Decide: C3 (desviación up-vs-down apareada = histéresis genuina), el residuo de C4 (¿la desviación ±25% del notch escala con F = no-linealidad, o con el estimador = todo lineal?), y P1-σ (drive estacionario por construcción).

## PREGUNTAS NUEVAS (campaña 2×9 / cirugía)

1. ¿La lengua de captura medida coincide con la pre-calculada F > A_S/|χ| (c=1) en AMBAS direcciones de barrido? Toda asimetría a (ω,F,t) apareados = histéresis/no-linealidad genuina.
2. Espectroscopía de notch: línea estacionada en el mínimo de |χ| — ¿el apartamiento crece con la amplitud del drive (física no lineal) o es ancho de banda del estimador (autotono vecino)? ¿Se recupera el ancho de la cicatriz con A_S multi-tono declarado?
3. par132 Q0 (σ>0) con línea fija y link ON/OFF: ¿el contenido autónomo crece a σ independiente del drive? ¿r≫1 y P<0 co-ocurren siempre (dos firmas de la misma autonomía)?
4. Predicción sellable ANTES de extender: el t de release de par129 Q1/Q2 más allá de 600 sale de la ecuación con A_S medido — testearlo si se alarga el horizonte.
5. Fase del canal drive vs arg(χ) con retardo τ explícito (la lente χ midió <1° en dominancia; sellarlo como canal en v3).
6. ¿Los picos b_Q de líderes con genoma cruzado (predicción 262.7/127.4 del apagado) reproducen en films nuevos? (mata la tentación de «τ por capa» para siempre).

**Archivos del juez**: `.../scratchpad/tap_chi/juez/{jc0_extraer_verificar.py, jc1_series.py, jc2_chi_r.py, jc3_eventos.py, jc4_c2.py, jc5_energia_spot.py, jc2/jc3/jc4_resultados.json, jz_series_*.npz, jz_r_*_Q*.npz, jz_chiscan_*.npz, jz_drive_*.npz}`.
---
## ENMIENDA post-veredicto (COA 2026-08-02, verificada — bitácora §8)
El r≫1 de par132-Q0 (C1-excepción y prescripción [2]) era FUGA ESPECTRAL de la Hann W=2:
razón r(W2)/r(W16) = 3.44/8.34/21.3/45.1 en t=400/450/500/580 (desaparece con W;
control esclavo par129-Q0 plano 0.994-1.004; tono propio 44146× la línea a t=580).
r≫1 RETIRADO como detector de autonomía (necesita piso de fuga local, convergencia en W
o regresión coherente). La autonomía de par132-Q0 queda por evidencia independiente
(σ>0 + tono propio + P<0), sin demostración de contenido autónomo en la línea del líder.
P<0 = exporta, no necesariamente auto-sostiene (conjunción P + pendiente de energía + σ).
La identidad r≡1 (C1 núcleo) INTACTA — W-invariante en régimen esclavo.
Cirugía 2×9: separar barridos/estaciones; clamp externo ≠ link real (dos experimentos);
nula prospectiva exige A_S de gemelo link-OFF o ventana temprana disyunta.
