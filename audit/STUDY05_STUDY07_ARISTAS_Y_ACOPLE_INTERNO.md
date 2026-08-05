# Auditoría de linaje Study05 → Study07: aristas, selección y acople interno

Fecha: 2026-08-04  
Estado: **AUDITORÍA DE CÓDIGO Y DATOS; NO MODIFICA LA FÍSICA**

## Pregunta

Esta auditoría registra de dónde partió la formación de estructuras en Study05, qué cambió
realmente en Study07 y qué problema queda abierto en la propagación de una fuerza de arista
dentro de un onion multimodal.

La pregunta central no es si el motor puede producir coherencia. Es más exigente:

> ¿La ley implementada permite que los links nazcan, compitan y afecten los grados internos
> que físicamente participan del enlace, o la topología y el canal de entrada ya vienen impuestos?

## Veredicto corto

1. **Study05 no hacía emerger aristas.** Elegía una topología completa de un catálogo de
   templates, sorteaba sus nodos y evaluaba el objeto entero. Las aristas existían desde el
   inicio y no nacían, morían ni competían durante la trayectoria.
2. **La selección de Study05 era selección de propuestas completas, no supervivencia interna de
   links.** El explorer filtraba grafos por observables globales. No había un outcome causal por
   arista.
3. **El sweep diferencial de Ola2 de Study05 no ejerció el acople inter-onion que pretendía
   validar.** Los artefactos entregaron `kappa_global`, pero el motor leyó `K_global` y usó el
   default `0.0`. Las 1.292 evaluaciones guardadas tienen la primera clave y ninguna tiene la
   segunda.
4. **La recursión de Study05 tampoco transportó el grumo como sistema dinámico completo.** La
   promoción conservó la red en `theta_internal_network`, pero expuso como `theta_internal` sólo
   el onion del nodo 0. La hidratación de la ola siguiente consume ese `theta_internal` singular.
5. **Study07 corrige una parte importante:** integra onions completos, conserva su estado y
   biografía, y aplica un Kelvin–Voigt retardado por arista. Sin embargo, hoy cada arista emite y
   recibe a través de una única coordenada escalar agregada por onion.
6. **El problema crítico de Study07 está en la interfaz onion–arista:** la fuerza KV no decide
   cómo se acopla al interior. El motor actual suma la misma fuerza generalizada a todos los
   modos. El onion responde de forma desigual después, pero el link entra sin identidad de capa,
   banda secundaria o modo.

Por tanto, Study07 tiene una propagación temporal de arista mucho más fiel que Study05, pero aún
no tiene una física de nacimiento de links ni una coordenada interna de conexión identificada.

## Custodia y alcance de la revisión

Repositorios inspeccionados:

- Study05: `doft-study05-internal-string-layers-below-quark`, commit
  `554100c88b38d7f67b1fd3a65fa23769db3e7234` (`paper done`), coincidente con
  `origin/main` al momento de la lectura;
- Study07: `doft-study07-worldline`, commit base de esta auditoría
  `710c68c779bedc13edc2473f2ad676445a84af35`.

El worktree de Study05 contenía un directorio **untracked** `migrate/`. No se modificó y fue
excluido como fuente de verdad: todas las referencias de esta auditoría pertenecen a archivos
versionados fuera de ese directorio. No se tocó código, bitácora ni dato crudo en ninguno de los
dos repositorios.

Esta es una auditoría retrospectiva del comportamiento implementado. No prueba que una
alternativa sea la ley física correcta y no convierte indicadores de lock en mecanismos.

## 1. Qué eran las aristas en Study05

### 1.1 La topología era una condición inicial completa

El explorer elegía aleatoriamente un target, un template y una muestra de bloques. La función
`build_plan()` copiaba y canonicalizaba las aristas declaradas por el template antes de ejecutar
la evaluación.

La campaña Ola2 paper ofrecía ocho templates cerrados:

- anillos de 2, 3, 4 y 5 nodos;
- grafos completos de 4 y 5 nodos;
- `ladder_2`;
- `bipartite_2_2`.

No existía un estado dinámico de arista, un evento de nacimiento o release, ni una búsqueda
dentro de la trayectoria. El sorteo decidía qué onions ocupaban los nodos de una forma ya
conectada.

Fuentes de código Study05:

- `src/olar/explorer_search.py`: selección de template, bloques y canonicalización del plan;
- `data/config/ola2_paper/ola2_templates.json`: topologías completas permitidas;
- `src/olar/explorer_cli.py`: creación de attempts y entities con las aristas ya declaradas.

