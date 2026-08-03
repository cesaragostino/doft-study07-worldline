# Gate L — el lazo recíproco explica el canal; el residuo grande vive en el onion activo

Fecha: 2026-08-02. Ejecutado contra el preregistro
`LINK_GRUMO_GATE_L_BIDIRECTIONAL_TRANSIENT_PREREG.md` sobre 8 pares / 16 films del panel
Gate F. Es calibración retrospectiva seleccionada por outcomes: no hay p-values ni claim
poblacional.

## Veredicto

La nula bidireccional sí compra dinámica: cerrar la arista Kelvin–Voigt mejora la
trayectoria Q frente a dos onions independientes en **16/16 films**, en las tres
ventanas. La mejora mediana crece con el tiempo:

| ventana | ΔE_Q feedback | E_Q coupled-frozen | E_drive coupled-frozen |
|---|---:|---:|---:|
| 0.2–2 | +0.0396 | 0.000285 | 0.0137 |
| 2–10 | +0.1590 | 0.000484 | 0.00606 |
| 10–20 | +0.3610 | 0.000946 | 0.00444 |

Pero **no es una brújula de salud**. Entre 2–10 u.t. la mejora es algo mayor en los
no-sanos (+0.167) que en los sanos (+0.145), y la nula reproduce mejor a los no-sanos
(`E_Q=0.000182`) que a los sanos (`0.00110`). El resultado no es paradójico: la
reciprocidad modela muy bien un receptor pasivo aunque éste nunca seleccione ni sostenga
la línea. Explicar el cable no equivale a explicar vida.

## La división realmente fuerte es fresh/transported, no sano/muerto

Entre 2–10 u.t.:

| brazo | E_Q coupled-frozen | ΔE_Q feedback | ventaja de b/e congelado sobre frío |
|---|---:|---:|---:|
| fresh | 0.000202 | +0.166 | 0 exacto (b=e=0) |
| transported | 0.01250 | +0.132 | +0.00364 |

Los fresh pasivos que no sobreviven son casi LTI de manual. Por ejemplo, los controles
fresh de par093/133/134 dan `E_Q={2.22e-4,1.57e-4,1.18e-4}` en 2–10. La biografía no
rompe la transferencia: hace que el onion traiga una trayectoria autónoma que una
linealización congelada puede dejar de seguir.

Esto afina Gate C/D: la respuesta incremental `χ·F` puede ser lineal y exacta mientras
la worldline base del onion no lo es. `linear_selected` describía el canal seleccionado,
no prometía que el par entero fuera un LTI alrededor de cero.

## Los dos fuera de patrón son el mismo ignitor

`par133_t` y `par134_t` comparten como nodo 0 a
`1bc9dcccf3bd7b83b9c0d10e3be64222215d90e6` y cambian sólo el socio. En ambos:

- `E_Q coupled-frozen` del par en 2–10: **1.32994 / 1.32991**;
- nodo 0 solo: **1.32995 / 1.32991**;
- el residuo Q cruza 0.01 en t=0.38, 0.1 en 1.02, 0.5 en 2.188 y 1.0 en 3.628 u.t.,
  exactamente los mismos bins para los dos socios;
- el socio también se desvía (`E_Q≈0.992/1.007`) porque recibe la trayectoria del
  ignitor que la nula ya perdió: el residuo se propaga por un link real.

El estado de llegada del ignitor es excepcional: `||b0||=62.442`, `||e0||=15520.953`.
La linealización fría tiene `max Re λ=+0.02744`; congelar su biografía la mueve a
`−0.002774`. Por eso la nula fría ya falla violentamente en 0.2–2
(`E_Q≈1.442`), mientras frozen rescata el arranque (`≈0.112`). La biografía **cambia el
signo de estabilidad local** del ignitor.

Frozen, sin embargo, diverge después. Este gate no permite adjudicar todo el residuo a
`b(t)`: la matriz es una linealización alrededor de amplitud cero aplicada a una IC de
energía enorme. Quedan mezclados tres mecanismos que el próximo gate debe separar:

1. no-linealidad rápida de memoria/energía a amplitud finita;
2. evolución de `b/e` durante la ventana;
3. propagación del error del ignitor al seguidor.

La igualdad film-a-film al cambiar de socio dice que el nacimiento del residuo es
propiedad del **onion dominante**; no que el socio sea irrelevante después.

## Qué aprendimos sobre `det[I−ΧK]`

El determinante estacionario sigue siendo útil para localizar modos y ganancias del
lazo. No decide salud:

- el feedback mejora 16/16, incluidos todos los muertos;
- los pasivos no-sanos son justamente los mejor explicados por el lazo lineal;
- los vivos más interesantes son los que dejan un residuo grande porque su fuente
  evoluciona.

La 2×9 ya no debe preguntar «¿aparece un polo que define vida?». Debe separar:

```text
geometría del canal recíproco    -> la nula bidireccional la explica
dinámica autónoma del onion      -> vive en el residuo de la fuente
selección/maduración/persistencia -> máquina H; no sale del determinante
```

## Próximo corte barato

Antes de correr 2×9, agregar sobre este mismo panel una nula
`NONLINEAR_FAST / SLOW_FROZEN`: usar el RHS completo para `(x,v,z)` y mantener `b/e`
fijos en su valor inicial, con la misma historia y KV recíproco. Prioridad: par133/134,
con fresh como control letal.

- Si cierra el residuo temprano, el culpable era linealizar una órbita de gran amplitud
  alrededor de cero.
- Si no cierra, repetir con `b/e(t)` observado como replay diagnóstico; la diferencia
  aísla la evolución estructural.
- Sólo después amerita una nueva campaña. Ninguna de estas nulidades se convierte en
  fitness.

## Integridad, límites y calzones sucios

- 16/16 films `COMPLETE`, manifiestos y todos los chunks reverificados por SHA-256.
- 0/16 `NUMERICALLY_UNRESOLVED`; peor coarse-vs-fine <0.001 contra límite 0.02.
- Método ZOH/expm, no bit-exacto al RK4 de producción; ley v1 `direct-only`.
- Primer intento: murió antes de scores (`KeyError block_id`) porque fresh no lleva esa
  clave; arreglo por `spec_fingerprint` canónico, sin consultar outcome.
- Primera salida completa: incumplía el prereg al agregar los nodos; se descartó. Se
  agregaron métricas `per_node` y se reranearon los 16 films.
- Una pasada adicional agregó identidades y `b/e` iniciales por nodo; la salida canónica
  volvió a verificar los films. No se eligió entre pasadas por el resultado.
- El primer `pytest` del arnés sintético murió en colección (`tools` no era paquete);
  se corrigió el path explícito y se volvió a ejecutar. No alcanzó código ni datos.
- La primera suite completa se invocó sin el `PYTHONPATH` del repo y murió en colección
  con 4 `ModuleNotFoundError: study07`; se reraneó con
  `PYTHONPATH=src:tools/link_grumo`: **130 passed, 210 warnings** (los warnings
  declarados direct-only/blowup de gates). Es cicatriz de entorno, no test rojo ejecutado.

Papeles:

- herramienta `tools/link_grumo/gate_l_bidirectional_transient.py`;
- salida `audit/LINK_GRUMO_GATE_L_BIDIRECTIONAL_TRANSIENT.json`;
- series de error cada 0.008 u.t. dentro de cada registro;
- entradas pinneadas y advertencias dentro del JSON.
