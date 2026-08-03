# Gate I — fenomenología de los residuos

Fecha: 2026-08-02. Branch `research/link-grumo-dynamics`.

Gate I no agrega estados ni ajusta umbrales. Es una lectura exploratoria, posterior a
Gate G/H, de los casos que una foto temprana o una etiqueta escalar describen de manera
incompleta. Usa sólo derivados ya existentes; no releyó ni modificó los films externos.
La salida completa queda localmente en
`logs/link_grumo/gate_i_residual_phenotypes.json` (SHA-256
`a59d1a0cd41f8f049dbfe7e1ee5fbc9ca61909c9bbf95c92fe45ddaaeda1491d`).

## 1. Resultado principal: los residuos no forman una sola bolsa

Los siete desacuerdos `captura Q a t=20 XOR salud coordenada a t=60` se separan en
cinco recorridos reproducibles:

| recorrido | n | casos | lectura |
|---|---:|---|---|
| coherencia de ventana deslizante | 2 | par003-t, olaB-par029-t | W4 acompaña una fase que sigue corriendo; W8 no consolida |
| captura intermitente | 1 | olaB-par036-t | tres episodios Q separados, no un único link sostenido |
| canal plano seleccionado antes de fase | 2 | par069-t, olaB-par070-t | la transferencia ya eligió canal; la fase cierra después de t=20 |
| canal provisional no plano | 1 | olaB-par010-f | hay ocupación, pero todavía no selección plana; lock a 47.24 |
| nucleación tardía | 1 | olaB-par007-f | a t=20 aún no hay línea común; lock a 40.83 |

Por tanto, “todavía no capturó” mezcla al menos tres cosas distintas, y “ya capturó”
mezcla captura consolidada, seguimiento deslizante e intermitencia.

## 2. Los tres falsos tempranos: qué comparten y qué no

Comparten cinco hechos:

* son `transported` y sus gemelos fresh tampoco llegan sanos a 60 (`NN`);
* tienen ocupación observada de la línea a t=20;
* están fuera del régimen de transferencia conjunta plana;
* S2 está capturado en 3/3;
* la primaria estricta todavía no está capturada en 3/3.

Esto da una primera interpretación de la biografía que antes no estaba separada: puede
crear **coherencia transitoria muy convincente en un par que no posee un canal viable**.
No siempre habilita ni sólo acelera; a veces sostiene un coqueteo.

Los dos casos deslizantes son una réplica especialmente limpia. Ambos tienen Q, S1 y S2
activos, ocupación observada y primaria no capturada, pero no tienen ocupación predicha
por la susceptibilidad fría. Esa firma aparece exactamente en 2/2 films del banco y los
dos fallan. Es post hoc y no puede convertirse en regla, pero sugiere una secuencia:

`biografía -> coherencia interna multicapas -> línea observada -> deriva fuera del canal`

W4 los llama activos durante todo el film. W8 los rechaza al final:

| film | Q W4 activo hasta 60 | Q W8 final | deriva corregida 50–60 | lock W8 histórico |
|---|---:|---:|---:|---|
| par003-t | 100% | 0.928 | 0.169 | ninguno |
| olaB-par029-t | 100% | 0.804 | 0.287 | ninguno |

El tercer falso, olaB-par036-t, es otro fenómeno: sí posee ocupación predicha y observada,
pero alterna tres episodios Q. Su firma booleana tiene un control sano casi exacto,
olaB-par069-f: ambos tienen Q+S2, carecen de S1/primaria y no son planos. Uno fragmenta
su captura; el otro entra una vez y permanece. El endpoint no decide el caso; lo decide
la morfología temporal.

## 3. Los cuatro falsos negativos forman una escalera de precursores

Entre los films sin Q activo a t=20 aparece una gradación descriptiva:

| precursor a t=20 | n | sanos a 60 |
|---|---:|---:|
| sin línea observada | 23 | 1 |
| línea observada, canal no plano | 8 | 1 |
| canal conjunto plano ya seleccionado | 2 | 2 |

El banco es case-control y estos cocientes no son probabilidades poblacionales. Aun así,
la ordenación es físicamente coherente y los cuatro positivos tardíos ocupan las tres
rutas: nucleación, consolidación provisional y selección plana previa a fase.

Los dos casos planos, par069-t y olaB-par070-t, no estaban realmente “sin formar”. A
t=20 ya tenían ocupación y `R≈1` en una banda plana; faltaba cerrar la fase Q. Sus locks
W8 llegan en 20.38 y 28.34. En cambio, olaB-par007-f no muestra precursor medible y
nuclea mucho después. olaB-par010-f ocupa una posición intermedia.

La biografía también se parte aquí en dos efectos:

* par069/par070 son `YN`: transported **habilita** el canal que fresh no logra;
* par007/par010 son `YY`: transported ya está trabado a t=20 y fresh llega después;
  aquí la biografía **acelera** una capacidad que ambos brazos poseen.

## 4. La semejanza estática no permite resolver los casos difíciles

Se compararon los 60 films con ocho coordenadas disponibles sólo hasta t=20, escaladas
robustamente: ocupación predicha/observada, Q/S1/S2, primaria, `dw` y error complejo.
Cada falso temprano tiene controles sanos extremadamente cercanos. Por ejemplo,
olaB-par029-t queda más cerca de un sano (distancia 0.352) que del otro caso deslizante
par003-t (0.449); olaB-par036-t tiene un sano a 0.376.

