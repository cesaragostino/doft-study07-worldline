# Gate J — instrumento causal de potencia y barrido poblacional

Fecha: 2026-08-02. Branch `research/link-grumo-dynamics`.

Gate J implementó el prerregistro `LINK_GRUMO_GATE_J_POWER_PREREG.md` y ejecutó el
instrumento sobre todos los films archivados del census. No cambió Gate H, los veredictos
W4/W8 ni la regla de fitness. El disco externo fue entrada de sólo lectura; vistas y
ledger quedaron bajo `logs/link_grumo`.

## 1. Resultado operacional

| magnitud | resultado |
|---|---:|
| films encontrados | 375 |
| vistas válidas | 375 |
| fallos | 0 |
| hashes de vista únicos | 375 |
| pares single-edge identificables | 375 |
| films de 60 u.t. | 301 |
| films de 120 u.t. | 74 |
| tamaño total de vistas | 15 MB |
| corrida final | 1,556 s con 2 lectores |
| re-verificación/reuso completa | 1.8 s |

El ledger es `logs/link_grumo/gate_j_power_population.json`, SHA-256
`6bbb9eee5f26e90c104d95598063b44caf053b963016fd6f21087ccaa8106934`.
Las 301 unidades cortas publican 233 cajas causales completas; las 74 largas, 473.

Esto cierra la pregunta práctica: la potencia puede medirse sobre la población existente
sin resimular. Tampoco requiere la constitución completa: usa únicamente la fuerza que el
motor ya registró y la suma de velocidades del estado previo.

## 2. Instrumento incorporado

`study07.instruments.link_power` v1.1 publica:

```text
P[k,j] = drive[k,j] * sum_m v_j,m[k-1]
```

con caja trailing de 2 u.t. calculada a tasa completa y salida cada 0.25 u.t. La vista
incluye potencia instantánea y media, fracción negativa, RMS de fuerza, `P/F²`, trabajo
acumulado y soporte completo/incompleto de la caja.

No publica un veredicto de salud. En particular:

* `P>0` significa inyección al nodo, no supervivencia;
* `P<0` significa extracción, no muerte automática;
* `P≈0` sólo se interpreta junto con `force_rms` y vitalidad;
* `P/F²` no se interpreta cuando el drive está en el piso.

Así la máquina ya puede recibir potencia sin confundir un número diminuto sobre un canal
apagado con balance energético real.

## 3. Causalidad y controles

La alineación `drive[k] × v[k-1]` quedó anclada con un caso donde usar `v[k]` produce otro
valor. También se verificaron:

* inyección y extracción con signo conocido;
* subventanas sin fuga de potencia anterior a `t0_tick`;
* invariancia de la caja ante el `hop` de publicación;
* rechazo fuerte de drive ausente/no finito y config inválida;
* declaración explícita de topología multiarista no identificable por edge;
* igualdad de arrays y `view_hash` entre el camino en memoria y el streaming, incluyendo
  el primer paso de un chunk que depende del último estado del chunk anterior.

La fórmula no nace sólo de estos tests: el tap de transferencia ya la había comparado con
la ley real y había obtenido cierre energético full-rate con residuo relativo menor que
`1e-5` en los films s600.

## 4. Optimización sin cambio de estimando

El primer intento poblacional mostró que `api.load_run` cargaba estados, kicks y todos los
chunks completos de varios films simultáneamente. El cálculo era barato, pero la presión de
memoria convertía el disco en cuello de botella.

Se agregó `link_power.run_path`: verifica manifiesto, COMPLETE y SHA de cada chunk; lee cada
chunk una vez; conserva sólo `drive` y suma modal de velocidades; transporta el estado
anterior a través del borde de chunk. Produce exactamente la misma vista que `run`.

La media trailing no resta cumsums globales. Cada caja publicada se reduce localmente sobre
sus muestras full-rate, evitando cancelación catastrófica cuando P cae muchas décadas.

## 5. Identificabilidad

Los 375 films del census tienen dos nodos y una arista. Por tanto, `P_node[:,j]` es potencia
del único link sobre el extremo `j`: el contraste poblacional no tiene ambigüedad de edge.

Esto no se extrapola automáticamente a grumos. Si un nodo tiene grado mayor que uno, la
worldline actual registra la suma de fuerzas y sólo identifica potencia neta del puerto
nodal. El instrumento se niega a repartirla entre links mediante locks o amplitudes.
Para potencia por edge en un grumo futuro, el recorder deberá guardar contribuciones por
arista o correr una intervención que las separe.

## 6. Qué quedó listo y qué no se abrió

Quedó lista una coordenada causal continua para cruzar con:

* formación y releases W4/W8;
* transported/fresh;
* ocupación de línea y régimen plano/no plano;
* vitalidad en ventanas posteriores disjuntas.

Gate J no abrió todavía esos outcomes. Por tanto aún no afirma que potencia temprana
prediga supervivencia, ni la promueve a fitness. El contraste siguiente debe congelar antes
de leer resultados:

1. cómo se asigna emisor/receptor sin mirar el outcome;
2. ventana temprana de potencia y ventana tardía de salud disjuntas;
3. tratamiento de inversión de signo y dirección cambiante;
4. control conjunto por selección de línea y coherencia;
5. análisis separado de magnitud, signo y drive apagado.

## 7. Reproducción

```bash
PYTHONPATH=src:tools/link_grumo python3 \
  tools/link_grumo/gate_j_power_population.py \
  --worldlines-root /Volumes/ExternalDisk/study07_census_arnold \
  --views-root logs/link_grumo/gate_j_power_views \
  --output logs/link_grumo/gate_j_power_population.json \
  --workers 2

PYTHONPATH=src python3 -m pytest -q tests/test_link_power.py
```

Commits de construcción anteriores a la lectura poblacional: `c97cf79` (contrato,
instrumento, runner y gates) y `039a7ed` (streaming bit-equivalente).
