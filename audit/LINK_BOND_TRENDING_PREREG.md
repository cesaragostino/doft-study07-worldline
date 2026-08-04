# Prerregistro — trending físico del bond a resolución nativa

Fecha: 2026-08-04

Estado: **SELLADO ANTES DE LA COSECHA POBLACIONAL**

Branch: `research/link-bond-trending`

## 1. Pregunta

Los films existentes ya contienen tres objetos que no deben fundirse en un score:

1. la fuerza KV realmente aplicada por el link;
2. el trabajo que esa fuerza hace sobre Q, S1 y S2;
3. el orden de fase que muestra si una relación resonante permanece trabada, desliza,
   se libera o recaptura.

Este frente pregunta cómo evolucionan esos objetos durante el film. No busca predecir
supervivencia, decidir fitness ni construir un nuevo árbitro de aristas.

## 2. Población y alcance identificable

La primera cosecha usa exclusivamente worldlines `COMPLETE` de dos nodos y una sola arista.
En ese dominio `drive[:,j]` es identificable como la fuerza del único link sobre el extremo
`j`. Un film multiarista falla fuerte: el recorder conserva fuerza nodal total y este frente
no la repartirá mediante pesos, locks ni amplitudes.

Fuentes previstas, sólo lectura:

```text
/Volumes/ExternalDisk/study07_census_arnold
```

Derivados nuevos, autorizados por el usuario y separados de la fuente:

```text
/Volumes/ExternalDisk/study07_link_bond_trending_v1
```

No se modifica ningún film, ledger previo, bitácora ni outcome histórico.

## 3. Resolución temporal: qué significa «calculado sobre dt»

Los estimandos consumen todos los ticks contiguos del film, con `stride_input=1`:

- la potencia usa `drive[k]` y `v[k-1]` en cada paso;
- la fase de cada capa se extrae de `x/v` en cada tick;
- las cajas de potencia y lock se construyen con todas las muestras `dt` dentro de la caja;
- `L_pq(t)` se evalúa para cada final de `dt` que ya posee una caja completa;
- recién después se publica además una fila de índice compacto cada `hop_ut`.

El `hop` reduce almacenamiento, no cambia el estimando. El manifiesto declara `dt`, cantidad de
muestras por caja, `hop_ticks`, rango de ticks consumido y si se retuvo o no la traza instantánea.
El instrumento permite no duplicar la traza completa porque ya vive en la worldline y es
regenerable. Sin embargo, **la cosecha pedida en este frente usa `retain_dt=true`**: conserva
`theta`, fase corregida, potencia instantánea y ambos `L_pq` para inspeccionar fluctuaciones sin
que el `hop` borre bailes breves. El índice a `hop_ut` sigue siendo la entrada liviana para resúmenes.

Defaults de la primera cosecha:

```text
lock_window_ut  = 4.0
power_window_ut = 2.0
hop_ut          = 0.25
ratios          = 1:1
lock_threshold  = 0.90
retain_dt       = true   # ejecución poblacional de este frente
```

`lock_threshold` sólo publica una bandera temporal compatible con el lector de capas existente.
No produce un veredicto final de salud.

## 4. Potencia exacta por capa

La worldline registra la fuerza del subpaso 0 del paso `k`; ese subpaso parte de
`estados[k-1]`. Como el RHS aplica la misma fuerza a todos los modos, la potencia por capa es
una partición algebraica exacta de la ley vigente:

\[
P_{i,\ell}[k]
=F_i[k]\sum_{m\in\ell}v_{i,m}[k-1],
\qquad \ell\in\{Q,S1,S2\}.
\]

Debe cerrar, salvo redondeo float64:

\[
P_{i,Q}+P_{i,S1}+P_{i,S2}
=F_i\sum_m v_{i,m}.
\]

Por fila de trending se publican:

- media causal de `P_layer`;
- fracción de muestras con signo negativo;
- trabajo acumulado por capa;
- potencia neta de ambos extremos por capa;
- fracción de la caja con signos opuestos entre extremos;
- RMS de la fuerza nodal.

