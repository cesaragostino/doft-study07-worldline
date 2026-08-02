# Gate B — cosecha de llegada, dominancia y endpoint

Estado: exploratorio, branch paralelo, no canónico. No se corrieron films nuevos. Las
worldlines externas se abrieron sólo para lectura y cada chunk usado se verificó contra
`COMPLETE`. Las salidas completas viven en `logs/link_grumo/`.

## Pregunta

¿Qué trae la biografía que permite cerrar a los transported, y cuál es la secuencia mínima
entre aparición de una línea, dominancia espectral, cierre de frecuencia y firmeza de fase?

## B1 — estado fijo de llegada `[0.5,5.0]`

Se leyeron 18 `chunk_00000`: nueve remotos del Gate A y sus fresh apareados.

1. **Más energía no es condición necesaria.** Transported tiene más E0 sólo en 4/9. Tiene
   mayor drive y mayor amplitud Q en 7/9, pero `olaB_par085` y `par101` cierran llevando
   simultáneamente menos E0, menos fuerza y menor amplitud Q que su fresh.
2. **La memoria lenta separa brazos, no explica todavía salud.** `b!=0` en 9/9 transported
   y `b=0` en 9/9 fresh por construcción. Es una huella biográfica perfecta, pero no un
   mecanismo ni un predictor hasta compararla entre éxitos y fallos transported.
3. **El link no funciona como fuente neta temprana.** El trabajo
   `P_i=drive_i·Σv_modos_i` suma negativo en los 9 transported y 9 fresh. En 6/9 transported
   un nodo recibe trabajo neto mientras el otro pierde; en 0/9 fresh. Hay transferencia
   direccional en parte del banco, dentro de un balance global disipativo.

La lectura mínima es que “link sano” no puede significar simplemente más combustible. Un
link puede seleccionar/alinear mientras extrae energía total.

## B2 — quién gana el espectro antes de cerrar la fase

Se definió, sin usar el outcome:

`rho = amplitud de la línea Q del onion dominante en el seguidor / mayor competidor Q del seguidor`.

La línea y el competidor se consideran separables sólo si distan al menos una resolución
Rayleigh. W8 deja seis transported realmente resolubles; tres candidatos “remotos” del Gate
A son remotos para deriva de fase pero no para separar dos líneas espectrales.

- Dominancia sostenida `rho>1`: 6/6 transported.
- Fresh resolubles con dominancia sostenida: 0/5.
- En los seis transported, la dominancia precede al cierre de fase.
- Adelanto mediano: 8.41 u.t.; rango aproximado 1.95–19.84 u.t.
- No hubo saltos de línea mayores que 2 Rayleigh en estas trayectorias.

Secuencia observada:

> aparece/responde la línea del socio → esa línea vence al competidor → después cierra la
> deriva de fase.

Esto es compatible con entrainment forzado, pero no lo demuestra. `rho` mide selección
espectral, no autonomía, atractor ni signo de energía.

## B3 — predictor temprano contra futuro disjunto

Se extendió el mismo observable a toda la población no-self resoluble, sin armónicos ni
mudez: 164 films (71 transported, 93 fresh). Predictor fijo `[0,8]`; endpoint tardío
`[50,60]`. Ningún film elegible tenía `t_lock<=8`, de modo que el predictor antecede al
evento del detector en toda esta muestra.

### Resultado completo, todavía reutilizando el banco de descubrimiento

- Transported, `rho` → firmeza+cierre a 60: AUC 0.956 (6 positivos/65 negativos).
- Transported, E0: AUC 0.828; amplitud de fuente 0.844; fuerza sobre seguidor 0.846.
- Mediana `rho`: 1.003 en positivos contra 0.214 en negativos.
- Umbral no ajustado `rho>1`: 3/5 (60%) positivos contra 3/66 (4.5%) con `rho<=1`.
- Control por vecinos próximos en `log(E0, fuerza, dw)`: el positivo tiene mayor `rho` en
  5/6 comparaciones. El sexto control no es cercano (`d≈1.0`).
