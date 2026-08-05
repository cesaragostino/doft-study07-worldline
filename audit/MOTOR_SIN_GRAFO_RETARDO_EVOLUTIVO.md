# Contrato conceptual v0 — motor sin grafo y retardo evolutivo

Fecha: 2026-08-05

Estado: **DIRECCIÓN DE DISEÑO; SIN IMPLEMENTACIÓN Y SIN RESULTADOS NUEVOS**

## 0. Propósito y custodia

Este documento fija una dirección para rehacer el acople entre onions sin programar de
antemano las aristas que el modelo debe explicar. No es una ley física cerrada, no modifica el
motor `v1`, no reinterpreta los films históricos y no convierte los instrumentos de lock en
ecuaciones de evolución.

El norte es más limitado y más exigente:

> Integrar onions completos que pueden influirse inicialmente todos con todos mediante sus
> coordenadas resonantes secundarias y una propagación retardada; permitir que esa misma
> interacción reorganice la geometría; observar después qué relaciones no se cancelaron, qué
> grumos se formaron y cuáles se disolvieron.

La dinámica debe surgir del RHS. Fase, lock, arista, grumo, captura, release y supervivencia son
lecturas posteriores de la trayectoria. Ninguna de esas palabras habilita, pondera ni apaga un
término del motor.

Esta propuesta reemplaza como norte de diseño el grafo inicial forzado de la sección 7.4 y los
puertos finitos de la sección 8 de
`audit/STUDY05_STUDY07_ARISTAS_Y_ACOPLE_INTERNO.md`. Las secciones se conservan como historia del
razonamiento; no se borran ni se presentan como implementación vigente.

## 1. Punto de partida comprobado

El motor `v1` integra por onion:

\[
X_i=(x_i,v_i,z_i,b_i,e_i),
\]

con modos Q/S1/S2, acoples internos, memoria y variables estructurales lentas. La red vigente:

1. recibe una lista fija de aristas;
2. asigna a cada arista un retardo fijo;
3. colapsa todos los modos del onion a `sum(x), sum(v)`;
4. calcula una fuerza Kelvin–Voigt escalar por nodo;
5. mezcla los contactos incidentes mediante una media por peso;
6. inyecta el mismo escalar en todos los modos del receptor, dividido por su masa.

Por eso esos films muestran la respuesta real del onion completo al KV impuesto, pero no pueden
validar retrospectivamente una interacción modal secundaria que nunca simularon. El KV queda
congelado como baseline histórico; no se lo maquilla con un retardo variable para llamarlo física
nueva.

Una propiedad del integrador sí debe preservarse: en cada etapa de RK4 se evalúan todas las
interacciones desde el mismo conjunto de estados de etapa y recién después se construye el estado
siguiente. Ningún resultado puede depender del orden en que el programa recorra onions o pares.

## 2. Ontología mínima del motor nuevo

El estado causal de cada onion se amplía a:

\[
Y_i=(X_i,\mathbf r_i,\mathbf u_i),
\qquad
X_i=(x_i,v_i,z_i,b_i,e_i).
\]

- `X_i` sigue siendo el onion diferencial completo. No se parte en portadora, puertos ni objetos
  link.
- `r_i` es su coordenada macroscópica dentro de la geometría de la corrida.
- `u_i` es la velocidad de esa coordenada.
- `r_i/u_i` son estado causal y biografía. Si un onion continúa a otra ola, no se re-sortean salvo
  intervención explícita.

Elegir dimensión, métrica, dominio y distribución inicial de `r/u` es elegir la condición inicial
del caldo, no elegir el grafo final. La organización espacial puede emerger aunque el escenario
geométrico sea parte del experimento.

No existe un objeto diferencial `EdgeState`. Tampoco existen en el motor:

- ocupación o salud de arista;
- memoria propia de link;
- puerto asignado por un detector;
- razón `p:q` elegida de antemano;
- evento `capture()` o `release()`;
- poda por amplitud pequeña, distancia, coherencia o costo computacional.

## 3. Todos contra todos como condición inicial

En cada subpaso, todo par no ordenado `i<j` es una oportunidad de interacción. Evaluar un par no
declara que exista un enlace: declara solamente que ninguna relación fue eliminada antes de que la
dinámica pudiera actuar.

Para cada par:

\[
\mathbf R_{ij}(t)=\mathbf r_j(t)-\mathbf r_i(t),
\qquad
d_{ij}(t)=\|\mathbf R_{ij}(t)\|,
\qquad
\tau_{ij}(t)=\frac{d_{ij}(t)}{c}.
\]

`c` es una escala declarada de la corrida. La ecuación anterior define un retardo dependiente del
estado. No presupone una función de Green, una teoría de campos ni una forma particular de
atenuación.