### 1.2 El explorer barato no simulaba el onion completo

El primer filtro usaba un Kuramoto reducido. Cada bloque aportaba un solo `omega_ref`; las fases
se acoplaban mediante la adyacencia normalizada por grado y mediante un campo medio complejo
`Z`. Los observables `R_mean_lastW`, varianza de fase, `QualityLock` y `memory_score_k10`
clasificaban el grafo completo.

En Ola2 paper se registraron:

```text
attempts                         5000
attempts marcados candidate       324
entities candidatas únicas        323
tasa de attempts candidate      6.48%
```

Esto demuestra que el explorador barato distinguió propuestas bajo **su** dinámica reducida.
No demuestra que los onions completos formaran esos links.

Fuente: `src/olar/explorer_engine.py` y
`data/processed/ola2_paper/explorer_report.md`.

### 1.3 El sweep diferencial de Ola2 tuvo acople inter-onion cero

El motor diferencial pretendía aplicar sobre la fase S1:

```text
F_inter,i = K_global / grado(i) · Σ_j sin(theta_S1,j(t−tau) − theta_S1,i(t))
```

Pero las dos puntas del contrato no usaron el mismo nombre:

- `resolve_engine_params()` y los artefactos escribieron `kappa_global`;
- `DifferentialNetwork.__init__()` leyó `K_global` con default `0.0`.

Lectura exhaustiva de
`data/processed/ola2_paper/sweep_merged/evaluations.jsonl`:

```text
evaluaciones                     1292  (= 323 entities × 4 seeds)
con engine_params.kappa_global   1292
con engine_params.K_global          0
sweep_passed                     1292
```

Los SHA-256 de los artefactos leídos son:

```text
attempts.jsonl              73201a04a841868ac3b822000239ce9dd6adb8d199cfda8455ef572c03574c3c
entities_candidates.jsonl   d415c9349f2a259fbdc75fcb813c94460fc96ca1f4c19728d94299bb7b86bff6
evaluations.jsonl           8af81221c0ed76fc63ce8e50876499b27c47cd80b81f76e5055a0154241f6fc7
paper_metrics_summary.json  539bf024126e1a768acf7995e179ca941bfd144721573f84b460011fb4e9e1b0
```

Se ejecutó además un control local, sin modificar fuentes, sobre la primera evaluación guardada:

```text
entity_id  8f88f4bf43a906c625f74942c00d8197b64c0b1748563b8ff94c192f6f34c689
eval_id    ffaa1c0a94cf568a05b5b9c07a6ff50925e703ded5c537106b24c24893446859
seed       962370196
nodos      2
aristas    1
kappa_global entregado  0.30000000000000004
K_global entregado      ausente
k_global usado          0.0
```

Se instanció el mismo sistema una vez con su arista y otra sin aristas. Durante 10 ticks, todas
las salidas de `step()` y todos los campos `x/v/z/b/e` fueron bit-exactos, con diferencia máxima
`0.0`. Esta prueba corta no es una estimación estadística: confirma la consecuencia determinista
del `k_global=0.0` en un caso real.

### 1.4 `sweep_passed` no era supervivencia

En `src/olar/sweep.py`, `sweep_passed` se asignaba a `is_finite_primary`: significaba que las
métricas primarias eran finitas. No verificaba persistencia, transmisión, potencia ni existencia
de cada arista.

El resumen paper reporta 323/323 entities de Ola2 evaluadas, 323/323 con sweep técnicamente
válido y 323 promovidas. Ese resultado no puede citarse como validación física de links: el
acople diferencial estaba apagado y el criterio `sweep_passed` era sanidad numérica.

### 1.5 La red promovida no viajó como dinámica recursiva

`src/core/promotion/blocks_from_ola.py` construía correctamente un objeto
`theta_internal_network` con nodos, aristas, asignación y procedencia. Sin embargo, el mismo
bloque promovido guardaba:

```text
theta_internal = theta_internal del nodo 0
```

La hidratación del siguiente sweep (`src/olar/hydration.py`) vuelve a leer
`block["theta_internal"]`; no consume `theta_internal_network` como nuevo sistema interno. Por
eso la red completa sobrevivía como catálogo y linaje, pero el onion del nodo 0 actuaba como su
representante físico en la ola siguiente.

Los conteos publicados muestran un estrechamiento del catálogo:

| ola | propuestas/attempts declarados | sweep técnico | promovidos |
|---|---:|---:|---:|
| 2 | 5.000 attempts; 323 entities | 323 | 323 |
| 3 | 3.000 | 402 | 118 |
| 4 | 1.000 | 462 | 7 |

Pero eso es selección externa entre representaciones. No es todavía una simulación continua
en la que el grumo completo participa como unidad dinámica y sus aristas sobreviven o se rompen.

## 2. Qué cambió en Study07

Study07 no usa la fase S1 como estado sustituto del onion conectado. Cada nodo conserva el estado
completo:

```text
X_i = (x_i[n], v_i[n], z_i[nz], b_i[nl], e_i[nl])
```

El link de red usa una ley Kelvin–Voigt retardada y cada arista puede declarar pesos y `tau`. El
checkpoint conserva estados, historia retardada, RNG, parámetros y topología. Por eso un link
puede alterar la energía, la memoria, `b`, el chirp y la biografía futura del onion sin
reconstruirlos desde un proxy.

Esas son diferencias sustantivas respecto de Study05. No deben confundirse, sin embargo, con
capacidades que Study07 todavía no posee:

- la topología se declara antes de correr;
- las aristas están activas desde `t=0`;
- `tau` es fijo durante cada film;
- no existe estado causal de nacimiento, ocupación, competencia o muerte de una arista;
- no existe todavía un grumo promovido que emerja y pase automáticamente a la ola siguiente.

Fuentes Study07: `src/study07/engine/network.py`, `src/study07/physics/coupling.py`,
`src/study07/physics/rhs.py`, `specs/PHYSICS_CONTRACT.md` y
`specs/CHECKPOINT_SCHEMA.md`.

## 3. Problema importante de Study07: KV no distribuye el link dentro del onion

### 3.1 Lo que el motor hace exactamente

Para cada onion se construye una coordenada emitida de dos componentes:

```text
x_emit,i = emission_scale_i · Σ_p x_i,p
v_emit,i = emission_scale_i · Σ_p v_i,p
```

La arista retarda esas sumas y la red calcula una fuerza escalar por nodo:

```text
F_i(t) = k · promedio_ponderado[x_emit,j(t−tau_e) − x_emit,i(t)]
       + g · promedio_ponderado[v_emit,j(t−tau_e) − v_emit,i(t)]
```

Finalmente, el RHS aplica:

```text
dv_i,p += F_i / mass_i,p     para todo modo p
```

La formulación compacta es:

\[
\dot{\mathbf v}_i \;{+}{=}\;
M_i^{-1}\,\mathbf 1\,F_i.
\]

El vector de entrada actual es, por construcción, `1 = (1,1,...,1)`.

### 3.2 Misma fuerza no significa misma trayectoria

No es correcto decir que todos los modos terminan afectados por igual:

- la aceleración directa cambia con `1/mass_p`;
- cada modo tiene distinta frecuencia y fricción;
- los resortes intra-capa e inter-capa redistribuyen la perturbación;
- memoria, energía, `e` y `b` cambian de acuerdo con el estado de cada capa.

Por eso el onion puede seleccionar, amplificar, suprimir o transferir internamente partes del
drive. Una resonancia interna real sigue siendo posible.

Pero esa selectividad ocurre **después de la entrada**. La ley KV produce `F_i`; no contiene una
regla que determine a qué capa o modo está unido el extremo de la arista. La implementación
actual resolvió esa pregunta imponiendo una fuerza uniforme sobre todos los modos.

### 3.3 Información que se pierde antes de entrar

La interfaz actual hace dos reducciones independientes:

1. **Emisión:** Q, S1 y S2 se colapsan a `sum(x)` y `sum(v)`. La arista no conoce qué banda
   emitió una contribución. Modos en contrafase pueden cancelarse en la suma.
2. **Recepción:** el escalar resultante se inyecta en todos los modos. La arista no conserva un
   extremo interno particular ni una proyección modal.

Además, cuando un nodo tiene varias aristas, `kv_force()` suma sus contribuciones y divide por la
suma de pesos incidente. El onion recibe una **media nodal** por los canales elástico y viscoso,
no fuerzas internas separadas por arista. Los `tau_e` siguen siendo individuales durante el
cálculo, pero sus llegadas terminan mezcladas en el mismo `F_i` antes de entrar al RHS.

Esto tiene consecuencias directas:

- dos aristas incidentes no ocupan ni compiten por grados internos distinguibles;
- un lock secundario observado no puede identificarse con el endpoint que transportó la fuerza;
- un cambio simultáneo de Q/S1/S2 puede provenir de la inyección uniforme y no de una cascada
  física entre capas;
