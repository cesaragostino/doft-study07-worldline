# DOUBLETAP del lector del lote suelto 120 u.t. (wf_122a505c) — VEREDICTO: BLOQUEA

# KILL DEL LECTOR leer_suelto120.py — VEREDICTO DEL JUEZ

**BLOQUEA.** El núcleo j3 (verbatim, regresión 4/4) no se tocó y sigue fiel. Las AMPLIACIONES tienen 1 defecto BLOQUEA y 3 ALTO reproducidos por mí, más 7 MEDIO y 3 BAJO confirmados. Ningún film del lote nuevo se abrió (verifiqué que los scripts de ambos matadores solo tocan npz del juez, sintéticos propios y el archivo de tanda 1).

## Re-ejecución del juez (regla: todo BLOQUEA/ALTO se re-corre)

1. **[BLOQUEA] sl5 fuera del rango sellado** (auditor). REPRODUCIDO (`repro_sl5_overrun.py`): con t_salida=28.8264 de par132, `np.arange` produce 17 ventanas y la última arranca EXACTO en t_salida+8 (fencepost fp) — ventana [t_salida+8, t_salida+13] 100% fuera del sello y GANADORA: código 1.63 vs 0.75 confinado (2.2×). El derrame es genérico además del fencepost: toda ventana con a>t_salida+3 se recorta solo en fin (~118.75), no en t_salida+8. Viola §15(b), punto 2 del veredicto y el propio docstring («en alguna ventana de 5 u.t. de ese rango»). En los films nuevos puede fabricar RELEASE falso.
2. **[ALTO] leer() no frena ante prefijo fallido** (auditor). CONFIRMADO por lectura directa concluyente (no ejecuté leer(): abriría films): línea 337 `write_text(json.dumps(res))` ANTES del raise (338-339); leer() (380-381) solo chequea `.exists()`. Un prefijo con bit_exacto:false deja el archivo y una corrida posterior de leer() abre los 4 films. Viola control (i) §15.
3. **[ALTO] SOBREVIVE espurio clase dos-líneas** (matador, t5c). REPRODUCIDO con mi propio runner: receptor = 0.65·cos(35.6t)+0.35·cos(12t) (tonos FIJOS, ground truth no-captura) → `a_sobrevive=True` en AMBAS familias (frac=1.0, rate neto 0.0407). Mecanismo medido (gen_traps3): slips NETOS 2.71 (la deriva contra φ_L cambia de signo cuando ω_L cruza 35.6 y se CANCELA) vs VARIACIÓN TOTAL 14.18 (rate 0.2130 → con tv el criterio (a) lo rechaza). Control t5 (tono 36.0): falló (a) por solo 4% (0.1044). Es exactamente la clase degenerada que fabricó el falso «doble episodio Q» de par132. Mitigación observable existente: t_cap(u) abierta (26.25/32.75/49.25) y w_final=35.601≠línea (36.375).
4. **[ALTO] Piso de mudez (punto 8) no implementado** (matador t9 + auditor). REPRODUCIDO: modo Q=0 exacto hasta t_salida y luego 1e-8·cos(φ_L) → `a_sobrevive=True/True`, frac=1.0, w_self=2.356 (borde inferior de la banda de búsqueda = basura). ρ=A_L/max(A_S,1e-300) sin piso alguno. Incumplimiento literal de un requisito sellado del punto 8, y el docstring declara «punto 8 respetado» listando solo 3 de 4 ítems.

## MEDIO/BAJO (evaluados por lectura + salidas re-corridas) — todos confirmados

- **Conteo de slips = deriva neta** (auditor+matador): +1/−1 slips reales → 0.0; deriva pura sin slips → 0.48; 6 slips ida+vuelta → 0.0006; ráfaga −46% por suavizado. Con el arreglo del sl5 aplicado, en par132 Q0 el conteo DECIDE (b): neto 0.75 vs tv 2.23 (umbral ≥2). Y slip_rate_post Q0=0.1069, al filo del 0.1 de (a). MEDIO — raíz del ALTO #3, exige pre-declaración.
- **rel_runs inicio-en-ventana** (ambos): t3b (release genuino arrancando 1 u.t. antes de la salida, 6 u.t. de ρ<1 adentro) → tercer_desenlace pese a slips 17.72 y frac 0.0; corrida con 0.5 u.t. adentro SÍ cuenta. MEDIO.
- **t10 filo de horizonte**: t_salida=117.51, ventana (a) VACÍA → tercer_desenlace=True afirmativo con ~1.2 u.t. observables, sin flag de censura. MEDIO.
- **Sin veredicto por unidad («los 3 Q») ni bandera para desacuerdo stft/demod en a/b** (código 227-254). MEDIO.
- **Bandera cruzada solo consolidado_desde** (ni orden entre modos ni episodios transitorios); docstring sobrevende «conjunto y orden ±3». Donde mira, dispara bien (t8c: 9.75 vs 116.25; t8d: 60.75 vs 74.75). MEDIO.
- **t_cap(u) = primera corrida global**, no la re-captura de §15(d) (T6: par132 → 53.75). En par134 repetiría la captura vieja y esconde el dato nuevo. MEDIO.
- **Falta b_Q final del seguidor** (docstring promete max/final; discriminador del puente (d)). MEDIO.
- **fin=118.75 vs 120** (slip-rate ~1%; Q0 par132 a 0.1069 del umbral). BAJO — declarar.
- **prefijo: fila final del chunk borde sin comparar** — VERIFICADO por mí contra el archivo real: chunk_00011 de par134 tiene 29105 filas en todos los arrays; borde=29104. BAJO.
- **>= y 33.6054 vs «>33.61»**: Δω=0.0046, Δt≈0.06 u.t. — declarado, inmaterial. BAJO/constancia.

