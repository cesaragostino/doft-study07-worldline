# Retardo de arista y onset interno — lectura de datos existentes

Fecha: 2026-08-03
Estado: **EJECUTADO, RETROSPECTIVO, NO DEFINE SUPERVIVENCIA**
Procedencia: frente experimental `research/k150-emergent-links`, cerrado el 2026-08-04
sin una ley evolutiva de arista.

## Corrección del objeto

El motor v1 no posee una arista que nazca o muera: la arista declarada permanece activa durante
todo el film. Por eso estos datos no permiten observar literalmente «supervivencia de la arista».
Permiten observar si sobre esa arista persiste una relación dinámica: correspondencia de ciclos,
fase, actividad y transmisión.

Tampoco se usa «sano» como sinónimo de supervivencia. Un retardo puro desplaza la llegada, pero no
atenúa su amplitud. La pregunta de esta lectura es más limitada:

1. ¿reducir `tau` mejora de manera monótona la relación que queda al final?;
2. ¿existe un tiempo muerto interno entre la llegada del drive y Q/S1/S2?;
3. ¿puede medirse el tiempo de vuelta del lazo con datos conservados?

## Integridad y calzones sucios

- El panel `tau` de 25 pares ya había sido abierto por el census. `POOLED.json` ya publicaba el
  contraste y sus discordancias. La selección posterior de par56/68/72 es **outcome-selected**:
  sirve para validar fenomenología, no para estimar frecuencia poblacional ni significación.
- W8 está anidado en W4 y la zona de la rodilla del detector tiene falso-firme conocido. Los
  veredictos W sólo se usan para localizar discordancias, no como verdad del nuevo lector.
- Los 25 pares `tau=0.05/0.2` ocupan la celda κ/τ diseñada, no todo el zoológico. En cada par se
  verificó misma composición, contenido de estado fuente, semilla, horizonte, `dt`, `k` y
  `gamma`; cambia el tamaño de historia y `tau`, que es la intervención buscada.
- La cola directa usa sólo cruces ascendentes por cero y resta/conteo de ticks. Un cruce por
  intervalo prueba cierre de frecuencia de ciclo, no fase constante ni transferencia energética.
- El onset ON/OFF se eligió después de conocer la implementación. Es una prueba de conformance
  temporal sobre dos onions, no una campaña causal poblacional.

## 1. Contraste apareado de `tau` ya existente

Fuentes canónicas:

- `data/census_arnold/POOLED.json`, SHA-256
  `c814c014d95ed0f31c905b2ae4444a4ee7476f8519b3022522e343ae1b460f8d`;
- `data/census_arnold/tabla_tanda2.json`, SHA-256
  `d5e65e28966ca5a7f7eaedd9d814dfdcd4abba311c70811cd9a83cc2e693cac4`.

El resultado histórico completo ya decía que acortar el retardo no resolvía el outcome final:

| lector | `tau=0.05` | `tau=0.2` | discordantes |
|---|---:|---:|---:|
| lock60 W4 | 6/25 | 5/25 | 2 favorecen corto, 1 favorece largo |
| lock60 W8 | 2/25 | 2/25 | 1 favorece corto, 1 favorece largo |

En la métrica básica de fase final del reporte, `tau=0.05` supera a `tau=0.2` en 11 pares y queda
por debajo en 14; la mediana apareada `R_final(0.05)-R_final(0.2)` es `-0.004416`. No hay una
ventaja final monótona del retardo corto.

Sí hay una señal de arranque: el `t_lock_tick` básico histórico ocurre antes con `tau=0.05` en
23/25 pares y empata en 2/25. Esto describe el detector heredado y no se convierte en ley: llegar
antes puede acelerar el primer episodio sin sostenerlo al final.

### Lectura directa de las tres discordancias

Se abrieron los seis films completos y se verificaron manifiesto, `COMPLETE` y todos sus chunks.
En los seis, `drive[k]` vuelve a reconstruirse con residuo `0.0` usando el `tau` correspondiente:

```text
tau=0.05 -> 625 ticks
tau=0.20 -> 2500 ticks
```

En los últimos 10 u.t., para cada capa y sentido se contó cuántos cruces receptores caen entre
dos llegadas fuente consecutivas de esa misma capa. `x/y` significa `x` intervalos con exactamente
un cruce sobre `y` intervalos observados.

