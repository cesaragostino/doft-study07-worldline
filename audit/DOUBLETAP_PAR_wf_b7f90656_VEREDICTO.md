# DOUBLE TAP PAR-LINK — VEREDICTO DEL JUEZ

Auditado: `src/study07/instruments/par.py` @ ffc8c72 (par.py y test_par_f0.py son BIT-idénticos en el HEAD actual 3456999, así que el veredicto aplica a ambos). Todo el trabajo en clones propios bajo `/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad/juez/` (git clone + checkout ffc8c72, regla §16). Baseline reproducido por el juez: **81 passed** (144s). No heredé ejecuciones: arnés propio (`juez/arnes_juez.py`), runner de mutantes propio (`juez/run_muts_juez.sh`), films construidos acá.

## 1. Veredicto: **NO PASADA** (arreglos A1–A10, con parche EJECUTADO y re-matado)

El patrón de 6 taps ("la física sale bien, los gates tienen agujeros") **se rompe esta vez**: hay 1 BLOQUEA de física del estimador, confirmado por re-ejecución independiente con controles. Un descubridor de links que declara FIRME entre dos nodos muertos no puede ser la etapa 0 del norte: todo census downstream mediría fantasmas. Además, 12 de 20 mutantes sobreviven la suite de gates — el veredicto (umbral, t_lock, firmeza, n>2, pulling, FFT) está esencialmente sin proteger.

**Re-ejecutado por el juez — 16/16 casos CONFIRMADOS, controles sanos (murieron como debían):**

| # | Hallazgo (lente) | Evidencia del juez (arnés propio) |
|---|---|---|
| F1 **BLOQUEA** | Muertos dan FIRME (c1) | 2 nodos apagados (underflow real, 188990 ticks x==0.0): estado=2, rw=1.0000, t_lock=14.47 = la hora de la muerte. 2 constantes: FIRME t_lock=0. CONTROL: apagado+vivo=0, vivos dw=3 → MUERTO ✓ |
| F2 ALTO | Armónico 2× rompe lock verdadero (c1) | A=0→FIRME rw=1.000; A=0.35→COQUETEO rw=0.941; A=0.5→COQUETEO rw=0.814 |
| F3 ALTO | 1 tick NaN → MUERTO silencioso (c1) | estado=0, rw_final=nan, frac_coq=0.000, SIN excepción; CONTROL sin NaN → FIRME |
| F4 ALTO | t_lock ANTES del lock (c1) | sesgo por dw_pre: 3.0→−0.54, 1.0→−1.17, 0.5→−1.98, 0.3→−3.26 u.t. (res declarada 0.008: subestimada 60–400×) |
| F5 ALTO | Ventanas pulling sin validar (c3) | film 1.2 u.t. declara temprana=5.5/tardia=10 y corre; cfg del PROPIO gate8 (temprana=0.3) publica dw_temprana=NaN con estado=2; tardia_ut=0 = film entero |
| Provenance ALTO (c3) | Umbrales cross-estimador | verificado por lectura: `tools/exprimir_c1.py` = theta CRUDO, `[::SUB=100]`, W_VENT=125 (1 u.t.), sin corrección §16; **cero** fixtures C1; el manifiesto dice "MEDIDOS" sin letra chica |
| X1–X5, F6 | n=1 IndexError crudo; stride_det=−100 silencioso (serie invertida, t_lock=0/frac=1); stride_det=0 ZeroDivisionError; lock-que-muere=coqueteo t_lock=0; FIRME con t_lock=NaN; zona gris: falso-FIRME hasta dw=0.236 ≈ 1.1/W=0.275 vs 2π/W=1.571 declarado (5.7×) | todos CONFIRMADOS |

**Arreglos (implementados en sandbox, branch `arreglos-juez` del clon; fuente en `juez/fixes/par_fixed.py` + `juez/fixes/test_par_f1_juez.py`; con ellos: F0 9/9 + F1 23/23 + suite completa 104 passed):**