- la respuesta diferencial de las capas demuestra susceptibilidad interna, pero no valida la
  geometría de entrada;
- los films generados con esta ley no contienen información suficiente para inferir
  retrospectivamente cuál habría sido el endpoint físico correcto.

La medición ON/OFF ya registrada en `audit/LINK_GRUMO_TAU_Y_ONSET_EXISTENTES.md` es coherente
con esta lectura: Q, S1 y S2 empiezan a diferir dentro del primer tick observable. Eso verifica
la implementación uniforme; no descubre un transporte interno resuelto por capa.

### 3.4 Qué parte de KV sigue siendo válida

Esta auditoría **no refuta Kelvin–Voigt** como ley constitutiva de una arista. KV puede seguir
siendo una descripción razonable de la fuerza producida por desplazamiento y velocidad relativos,
incluido su retardo.

Lo no validado es el mapa entre esa fuerza y los grados internos del onion. En forma general, una
interfaz que conserve endpoints necesitaría distinguir:

\[
y_{i,e}=\mathbf C_{i,e}^{\mathsf T}\mathbf x_i,
\qquad
\dot{\mathbf v}_i\;{+}{=}\;M_i^{-1}\mathbf B_{i,e}F_e.
\]

- `C_i,e` expresa qué coordenada del onion emite por la arista `e`;
- `B_i,e` expresa sobre qué coordenada actúa la fuerza recibida.

Esta escritura **no es una propuesta de ley final** ni autoriza inventar `B/C`. Sólo exhibe el
grado de libertad que el vector uniforme actual fijó silenciosamente. Si el link nace de locks
secundarios, asignar `B/C` mediante un detector externo de esos locks repetiría el problema del
árbitro de salud: el instrumento fabricaría la arista que luego pretende explicar.

El mecanismo tendría que surgir de la propia dinámica o de una coordenada física ya presente en
el onion. Los datos actuales pueden servir luego para rechazar o comparar una implementación,
pero no identifican por sí solos ese mapa porque fueron generados con entrada uniforme.

## 4. Comparación operativa

| propiedad | Study05 | Study07 vigente |
|---|---|---|
| nacimiento de arista | no; template previo | no; topología previa |
| muerte/release de arista | no | no como estado de arista |
| objeto inter-onion | fase S1 en sweep; fase reducida en explorer | suma de `x/v` de todos los modos |
| ley de red | seno de diferencia de fase, normalizado por grado | Kelvin–Voigt retardado, media ponderada |
| destino interno | `drive_s1` | misma fuerza sobre todos los modos, dividida por masa |
| retardo | global `tau_field` | `tau` por arista, fijo durante el film |
| onion conectado | estado interno completo en sweep | estado completo `x/v/z/b/e` |
| validación Ola2 publicada | acople diferencial apagado por mismatch | fixtures y reconstrucción bit-exacta del KV |
| selección | filtro externo del grafo completo | M1/M2 son contratos experimentales; explorer aún borrador |
| herencia del grumo | red guardada como metadata; física heredada desde nodo 0 | checkpoint completo, pero sin promoción evolutiva resuelta |
| identidad interna por arista | no | no |

## 5. Consecuencia para el norte del modelo

Study05 sirve como antecedente de infraestructura: templates, muestreo, canonicalización,
identidades, sharding, catálogo y promoción documental. No sirve como evidencia de que los
grumos hayan emergido físicamente por supervivencia de aristas.

Study07 preserva por primera vez una realimentación retardada sobre la biografía completa del
onion. Pero el enunciado correcto hoy es limitado:

> Una arista declarada transmite una fuerza KV retardada entre coordenadas agregadas de dos
> onions; cada onion filtra internamente esa fuerza según su constitución y estado.

Todavía no puede afirmarse:

> Una banda secundaria concreta forma una arista, ocupa un canal interno, compite con otras
> aristas y sobrevive como parte de un grumo emergente.

Antes de correr un todos-contra-todos o construir una regla de salud, falta decidir físicamente
qué constituye el extremo interno de una arista y cómo puede aparecer sin un clasificador
externo. Cambiar sólo el scheduler, `tau`, los pesos o el detector no corrige la pérdida de
identidad modal en la interfaz actual.

## 6. Límites y deuda explícita

- No se ejecutó una nueva campaña y no se modificó ningún resultado histórico.
- El control bit-exacto de Study05 cubrió un caso real durante 10 ticks. La inspección de claves
  sí cubrió las 1.292 evaluaciones Ola2 paper.