- Permutación simple da 0/100.000 AUC iguales o mayores, pero **no es citable**: no clusteriza
  por nodos y cinco positivos pertenecen al banco que originó la hipótesis.

Fresh se comporta distinto: `rho>1` da 0/7 positivos, mientras sus cuatro positivos tienen
`rho<1`. El valor continuo todavía ordena (AUC 0.739), pero el umbral 1 no es una ley
universal. Historia y mecanismo de cierre importan.

### Retiro honesto del banco que generó la hipótesis

Se retiraron `par043`, `par101`, `par129`, `par134`, `olaB_par093` y `olaB_par094`
transported:

- quedan 158 films y 5 positivos conjuntos;
- AUC conjunta de `rho` = 0.782;
- para transported queda un solo positivo nuevo, aunque ocupa rango AUC 0.953.

La señal sobrevive en dirección, pero la validación transported independiente no tiene aún
outcome suficiente.

## El hallazgo ontológico: cerrar no es quedar firme

En los 164 films:

- cierre físico tardío: 21;
- firmeza de fase final: 12;
- ambos: 10;
- cierre sin firmeza: 11;
- firmeza sin cierre: 2.

`rho` predice mejor firmeza (AUC conjunta 0.866) que cierre de frecuencia (0.751). Esto
sugiere que la selección espectral temprana está más cerca de la estabilidad del patrón que
del simple pulling.

Pero “ambos a 60” tampoco equivale a supervivencia final. `par129` y `par131`, negativos de
firmeza corta pese a cerrar frecuencia, desarrollan episodios sostenidos y recapturas en los
films de 600 u.t. El endpoint de 60 mide **maduración temprana**, no destino asintótico.

## Regla mínima que emerge, sin convertirla en ley

El candidato compacto ya no es energía absoluta ni `t_lock`:

1. `rho(t)` pregunta **quién posee el espectro del seguidor**;
2. cierre de frecuencia pregunta si dejaron de derivar;
3. firmeza pregunta si la relación de fase persiste;
4. horizonte/recovery distingue muerte de maduración tardía.

La sanidad provisional de un link es una secuencia, no mil parámetros:

> una línea recibida gana contra el competidor, luego frecuencia y fase cierran, y el patrón
> persiste o se recupera después de perturbaciones.

La energía y la susceptibilidad explican por qué puede ocurrir, pero no sustituyen ese orden
observable.

## Próximo test con mejor valor/CPU

Antes de una cirugía nueva:

1. medir `rho` temprano en un conjunto prospectivo o holdout transported con más positivos;
2. extender el endpoint a tiempo-a-maduración, duración, release y recaptura;
3. calcular la transferencia esperada del genoma para separar respuesta forzada ordinaria
   de residuo no explicado;
4. usar `par085` y `par101` como controles de cierre con poco combustible, y `par129/131`
   como controles de maduración tardía.

Sólo si `rho` observado excede lo esperable por drive×susceptibilidad, o persiste al retirar
el drive, se justifica hablar de autonomía/atractor nuevo.

## Reproducción

```bash
python3 tools/link_grumo/gate_b_arrival.py \
  --worldlines-root /Volumes/ExternalDisk/study07_census_arnold \
  --gate-a logs/link_grumo/triage_cinematica.json \
  --output logs/link_grumo/gate_b_arrival.json

python3 tools/link_grumo/gate_b_dominance.py \
  --worldlines-root /Volumes/ExternalDisk/study07_census_arnold \
  --gate-a logs/link_grumo/triage_cinematica.json \
  --gate-b-arrival logs/link_grumo/gate_b_arrival.json \
  --output logs/link_grumo/gate_b_dominance.json

python3 tools/link_grumo/gate_b_population.py \
  --tables-root /Users/cagostino/code/doft-study07-worldline/data/census_arnold \
  --worldlines-root /Volumes/ExternalDisk/study07_census_arnold \
  --output logs/link_grumo/gate_b_population.json

python3 tools/link_grumo/gate_b_evaluate.py \
  --input logs/link_grumo/gate_b_population.json \
  --discovery logs/link_grumo/gate_b_dominance.json \
  --output logs/link_grumo/gate_b_evaluate.json
```