- **A1 (BLOQUEA)**: piso de mudez por nodo (std de la señal Q en ventana final < max(1e-12, 1e-3·std propio del film) ⇒ MUDO) → estado=3 para todo par con nodo mudo, canal `nodos_mudos` en el manifiesto. Gate: film que muere JAMÁS firme. Umbral PROVISORIO declarado.
- **A2**: NaN/Inf en fase ⇒ RuntimeError fail-loud (contrato api).
- **A3**: validación de valores — n_nodos≥2, ventana temprana (0.5, temprana_ut] dentro del film, 0<tardia_ut≤film, stride_det≥1, sosten_ventanas>0, w_ut>0 ⇒ RuntimeError. Obliga corregir la cfg del gate8 (temprana 0.3→0.8: el gate versionado ejercitaba el bug).
- **A4**: detector de armónicos declarado (razón 2º/1º pico > 0.25 ⇒ `nodos_armonico` + nota de no-confiabilidad). El fix real (Hilbert/multi-armónico) queda NO-CUBIERTO.
- **A5**: sesgo de t_lock DECLARADO en nota (medido −0.5…−3.3 u.t.) + gate cota [t*−W, t*+1]; gate4 apretado a t*+1 (la cota vieja 2W+0.5 dejaba vivo a M06).
- **A6**: dos números declarados: `zona_falso_firme_dw`=1.1/W (frontera MEDIDA, cruce |sinc|=0.95) y `punto_ciego_dw`=2π/W (cero de la sinc); docstring corregido.
- **A7**: semántica de borde en la nota: FIRME=firme AL FINAL; lock que muere=coqueteo aunque t_lock exista; franja final ~3W no fechable.
- **A8**: `procedencia_umbrales` honesta: "MEDIDOS en C1 con OTRO estimador (crudo, SUB=100, W=1) — transferidos POR HIPÓTESIS, NO re-ejecutados" (conserva el substring que gate8 exige).
- **A9**: manifiesto citable: `dt`, `w_ticks_efectivo`, `estados_codigo` máquina-legible; `ESTADOS` corregido (estaba invertido).
- **A10**: fold de 13 kill-tests + 10 gates nuevos (23 tests, 0.9s, dt=8e-4).

## 2. Tabla de mutantes (20 definidos; 15 re-corridos por el juez sobre F0 pristine, 12 vivos re-matados sobre el código arreglado)

| Mutante | F0 pristine (juez) | Re-matanza F1 (juez, código arreglado) |
|---|---|---|
| M01 sin corrección fase | MUERTO gate1 (batch c2; no re-corrido: no era vivo) | — |
| M02 w_full con signo | MUERTO gate1 (idem) | — |
| M03 rw_final sin ventana | MUERTO gate4 (idem) | — |
| M04 umbral_firme=0.9 | **VIVO 9/9** | **MUERE** kt_m04 (banda 0.90–0.949) |
| M05 episodios sostén 2W | MUERTO gate3 (batch c2) | — |
| M06 t_lock=fin del sostén | **VIVO 9/9** | **MUERE** kt_m06 (+gate4 apretado) |
| M07 firme por sost_firme | **VIVO 9/9** | **MUERE** kt_m07 (lock que muere) |
| M08 temprana desde tick 0 | **VIVO 9/9** | **MUERE** kt_m08 (transitorio) |
| M09 pulling con w_full | MUERTO gate5 (batch c2) | — |
| M10 pares solo (0,1) | **VIVO 9/9** | **MUERE** kt_m10 (3 nodos) |
| M11 FFT sin Hann | **VIVO 9/9** | **MUERE** kt_m11 (tono+rampa) |
| M12 FFT sin zeropad | **VIVO 9/9** | **MUERE** kt_m12 (w=4.9 entre bins; aplicado a mano sobre el arreglado: su patrón quedó duplicado por _razon_armonica) |
| M13 punto ciego en muestras | **MUERTO gate7** (predicción c2 confirmada) | — |
| M14 _rw_movil off-by-one | **VIVO 9/9** | **MUERE** kt_m14 (contrato unitario) |
| M15 theta duplicado sin fallback | **VIVO 9/9** | **MUERE** kt_m15 (film sin capa Q) |
| M16 estado string | **MUERTO gate1** (predicción c2 confirmada) | — |
| M17 rw_final=max | **MUERTO gate3** — c2 lo tenía PENDIENTE; el juez lo mata en F0 (corrección al reporte de c2); kt_m17 foldeado igual como contrato | — |
| M18 dphi_final film entero | **VIVO 9/9** | **MUERE** kt_m18 |
| M19 umbral_coqueteo=0.5 | **VIVO 9/9** | **MUERE** kt_m19 (rw≈0.69) |
| M20 min_firme=1 muestra | **VIVO 9/9** | **MUERE** kt_m20 (cruce breve) |

**Balance: 12/20 vivos en F0 (60% de fuga del veredicto) → 12/12 muertos tras los arreglos.** Condición dura de la casa CUMPLIDA: re-matanza ejecutada contra el código arreglado, un mutante por vez, restore + purga de `__pycache__` (resultados: `juez/muts_juez_results.txt`, `juez/rematanza_results.txt`, logs `juez/log_M*.txt`/`rm_M*.txt`).

## 3. Contrato por cláusula