- No se auditó aquí cada rama legacy de Study05; la afirmación se limita al pipeline paper
  versionado en el commit declarado.
- Los conteos Ola3/Ola4 describen el pipeline y no rehabilitan el acople diferencial de Ola2.
- Que el input uniforme sea insuficiente para la interpretación buscada no prueba cuál es el
  input correcto.
- No se propone reintroducir el detector de lock como árbitro. Ese frente quedó cerrado como
  inconcluso en `docs/research/link_grumo/README.md`.
- `M2` en campos históricos de Study05 puede ser una magnitud derivada; `M2` en
  `specs/EXPERIMENT_CONTRACT.md` de Study07 es un tipo formal de campaña. No deben confundirse.

## 7. Enmienda conceptual posterior: dos onions completos, piel contra piel

**Estado:** corrección del norte de diseño posterior a la auditoría y a la cosecha de trending.
No altera los resultados medidos ni rehabilita los films como evidencia de una física que no
simularon. Sí reemplaza como dirección de implementación cualquier lectura de la sección 3.4
que convierta `B/C`, un puerto o una arista en una nueva pieza física independiente.

### 7.1 La unidad física y numérica es el onion completo

El onion no se parte en un oscilador portador, un conjunto de puertos y un objeto link que luego
se vuelven a ensamblar. En cada `dt` se integra el estado diferencial completo:

\[
X_i=(x_i,v_i,z_i,b_i,e_i,\ldots),
\qquad
\dot X_i=F_i(X_i)+\sum_j\epsilon_{ij}\,
\mathcal I^{(S)}_{ij}\!\left(X_i(t),X_j(t-\tau_{ij})\right).
\]

La notación \(\mathcal I^{(S)}\) sólo reserva el lugar donde la interacción piel contra piel
entra por las dinámicas resonantes secundarias **ya contenidas** en los dos estados completos.
No define un detector, una proyección modal elegida desde afuera ni una ecuación autónoma de la
arista. La ecuación recíproca de \(j\) se integra en el mismo paso y la respuesta se propaga al
resto de cada onion mediante sus propios acoples diferenciales internos.

Por lo tanto:

- las resonancias secundarias no son piezas separables del onion ni puertos discretos que un
  árbitro asigna;
- el link no agrega una «dinámica del link», una salud, una memoria o un oscilador nuevo;
- el link es la relación persistente que emerge entre las trayectorias completas cuando sus
  dinámicas secundarias se capturan, se arrastran, se relevan o se liberan;
- la interacción no debe reducirse a una fuerza escalar agregada aplicada por igual a todos los
  modos. Que el onion completo responda no significa que todos sus grados reciban el mismo
  término externo.

El problema de implementación pendiente no es decidir qué fracción del onion simular, sino
transcribir desde las coordenadas secundarias que el motor ya posee el término local de
interacción \(\mathcal I^{(S)}\), sin duplicar dinámica interna ni inventar un proxy que la
reemplace.

### 7.2 El tamaño inmediato de un término no decide su existencia

Se retira explícitamente el criterio «primero probar si el término basta». La pregunta física es
si el término representa el mecanismo postulado. Si lo representa, se integra en su `dt` nativo
aunque su efecto instantáneo sea \(10^{-8}\), cero dentro de la resolución de un film corto o
pequeño frente a otro término.

En un sistema evolutivo, una perturbación diminuta puede cambiar el tiempo de captura, el orden
de encuentros, una competencia posterior o la biografía transmitida a otra ola. Su relevancia no
puede decidirse sólo por amplitud inmediata, AUC, significación estadística o capacidad de
clasificar supervivientes. Esas medidas sirven para observar y comparar trayectorias; no para
borrar términos físicos de la ecuación.

Esto tampoco declara que toda fórmula candidata sea correcta. Exige una correspondencia física
con el estado diferencial existente y resultados prospectivos que permitan refutarla. Lo que se
elimina es el salto lógico desde «el efecto medido es pequeño» hacia «el mecanismo no importa».

### 7.3 Locks, lenguas y reducciones son lecturas, no árbitros del motor

Los \(L_{p:q}\), la coherencia de fase, las lenguas de Arnold y las reducciones tipo Adler pueden
describir desde afuera lo ocurrido en las trayectorias integradas. Son instrumentos valiosos para
detectar captura, pulling, relevo y release. No deben:

