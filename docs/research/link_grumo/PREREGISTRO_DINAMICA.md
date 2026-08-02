# Prerregistro vivo v0 — dinámica física del link y del grumo

Estado: frente exploratorio paralelo. Este texto fija preguntas y discriminantes; no
declara resultados canónicos y no sustituye los prerregistros de campañas ya selladas.

## 1. Objetos físicos operativos

**Onion.** Sistema con genoma, estado interno y biografía. Puede emitir, responder,
almacenar y disipar energía. Su frecuencia dominante no agota su estado.

**Link.** Interacción que modifica la trayectoria conjunta. Debe distinguirse entre:

- parecido espectral por ventana;
- seguimiento forzado pasivo;
- captura de fase con cierre de frecuencia;
- transporte neto de energía;
- realimentación que cambia la persistencia futura.

**Grumo.** Conjunto donde los links cierran al menos un modo colectivo. Una unión visual o
una colección de respuestas esclavas al mismo emisor no basta.

## 2. Marcos conocidos que se usarán sólo si dejan sus firmas

1. **Respuesta lineal forzada / Bode–Nyquist.** Predice amplitud y fase desde la
   susceptibilidad del receptor. Firma: respuesta proporcional al drive, sin umbral propio
   ni histéresis, y notches determinados por el genoma.
2. **Injection locking / ecuación de Adler.** Firma: cierre de la velocidad de fase,
   phase slips antes de capturar y frontera que depende conjuntamente de detuning y fuerza.
3. **Captura por chirp / autoresonancia.** Firma: mismatch de fase acotado mientras la
   frecuencia impuesta barre, con umbral de amplitud y release al perder seguimiento.
4. **Resonancia subarmónica o p:q.** Firma obligatoria: cierre sostenido de la combinación
   de fases p:q y energía espectral coherente en las líneas implicadas. La cercanía de una
   razón racional, sola, no decide.
5. **Crecimiento transitorio no normal.** Puede amplificar una biografía aun si todos los
   polos son estables. Firma: gran respuesta dependiente del estado inicial que finalmente
   decae y no requiere un atractor nuevo.
6. **Modos colectivos de redes acopladas.** Firma: el conjunto sostiene una trayectoria
   que no se explica como suma de drives externos ni aparece en las parejas aisladas.

Algo se considerará nuevo sólo después de excluir estos mecanismos con sus propios
controles.

## 3. Hipótesis y decisiones

### H0 — coherencia fabricada por el instrumento

Nula física: dos fases con deriva constante y sin coupling pueden superar el umbral de
coherencia por la ventana finita.

Un episodio no será llamado captura si sólo cumple `R_W >= umbral`. Debe además mostrar,
en la misma ventana:

- reducción real de la pendiente de la diferencia de fase;
- cierre de frecuencia por encima de la resolución declarada;
- estabilidad frente a W o corrección explícita de la respuesta sinc del estimador;
- separación respecto de una nula link-OFF o phase-scrambled apareada.

### H1 — seguimiento forzado pasivo

Predicción: el receptor copia la línea del emisor con amplitud y fase explicables por su
transferencia, mientras absorbe energía y vuelve a su trayectoria propia cuando desaparece
el drive.

Decide a favor: cierre subporcentual entre respuesta medida y predicha, potencia receptora
positiva y ausencia de persistencia adicional en el control OFF.

### H2 — la biografía cambia el presupuesto de interacción

La ventaja transported se descompone en cuatro candidatos, sin elegir uno de antemano:

- amplitud/energía disponible para emitir;
- tono propio contra el cual compite la línea recibida;
- estado interno que viste la susceptibilidad;
- fase y frecuencia efectivas al momento del encuentro.

El contraste transported–fresh sigue siendo apareado por genoma y semilla. La explicación
se decide con mediciones tempranas disjuntas de la supervivencia posterior. Energía inicial
es un predictor, no una causa declarada, hasta intervenirla o aparearla.

### H3 — encuentro remoto genuino

El eje aislado no basta. Un caso remoto fuerte exige:

1. detuning medido dentro del film, antes del episodio, fuera de la zona de falso-firme;
2. cierre posterior de frecuencia y fase;
3. control W4/W8 o estimación coherente;
4. descarte de simple cambio del pico dominante por respuesta lineal;
5. potencia y trayectoria del tono propio publicadas.

Los casos que no pasen estas cinco capas siguen siendo datos, pero no banco p:q.

### H4 — entrada p:q

Se medirán combinaciones de fase p:q sobre líneas con nombre por capa. La búsqueda racional
debe compararse contra controles muertos con igual o mejor residual. La hipótesis gana sólo
si la captura p:q precede de forma reproducible al cambio 1:1 o a la nueva línea y aporta
predicción fuera de muestra.

### H5 — link sano y grumo autosostenido

Un link puede ser buen transmisor sin financiar supervivencia. Se publican tres niveles:

- compatibilidad de recepción;
- cierre de fase del lazo;
- balance y persistencia energética.

Para un grumo se buscará una intervención mínima: retirar o cortar un link y observar si el
modo colectivo desaparece, se redistribuye o persiste. La existencia de un hub en el grafo
de parejas es sólo una selección de candidatos, no evidencia de un grumo simultáneo.

## 4. Primera cola de trabajo

1. Releer el census con una nula física del estimador y validación local de cada `t_lock`.
2. Separar núcleo cercano y cola remota: no imponer una única curva monótona.
3. Auditar los candidatos remotos W8 con frecuencias tempranas/tardías, fase, energía y
   racionales contra controles.
4. Sustituir energía inicial por fuerza real de drive cuando el canal esté disponible.
5. Calcular transferencia y notches de los nodos que reaparecen en links remotos.
6. Elegir motivos de tres nodos para probar cierre colectivo, no sólo parejas independientes.

## 5. Criterio de novedad

No se llamará dinámica nueva a una respuesta lineal, un falso-firme de ventana, un
transitorio por condición inicial ni un lock conocido por chirp. Sería evidencia nueva si,
con controles apareados, ocurre al menos uno:

- nace una línea que no pertenece al emisor y sobrevive al retirarlo;
- la biografía modifica la transferencia de un modo no reducible a energía o estado frío;
- un circuito de onions sostiene actividad que todas sus parejas pierden aisladas;
- aparece una regla reproducible de selección p:q ausente en controles racionalmente
  equivalentes.
