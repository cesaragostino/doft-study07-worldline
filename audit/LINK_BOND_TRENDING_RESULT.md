# Resultado — trending físico del bond a resolución nativa

Fecha: 2026-08-04

Estado: **COSECHA COMPLETA; LECTURA DESCRIPTIVA POST HOC**

Branch: `research/link-bond-trending`

Prerregistro: `audit/LINK_BOND_TRENDING_PREREG.md`

## 1. Custodia y artefactos

Fuente, tratada sólo lectura:

```text
/Volumes/ExternalDisk/study07_census_arnold
```

Salida nueva, separada de films y ledgers anteriores:

```text
/Volumes/ExternalDisk/study07_link_bond_trending_v1/population_full_dt_1to1
```

Artefactos canónicos:

| objeto | valor |
|---|---:|
| `population.json` | SHA-256 `5bee91802f310b9372a524a8a4ada0a571d0ba22582759e64ecf9b29d733e79f` |
| `population_panel.json` | SHA-256 `37186138c2e36ba7ae5e123ef9008638cd006786f4555d95a9bfaced273703d0` |
| tamaño total | 52 GB |
| films | 375/375, cero fallos |
| horizonte | 301×60 u.t.; 74×120 u.t. |
| brazos | 200 transported; 175 fresh |
| contraste apareado | 175 pares t/f; 25 transported sin gemelo fresh |
| tiempo de cosecha | 3.216 s con 4 workers |

Cada unidad verificó `manifest_sha`, `COMPLETE`, SHA de todos sus chunks, continuidad de
ticks, topología de una sola arista, finitud y cierre de potencia por capas antes de escribir.
Las 375 vistas fueron recargadas y su `view_hash` fue verificado por el runner. La fuente no fue
modificada y ningún derivado vive dentro de ella.

Configuración efectiva sellada:

```text
instrument        = link_bond_trend v1.1
lock_window_ut    = 4.0
power_window_ut   = 2.0
hop_ut            = 0.25
ratios            = 1:1
lock_threshold    = 0.90
retain_dt         = true
stride_input      = 1
```

La vista compacta se publica cada 0.25 u.t., pero `theta`, fase corregida, potencia instantánea
y `L_1:1(t)` crudo/corregido se guardan para cada `dt`. En un film de 60 u.t. son 750.001 ticks
de fase/potencia y 700.002 finales consecutivos con caja W4 completa.

## 2. Validaciones antes de leer el patrón

El smoke t/f reprodujo exactamente el panel compacto con y sin retención full-`dt`. La suma
Q+S1+S2 coincidió con `link_power` sellado en el tick común con error máximo
`8.33e-17`; el instrumento también exige ese cierre en cada film.

Pruebas específicas:

```text
16 passed
```

Cubren alineación `drive[k]×v[k-1]`, cierre por capa, lock/release/recaptura sintéticos,
retención de `L` en cada `dt`, invariancia ante `hop`, mudez, topología, streaming/hashes,
round-trip de View y lector poblacional.

Suite completa del repo al cierre:

```text
144 passed, 210 warnings in 154.06s
```

Los 210 warnings son los `PHYSICS_CONTRACT`/blowup históricos esperados por sus tests; no hay
warnings nuevos atribuidos al instrumento de trending.

## 3. ¿Estables, intermitentes o nunca lockeados?

La etiqueta de este apartado es solamente una descripción temporal sobre la grilla compacta:

- `stable`: `locked` en todas las filas;
- `never`: `locked` en ninguna;
- `intermittent`: cualquier mezcla;
- `locked`: `L_corrected_fixed>=0.90` y señal no muda en ambos extremos.

No es salud, supervivencia ni fuerza de enlace.

### Films de 60 u.t.

| brazo/capa | stable | intermittent | never | films con cambios |
|---|---:|---:|---:|---:|
| transported Q | 20 | 58 | 85 | 58/163 |
| transported S1 | 13 | 61 | 89 | 61/163 |
| transported S2 | 17 | 59 | 87 | 59/163 |
| fresh Q | 1 | 53 | 84 | 53/138 |
| fresh S1 | 0 | 30 | 108 | 30/138 |
| fresh S2 | 0 | 26 | 112 | 26/138 |

No hay una dicotomía limpia. A 60 u.t. la mediana de `locked_fraction` sigue siendo cero en
todas las capas de ambos brazos: el grupo transported trae más locks y algunos completamente
estables, pero también abundan los nunca lockeados.

### Films de 120 u.t. — misma población apareada 37×37

| brazo/capa | stable | intermittent | never | films con cambios |
|---|---:|---:|---:|---:|
| transported Q | 21 | 16 | 0 | 16/37 |
| transported S1 | 18 | 18 | 1 | 18/37 |
| transported S2 | 21 | 16 | 0 | 16/37 |
| fresh Q | 0 | 33 | 4 | 33/37 |
| fresh S1 | 0 | 27 | 10 | 27/37 |
| fresh S2 | 0 | 28 | 9 | 28/37 |

En este banco largo la diferencia visual es fuerte: transported tiende a sostener; fresh
tiende a bailar. Eso describe estos pares y esta lectura 1:1; no autoriza convertirlo en regla
evolutiva.

## 4. Contraste t/f: el patrón no depende sólo de la corrección

Delta = mediana temporal de lock transported menos fresh, mismo par. Se informan crudo y
corregido porque la corrección usa todo el film.

