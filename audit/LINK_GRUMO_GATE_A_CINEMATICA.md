# Gate A — cinemática de remotos y fresh apareados

Estado: resultado exploratorio del branch paralelo; no canónico. Fuente sólo lectura:
`data/census_arnold` del checkout principal. Derivado reproducible:
`logs/link_grumo/triage_cinematica.json`.

## Pregunta

Antes de asignar un mecanismo: ¿los nueve candidatos remotos reducen realmente la pendiente
de diferencia de fase, quién cambia de frecuencia y qué hace el fresh de la misma pareja?

## Método mínimo

- Mismos nueve casos definidos por el banco basal: transported, W8, `dw` aislado ≥1,
  detuning temprano fuera de falso-firme y tardío dentro.
- Control: brazo fresh del mismo par, genomas y semilla.
- Fase corregida igual que `par_link`, pero pendiente estimada por regresión local sobre
  ventanas móviles W4 y W8, hop 0.5 u.t.
- Cierre por escala: `|d(Δφ)/dt| < 1.1/W` sostenido ≥2 u.t.
- El tiempo se publica al final de la ventana: no pretende ser el instante causal.
- Categorías de trayectoria puramente descriptivas; no son nombres físicos.

## Resultado

1. **Cierre cinemático robusto: 9/9 transported, 0/9 fresh.** Todos pasan W4 y W8; no hay
   banderas de mudez ni armónico en ninguno de los 18 films. El banco remoto no se reduce a
   falso-firme por deriva constante.
2. **Hay al menos tres topologías, no una “cola remota” única:**

   - ancla–seguidor: 6/9;
   - convergencia compartida: `olaB_par085`;
   - línea final fuera del intervalo de llegada: `par129` y `par134`.

   Esto obliga a buscar mecanismos por trayectoria; un solo ajuste poblacional mezclaría
   fenómenos diferentes.
3. **E0 total no explica la ventaja apareada.** Transported tiene más E0 que fresh sólo en
   4/9; la mediana apareada `E0_t/E0_f=0.402`. Aun así, cierra 9/9 contra 0/9. La correlación
   poblacional previa de E0 sigue siendo real como predictor, pero no es una regla suficiente
   de biografía ni de salud.
4. **La biografía cambia fuertemente el estado de llegada.** La mediana de la distancia
   media entre frecuencias tempranas transported y fresh es 1.51 rad/u.t. en los mismos
   pares. Antes de buscar una causa interna hay que separar cambio de tono efectivo, fuerza
   del drive, amplitud del autotono y susceptibilidad vestida.
5. **La existencia del cierre es robusta; su timestamp no.** W4 y W8 discrepan varios u.t.
   en algunos casos y `t_lock` puede quedar antes o después del estimador de pendiente. No se
   debe usar todavía `t_lock` para afirmar precedencias finas (“S2 ocurrió X antes”).

## El intento que se descartó

Una primera pendiente en bins de 0.5 u.t. daba sólo 5/9 cierres. Al mirar las series, los
bins confundían el bamboleo intra-ciclo de la fase elípticamente corregida con releases.
Al estimar la deriva en W4/W8, los nueve cierran y el final coincide con el detuning tardío.
El resultado 5/9 queda descartado, no reutilizado como evidencia.

## Lectura física provisional

El hecho mínimo ahora defendible es más fuerte que “el detector vio coherencia” y más débil
que “hay un atractor conocido”:

> La biografía coloca a las mismas parejas en trayectorias de llegada distintas y, en este
> banco seleccionado, todas terminan cerrando la deriva de fase; el fresh no. Ese cierre se
> realiza mediante al menos tres geometrías cinemáticas.

No se decide aún si las seis ancla–seguidor son seguimiento forzado, si los dos casos fuera
del intervalo son un drive chirpeado o una línea colectiva, ni si la convergencia compartida
intercambia energía en ambos sentidos.

## Próximo gate barato

Sobre estos 18 films, medir antes y durante el cierre:

1. amplitud real del drive;
2. dominancia de la línea recibida sobre el autotono;
3. transferencia esperable del genoma;
4. potencia con signo por dirección;
5. cambio de estado interno.

El objetivo es explicar por qué cinco transported con menos E0 que su fresh igualmente
cierran. Sólo el residuo no explicado justificará una cirugía nueva.