## Verificaciones positivas (para el registro)

Regresión núcleo 4/4 intacta; **extraer() es verbatim de j0_extraer.py del juez** (slices x/b, dt_s=dt·10, capas — cotejado por mí; ningún matador lo había revisado); T1 chirp exacto (C_fit=9.9500, resid=0.0, t_salida Δ=1.8e-3); T2 captura perfecta y t_cap(u)=10.25 exacto; t6 banda-no-alcanzada limpio; bandera cruzada dispara donde corresponde; ω_self [2,4] vs [1,6] inmaterial (spread ≤0.05 frente a banda ±1.5); lookup de banda por receptor correcto; exclusión de rng_state_json justificada; b_S1 dinámica usa b1[:,1] correcto.

## Arreglos obligatorios antes del commit (diffs conceptuales)

1. **sl5 confinado**: `a ∈ np.arange(t_salida, t_salida+3.0+1e-9, 0.5)`, `b = min(a+5.0, t_salida+8.0, fin)` (solo ventanas de 5 u.t. contenidas; declarar tratamiento si fin<t_salida+8). Post-arreglo: par132 Q0 debe dar 0.75.
2. **Gate real en leer()**: parsear CONTROL_PREFIJO.json y exigir `set(UNITS) <= set(ctl)` y `all(r['bit_exacto'])`; si no, SystemExit.
3. **Slips**: agregar `_n_slips_tv = Σ|Δψ|/2π`; publicar slip_rate_post_tv y slips_max_5ut_tv junto a los netos; el veredicto sellado atado a UN conteo elegido por COA AHORA (recomendación del juez: cruces discretos de 2π); bandera `degenerado_no_coherente` cuando los conteos discrepan sobre el umbral.
4. **Piso de mudez**: amp_mediana por modo + flag `mudo` bajo piso declarado → sellado del modo no-evaluable; corregir docstring del punto 8.
5. **rel_runs por solapamiento**: `min(e[1], t_salida+8) − max(e[0], t_salida) >= 2.0`.
6. **Censura**: si `fin − t_salida < margen declarado` (propuesta 10 u.t.) → sellado CENSURADO, no tercer_desenlace afirmativo.
7. **sellado_unidad** (AND sobre 3 Q por familia, regla de (b) declarada) + **bandera_ab** (desacuerdo stft/demod en a/b); bandera de orden entre modos o degradar docstring.
8. **t_recap(u)**: primera corrida ≥2 u.t. con inicio > t_salida, junto a t_cap(u) global.
9. **bq_receptor_final_Q** = |b1[-1,0]|.
10. Re-correr matar() (debe seguir 4/4 — nada toca el núcleo), committear, y recién entonces prefijo→leer.

## Recomendados (no bloquean)

Declarar fin=T−W/2−0.25 y el ~1% del slip-rate (opcional ψ hasta T−0.5); prefijo con borde=len(fb['ticks']) real (29105) y m-por-key en el JSON; assert n_layers≥2 en vez de zeros silencioso; línea en docstring fijando 33.6054 como techo operativo; git-hash del lector + umbrales declarados dentro de LECTURA.json.

## Declaraciones para §16 (al leer)

Ver lista estructurada: conteo de slips elegido + doble publicación neto/tv con bandera; limitación del sello (a) ante la clase dos-líneas — un SOBREVIVE de par134 solo se cita con t_cap(u) cerrada, w_final sobre la línea y sin banderas; solapamiento ≥2 u.t. como lectura de «dentro de»; margen de censura declarado; piso de mudez declarado; ventanas de slips contenidas (el 1.63 histórico de par132 queda anulado → 0.75); agregación por unidad; fin=118.75; ≥ con 33.6054; ω_self [2,4] con número; t_cap/t_recap; estado de la fila final del chunk de borde; y las verificaciones positivas del kill con el lote nuevo intacto.

**Estándar aplicado**: este lector decide la predicción central de COA (¿par134 sobrevive tras cruzar su banda?). Los dos modos de fallo que cuestan el norte están demostrados hoy: un falso SOBREVIVE (t5c/t9) y un RELEASE inflado desde fuera de la ventana sellada (sl5). Los arreglos son campos adicionales, gates y recortes de ventana — ninguno toca el núcleo del juez ni los campos ya sellados — y deben decidirse y committearse ANTES de abrir film alguno, como exige §15.