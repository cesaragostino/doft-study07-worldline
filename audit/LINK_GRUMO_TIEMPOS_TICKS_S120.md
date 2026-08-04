# Tiempos directos en ticks — cuatro pares s120

Estado: **CERRADO PARA ESTA LECTURA; ESTUDIO EVOLUTIVO INCONCLUSO**. Sólo el tiempo de
propagación de arista queda identificado causalmente. Los tiempos de cruce de capas son
observaciones, no retardos internos.

Fecha: 2026-08-03
Procedencia: frente experimental `research/k150-emergent-links`, cerrado el 2026-08-04.
El protocolo de medición quedó sellado en `6a427f9` antes de abrir los datos; su spec
exploratoria no se trasladó porque no establecía una física v2.

## Pregunta y método

Se intentó medir, en este orden:

1. tiempo de propagación de la arista;
2. tiempo entre llegada y cruce de Q/S1/S2;
3. tiempo de lazo.

La lectura usa sólo ticks enteros y el `dt` del manifiesto. No usa FFT, filtros, interpolación,
fase desenrollada, derivadas ni outcomes de lock/salud. El nodo 0 se toma como emisor de
referencia operacional y el nodo 1 como receptor; eso no convierte el lazo bidireccional en un
drive unilateral.

Herramienta:

```bash
python3 tools/link_grumo/medir_tiempos_ticks.py \
  --runs-root /Volumes/ExternalDisk/study07_lote_suelto_120/unidades \
  --output logs/link_grumo/tiempos_ticks_s120.json
```

La salida local contiene cada evento y cada diferencia de ticks; está ignorada por Git y se
regenera con el comando anterior. El lector rechaza una salida sobre `/Volumes/ExternalDisk`.

## Custodia

Se verificaron los 23 chunks de cada worldline contra `COMPLETE`, 92 chunks en total. Cada film
tiene 1.500.001 filas contiguas (`tick 0` a `tick 1.500.000`).

| unidad | SHA-256 manifest | SHA-256 COMPLETE |
|---|---|---|
| `s120_par129_t_k03_tau02` | `c045df3833f168603c5838e7b9f15f8874a2ace9a4f76b2fedc112768a53ca94` | `7438281b8aa3905d3c464e1b4270ffc48122a0b5b3bd99edf3bac82241ab268a` |
| `s120_par131_t_k03_tau02` | `16abffb5092d1c5c948fb6a0a80cf5c49456cb622351d438308dcd62fa644226` | `d7c79d058538708b7b4893bd484cde5e58e5e07dd911d01f27640346705d3865` |
| `s120_par132_t_k03_tau02` | `e38b50b36fc8a35c0f51c8df12976a3853eb0bbdf82016dbc70cb54eefbc217c` | `81c3fe6ed3af402e99dd0feff0496b9818e0df47355bcb9da8db680d6ceeb534` |
| `s120_par134_t_k03_tau02` | `bc4f22b95c9b022967635881ca4d49e7187f78cfb5fa0a9baa34412b1f9c322c` | `92510e00fb509234ed6a30aa8dd83a9ef7d1c1c980a934d501802bf1cdb98b3a` |

## Resultado 1 — el tiempo de arista está medido

Los cuatro manifiestos declaran:

```text
dt  = 0.00008 u.t.
tau = 0.2 u.t.
tau / dt = 2500 ticks
```

Para cada film se reconstruyó la fuerza de ambos nodos con la semántica real del recorder:

```text
drive[k] usa state[k-1] y state[k-1-2500]
```

Desde `drive[2501]` hasta el final hay 1.497.500 filas reconstruibles por film. Sobre los cuatro
films son 11.980.000 valores escalares de fuerza. Los 11.980.000 coinciden **bit-exacto** con el
registro: residuo máximo y RMS iguales a `0.0`.

Por tanto:

```text
T_edge = 2500 ticks = 0.2 u.t.
```

Esto confirma el transporte causal que implementa v1. No demuestra que `tau` cambie, que sea una
distancia evolutiva ni que atenúe amplitud: en estos films es un parámetro fijo.

## Resultado 2 — cruces de capa observables, pero no un tiempo interno único

Evento usado: cruce ascendente por cero, `y[k-1] < 0` y `y[k] >= 0`, sin interpolar. Cada cruce
de emisión del nodo 0 se desplaza 2500 ticks; desde esa llegada se toma el próximo cruce de la suma
de posiciones Q, S1 o S2 del nodo 1.

La tabla da la mediana de `cruce_capa - llegada` en ticks. `comp.` es la cantidad de llegadas que
terminan asignadas a un cruce ya usado por otra llegada: expone ciclos faltantes o asociaciones
múltiples. No se corrigen esos casos.

| unidad | período ref. mediano | Q: lag / comp. | S1: lag / comp. | S2: lag / comp. |
|---|---:|---:|---:|---:|
| par129 | 3186 | 859,5 / 45 | 2523 / 0 | 2400 / 1 |
| par131 | 3186 | 844 / 47 | 2433 / 0 | 2440 / 49 |
| par132 | 2347 | 739 / 151 | 824 / 29 | 1805 / 79 |
| par134 | 2348 | 651 / 17 | 506 / 1 | 1898 / 0 |

Estos valores no son constantes de propagación. La secuencia cruda muestra por qué:

- en par129, los primeros lags Q incluyen `221, 8133, 4448, 767, 8581` ticks y al final oscilan
  entre aproximadamente 400 y 1150 ticks;
- en par132, S2 sigue perdiendo o saltando ciclos al final: sus últimos períodos incluyen
  `1669, 4918, 4373, 1819, 4581, 4556` ticks mientras la referencia ronda 2180;
- en par134, S2 sí termina en correspondencia uno-a-uno: sus últimos períodos quedan entre 2159
  y 2197 ticks mientras la referencia queda entre 2176 y 2180; el lag final ronda 1800 ticks;
- S1 termina cerca de uno-a-uno en los cuatro films, pero con offsets distintos y deriva durante
  el chirp.

La observación útil es temporal y simple: algunas capas alcanzan una relación de ciclos estable y
otras pierden, duplican o relevan ciclos. Eso puede describir organización, pero el número
`próximo cruce - llegada` es un offset de una señal periódica dentro de un lazo cerrado. Puede
cambiar una vuelta completa sin que haya cambiado un transporte físico.

## Veredicto honesto

- **Tiempo de arista:** identificado y verificado bit-exacto, `2500 ticks`.
- **Tiempo interno del onion:** no identificado por estos films libres. La ley aplica la fuerza a
  todos los modos en el mismo subpaso; Q/S1/S2 no contienen una cascada de delays explícitos. Sus
  cruces posteriores mezclan fase, período propio, acople interno y realimentación.
- **Tiempo de lazo:** no identificado. Sin un evento etiquetado o una perturbación apareada no se
  puede decidir qué cruce de retorno pertenece a qué emisión.

El mínimo de un tick observado en algunos cruces no prueba una respuesta interna de un tick. Es
precisamente la señal de que el origen periódico es ambiguo. Para separar el tiempo interno haría
falta, más adelante y sólo si se decide abrir esa prueba, una perturbación temporal etiquetada y
su control apareado. No se implementó ni se autorizó esa campaña aquí.

Actualización posterior: se encontró en disco un control ON/OFF determinista ya existente y se
ejecutó esa comparación sin campaña nueva. Acota el onset interno a la primera fila guardada; ver
`audit/LINK_GRUMO_TAU_Y_ONSET_EXISTENTES.md`. La no-identificabilidad declarada arriba sigue
vigente específicamente para estos films libres y sus cruces periódicos.