El estado recibido de `j` se consulta en:

\[
t_{j\to i}^{\rm src}=t-\tau_{ij}(t).
\]

La misma construcción se aplica en la recepción inversa. Compartir distancia y ley no implica que
ambos extremos reciban el mismo valor: cada uno recibe la historia causal del otro.

### 3.1 Historia anterior al nacimiento

El `HistoryBuffer` vigente rellena todo su pasado con el estado de `t=0`. Esa convención no puede
heredarse silenciosamente: fabricaría una emisión eterna anterior al nacimiento.

El contrato nuevo debe distinguir:

- `t_src` posterior al nacimiento: interpolar el estado realmente integrado;
- `t_src` anterior al nacimiento: ausencia de señal, salvo que una campaña declare y serialice una
  prehistoria física distinta.

Así existe un **cero causal** sin un filtro de distancia: todavía no llegó una emisión posible.

### 3.2 Retardo no equivale por sí solo a atenuación

Retrasar una señal periódica cambia su fase de llegada, no necesariamente su amplitud. Por eso no
se declara que un retardo mayor sea siempre un vínculo más débil. La compatibilidad puede tener
ventanas, relevos y cuencas a retardos finitos, incluidas relaciones remotas.

Se separan tres nociones de cero:

1. **cero causal:** no existe todavía señal emitida que pueda haber llegado;
2. **cero dinámico:** la interacción instantánea existe, pero su trabajo o efecto acumulado se
   cancela a lo largo de la trayectoria;
3. **cero asintótico:** una envolvente de alcance `a(d)` tiende a cero cuando `d→∞`.

Los dos primeros surgen sin apagar pares. El tercero es una decisión constitutiva todavía abierta.
Si se incorpora `a(d)`, su forma y escala deben declararse como parte del modelo. No se adopta
`1/d²`, un corte duro ni otra potencia por analogía externa.

## 4. Interacción elemental: una ley por par, sin fase aguas arriba

La pieza central pendiente se denomina aquí `J_ij` únicamente para identificar una interfaz
matemática. No es un objeto link ni posee estado propio:

\[
\mathcal J_{ij}
\left(
Y_i(t),Y_j(t),
X_i^{S}(t-\tau_{ij}),X_j^{S}(t-\tau_{ij}),
\mathbf R_{ij}(t)
\right)
\longrightarrow
\left(
\mathbf f^{S}_{i\leftarrow j},
\mathbf f^{S}_{j\leftarrow i},
\mathbf A_{i\leftarrow j},
\mathbf A_{j\leftarrow i}
\right).
\]

Cada recepción combina el estado actual del receptor con la historia secundaria retardada del
emisor. La evaluación conjunta necesita por eso los dos estados actuales y las dos historias
retardadas; no sustituye un sentido por el otro.

- `f^S` son contribuciones vectoriales sobre aceleraciones de modos secundarios concretos.
- `A` son contribuciones sobre la evolución de la velocidad macroscópica.
- Las cuatro salidas se producen en la misma evaluación del par y desde la misma ley
  constitutiva. No se calcula primero un lock para decidir después una fuerza espacial.
- Las contribuciones se suman sin normalizar por el número de vecinos. Si existe un presupuesto
  finito, debe vivir en las ecuaciones o en la constitución del onion, no en una división por grado.

El RHS queda estructuralmente:

\[
\dot X_i(t)=F_i(X_i(t))+
\sum_{j\ne i}\mathcal I^{(S)}_{i\leftarrow j}(t),
\]

\[
\dot{\mathbf r}_i(t)=\mathbf u_i(t),
\qquad
\dot{\mathbf u}_i(t)=
\mathcal A_i^{\rm propia}(Y_i(t))+
\sum_{j\ne i}\mathbf A_{i\leftarrow j}(t).
\]

No se presupone todavía fricción, confinamiento, atracción, repulsión ni conservación
macroscópica. `A_propia` puede resultar nula. Esas decisiones no se rellenan por costumbre.

### 4.1 Qué entra a la interacción secundaria

`J_ij` debe leer coordenadas y velocidades diferenciales reales de los modos secundarios de ambos
onions. No recibe:

- fases estimadas;
- frecuencias extraídas por ventana;
- coherencia `R`;
- lenguas de Arnold;
- `L_pq`;
- etiquetas FIRME/COQUETEO/MUERTO;
- potencia promediada por un instrumento.

Si dos modos se capturan, hacen pulling, entran en una relación `p:q`, se relevan o pierden
compatibilidad, eso debe aparecer al integrar sus `x/v` y el resto de `X`. La fase se deriva luego
de esas trayectorias para observar lo ocurrido.

### 4.2 Forma diferencial mínima que puede investigarse

