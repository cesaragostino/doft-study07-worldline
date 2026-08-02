# Orden costo/valor — dinámica de link y grumo

Este orden maximiza información física por CPU. No ordena por belleza matemática ni por
parecido con una teoría conocida. Cada marco físico funciona como generador de preguntas;
el nombre del mecanismo se asigna sólo después de observar sus firmas y controles.

## Escala de costo

- **C0 — segundos:** JSON y vistas derivadas existentes; ninguna worldline nueva.
- **C1 — minutos:** lectura parcial de films archivados, FFT/demodulación y tablas.
- **C2 — hasta ~1 CPU-h:** Jacobianos, susceptibilidad y relectura completa de un banco
  pequeño; todavía sin integrar films nuevos.
- **C3 — 1–10 CPU-h:** cirugías cortas y pocos controles contrafactuales.
- **C4 — 10–100 CPU-h:** films largos, motivos de tres nodos y réplicas.
- **C5 — >100 CPU-h:** census o evolución poblacional nuevos.

El tiempo humano de preparar un instrumento se declara aparte: CPU barata no significa
pregunta fácil.

## Prioridad efectiva

| # | Prueba | CPU | Valor físico | Qué puede decidir |
|---:|---|:---:|:---:|---|
| 1 | Cinemática de los 9 remotos + fresh apareado | C0 | 5/5 | Falso cierre, ancla-seguidor, convergencia compartida o línea fuera del intervalo de llegada |
| 2 | Descomponer transported–fresh antes del outcome | C0–C1 | 5/5 | Si biografía cambia llegada, fuerza, tono competidor, susceptibilidad o sólo el detector |
| 3 | Dominancia, transmisión y signo de energía en los mismos episodios | C1 | 5/5 | Distingue sombra forzada, receptor activo y link que devuelve energía |
| 4 | Transferencia/notches del genoma en casos y controles | C1–C2 | 4.5/5 | Cuánto explica una respuesta forzada sin parámetro libre y dónde queda residuo real |
| 5 | Ventana temprana que predice futuro disjunto | C0–C1 | 4/5 | Candidato mínimo de salud sin contaminar predictor con supervivencia |
| 6 | Fase p:q en líneas con nombre, sólo banco + controles | C1–C2 | 4/5 | Entrada racional real versus coincidencia de razones o cambio de pico |
| 7 | Recurrencia de nodos y motivos del grafo | C0 | 2.5/5 | Selecciona tríos; por sí sola no demuestra grumo |
| 8 | Cirugía ON/OFF, drive congelado o replay | C3 | 5/5 | Causalidad: quién conduce, memoria, histéresis y persistencia al retirar el link |
| 9 | Motivos simultáneos de tres nodos | C3–C4 | 5/5 | Primera prueba genuina de modo colectivo/grumo |
| 10 | Census/evolución nuevos | C5 | 5/5 | Sólo después de fijar el observable de salud y los casos decisores |

Que una prueba barata aparezca más abajo significa que no decide física por sí sola. El
grafo, por ejemplo, sirve para elegir tríos pero no merece conducir la interpretación.

## Gates: cuándo subir el costo

### Gate A — validez cinemática

No se abre ningún film nuevo hasta publicar, por caso y fresh:

- detuning dentro del film al llegar y al final;
- trayectoria binned de la pendiente de diferencia de fase;
- primer cierre sostenido y releases;
- desplazamiento de cada onion y posición de la línea final respecto del intervalo inicial;
- banderas de mudez/armónico.

Si el supuesto lock no reduce realmente la deriva, sale del banco físico aunque conserve
un `t_lock` instrumental.

### Gate B — mecanismo sin intervención

Para cada caso que pasa A se exige una ficha con cinco canales separados:

1. fase;
2. frecuencia;
3. dominancia de la línea recibida sobre el autotono;
4. amplitud/fuerza del drive;
5. dirección de transporte energético.

Una coincidencia espectral no puede sustituir ninguno de los otros canales.

### Gate C — residuo que justifica cirugía

Sólo se simula si quedan dos mecanismos que predicen resultados distintos bajo una
intervención concreta. La corrida se diseña para romper ese empate, no para producir más
películas parecidas.

### Gate D — grumo

Los tríos se eligen por roles complementarios observados, no sólo por grado del grafo. Un
grumo requiere que retirar un link cambie o destruya una trayectoria colectiva que las
parejas aisladas no sostienen.

## Disciplina de mente abierta

- Primero se describen trayectorias y balances; después se comparan con patrones conocidos.
- Toda clasificación conserva un estado `no_decidible`.
- Los residuales y contradicciones se guardan; no se absorben aumentando parámetros.
- Una teoría conocida que ajuste no es una victoria por autoridad: debe predecir un dato no
  usado o sobrevivir una intervención.
- Una desviación tampoco es automáticamente física nueva: primero se excluyen instrumento,
  mudez, armónicos, leakage, resolución y selección retrospectiva.

## Primera ejecución

Se inicia por #1. Es la combinación más barata y más destructiva de hipótesis: usa las
fases ya archivadas para comparar cada remoto transported con su fresh idéntico en genoma,
par y semilla, sin generar datos nuevos.