| Cláusula | Estado @ ffc8c72 |
|---|---|
| Extracción θ unificada con fase | **CUMPLE** (gate8 bit-exacto; M15 muestra que solo un gate con film Q lo protege — kt foldeado) |
| Whitelist de config | CUMPLE en CLAVES, **VIOLA en VALORES** (stride_det −100/0, w_ut 0, ventanas imposibles corren o revientan crudo) → A3 |
| Fail-loud ("el instrumento FALLA, no sustituye") | **VIOLADO**: NaN→veredicto MUERTO silencioso; n=1→IndexError crudo; ventanas clampean/NaN en silencio (la cfg del propio gate8 lo ejercita en los 81 passed) → A2/A3 |
| Veredicto por par | **VIOLADO en el borde de amplitud** (BLOQUEA: sin piso, cadáveres firmes; la View no exporta amplitud — el juez §16 llevaba amp_min) → A1. Semántica FIRME=al-final legítima pero NO declarada → A7 |
| Corrección §16 | Exacta a la del juez j3 (verificado por c1 línea a línea; consistente con lo que yo medí) pero asume TONO PURO: rompe con armónico 2× (14/150 bloques reales) → A4 declarativo, fix real pendiente |
| Umbrales con procedencia MEDIDA | **SOBRE-DECLARADO**: medidos con OTRO estimador (crudo, decimado SUB=100, W=1) y transferidos sin re-ejecución a fase corregida W=4 → A8; recalibración = NO-CUBIERTO |
| Punto ciego DECLARADO | Declarado 2π/W=1.571; frontera falso-FIRME MEDIDA ≈0.24–0.28 (=1.1/W del panel §16): conservador 5.7× y tira la franja útil [0.63, 1.57] → A6 |
| t_lock con resolución stride_det | Resolución real dominada por el sesgo de ventana forward (−0.5…−3.3 u.t. según dw_pre), no por stride_det → A5 (declarado+acotado, convención early se mantiene) |
| Manifiesto citable | Falta dt, W efectivo, mapa estado→nombre; `ESTADOS` en orden INVERSO al código; t_lock relativo a t0_tick sin declarar → A9 |
| Escritura/relectura de vista, view_hash, film_intervenida | CUMPLE (c3 ejecutado; el juez no lo re-ejecutó — cubierto por gate8 en mis corridas 81/104 passed) |

## 4. NO-CUBIERTO consolidado

1. **Calibración de umbrales con ESTE estimador**: no existe adapter C1-npz→worldline ni gate que reproduzca los 7 links firmes/hombro de §13 con fase corregida y W=4 (films en /Volumes/ExternalDisk read-only). Riesgo direccional: la corrección SUBE rw ⇒ 0.95-crudo puede sobre-llamar FIRME. Debe resolverse (o declararse en el prereg del census) ANTES de que `estado` decida links.
2. **Armónicos**: A4 solo DECLARA (`nodos_armonico`); el veredicto sigue degradándose con A≥0.35. Fix real (Hilbert/multi-armónico) + validación contra los 14 bloques reales 2× = siguiente iteración.
3. **Default W=4 jamás ejecutado contra film real ≥3W**: el único film real (f8, 1.2 u.t.) corre con w_ut=0.24. Falta fixture real largo (≥150k ticks) con sha versionado.
4. **Cableado al census**: `campana._vistas_y_metricas` corre solo energy+phase; ninguna fila de ledger lleva view_hash_par; nada en tools/ referencia par_link. La regla del census (¿estado==2, o estado==2 OR t_lock finito?) debe fijarse en el prereg citando la nota nueva (A7) — hoy la etapa 0 no está conectada al universo que dice descubrir.
5. **Escala 11175 pares** (150 nodos, 750k ticks): medida por c3 — ~10.6 min/proceso (ajuste 123 ms/nodo + 55.4 ms/par, validado n=30 al 1.8%) y ~5.4–7 GB pico por worker; rw por par no se retiene (no crece con pares). NO re-ejecutada por el juez; es diseño viable, no bug — presupuestar por worker y considerar `del unw, grad` (−1.8 GB). Los arreglos A1/A4 agregan un rfft 8× por nodo (~+0.2 s/nodo a 750k ticks): despreciable frente a los 55 ms/par.
6. **Umbrales nuevos de los arreglos sin procedencia medida**: PISO_AMP_REL=1e-3 y UMBRAL_ARMONICO=0.25 son PROVISORIOS (declarados en el código); medirlos contra e_floor y los bloques armónicos reales antes del census.
7. Vistas por nivel (cláusula 2 de COA: onion/grumo/cluster) — pendiente igual que F4; `permitir_incompleto` y propagación `film_intervenida` sin test específico de par (dos asserts baratos, no foldeados por el juez).

**Repos reales verificados INTACTOS al cierre**: `/Users/cagostino/code/doft-study07-worldline` → `git status --porcelain` vacío, HEAD 3456999 (commit de registro §18 posterior al tap, preexistente — par.py sin diff contra ffc8c72); `/Users/cagostino/code/doft-study06-fundamental-lock-dynamics` → limpio. Cero mutaciones fuera de los clones de scratchpad; clon del juez restaurado tras cada mutante (los arreglos viven solo en el branch `arreglos-juez` del clon y en `/private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad/juez/fixes/{par_fixed.py,test_par_f1_juez.py}`, listos para foldear tras revisión de COA).