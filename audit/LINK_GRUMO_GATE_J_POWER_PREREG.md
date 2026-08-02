# Gate J — prerregistro del instrumento causal de potencia

Fecha: 2026-08-02. Branch `research/link-grumo-dynamics`.

## 1. Pregunta

Gate H distingue conectividad espectral de vitalidad, pero deja el eje de potencia en
`UNKNOWN`. Gate J pregunta si un link que domina espectralmente está inyectando energía
en el receptor, extrayéndola o conservando sólo una cola geométrica mientras se apaga.

El instrumento se incorpora como medición continua. No modifica los estados de Gate H,
no redefine `lock` y no entra todavía en fitness.

## 2. Magnitud y alineación congeladas

La worldline registra `drive[k,j]`: fuerza Kelvin–Voigt total aplicada al nodo `j` en el
subpaso 0 del paso `k`. Ese subpaso parte del estado almacenado en `estados[k-1]`.
Como la misma fuerza se aplica a todos los modos del nodo, la potencia de puerto es:

```text
P_node[k,j] = drive[k,j] * sum_m v_j,m[k-1]
```

Convención:

* `P_node > 0`: el campo inyecta energía mecánica al nodo;
* `P_node < 0`: el campo extrae energía mecánica del nodo;
* `P_node = 0`: balance instantáneo, no prueba ausencia de link.

Se prohíbe usar `v[k]`: mezclaría la fuerza del comienzo del paso con el estado posterior.
La fórmula anterior ya fue verificada contra la ley y produjo cierre energético full-rate
con residuo relativo menor que `1e-5` en el tap de transferencia.

## 3. Serie publicada

El instrumento `link_power` calcula el producto a tasa completa y publica una grilla
barata después de agregar causalmente:

* `p_node_instant`: muestra instantánea, principalmente para auditoría;
* `p_node_mean`: media trailing de caja de 2 u.t.;
* `fraction_negative`: fracción trailing con potencia negativa;
* `force_rms`: RMS trailing de la fuerza;
* `p_over_force2`: `p_node_mean / force_rms²`, siempre citada junto a `force_rms`;
* `work_node`: integral causal acumulada desde el comienzo de la ventana;
* `window_complete`: declara cuándo la caja causal ya tiene soporte completo.

La caja se evalúa sobre las muestras full-rate antes de submuestrear la salida. Así el
`hop` no redefine la potencia ni introduce aliasing en el producto.

Defaults congelados para la vista poblacional:

```text
box_ut = 2.0
hop_ut = 0.25
t0_tick = 1
t1_tick = fin del film
```

No habrá umbral de signo optimizado en esta etapa. Una potencia minúscula sobre drive
apagado debe conservar su número y combinarse después con `force_rms`/vitalidad, no ser
promovida silenciosamente a `BALANCED`.

## 4. Qué identifica el film

El canal `drive[:,j]` contiene la suma de todas las fuerzas de red sobre el nodo.

* En una unidad con dos nodos y una sola arista, `P_node[:,j]` es potencia de ese link
  sobre el extremo `j`: identificación por arista válida.
* Con grado mayor que uno, sólo se identifica la potencia neta de puerto del nodo. No se
  repartirá entre aristas usando amplitudes, locks ni pesos: eso fabricaría una
  descomposición que la worldline no registra.

La vista publicará grados nodales y la bandera `single_edge_pair_identifiable`.

## 5. Uso poblacional y criterio de decisión

El primer barrido será offline y read-only sobre los 375 films archivados. Las vistas y
el ledger derivados quedarán bajo `logs/link_grumo`; nunca en el disco externo.

La potencia se cruza contra estados ya sellados, sin reentrenarlos:

1. `DOMINANT` con `p_receiver>0` y actividad no muda: recepción energéticamente financiada;
2. `DOMINANT` con drive/actividad en piso: cola espectral, no supervivencia;
3. `DOMINANT` con `p_receiver<0`: receptor exportador o link actuando como sumidero;
4. `RELEASED` con trabajo/memoria remanente: posimagen, no canal vivo.

El resultado que justificaría promover potencia a fitness debe ser prospectivo: potencia
en una ventana temprana predice vitalidad o persistencia en una ventana posterior disjunta,
condicionando por selección de línea y coherencia. Correlación simultánea no basta.

## 6. Gates antes del barrido

1. alineación `drive[k]` contra `v[k-1]` anclada por valor;
2. ventanas trailing estrictamente causales y sin fuga antes de `t0_tick`;
3. signo verificado con inyección y extracción sintéticas;
4. invariancia de la caja frente al `hop` de publicación;
5. film sin `drive`, no finito o con formas incompatibles falla fuerte;
6. topología multiarista se declara no identificable por edge;
7. escritura de vistas sólo debajo del worktree y entradas externas read-only.

Gate J es inicialmente un instrumento de medición. La regla evolutiva queda congelada
hasta abrir el contraste early-power → late-vitality.