- crear o apagar interacciones dentro del RHS;
- seleccionar de antemano qué banda puede tocar a cuál;
- convertir un umbral de observación en una ley de formación;
- sustituir la integración completa por una dinámica reducida porque reproduzca una métrica.

Una reducción puede explicar después una región del comportamiento. No adquiere por eso derecho
a reemplazar la física generadora, y tampoco queda descartada porque explique sólo una fracción
minúscula de la evolución.

### 7.4 El grafo inicial fuerza encuentros; el grafo formado es un resultado

Para iniciar una corrida hace falta declarar qué pares entran en contacto o tienen oportunidad de
interactuar. Ese grafo inicial es una condición experimental forzada: no presupone que sus links
estén formados, sanos ni destinados a sobrevivir. No debe existir un filtro previo de «links sin
oportunidad» basado en films históricos.

A partir de esos encuentros, son resultados de la integración:

- cuántas capturas aparecen;
- qué razones secundarias participan;
- cuánto persisten, fluctúan o se liberan;
- qué competencia introduce la biografía acumulada;
- qué distribución de enlaces y qué grumos quedan al final de una ola y entre olas.

En consecuencia, no se fija como input la distribución de enlaces que se intenta explicar. Se
fija una condición inicial reproducible de encuentros y se mide la población que la dinámica
forma. Si más adelante el pasado sesga nuevos encuentros, ese sesgo debe provenir del estado y la
historia efectivamente integrados, no de un clasificador externo de salud.

### 7.5 Lugar del Kelvin–Voigt vigente

El KV retardado actual puede conservar valor como control histórico y como ley de un enlace
macroscópico **ya constituido**. No representa por sí mismo la formación piel contra piel buscada:

1. calcula una señal desde sumas globales de posición y velocidad;
2. presupone una arista ya presente;
3. devuelve una fuerza escalar a todos los modos;
4. pierde la identidad de las resonancias secundarias cuyo lock debería emerger.

El problema no es que KV sea una fórmula en vez de una ecuación diferencial. El problema es que
resume y aplica de antemano una relación macroscópica que aquí debería nacer de la integración de
los dos onions completos. Por eso los `B/C` de la sección 3.4 sólo deben leerse como una forma de
exhibir cuánta información borra la interfaz uniforme, no como arquitectura recomendada.

### 7.6 Qué permiten decir los gráficos actuales

El trending a `dt` completo conserva un resultado útil: los enlaces impuestos por KV no son
constantes; sus potencias, fases, episodios de lock y rutas energéticas fluctúan, se relevan y a
veces convergen. El panel P2 es especialmente claro como trayectoria energética del motor
vigente. Eso es un dato real de esos films.

La abundancia de ruido y phase slips es **compatible** con una entrada KV global que mezcla las
capas y las fuerza uniformemente, pero estos mismos films no pueden demostrar que ésa sea toda la
causa. Fueron producidos por ese mecanismo y no contienen el contrafactual con interacción
secundaria local. P2 queda entonces como baseline exigente, no como validación de la física del
link.

La expectativa de que una interacción secundaria correctamente integrada converja en menos u.t.
es una **predicción prospectiva**, no un hallazgo que pueda atribuirse retroactivamente. Tendrá
valor cuando dos corridas apareadas —KV histórico y mecanismo secundario— partan de los mismos
onions, encuentros, semilla y horizonte, y se comparen sin cambiar el instrumento de lectura.

### 7.7 Contrato conceptual para el próximo diseño

Un diseño futuro sólo será consistente con esta enmienda si cumple simultáneamente:

1. integra el RHS completo de cada onion en cada `dt`;
2. introduce la interacción a través de variables secundarias físicas ya existentes;
3. deja que los acoples internos del propio onion propaguen esa perturbación;
4. no crea estado, memoria, salud ni árbitro independiente para la arista;
5. no usa el detector de lock para decidir qué ecuación ejecutar;
6. conserva términos físicamente justificados aunque sean pequeños en una campaña corta;
7. fuerza sólo las oportunidades iniciales de encuentro y trata la formación como outcome;
8. registra locks, fase, potencia y tiempos como observables, no como sustitutos del motor.

Queda abierta una sola cuestión de diseño físico antes de tocar el motor: identificar en las
ecuaciones vigentes la forma exacta de \(\mathcal I^{(S)}\) que acopla dos superficies secundarias
sin sumar globalmente los modos, sin reinjectar dinámica que ya propaga el onion y sin crear una
ontología adicional. Mientras eso no esté escrito y auditado, implementar un nuevo KV, un puerto
o un árbitro sólo cambiaría de proxy.
