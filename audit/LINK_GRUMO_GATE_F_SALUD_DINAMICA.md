# Gate F — salud como trayectoria de selección y consolidación

Fecha de cosecha: 2026-08-02. Frente paralelo `research/link-grumo-dynamics`.

Este documento es una auditoría separada. No modifica ni reemplaza `docs/bitacora` ni
los outcomes sellados del census. Las worldlines bajo `/Volumes/ExternalDisk` se usaron
en modo sólo lectura; las salidas derivadas quedaron bajo `logs/link_grumo`.

## 1. Pregunta y banco congelado

Gate E había dejado 8 `salud_60=True` dentro de su población elegible: films no-self,
resolubles en W8 y sin banderas de mudez/armónicos. Gate F0 tomó, sin optimizar por
outcome, el otro brazo del mismo par y semilla como control exacto.

El banco resultante tiene 8 pares y 16 films. Siete pares son discordantes en el outcome
Gate E. El octavo (`olaB_par008`) es sano en ambos brazos. Por eso el banco ampliado
contiene 9 films `salud_60=True`, no ocho. No es una contradicción: el transported de ese
par había quedado fuera de Gate E porque su detuning temprano en-film no era resoluble.

La selección es útil para mecanismo apareado, pero no es prospectiva: los targets fueron
descubiertos por el mismo outcome que se estudia.

## 2. Qué separa respuesta, selección y salud

La película móvil distingue tres cosas que antes quedaban mezcladas:

1. **Respuesta lineal compatible:** `R=(Q/F)/chi_Q` está cerca de uno. El receptor responde
   como predice su constitución fría.
2. **Selección/ocupación:** la línea conducida supera al competidor interno del receptor,
   `rho_pred>1` de forma sostenida.
3. **Consolidación:** una capa secundaria mantiene lock y el link conserva el canal hasta
   el horizonte.

Los conteos al final del film son:

| Señal persistente | films con señal | sanos Gate E entre ellos | sanos sin señal |
|---|---:|---:|---:|
| ocupación Q predicha | 10 | 9 | 0/6 |
| ocupación Q observada | 11 | 9 | 0/5 |
| `R≈1` con `chi` plana | 10 | 6 | 3/6 |
| ocupación + `R≈1` + `chi` plana | 6 | 6 | 3/10 |
| captura S1 | 10 | 9 | 0/6 |
| captura S2 | 8 | 7 | 2/8 |

El décimo caso con ocupación Q y S1 persistentes es `olaB_par013_t`: Gate E lo llama no
sano por el guard de frecuencia cruda, pero la auditoría de coordenadas de §5 muestra que
su link sigue dinámicamente trabado.

La conclusión compacta es negativa y positiva a la vez:

* `R≈1` **no es salud**. Cuatro controles fresh reproducen correctamente la respuesta
  lineal, pero la línea queda por debajo del competidor y el link no se forma.
* La ocupación persistente es la separación más simple de este banco: todos los sanos la
  tienen. No basta afirmar causalidad porque fue observada hasta el endpoint.
* S1 persistente acompaña exactamente al mismo conjunto de diez links dinámicos.
* S2 no es una ley universal: `olaB_par008_f` llega sano sin episodio S2 sostenido, y
  `olaB_par013_f` pierde S2 antes del final y aun así llega sano.

Por tanto, “release S2 mata el link” queda negado como regla general en este banco. S2
puede ser una vía de consolidación, no el único soporte posible.

## 3. Dos rutas dinámicas, no una fórmula mágica

La clasificación descriptiva —formulada después de ver el banco— produce cinco grupos:

| Ruta | n | sanos Gate E | lectura física |
|---|---:|---:|---|
| `linear_selected` | 6 | 6 | canal Q ocupa, `R≈1`, banda `chi` plana |
| `selected_nonflat_or_nonlinear` | 4 | 3 | ocupa y consolida S1, pero la aproximación puntual fría no cierra |
| `passive_linear_response_below_selection` | 4 | 0 | responde bien al drive, sin desplazar al competidor |
| `observed_cross_response_without_cold_selection` | 1 | 0 | respuesta cruzada grande, no explicada por selección fría |
| `no_persistent_selected_channel` | 1 | 0 | no queda canal seleccionado |

