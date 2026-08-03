# Gate K — prerregistro potencia temprana → salud tardía

Fecha: 2026-08-02. Branch `research/link-grumo-dynamics`.

## 1. Pregunta y separación temporal

Gate J produjo una medición causal de potencia para los 375 films del census. Gate K
pregunta si esa medición aporta información sobre supervivencia y no sólo describe un
link que ya está sano.

La comparación primaria queda congelada antes de cruzar potencia con outcome:

```text
predictor: link_power en [2,20] u.t. (cajas trailing de 2 u.t.)
outcome:   coordinate_health en [50,60] u.t. sellado por Gate F
```

La primera caja completa termina en `t=2`; la última caja temprana termina en `t=20`.
No hay muestras ni soporte causal entre 20 y 50 en el predictor. No se modifican Gate F,
Gate H, `lock`, fitness ni los datos externos.

Entradas congeladas:

* `logs/link_grumo/gate_j_power_population.json`;
* `logs/link_grumo/gate_f_health_coordinates.json`;
* `logs/link_grumo/gate_g_evaluate.json`, sólo para el control secundario por dinámica
  temprana ya abierta.

Los joins exigirán igualdad exacta de `run_id` y `worldline_hash`. Las views de potencia
se resolverán por hash y se verificarán con su manifest; no se releerán worldlines.

## 2. Coordenadas de potencia sin elegir roles por outcome

Para cada caja completa, sean `P0` y `P1` las potencias medias de los dos extremos:

```text
entrada    = max(P0,0) + max(P1,0)
salida     = max(-P0,0) + max(-P1,0)
intercambio = min(entrada, salida)
```

`intercambio` es positivo sólo cuando un extremo recibe potencia y el otro la entrega.
Es invariante al orden de los nodos y no presupone quién es emisor, receptor, líder o
superviviente. No se elegirá el signo retrospectivamente.

Sobre cada intervalo se publicarán, sin umbral optimizado:

* `exchange_rate`: media de `intercambio`;
* `opposed_fraction`: fracción de cajas con `P0*P1<0`;
* `net_power`: media de `P0+P1`;
* `dissipation_rate`: media de `max(-(P0+P1),0)`;
* `injection_rate`: media de `max(P0+P1,0)`;
* `force2`: media de `force_rms[0]^2 + force_rms[1]^2`;
* `exchange_efficiency = exchange_rate/force2`, siempre acompañada por `force2`.

La coordenada primaria es `exchange_rate`. `exchange_efficiency` y
`opposed_fraction` preguntan por geometría/dirección de transferencia; `force2` evita
confundir potencia con mera magnitud de drive. Un denominador cero produce `null`, no un
valor imputado.

## 3. Población y contrastes congelados

### 3.1 Contraste primario apareado

Se usarán los 170 pares transported/fresh de Gate F. El contraste informativo principal
son los pares discordantes en `coordinate_health`: mismo par, genomas, `dw` aislado y
semilla, distinto brazo/biografía. Para cada coordenada se contará:

* sano mayor;
* no sano mayor;
* empate;
* mediana de la diferencia sano menos no sano.

El resultado es descriptivo porque los nodos se reutilizan entre pares. No se fabricará
un `p` iid por film. También se informarán AUC y medianas para toda la población y por
brazo, con la misma advertencia.

### 3.2 Aporte más allá de fuerza, biografía y `dw`

En los 340 films se comparará `exchange_rate` con `force2` y se calculará un residual de
ranking de potencia después de ajustar únicamente por:

```text
arm + log1p(isolated_dw) + ranking(force2)
```

El ajuste no usa el outcome. Su AUC residual es diagnóstico de aporte condicional, no
una ley causal ni un nuevo score.

### 3.3 Control por coherencia y ocupación tempranas

El banco case-control apareado de Gate G contiene 60 films cuyas capas ya fueron
abiertas hasta `t=20`. Se evaluará por leave-one-pair-out, con regresión logística ridge
fija (`lambda=1`), sin búsqueda de hiperparámetros:

```text
M0 dinámica: arm + log1p(dw) + primary_rw_end20 + log1p(rho_observed_end20)
M1 drive:    M0 + force2
M2 potencia: M1 + exchange_rate + exchange_efficiency + opposed_fraction
```

Las variables positivas de escala abierta se transformarán dentro de cada fold con
`asinh(x/mediana_positiva_train)` y luego todas las columnas continuas se estandarizarán
con el train. Se informarán AUC y log-loss out-of-pair. Gate G fue seleccionado por
outcome: estos números comparan mecanismos dentro de ese banco y no son prevalencia ni
validación independiente.

## 4. Sensibilidades y fuera de patrón

La ventana primaria `[2,20]` tendrá tres sensibilidades congeladas:

* `[2,10]`: señal muy temprana;
* `[10,20]`: consolidación temprana;
* `[20,40]`: maduración todavía disjunta del outcome.

Se repetirán los rankings con `raw_health` y con `firm` de Gate F. La población limpia
excluye las banderas armónicas/mudas; la inclusión de las tres banderas se informa como
sensibilidad, no se decide después de ver el signo.

Se listarán explícitamente:

* sanos con poca transferencia temprana;
* no sanos con mucha transferencia temprana;
* casos donde fuerza y potencia discrepan;
* fallos de coherencia temprana de Gate G que la potencia corrige o empeora.

Los extremos se definen por cuartiles poblacionales, no por cortes elegidos mirando los
outcomes.

## 5. Lecturas posibles ya congeladas

1. **Potencia aporta:** el sano gana apareadamente y M2 mejora el log-loss fuera de par
   respecto de M1 sin inversión grave entre brazos. Justifica conservar potencia como
   coordenada de vitalidad a probar prospectivamente; no justifica meterla en fitness.
2. **Potencia replica drive:** `exchange_rate` separa, pero pierde señal al controlar
   `force2` y M2 no mejora M1. Sirve para contabilidad energética, no como orden de salud.
3. **Potencia es tardía:** `[20,40]` separa pero `[2,20]` no. Describe consolidación, no
   predice nacimiento.
4. **No aporta o invierte:** se conserva el instrumento para diagnóstico físico y se
   rechaza su promoción a supervivencia.

No se exige que una física conocida gane. El objetivo es saber si el link conectado está
energéticamente vivo y si esa propiedad antecede a su salud tardía.

## 6. Contrato de integración provisional

Hasta abrir Gate K, `link_power` permanece aditivo y opt-in:

* views nuevas con `instrument_id/version/config_hash`, sin sobrescribir views viejas;
* `view_hash_power` opcional en ledgers futuros;
* ausencia de la vista significa `UNKNOWN`, nunca `0` ni link muerto;
* ningún cambio silencioso de estados, outcomes históricos o fitness;
* merge por commits separados: instrumento+tests, runner poblacional, y sólo después
  documentación/veredicto.

El plan definitivo de integración se escribirá después del resultado, para que el branch
principal pueda aceptar la medición sin aceptar por accidente una regla de selección.