| horizonte/capa | mediana delta raw | raw t>f | mediana delta corrected | corrected t>f |
|---|---:|---:|---:|---:|
| 60 Q | +0.123 | 100/138 | +0.142 | 101/138 |
| 60 S1 | +0.151 | 111/138 | +0.306 | 119/138 |
| 60 S2 | +0.185 | 112/138 | +0.249 | 109/138 |
| 120 Q | +0.145 | 31/37 | +0.071 | 37/37 |
| 120 S1 | +0.196 | 35/37 | +0.119 | 36/37 |
| 120 S2 | +0.231 | 35/37 | +0.181 | 37/37 |

La biografía transported está asociada a mayor orden 1:1 por capa aun en fase cruda. La
corrección no inventa el signo poblacional, pero sí cambia su fuerza y vuelve unánimes dos
capas del banco largo.

### Fuera de patrón, conservados

El efecto no es ley por par. Reversiones corrected grandes a 60 u.t.:

- Q: `par122_t` queda `-0.635` debajo de su fresh;
- S1: `olaB_par065_t` queda `-0.893` debajo de su fresh;
- S2: `par065_t` queda `-0.688` debajo de su fresh;
- a 120 u.t. queda una reversión S1: `olaB_par005_t`, delta `-0.096`.

Los máximos bailes también están declarados en el panel: `olaB_par022_f` cambia 38 veces en Q,
`olaB_par011_f` 28 en S1 y `olaB_par098_f` 36 en S2. Son candidatos de inspección, no datos
descartados.

## 5. Calzón sucio mayor: la fase corregida mueve categorías

`corrected_fixed` cambió la categoría temporal raw (`stable/intermittent/never`) en
**311/1.125 film×capa = 27,6%**. El caso no es marginal:

- en transported de 120 u.t., raw ve sólo 5 estables por capa; corrected ve 21 Q, 18 S1 y 21 S2;
- en transported de 60 u.t., raw no ve estables; corrected crea 20 Q, 13 S1 y 17 S2;
- `par129_t/S2` pasa de mediana raw `0.217` a corrected `0.988`;
- `par133_t/Q` pasa `0.238→0.940` y `par134_t/Q`, `0.277→0.924`.

Esto no invalida el patrón t/f porque también aparece en raw. Sí invalida vender
`corrected_fixed` como lectura inocua o causal. Los films con chirp/anisotropía fuerte dependen
mucho de la referencia de fase. Por eso ambas series quedan retenidas y el panel reporta su
desacuerdo.

## 6. Potencia: disipación dominante, pero no universal caja por caja

En los 375 films, la mediana temporal de potencia neta total es negativa en **375/375**. La
mediana poblacional de esas medianas es `-2.09e-6`. Sin embargo, la nueva población contiene
**2/102.510** cajas compactas con potencia neta positiva, ambas en
`olaB_par096_t_k03_tau02`:

| t (u.t.) | P_Q | P_S1 | P_S2 | P_total |
|---:|---:|---:|---:|---:|
| 36.49992 | -0.6175 | +0.0568 | +0.7537 | +0.1929 |
| 36.99992 | -0.3325 | +0.0447 | +0.4956 | +0.2078 |

Ese link tiene `L=1.0` estable en Q/S1/S2 durante todo el panel compacto. La inversión de dos
cajas proviene de devolución S2 mayor que la absorción Q en esos instantes; el film sigue siendo
fuertemente disipativo en su mediana y vuelve a P_total negativa inmediatamente.

Esto **no contradice** el conteo anterior `0/94.580`: Gate K contenía 340 films y terminaba en
`olaB_par094`; `olaB_par096_t` no estaba en ese jurado. Sí corrige la extrapolación indebida
"ninguna caja poblacional puede ser positiva". La regla durable pasa a ser: disipación neta
abrumadoramente dominante, con devoluciones suavizadas raras pero reales.

## 7. Qué queda calculado, sin interpretación forzada

Por film, nodo y capa Q/S1/S2:

- fase cruda y corregida en cada `dt`;
- lock 1:1 raw/corrected para cada final de `dt` con W4 completa;
- fase combinada, deriva y mudez;
- potencia instantánea `drive[k]×v_layer[k-1]` en cada `dt`;
- potencia media P2, trabajo acumulado, fracción negativa y signos opuestos;
- resumen liviano para localizar estables, intermitentes, slips y excepciones.

No se calculó bond strength, health, AUC, fitness ni supervivencia. Esta cosecha responde la
pregunta instrumental: permite ver cuándo el enlace fluctúa, baila o permanece ordenado, y
qué hacen simultáneamente fase y energía.

## 8. Límites que siguen en pie

- Sólo es identificable por edge en films de dos nodos y una arista.
- La potencia por capa particiona la inyección uniforme del motor vigente; no demuestra un
  endpoint físico propio de S1/S2.
- W4 suaviza la coherencia aunque se publique `L(t)` en cada `dt`.
- Esta cosecha es 1:1; no barre p:q ni maximiza sobre razones.
- `corrected_fixed` usa futuro del mismo film y no puede decidir online.
- Los horizontes 60/120 pertenecen a bancos distintos salvo el contraste interno de los 37
  pares largos; no se comparan como si fueran una extensión aleatoria del mismo muestreo.

## 9. Reproducción

```bash
PYTHONPATH=src:tools/link_grumo python3 \
  tools/link_grumo/run_link_bond_trending.py \
  --worldlines-root /Volumes/ExternalDisk/study07_census_arnold \
  --output-root /Volumes/ExternalDisk/study07_link_bond_trending_v1/population_full_dt_1to1 \
  --workers 4 --retain-dt

PYTHONPATH=src:tools/link_grumo python3 \
  tools/link_grumo/read_link_bond_trending.py \
  --ledger /Volumes/ExternalDisk/study07_link_bond_trending_v1/population_full_dt_1to1/population.json \
  --output /Volumes/ExternalDisk/study07_link_bond_trending_v1/population_full_dt_1to1/population_panel.json
```
