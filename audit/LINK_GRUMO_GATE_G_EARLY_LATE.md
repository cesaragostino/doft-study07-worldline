# Gate G — qué señal temprana sobrevive al cambio de brazo

Fecha: 2026-08-02. Branch `research/link-grumo-dynamics`.

Gate G es la prueba early→late que cierra el tramo abierto por Gate F. No modifica
`docs/bitacora`. Las capas se leyeron de worldlines externas en modo sólo lectura hasta
20 u.t.; el outcome `[50,60]` proviene de views locales ya construidas.

## 1. Diseño congelado antes de abrir las capas

Se excluyeron los 16 films de Gate F. Entre los pares restantes se congelaron 30 pares
exactos, elegidos por ranking SHA-256 dentro de estratos de outcome:

| Categoría | significado transported/fresh | pares |
|---|---|---:|
| YN | transported sano, fresh no sano | 12 |
| NY | transported no sano, fresh sano | 4 |
| YY | ambos sanos | 6 |
| NN | ambos no sanos | 8 |

Son 60 films: 28 `coordinate_health=True`, 32 negativos y cero banderas de mudez o
armónicos. El outcome era conocido al seleccionar; las trayectorias Q/S1/S2 de estos
films no se habían abierto en este frente.

Es un diseño case-control apareado para comparar mecanismos. No estima prevalencia ni
valor predictivo poblacional.

## 2. Resultado: convergen dos observaciones del mismo hecho

En la última ventana anterior a t=20, los rankings contra salud `[50,60]` fueron:

| Medición temprana | AUC descriptivo | mediana sano | mediana no sano |
|---|---:|---:|---:|
| coherencia primaria Q W8 | 0.963 | 0.975 | 0.322 |
| ocupación observada de la línea | 0.929 | 2.511 | 0.690 |
| coherencia Q W4 | 0.927 | 0.993 | 0.521 |
| ocupación predicha por `chi` fría | 0.887 | 2.058 | 0.206 |
| `dw` primaria | 0.869 | 0.040 | 1.149 |
| coherencia S2 | 0.821 | 0.979 | 0.436 |
| coherencia S1 | 0.717 | 0.970 | 0.368 |
| error complejo `R=(Q/F)/chi` | 0.577 | 1.205 | 1.096 |

Las dos señales superiores no son dos parámetros independientes. Son dos vistas de un
mismo cambio dinámico:

* **ocupación espectral:** una línea compartida desplaza al competidor interno;
* **coherencia temporal:** los dos onions mantienen una relación de fase sobre esa línea.

En los 16 pares discordantes, el brazo que sobrevivió tuvo mayor ocupación observada y
mayor coherencia Q en **16/16**. La ocupación fría ganó 14/16, S2 14/16, S1 13/16 y el
error `R` sólo 9/16.

El resultado no es simplemente “transported tiene más memoria”. La coherencia primaria
separa dentro de ambos brazos:

| Estrato | AUC coherencia primaria | AUC ocupación observada | AUC S1 |
|---|---:|---:|---:|
| transported | 0.968 | 0.880 | 0.796 |
| fresh | 0.985 | 0.955 | 0.475 |

S1 pierde completamente dirección dentro de fresh. Es una marca de ruta/biografía, no el
orden de salud común. S2 conserva información, pero sigue por debajo del estado Q.

## 3. Los umbrales muestran captura, no destino

Usando únicamente umbrales ya existentes, sin optimizarlos en Gate G:

| Estado sostenido al borde t=20 | films activos | sanos futuros | sanos entre inactivos |
|---|---:|---:|---:|
| ocupación Q predicha `rho_pred>1` | 28 | 25 | 3/32 |
| ocupación Q observada `rho_obs>1` | 37 | 27 | 1/23 |
| captura Q W4 `rw>=0.90` | 27 | 24 | 4/33 |
| captura primaria W8 | 12 | 12 | 16/48 |
| captura S1 | 24 | 18 | 10/36 |
| captura S2 | 20 | 17 | 11/40 |
| `R≈1`, banda `chi` plana | 10 | 3 | 25/50 |
| ocupación + `R≈1` + `chi` plana | 3 | 3 | 25/57 |

La captura primaria estricta es específica pero demasiado tardía: no produce falsos
positivos en este banco, pero todavía no apareció en 16 de los 28 sanos. La ocupación es
anterior y sensible, aunque todavía permite coqueteos que luego liberan.

Otra vez, `R≈1` no es salud. En este banco aparece incluso con más frecuencia entre los
negativos: es respuesta pasiva compatible, no selección de una línea.

## 4. Los siete contraejemplos que impiden una ley estática

Tres films tienen captura Q W4 a t=20 y no llegan sanos a 60:

* `par003_t_k03_tau02`
* `olaB_par036_t_k03_tau02`
* `olaB_par029_t_k03_tau02`

Los tres viven en respuesta no plana. Dos muestran también S1/S2 casi perfectos a t=20.
Por tanto, ni siquiera Q+S1+S2 trabados garantizan supervivencia futura: una captura puede
seguir chirpeando o abandonar la banda en un horizonte mayor. W4 ve el coqueteo; W8 y la
persistencia futura deciden si se convirtió en link estable.