Esta partición dice dónde hace trabajo el **input uniforme del motor actual**. No demuestra que
la arista tenga un endpoint físico separado en S1 o S2.

## 5. Fase y orden de lock

Para cada nodo y capa:

\[
\theta_{i,\ell}[k]
=\operatorname{atan2}\left(\sum_{m\in\ell}v_{i,m}[k],
                            \sum_{m\in\ell}x_{i,m}[k]\right).
\]

Se publican en paralelo dos lecturas ya presentes en el linaje instrumental:

1. `raw`: usa `theta` directamente;
2. `corrected_fixed`: usa la corrección elíptica de `par_link` con la frecuencia media del film
   para cada nodo/capa.

La segunda es **observacional y no causal** porque fija su referencia usando el film completo.
Se usa para visualizar estabilidad sin que la elipse de `atan2(v,x)` fabrique diferencias; no
puede entrar en una decisión online. Publicar ambas expone su desacuerdo en vez de esconderlo.

Para una relación declarada `p:q`, definida por `q*omega_0 ~= p*omega_1`:

\[
L^{\ell}_{p:q}(t;W)=
\left|\frac{1}{W}\sum_{t-W}^{t}
e^{i(q\phi_{0,\ell}-p\phi_{1,\ell})}\right|.
\]

La primera cosecha poblacional usa sólo `1:1`: es el estimando de capas ya auditado y evita un
barrido post hoc sobre racionales. El instrumento acepta otros `p:q` declarados en la config;
cada panel posterior deberá fijar su lista antes de abrir resultados.

Por fila se publican:

- `L_pq_raw` y `L_pq_corrected_fixed`;
- fase combinada envuelta al final de la caja;
- deriva de la combinación de fase durante la caja;
- frecuencia media de cada extremo/capa;
- amplitud `std(x_layer)` y bandera causal de mudez;
- bandera `locked = L_corrected>=0.90 AND no_mudo`.

## 6. Resultado buscado y nulas

El resultado es descriptivo: curvas por link y capa. Las preguntas son:

- ¿el lock permanece alto o alterna captura/release?;
- ¿la fase combinada queda acotada o acumula slips?;
- ¿S1/S2 absorben, devuelven o disipan trabajo mientras están lockeadas?;
- ¿la fuerza crece durante los deslizamientos o cae cuando el bond se organiza?;
- ¿existen links espectralmente trabados con potencia secundaria casi nula?

Nulas conservadas:

- fuerza grande no implica bond fuerte;
- coherencia alta no implica transferencia dirigida;
- potencia por capa no identifica endpoint de arista;
- `locked` en una caja no implica supervivencia futura;
- una referencia fija de fase puede ocultar parte de un chirp fuerte.

No se calculará AUC, umbral de salud ni ranking evolutivo en esta etapa.

## 7. Gates antes de población

1. alineación exacta `drive[k] * v_layer[k-1]`;
2. cierre `sum_layer(P) == P_node` a tolerancia float64 declarada;
3. lock sintético 1:1 estable, deriva conocida y release/recaptura;
4. invariancia de valores coincidentes frente al `hop` de publicación;
5. guard de mudez: amplitud nula no puede producir `locked`;
6. rechazo de ticks discontinuos, hashes inválidos, NaN/Inf y topología multiarista;
7. `view_hash` recomputado después de escribir;
8. smoke sobre dos brazos de un mismo par antes del barrido completo.

## 8. Calzones sucios anticipados

- `corrected_fixed` usa futuro del mismo film para fijar la escala de fase; se prohíbe venderlo
  como predictor causal.
- El motor inyecta `F` uniformemente. Ver potencia S2 no prueba que el link haya entrado por S2.
- `1:1` por capa suma modos internos; puede esconder locks entre modos individuales o p:q.
- Las ventanas W4 y P2 suavizan eventos menores a esas escalas. Aunque `L(t)` se guarda para cada
  final de `dt`, no promete fechar una transición mejor que el soporte de su ventana W4.
- Esta cosecha describe la física v1 que produjo los films; no corrige la interfaz KV auditada en
  `audit/STUDY05_STUDY07_ARISTAS_Y_ACOPLE_INTERNO.md`.