El motor actual ya conecta modos internos mediante diferencias de coordenadas. La continuación
inter-onion más cercana a esa gramática tendría una estructura del tipo:

\[
\left[\mathcal I^{(S)}_{i\leftarrow j}\right]_{v_\mu}
=
\frac{1}{m_{i\mu}}
\sum_{\nu\in S_j}
a_{i\mu,j\nu}(d_{ij})\,
\Psi\!\left(
x_{i\mu}(t),v_{i\mu}(t),
x_{j\nu}(t-\tau_{ij}),v_{j\nu}(t-\tau_{ij})
\right).
\]

Esta expresión fija solamente dónde viven los términos y qué información pueden usar. No fija
`Psi`, no selecciona parejas modales y no declara una ley. Una primera candidata podrá reutilizar
la diferencia de coordenadas ya existente, pero sólo será física nueva cuando su significado y su
reciprocidad estén escritos explícitamente; copiar un resorte por familiaridad no alcanza.

### 4.3 El puente modal–espacial es la única deuda física central

Los modos actuales son coordenadas escalares con masa, frecuencia, fricción y capa. No traen forma
modal, orientación ni un mapa hacia un centro macroscópico vectorial. Por eso hoy no se puede
deducir de los genomas cómo `f^S` produce `A`.

La implementación no debe ocultar ese hueco mediante una regla `lock => atracción`. Antes de
cerrar `J_ij` habrá que fijar cuál de estas afirmaciones pertenece realmente al modelo:

1. los modos secundarios representan deformaciones espaciales y su constitución debe declarar el
   mapa geométrico que proyecta una interacción sobre modos y centro; o
2. `r/u` son coordenadas relacionales adicionales y su evolución requiere una ley nueva,
   explícitamente declarada como tal.

No se elige aquí una de las dos. Lo importante es que el motor no finja haber derivado el puente
que todavía no existe.

## 5. Realimentación que puede producir exclusividad

La exclusividad buscada no es `grado<=V` ni «un puerto ocupado». Es una consecuencia posible del
circuito:

```text
todos los pares
  -> recepción secundaria retardada
  -> intercambio que se sostiene o se cancela
  -> cambio de X_i y X_j
  -> cambio de r/u por la misma interacción
  -> cambio de distancias y retardos
  -> nuevas condiciones de compatibilidad
```

Un encuentro persistente cambia simultáneamente la biografía interna y la geometría. Los demás
onions ya no encuentran el mismo objeto ni el mismo retardo. De ese modo un vínculo temprano puede
sesgar encuentros posteriores sin reservar un asiento en software.

No se afirma que menor retardo sea siempre mejor. La dependencia retardada puede estabilizar
cuencas a distancia finita y puede volver compatibles retardos mayores. Tampoco se exige repulsión
explícita de pares débiles: el movimiento hacia relaciones dominantes puede aumentar indirectamente
la separación respecto de otras.

La hipótesis evolutiva a probar es que la integración completa produzca, con el tiempo, una
distribución muy desigual de efectos acumulados: pocas relaciones persistentes y muchas cuya
contribución neta se cancela o se vuelve asintóticamente despreciable. No se programa esa
distribución como input.

## 6. Ruptura y release como trayectorias

El motor no contiene eventos discretos de link. Una relación puede recorrer continuamente:

```text
captura aparente
  -> pulling / slips / relevo
  -> menor intercambio coherente
  -> reorganización interna y geométrica
  -> nuevo retardo
  -> pérdida o cambio de compatibilidad
```

También puede invertir el recorrido y recapturar. Los instrumentos podrán fechar episodios o
cruces operativos, pero esas fechas no vuelven al RHS.

Al desaparecer una relación persistente no se restaura el estado anterior. Sus consecuencias
permanecen en `x/v/z/b/e/r/u` y afectan el resto de la evolución. No hay memoria de arista porque la
memoria relevante ya está en los onions y en la geometría integrada.

## 7. El grafo y los grumos son productos de lectura

Después de correr una trayectoria, una vista puede reconstruir por par:

- intercambio instantáneo y acumulado de potencia;
- fases y frecuencias derivadas de `x/v`;
- cierres `p:q` observados;
- retardos y distancias recorridos;
- episodios de captura, pulling, relevo, recaptura y ruptura;
- dependencia entre cambio geométrico y cambio interno.

Con esas trayectorias se puede definir, para un horizonte declarado, un grafo observado y sus
componentes o grumos. Ese grafo es una descripción del resultado. Cambiar el instrumento puede
cambiar la lectura, pero nunca la trayectoria ya integrada.

La potencia trending existente conserva valor metodológico, aunque sus números históricos
pertenecen al KV. En el motor nuevo deberá descomponerse por par y por modo directamente desde las
contribuciones devueltas por `J_ij`, sin reconstruir una segunda copia de la fuerza.

