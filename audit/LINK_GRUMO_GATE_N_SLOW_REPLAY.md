# Gate N — lectura `OBSERVED_B_REPLAY`

Fecha: 2026-08-03. Estado: **EJECUTADO** después del preregistro sellado en el commit
`533857c`, anterior al simulador y a toda salida.

## Veredicto primario

**CIERRE FUERTE LENTO.** La trayectoria estructural observada `b(t)` es suficiente para
reconstruir la worldline rápida del ignitor de `par133_t/par134_t` que Gates L/M no
podían explicar. En `[2,10]`, nodo 0:

| variante | `par133_t`: `E_Q` / razón vs M | `par134_t`: `E_Q` / razón vs M |
|---|---:|---:|
| `SOURCE_Q_B` | 0.0141200 / 0.0105870 | 0.0141189 / 0.0105864 |
| `SOURCE_ALL_B` | 3.31e-7 / 2.48e-7 | 3.34e-7 / 2.50e-7 |
| `ALL_B` | 3.31e-7 / 2.48e-7 | 3.34e-7 / 2.50e-7 |

El cierre fuerte preregistrado exigía en ambos `E_Q<=0.10` y razón contra Gate M
`<=0.25`. Ya lo cumple `SOURCE_Q_B`; la localización sellada es por tanto
`SOURCE_Q_B_SUFFICIENT`. Reinyectar todo `b` del emisor elimina casi exactamente el
residuo restante. Reinyectar además el `b` del receptor no compra nada visible para el
nodo fuente.

La réplica entre socios es muy precisa y difícil de adjudicar al receptor: los números
de `par133/134` coinciden a cuatro-cinco cifras en las tres ablaciones. Es el mismo reloj
estructural del ignitor conduciendo dos encuentros.

## La segunda capa del resultado: Q domina, S1/S2 corrigen la fase acumulada

`SOURCE_Q_B` explica alrededor de 99% del error agregado, pero no reproduce toda la
trayectoria punto a punto. En ambos films su error local cruza `0.01` a `t=4.020`, `0.1`
a `t=10.004` y `0.5` a `t=16.476`. En `[10,20]` el `E_Q` agregado todavía es sólo
`0.0796` porque el error tardío pesa poco en amplitud, pero la deriva local existe.

Al replayear también `b_S1/b_S2` del emisor no cruza siquiera `0.01` en 20 u.t. y
Q/emisión quedan en `~10^-7–10^-6`. Durante ese tramo el ignitor cambia:

- `b_Q`: `61.794 → 77.168`;
- `b_S1`: `0.3166 → 0.4691`;
- `b_S2`: `8.9657 → 9.5797`.

La lectura mínima es: `b_Q` porta el chirp dominante; la evolución de las otras capas
ajusta acoples/frecuencias internas y evita que el error de fase se acumule. Esto es más
específico que «la biografía importa», pero todavía es suficiencia de estado observado,
no dirección causal aislada.

## Controles y fuera del patrón

Los fresh prioritarios tienen `b≈0` y las tres ramas quedan esencialmente idénticas a
Gate M (`E_Q` cambia menos de `2e-9`); ninguno tensiona el control. En el panel completo,
`ALL_B` reduce la mediana transported en `[2,10]` a razón `0.000766` contra Gate M,
mientras fresh queda en `1.000073`. Eso no prueba que `b` sea salud: describe exactamente
la ruta transported que porta estado lento, y además usa el outcome futuro.

`par043_f/ALL_B` conserva la misma no-convergencia de Gate M (`0.03843>0.02`) y se
publica `NUMERICALLY_UNRESOLVED`. No altera el primario.

## Qué descubrió y qué era conformance por construcción

`ALL_B` casi exacto es en parte una prueba de cierre del propio sistema de ecuaciones:
en la ley actual, `b` es la única variable lenta que entra directamente en `(x,v,z)`;
`e` sólo alimenta `db/dt`. Si se entrega la `b(t)` verdadera, el RHS determinista debería
reconstruir el film. Gate N confirma que lo hace con delay, historia, amplitud finita y
dos nodos, y que no queda otra fuerza grande escondida en esos films.

El contenido físico no-trivial está en la ablación: `b_Q` sola captura casi todo el
reloj común y `b` del emisor completo cierra; el receptor no es necesario para la
worldline del ignitor en estos dos casos. Pero los receptores de par133/134 casi no
cambian (`|b_Q(20)|<2e-5`), así que no se generaliza «el receptor nunca importa».

## Consecuencia para salud

Este resultado **no convierte `b_Q` en la regla de supervivencia**. El reloj del líder
es casi idéntico con socios distintos, mientras la cobertura, releases y destino del
canal cambian. El emisor aporta una agenda móvil de frecuencia/actividad; el receptor y
el par deciden si existe susceptibilidad, potencia y continuidad suficientes para
seguirla.

El próximo objeto útil no es otro score de `b`, sino la secuencia conjunta:

`reloj del emisor → margen móvil del receptor → captura/release → vitalidad/potencia`.

Con los datos existentes se puede probar si los residuos de Gate I salen del margen
`chi*F/A_S` antes de liberar, separando apagado de fuente, notch de susceptibilidad y
competidor. El postproceso de coherencia cruzada inspirado por el paper sigue en la cola,
pero no desplaza este corte más directamente ligado a la dinámica que Gate N acaba de
localizar.

## Calzones sucios e instrumento

- Outcome leakage explícito: cada replay usa `b(t)` futura del mismo film. No es
  predictor, causalidad ni fitness.
- `e(t)` no se corrió porque es algebraicamente inerte en el RHS rápido cuando `b` está
  prescrita. Un unitario verifica esa degeneración.
- Panel retrospectivo/outcome-selected: grupos son descripciones, no prevalencias.
- RHS v1 `direct-only`; los kernels descartados siguen fuera de alcance.
- `E_drive≈0.020` persiste cuando Q/emisión ya están en `~10^-7`. Es piso de etiquetado:
  el paso coarse guarda `f0` del comienzo del intervalo, mientras el film downsampleado
  guarda el `f0` del décimo paso productivo, separados `9*8e-5=0.00072` u.t. No se vende
  como fuerza residual.
- Cuatro shards exhaustivos por índice, mismas entradas y variantes predeclaradas. El
  merge exige 16 posiciones únicas, las tres ablaciones en los cuatro prioritarios y
  proyección/freeze exactos.
- Error de proyección de `b` y deriva de coordenadas congeladas: cero exacto en todas
  las unidades/variantes.

## Custodia

- salida: `audit/LINK_GRUMO_GATE_N_SLOW_REPLAY.json`;
- SHA-256 salida:
  `49750222c4eb62e5ea17db83580d8b30f494c3aaa7144bf6aa06624c72635131`;
- simulador: `tools/link_grumo/gate_n_slow_replay.py`, SHA-256
  `572083a5ae244a0a90b4a19a30872e577ecf569d80144639e7a442ee1ff36180`;
- merge: `tools/link_grumo/gate_n_merge.py`, SHA-256
  `9fc14dcace9c9d1824c927cac95d5b3f93b902eacfac19a0284792c212c7c211`;
- preregistro: SHA-256
  `b12dd86c86687987857c61d224bea7d0f0b596b6450a0bda84ddc8d97715e439`;
- Gate M pin:
  `230381973ce113db05e2bdae08d89d790b11b0c5fede61df79ff99cf1cf8e9b8`.

El disco externo fue sólo lectura; shards y salidas viven localmente.