Esto es un resultado negativo importante: no se ve un escalar temprano ausente que
separe limpiamente los residuos. Más mediciones de la misma foto probablemente no
resuelvan el problema. Lo que falta es trayectoria: continuidad, slips, deriva acumulada
y salida de banda.

## 5. Los cuatro films largos separan reloj del líder y morfología del link

Los dos líderes repetidos producen relojes casi idénticos con socios distintos, mientras
la topología del canal cambia:

| familia del líder | pares | cruce `SOURCE_FADED` | cobertura canal | releases | final del canal |
|---|---|---:|---:|---:|---|
| C≈10.18 | 129 / 131 | 353.75 / 354.75 | 0.906 / 0.869 | 0 / 2 | dominante / dominante |
| C≈9.88 | 132 / 134 | 304.25 / 304.25 | 0.188 / 0.475 | 4 / 1 | liberado / liberado |

Con n=2 por familia esto es una pista, no una inferencia estadística. Pero la separación
es difícil de atribuir a azar de lectura: el tiempo de apagado del líder se replica a
0–1 u.t., y el mismo reloj permite historias de releases muy diferentes. La lectura
más económica es:

* el **líder** aporta la worldline/chirp y un reloj de vitalidad;
* el **receptor y el par** determinan susceptibilidad, relevos y cicatrices del canal.

La memoria estructural también pertenece al episodio, no sólo al reloj. Con el mismo
líder C≈9.88, `b_S1` alcanza 0.268 en par132 y sólo 0.0064 en par134, una diferencia de
aproximadamente 42 veces. En par132 el pico llega 35.45 u.t. después de comenzar el último
hueco; en par134 llega 7.25 u.t. después de perder dominancia, todavía dentro de la gracia
previa al release. Es una **posimagen** de la interacción, no evidencia de canal vivo.

El residuo opuesto aparece en par129/131: conservan una línea espectral dominante hasta
600 cuando fuente y recepción han caído a fracciones del orden de `1e-7` de sus picos.
Es una **cola espectral sobre fuente apagada**. Gate H la representa bien como
`DOMINANT x SOURCE_FADED`, pero la palabra `DOMINANT` sola la habría confundido con vida.

## 6. Mapa fenomenológico mínimo, sin inflar la máquina

No conviene crear cinco estados nuevos. Los residuos se describen mejor con etiquetas
ortogonales de diagnóstico:

1. **ruta del canal:** `FLAT_SELECTED`, `NONFLAT_PROVISIONAL`, `LATE_NUCLEATION`;
2. **régimen de fase:** `CONSOLIDATING`, `SLIDING`, `INTERMITTENT`;
3. **causa de transición:** `SOURCE_DECAY`, `SUSCEPTIBILITY_NOTCH`, `COMPETITOR` o
   `UNKNOWN`;
4. **memoria:** `AFTERIMAGE` si la variable estructural persiste o culmina después de
   perder dominancia.

Son anotaciones causales sobre la trayectoria, no puertas de supervivencia. La máquina
Gate H permanece sin cambios.

## 7. Consecuencia para la regla de salud

Gate I vuelve más estricta, y más simple, la conclusión anterior:

> Un link está sano ahora cuando una línea común ganó, su relación de fase no sólo es
> alta sino estable entre escalas temporales, y todavía existe actividad para sostenerla.

S2 sigue siendo una pista de ruta y maduración, pero no una ley: está alto en los tres
falsos tempranos. Q tampoco basta si una ventana corta persigue una fase deslizante.
Y dominancia tampoco basta sobre una fuente apagada. Las tres comprobaciones mínimas son
**selección de línea, persistencia multiescala y vitalidad**.

“Sobrevivirá para siempre” no aparece como propiedad fija. El modelo debe reevaluar esas
tres condiciones y permitir release/recaptura.

## 8. Próxima medición barata

No hace falta correr films nuevos. El banco de máxima información queda reducido a:

* deslizamiento: par003-t y olaB-par029-t, con olaB-par005-t como control sano cercano;
* intermitencia: olaB-par036-t contra olaB-par069-f, que comparte las mismas banderas;
* selección antes de fase: par069-t y olaB-par070-t;
* nucleación/consolidación: olaB-par007-f y olaB-par010-f, usando sus twins transported
  como controles de aceleración.

En esos eventos basta extraer, en ventanas estrechas, tres tasas ya disponibles:
`d ln(ocupación)/dt`, deriva acumulada de fase y descomposición del cambio en línea
recibida entre drive/susceptibilidad/competidor. Eso permitiría asignar causas a slips,
releases y capturas tardías sin sumar parámetros a fitness ni abrir todo el censo otra
vez.

## 9. Reproducción

```bash
PYTHONPATH=src:tools/link_grumo python3 \
  tools/link_grumo/gate_i_residual_phenotypes.py \
  --gate-g logs/link_grumo/gate_g_evaluate.json \
  --gate-h logs/link_grumo/gate_h_state_machine.json \
  --long-reader /Users/cagostino/code/doft-study07-worldline/data/film_largo_600/LECTURA_v2.json \
  --output logs/link_grumo/gate_i_residual_phenotypes.json

PYTHONPATH=src python3 -m pytest -q \
  tests/test_gate_i_residual_phenotypes.py tests/test_link_state_machine.py
```

Límites: clases y firmas fueron nombradas post hoc; vecinos cercanos son descriptivos;
el outcome de Gate G termina a 60 u.t.; las familias largas tienen dos réplicas cada una;
la pata de potencia continúa sin serie temporal.