## 8. Contrato de integración y registro

Una implementación compatible debe cumplir:

1. integrar `X/r/u` conjuntamente en cada etapa RK4;
2. evaluar cada par desde el mismo estado de etapa;
3. producir juntas las dos recepciones modales y las dos contribuciones geométricas;
4. acumular contribuciones por suma, sin media por grado;
5. conservar el estado modal secundario necesario en la historia causal;
6. interpolar por tiempo físico, porque `tau_ij(t)` ya no pertenece a grupos fijos;
7. rechazar una consulta más antigua que la historia disponible, salvo el cero causal o una
   prehistoria serializada explícitamente;
8. registrar `r/u`, distancia, retardo y las contribuciones causales usadas por el RHS;
9. incluir esos campos en checkpoint y continuación entre olas;
10. mantener instrumentos, clasificación, filesystem y selección fuera del integrador.

No se protege la arquitectura `v1` si contradice estas condiciones. Sí se conserva `v1` congelado
para reproducir población y controles históricos. El motor nuevo necesita versión de contratos,
schemas y fixtures propia; no puede sobrescribir silenciosamente el significado de una worldline
anterior.

## 9. Guardas contra física fabricada

Antes de interpretar una corrida, el motor nuevo debe demostrar al menos:

- **onion aislado:** con cero interacción externa reproduce su RHS interno de referencia;
- **permutación:** renombrar nodos o cambiar el orden de recorrido no cambia la trayectoria
  correspondiente más allá del redondeo declarado;
- **todos los pares:** ningún par desaparece por un umbral de distancia, amplitud, lock o potencia;
- **causalidad de nacimiento:** antes de la primera llegada no se inyecta el estado congelado de
  `t=0`;
- **identidad modal:** una contribución secundaria no se convierte en un escalar uniforme antes de
  entrar al onion;
- **reciprocidad constitutiva:** ambos sentidos usan la misma ley y parámetros del par, aunque sus
  valores instantáneos difieran por historia;
- **un solo RHS:** trending y ledgers consumen contribuciones emitidas por la evaluación real; no
  reimplementan la fuerza;
- **refinamiento temporal:** los outcomes distribucionales declarados no son artefactos del `dt`;
- **sin eventos ocultos:** el código del motor no contiene estados de lock, salud, captura o
  release.

Estas guardas no eligen la física. Impiden que el software agregue decisiones que la ecuación no
contiene.

## 10. Decisiones fijadas y decisiones abiertas

### Fijadas por este contrato

1. El onion completo sigue siendo la unidad diferencial.
2. La geometría forma parte del estado causal mediante `r/u`.
3. El retardo se deriva dinámicamente de la distancia.
4. Todos los pares tienen oportunidad inicial; no hay grafo fijo ni puertos.
5. La interacción entra por coordenadas secundarias individualizadas.
6. La fase y los locks no existen aguas arriba del integrador.
7. Una única evaluación por par debe alimentar dinámica interna y geometría.
8. No hay health flag, captura, release ni poda dentro del motor.
9. Exclusividad, aristas y grumos son resultados de evolución y lectura.
10. Toda consecuencia queda en la biografía completa y viaja entre olas.

### Abiertas, sin valor inventado

1. Forma exacta de `Psi` y del mapa modal entre dos onions.
2. Puente entre fuerzas modales escalares y evolución espacial vectorial.
3. Dimensión, dominio, contorno y distribución inicial de `r/u`.
4. Valor y unidades de `c`.
5. Existencia y forma de una envolvente de alcance `a(d)`.
6. Comportamiento cuando `d→0`; no se introduce un `epsilon` silencioso ni una colisión ficticia.
7. Prehistoria diferente de cero, si alguna campaña la necesita.
8. Escala de la suma entre números distintos de modos secundarios; no se normaliza por grado como
   atajo.
9. Significado constitutivo de la componente macroscópica propia `A_propia`, incluida la opción
   nula.

Estas decisiones son parte de la física que se quiere probar. El costo de implementación no las
resuelve ni autoriza reemplazarlas por proxies.

## 11. Criterio de cierre del diseño

El documento está listo para convertirse en spec ejecutable cuando `J_ij` pueda escribirse sin
usar observables de ventana y cuando el puente modal–espacial tenga una interpretación explícita.
No hace falta predecir qué links vivirán ni demostrar de antemano que la dinámica formará grumos.
Justamente ésos son los outcomes.

El criterio mínimo es más simple:

> Cada término implementado debe corresponder a una variable del estado y actuar en su `dt`
> nativo; ninguna conclusión observada debe reaparecer aguas arriba como causa.