Los seis `linear_selected` son precisamente los seis targets transported resolubles. Sus
controles exactos tienen cuatro respuestas pasivas lineales, una respuesta cruzada no
seleccionada y un caso sin canal. Esto explica por qué la susceptibilidad sola no separaba
salud: lo que cambia con la biografía no es necesariamente el receptor estático, sino la
capacidad de la trayectoria para hacer que una línea **ocupe** el receptor.

Los cuatro links de la segunda ruta son los pares cercanos `olaB_par008/013` en ambos
brazos. Allí `chi` no es plana en W8 y el modelo frío puntual deja de ser el lenguaje
adecuado. Tres pasan Gate E; el cuarto es el borde de coordenadas de §5.

En el lenguaje de dinámica física conocida, sin imponerlo como autoridad:

* la respuesta pasiva bajo selección se parece a un oscilador forzado que muestra la
  frecuencia del drive sin estar entrained;
* la ruta lineal seleccionada se parece a captura en una banda de sincronización: gana
  amplitud relativa y fija el desfase compatible con la respuesta del receptor;
* la ruta no plana se parece a captura cerca de una resonancia móvil/no lineal, donde un
  único valor frío de `chi(omega)` no representa el estado vestido.

El patrón útil no es el nombre de la teoría: es la separación empírica entre **responder**,
**seleccionar una línea** y **mantenerla**.

## 4. Orden de los cambios en la ruta transported

En los seis targets transported, el canal conjunto Q (`rho_pred>1`, `R≈1`, `chi` plana)
aparece antes que S2 con separación inequívoca en 3/6 films; en los otros 3/6 sus soportes
temporales se solapan. No hay ningún film donde S2 sea inequívocamente anterior al canal
Q. La mediana de tiempos de confirmación es:

`t_S2 - t_Qjoint = +8.5 u.t.`

S2 queda inequívocamente antes del cierre primario en 2/6 y solapado en 4/6; tampoco hay
un orden inverso inequívoco. La mediana es:

`t_S2 - t_primary = -5.5 u.t.`

La secuencia compatible con todos los films es entonces:

`selección/captura Q -> consolidación secundaria -> lock primario visible`

Las ventanas impiden fechar cada transición como un punto. Por eso se publican inicio de
soporte y fin de confirmación, y sólo se llama “anterior inequívoco” cuando la confirmación
de un evento termina antes de que empiece el soporte del siguiente.

Esto refina, sin borrar, el hallazgo retrospectivo C1: S2 sí tiende a preceder la forma
primaria, pero no parece ser el primer cambio del link. El canal Q ya comenzó a
seleccionarse antes.

## 5. Auditoría del outcome salud60: dos coordenadas mezcladas

Gate E define firmeza con coherencia de fase **corregida**, pero usa como guard de falso
firme `dw` estimado en `theta` **cruda**. En onions chirpeantes/cercanos esas coordenadas
no son intercambiables en una ventana finita.

Gate F3 mantuvo el mismo `rw`, horizonte, W8 y corte `1.1/W=0.1375`, pero midió la deriva
como pendiente de la propia diferencia de fase corregida en `[50,60]`. Es una sensibilidad
post hoc; no reemplaza a Gate E.

Resultados sobre 340 films no-self:

| Outcome | total | transported | fresh |
|---|---:|---:|---:|
| salud con `dw` cruda | 53 | 44 | 9 |
| salud con deriva corregida | 71 | 59 | 12 |

Hay 18 flips, todos `raw=False -> corrected=True`; ninguno en sentido contrario. Los 71
films con `rw>=0.95` pasan también el guard de deriva cuando se evalúa en la fase
corregida. En los 170 pares exactos, el contraste medio transported-fresh pasa de +0.206
a +0.276. El guard crudo estaba descartando preferentemente links transported coherentes.

La conclusión anterior de Gate E sobre el estrato remoto es robusta: entre sus 164 films
elegibles sólo cambia un caso (8 a 9 positivos) y el AUC de `rho_pred` cambia de 0.944 a
0.941. El problema se concentra en links cercanos/no resolubles y chirpeantes.

`olaB_par013_t` es un ejemplo, no una excepción solitaria: `rw=0.9956`, `dw_cruda=0.1515`
y pendiente corregida `0.0359`. S1/S2 y ocupación sobreviven hasta el final. Llamarlo
“muerto” físicamente por exceder apenas el corte en otra coordenada no está justificado.

