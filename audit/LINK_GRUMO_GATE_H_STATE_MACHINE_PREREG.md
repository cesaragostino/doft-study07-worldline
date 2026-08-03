# Gate H — preregistro de la máquina de estados del link

Fecha: 2026-08-02. Branch `research/link-grumo-dynamics`.

Este documento se escribe antes de ejecutar la máquina sobre los cuatro films de
600 u.t. No modifica `docs/bitacora`. Las entradas históricas permanecen en modo sólo
lectura y toda salida derivada debe quedar bajo `logs/link_grumo` de este worktree.

## 1. Corrección de alcance

Gate F/G mostró que ocupación y coherencia Q tempranas anticipan el outcome de fase a
60 u.t. El lector modal v2 y el film de 600 u.t. mostraron además que una línea puede
dominar y conservar fase mientras emisor y receptor se apagan juntos varias décadas.

Por eso una única escala `muerto < vivo` mezclaría dos preguntas diferentes:

1. **¿Existe ahora un canal identificable entre los onions?**
2. **¿Ese canal acompaña actividad sostenible o sólo copia una señal que desaparece?**

Gate H no fuerza un escalar de salud. Construye el producto de un estado de canal y un
estado de vitalidad. La política evolutiva podrá usar ambos sin perder la distinción.

## 2. Entradas permitidas

La máquina es causal: en tiempo `t` sólo usa observaciones con tiempo `<=t`.

### Canal

* línea del emisor válida y por encima del piso local;
* modo receptor no mudo;
* dominancia concordante en las dos familias ya selladas:
  `rho_stft > 1 AND rho_demod > 1`;
* zona de aproximación descriptiva:
  `rho_stft > 0.8 AND rho_demod > 0.8`.

La dominancia debe durar 2 u.t. antes de confirmar un canal. Un release sólo puede
ocurrir después de una captura confirmada. Un hueco de hasta 8 u.t. queda en gracia;
si otro modo entra antes del vencimiento, el link continúa. Un modo nuevo solapado con
el saliente es un relevo, no una muerte.

### Vitalidad

Se mantienen coordenadas separadas:

* amplitud del drive respecto de su máximo causal;
* amplitud de la línea recibida respecto de su máximo causal;
* pendiente logarítmica causal de la actividad recibida en 30 u.t.;
* cuando exista, signo de la potencia del link sobre emisor y receptor.

El piso relativo inicial es `1e-4`, heredado del lector largo. La banda descriptiva de
estacionariedad es `|d ln A/dt| <= 0.005`, heredada del guard de drive estacionario. No
se presentan como constantes físicas universales: la salida publicará las coordenadas
continuas junto al estado y deberá incluir sensibilidad antes de usarlas para selección.

## 3. Estados del canal

* `UNOBSERVABLE`: línea inválida, modo mudo o dato ausente. No equivale a release.
* `ABSENT`: nunca hubo canal confirmado y no hay aproximación.
* `APPROACH`: hay `rho>0.8` concordante o una captura todavía no confirmó 2 u.t.
* `DOMINANT`: al menos un modo confirma dominancia concordante durante 2 u.t.
* `GRACE`: terminó la dominancia confirmada, pero el hueco todavía no supera 8 u.t.
* `RELEASED`: el hueco superó 8 u.t. Un episodio posterior puede recapturar.

`capture`, `relay`, `recover`, `release` y `recapture` son eventos. No se convierten en
estados permanentes.

## 4. Estados de vitalidad

* `UNOBSERVABLE`: faltan amplitudes o la línea no es válida.
* `SOURCE_FADED`: el drive cayó por debajo de `1e-4` de su máximo causal.
* `RECEIVER_FADED`: la línea recibida cayó por debajo del mismo piso causal.
* `GROWING`, `SUSTAINED`, `DECAYING`: signo de la pendiente logarítmica recibida fuera
  o dentro de la banda `+-0.005`.

La potencia, cuando esté disponible, se etiqueta aparte como `INTO_RECEIVER`,
`OUT_OF_RECEIVER`, `BALANCED` o `UNKNOWN`. Una respuesta con `rho>1` y potencia positiva
puede seguir decayendo: ninguno reemplaza al otro.

## 5. Invariantes que debe custodiar el código

1. Fase Q, `R≈1`, S1, S2 y `b` no crean ni matan un canal.
2. No hay release sin captura previa.
3. Un dato no observable no se convierte en ausencia física.
4. Un hueco corto o un relevo modal no destruyen el link.
5. `DOMINANT + DECAYING/SOURCE_FADED` es un resultado válido: conectado no significa
   superviviente.
6. `b_S1` puede persistir después del release; es memoria, no estado vivo.
7. No existe muerte irreversible: `RELEASED -> DOMINANT` queda registrado como
   recaptura.

## 6. Primera evaluación sellada

Sin releer raws, se usarán:

* episodios citables `u=0.8/1.0` de `LECTURA_v2.json`;
* series pequeñas ya extraídas `jz_series_<par>.npz` para amplitudes y pendientes;
* los pares `129, 131, 132, 134`, elegidos antes de Gate H por la campaña larga.

Predicciones cualitativas anteriores a ejecutar:

* par132 y par134 deben terminar `RELEASED`, aunque `b_S1` conserve memoria;
* par129 y par131 pueden terminar `DOMINANT`, pero no deben llamarse sanos si la fuente
  o la actividad recibida están bajo piso o decayendo;
* la cicatriz modal de par134 no debe producir muerte de unidad mientras otro modo cubra
  el canal;
* par129 debe registrar al menos una recaptura real.

La evaluación es de consistencia sobre casos elegidos, no validación poblacional ni
ajuste de umbrales.