| par / tau | Q 0→1 · 1→0 | S1 0→1 · 1→0 | S2 0→1 · 1→0 |
|---|---:|---:|---:|
| 56 / 625 | 11/11 · 11/11 | 11/32 · 0/10 | 10/10 · 10/10 |
| 56 / 2500 | 11/11 · 11/11 | 11/22 · 5/10 | 11/11 · 10/10 |
| 68 / 625 | 18/18 · 14/18 | 18/18 · 18/18 | 18/18 · 17/17 |
| 68 / 2500 | 18/18 · 18/18 | 18/18 · 18/18 | 18/18 · 18/18 |
| 72 / 625 | 12/14 · 14/14 | 8/14 · 14/14 | 10/14 · 14/14 |
| 72 / 2500 | 15/15 · 15/15 | 15/15 · 14/14 | 14/14 · 14/14 |

Lectura:

- par56 no sostiene una diferencia limpia de «supervivencia»: Q/S2 cierran ciclos en ambos
  retardos y S1 conserva multiplicidad interna en ambos;
- par68 muestra que un veredicto de fase y un conteo de ciclos no son equivalentes: el retardo
  largo cierra todos los conteos aunque W4/W8 favorecían al corto; puede existir 1:1 con fase
  deslizante;
- par72 es el contraejemplo físico directo a «menos delay siempre transmite mejor»: con 625
  ticks la dirección 0→1 pierde o duplica ciclos S1/S2; con 2500 ticks las tres capas quedan
  uno-a-uno en ambos sentidos durante toda la cola observada.

Por tanto, el valor absoluto de `tau` no ordena la supervivencia dinámica. Importa dónde cae la
llegada respecto del ciclo y de la constitución del par. Un retardo mayor puede ser más compatible.

## 2. Onset interno ON/OFF

Se usaron dos clamps estacionarios deterministas ya existentes:

- `34b`: OFF contra ON `F0=0.19296379`, `omega=30.17`;
- `61b`: OFF contra ON `F0=0.86382812`, `omega=33.69`.

Cada ON/OFF comparte contenido de estado fuente, semilla y fila 0 bit-exacta; `T=0`. Se verificó
el SHA de manifiesto, `COMPLETE` y `chunk_00000` de cada unidad.

En ambos casos:

```text
primer drive distinto = tick 1
primer x distinto en Q/S1/S2 = tick 1
primer v distinto en Q/S1/S2 = tick 1
primer b distinto = tick 1
primer e distinto = tick 1
dt = 0.00008 u.t.
```

El límite medido es:

```text
0 < T_internal,onset <= 1 tick = 0.00008 u.t.
```

No se afirma que el tiempo físico sea exactamente un tick: el drive actúa durante el primer paso
y la próxima observación guardada es la fila 1. Sí queda negado un transporte interno lento
Q→S1→S2 en v1. Todas las capas empiezan a responder dentro del mismo intervalo RK4. Los tiempos
largos de captura, chirp, memoria o reorganización son otra cosa.

## 3. Tiempo de vuelta del lazo

No queda identificado con los datos existentes. La búsqueda halló:

- `0` worldlines Study07 de dos nodos con manifiesto intervenido;
- `0` archivos `events.jsonl` en census, s120, s600 y corridas archivadas de Study07;
- referencias documentales a kicks en Study06, pero ningún artefacto etiquetado y trazable que
  permita aparear origen, llegada y retorno.

En un film libre periódico no se puede decidir qué cruce de vuelta pertenece a qué emisión. El
próximo experimento mínimo no es poblacional: una única hija `kick` y su twin sin kick, a `T=0`,
sobre un par ya organizado. Se medirían por diferencia bit-exacta:

1. tick del kick en A;
2. primer tick diferente en B;
3. primer tick posterior diferente en A atribuible al retorno.

Debe correrse sólo después de verificar que el contrato de hija vigente preserva intervención,
checkpoint y linaje. No se ejecutó aquí.

## Reproducibilidad

```bash
python3 tools/link_grumo/medir_tau_y_onset_existentes.py \
  --census-root /Volumes/ExternalDisk/study07_census_arnold \
  --cirugia-root /Volumes/ExternalDisk/study07_cirugia_linea_fija \
  --output logs/link_grumo/tau_y_onset_existentes.json
```

- herramienta SHA-256:
  `baa8060ef525a946e5d2e76b95f99fa6c450167f382a20af675d0540909fbb72`;
- salida local SHA-256:
  `b9d63ea435ee9087e0228421ca3dc4472997a2ba8654ece494b975437cac097a`.

La salida contiene los intervalos individuales, sus ticks y toda la custodia. Vive en `logs/`,
ignorada por Git y regenerable. El disco externo se abrió sólo para lectura.