Para el próximo outcome prospectivo conviene sellar antes de correr:

* coherencia, deriva y releases medidos sobre una misma fase;
* señal no muda;
* persistencia o recurrencia hasta una ventana futura;
* el outcome crudo conservado como sensibilidad, no mezclado dentro de la regla principal.

## 6. Qué significa hoy “salud” para el modelo evolutivo

Los datos no justifican un escalar constitucional que decida todo. Sí justifican una
máquina de estados pequeña:

`canal elegible -> línea seleccionada -> consolidación secundaria -> persistencia`

En la ruta remota lineal, `rho_pred` y `R` permiten observar los dos primeros estados. En
la ruta cercana/no plana, S1 y la coherencia corregida muestran consolidación aunque la
respuesta fría puntual falle. S2 es frecuente y ordena la maduración transported, pero no
es necesaria en todos los links.

Como candidato exploratorio, no como ley, este banco sugiere:

`link dinámicamente vivo a 60 = ocupación Q persistente + algún soporte secundario persistente`

Aquí S1 es el soporte común; en C1 S2 había sido el predictor parcial más fuerte. Esa
diferencia impide hardcodear el nombre de una capa. La hipótesis general más económica es
“al menos un canal secundario consolida la línea seleccionada”, y la identidad S1/S2 puede
depender del onion, de la biografía o de la ruta de captura.

Para grumos, esto sugiere que una arista no debe existir por una coincidencia instantánea
de frecuencias. Debe ganar ocupación, consolidar algún canal secundario y no mostrar slips
o releases no recuperados dentro del horizonte de evaluación.

## 7. Próxima prueba barata y decisiva

Antes de una cirugía causal, la prueba de mejor relación física/CPU es prospectiva y
temporal sobre un holdout:

1. sellar salud en fase corregida y una ventana futura común;
2. medir en `[0,20]` ocupación Q, `R`, S1 y S2;
3. predecir persistencia/release en `[40,60]`, sin reutilizar el endpoint en el predictor;
4. estratificar desde el inicio entre banda `chi` plana y no plana;
5. publicar por separado las rutas remote-linear y close/nonlinear.

El banco actual ya muestra por qué ningún marcador aislado alcanza: `R` sin ocupación es
respuesta pasiva; S2 puede faltar o liberarse sin muerte; y el lock primario visible llega
después del cambio que seleccionó el canal.

## 8. Límites

* Banco Gate F elegido por positivos; conteos descriptivos, sin p inferencial.
* `candidate_dynamic_link` y la pendiente OLS corregida son hipótesis post hoc.
* W4/W8 acotan eventos por intervalos, no por instantes causales.
* No hubo intervención selectiva sobre S1/S2; su papel causal sigue abierto.
* `chi` fría v1 descarta kernels internos diferidos y no representa bandas no planas.
* Sesenta unidades de tiempo no prueban supervivencia asintótica.

## 9. Reproducción

```bash
PYTHONPATH=src:tools/link_grumo python3 tools/link_grumo/gate_f_select_bank.py \
  --gate-e logs/link_grumo/gate_e_fixed_horizon.json \
  --tables-root /Users/cagostino/code/doft-study07-worldline/data/census_arnold \
  --worldlines-root /Volumes/ExternalDisk/study07_census_arnold \
  --output logs/link_grumo/gate_f_bank.json

PYTHONPATH=src:tools/link_grumo python3 tools/link_grumo/gate_f_timeline.py \
  --bank logs/link_grumo/gate_f_bank.json \
  --blocks /Users/cagostino/code/doft-study06-fundamental-lock-dynamics/data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json \
  --output logs/link_grumo/gate_f_timeline.json

PYTHONPATH=src:tools/link_grumo python3 tools/link_grumo/gate_f_evaluate.py \
  --timeline logs/link_grumo/gate_f_timeline.json \
  --output logs/link_grumo/gate_f_evaluate.json

PYTHONPATH=src:tools/link_grumo python3 tools/link_grumo/gate_f_health_coordinates.py \
  --tables-root /Users/cagostino/code/doft-study07-worldline/data/census_arnold \
  --gate-e logs/link_grumo/gate_e_fixed_horizon.json \
  --output logs/link_grumo/gate_f_health_coordinates.json
```