Cuatro films hacen el recorrido inverso: no tienen captura Q W4 al borde t=20 y llegan
sanos a 60:

| film | `t_lock` W8 histórico |
|---|---:|
| `par069_t_k03_tau02` | 20.376 |
| `olaB_par070_t_k03_tau02` | 28.336 |
| `olaB_par007_f_k03_tau02` | 40.832 |
| `olaB_par010_f_k03_tau02` | 47.240 |

Son capturas tardías reales. Una regla aplicada sólo en t=20 las mataría antes de que se
formen.

Éste es el límite decisivo de cualquier score de nacimiento: el sistema continúa
cambiando. La salud no es una propiedad fija que pueda inferirse perfectamente desde la
primera ventana.

## 5. Orden temporal: cambio antes que forma, con resolución limitada

Entre los 18 sanos donde ocupación y lock primario ya aparecen antes de t=20, la ocupación
se confirma primero en 15/18, con mediana:

`t_occupation - t_primary = -3.5 u.t.`

S1 precede a la forma primaria en 15/15 casos medibles y S2 en 13/14. Sin embargo, por el
soporte W4/W8, la mayoría de intervalos se solapan: sólo 2 casos prueban ocupación
inequívocamente anterior y ninguno prueba el orden inverso.

La lectura compatible con Gate F y Gate G es:

`competencia de línea -> consolidación variable -> coherencia primaria visible`

El primer cambio común es la competencia/ocupación Q. S1 y S2 pueden adelantarse a la
forma visible, pero su identidad depende de la ruta.

## 6. Regla mínima operacional para el modelo evolutivo

No aparece una “fórmula de supervivencia” inmutable. Aparece una máquina de estados de
cuatro pasos que usa medidas ya existentes:

1. **Candidato:** `rho_pred` indica que el receptor podría amplificar la línea.
2. **Link provisional:** `rho_obs>1`; la línea compartida ganó la competencia espectral.
3. **Link sano ahora:** coherencia Q W8 sostenida, deriva en la misma fase corregida y
   señal no muda.
4. **Evolución:** reevaluar; release devuelve el link a provisional o ausente, y una
   recaptura tardía puede volver a crearlo.

S1/S2 quedan como coordenadas de maduración y diagnóstico de ruta. No deben ser puertas
universales de supervivencia. `R` queda como validación del mecanismo lineal cuando la
banda es plana, no como criterio de vida.

La regla natural y simple es:

> Un link está vivo mientras una línea compartida gane y conserve coherencia; sobrevive
> si ese estado persiste o se recaptura antes del horizonte de selección.

Esto encaja con captura, entrainment y phase slips de dinámica forzada conocida, pero la
decisión sale de los films: responde correctamente, gana la línea y la mantiene son tres
cosas distintas.

## 7. Consecuencia para grumos y olas

El modelo no debería congelar un edge después del primer lock ni destruir para siempre un
par que todavía no capturó. Entre olas:

* los onions siguen evolucionando;
* los links provisionales compiten por ocupación;
* sólo los links coherentes aportan conectividad efectiva al grumo;
* releases y recapturas cambian el grafo;
* los clusters se observan sobre la persistencia/recurrencia de edges sanos, no sobre una
  coincidencia instantánea de frecuencias.

Así la complejidad queda en la trayectoria del sistema, no en mil parámetros de fitness.

## 8. Límites

* Banco balanceado por outcome conocido; AUC y proporciones son descriptivos.
* Las capas eran nuevas para el frente, pero los films no son un experimento prospectivo.
* W4 puede sostener coqueteos que W8 rechaza; no son estimadores intercambiables.
* La corrección local por ventana detecta estado instantáneo, no deriva acumulada entre
  ventanas.
* No hubo cirugía causal sobre capas ni sobre ocupación.
* El outcome termina en 60 u.t.; no demuestra estabilidad asintótica.

## 9. Reproducción

```bash
PYTHONPATH=src:tools/link_grumo python3 tools/link_grumo/gate_g_select_holdout.py \
  --health logs/link_grumo/gate_f_health_coordinates.json \
  --gate-f-bank logs/link_grumo/gate_f_bank.json \
  --tables-root /Users/cagostino/code/doft-study07-worldline/data/census_arnold \
  --worldlines-root /Volumes/ExternalDisk/study07_census_arnold \
  --output logs/link_grumo/gate_g_bank.json

PYTHONPATH=src:tools/link_grumo python3 tools/link_grumo/gate_g_early_timeline.py \
  --bank logs/link_grumo/gate_g_bank.json \
  --blocks /Users/cagostino/code/doft-study06-fundamental-lock-dynamics/data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json \
  --output logs/link_grumo/gate_g_early_timeline.json

PYTHONPATH=src:tools/link_grumo python3 tools/link_grumo/gate_g_evaluate.py \
  --early logs/link_grumo/gate_g_early_timeline.json \
  --health logs/link_grumo/gate_f_health_coordinates.json \
  --output logs/link_grumo/gate_g_evaluate.json
```
