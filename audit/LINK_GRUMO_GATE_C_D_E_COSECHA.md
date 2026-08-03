# Gates C–E — transferencia, captura compleja y horizonte fijo

Estado: exploratorio, branch paralelo, no canónico. No se corrieron films nuevos. El disco
externo se abrió sólo para lectura; los chunks usados se verificaron contra `COMPLETE`. No
se modificó `docs/bitacora`. Las salidas completas viven en `logs/link_grumo/` y no se
versionan.

## Pregunta

¿La línea que aparece en el seguidor es sólo señal presente en el mismo bin, o es una
respuesta causal del receptor al campo del socio? ¿Qué parte de la salud explica la
constitución del receptor, qué parte identifica una captura ya formada, y qué parte queda
sin explicar?

Se usaron dos observables sin ajuste poblacional:

```text
rho_pred = |chi_Q(omega_linea)| A_force / A_competidor
R        = (Q_hat/F_hat) / chi_Q(omega_linea)
```

`rho_pred` estima si la línea forzada puede vencer la señal competidora. `R≈1` exige a la
vez amplitud y fase correctas: no sólo hay potencia en el bin, el receptor está obedeciendo
su transferencia causal.

## C0 — calibración antes de mirar outcomes

`chi` se calculó sobre el Jacobiano de la ley real en `(x,v,z)`, con `b,e` congeladas y
drive externo unitario. No es el sustituto x-only `M,C,K`: conserva la memoria interna `z`.

- Receptor de `par134`: recupera notches Q0=33.695 y Q1=34.375, a 0.005 rad/u.t. de los
  valores arbitrados 33.69 y 34.37.
- Control `par129`: cero mínimos espurios Q0/Q1/Q2 en 20.4–28.
- Films de 600 u.t.: 11 modos elegibles reproducen
  `A_L/(|chi|F)=1`; máximo error de la mediana por modo 0.123%. `par132-Q0` queda publicado
  pero excluido de calibración por la fuga espectral autónoma ya arbitrada.

Esto valida el instrumento y también una restricción: donde `chi` varía mucho dentro de una
Rayleigh, evaluarla en el centro de W8 no representa la convolución de la ventana. Hay 102
de 164 casos con `max(chi)/min(chi)>2` en `omega±Rayleigh/2`; se publican, pero el estrato
plano se analiza aparte.

## C1 — qué compra la susceptibilidad

En 164 films tempranos:

- `chi_Q` sola no separa salud: AUC 0.463 con el endpoint inicialmente usado.
- En banda plana, la identidad de amplitud cae dentro de factor 2 en 60/62 films.
- Vestir al receptor con su `b` inicial no explica la ventaja biográfica. En el banco B1,
  mediana `chi_vestida/chi_fria=1.00000004` para transported; el error de transferencia no
  cambia materialmente. Fresh tiene `b=0` por construcción.

La biografía no parece actuar primariamente desplazando la susceptibilidad rápida del
**receptor**. La separación aparece en la fuerza emitida, la coherencia de la trayectoria y
la ocupación espectral que el par ya trae.

## D1 — negativo importante: no es un polo frío del grumo

Se probó la geometría lineal de dos nodos con auto-término del acople:

```text
L = chi_i D chi_j D exp(-2 i omega tau) /
    [(1 + chi_i D)(1 + chi_j D)],     D = k + i gamma omega
```

Si el link fuera una auto-oscilación fría tipo Barkhausen/Nyquist, `L` debería acercarse a
`+1`. No ocurre:

- `|L|` mediano en sanos: 0.0071; distancia a `+1` ≈1;
- distancia y fase de Nyquist no separan sanos;
- retirar el banco de descubrimiento no rescata el criterio.

Este negativo favorece entrainment de trayectorias ya oscilantes frente a nacimiento por
inestabilidad lineal del lazo frío. No excluye un atractor no lineal o vestido más tarde.

## D2 — la firma de captura forzada

En los nueve transported remotos exitosos y sus fresh apareados, ventana `[0.5,5]`:

- transported resolubles: 6/6 cierran la fase de `R`, error mediano 0.085° y máximo 0.944°;
- fresh resolubles: 1/5 dentro de 15°, mediana 55.46°;
- los cuatro transported que siguen siendo resolubles al partir la ventana cierran en ambas
  mitades, mediana del peor error 0.335°; fresh 0/4, mediana 128.95°;
- en los nueve pares completos transported tiene menor error de fase y menor error complejo
  en 9/9.

El outlier transported de 81.9° (`olaB_par085`) no contradice el patrón: su línea está a
0.265 rad/u.t. de la propia con Rayleigh 1.396, por lo que `Q_hat/F_hat` mezcla ambas.

La lectura mínima es fuerte: en los remotos resolubles exitosos, el seguidor no comparte
sólo una frecuencia; su componente compleja satisface `Q=chi F`.

## E — corrección del horizonte 60/120

Gate B3 reutilizó `estado/dw_tardia` de tablas como si todos fueran `[50,60]`. Auditoría de
las views mostró 151 films de 60 u.t. y 13 de 120 u.t. Se rehízo el veredicto a un horizonte
común:

- `rw_final` con W8 sobre la fase corregida truncada a 60;
- `dw_tardia` en `[50,60]`;
- salud_60 = `rw_final>=0.95 AND dw<0.1375`.

La implementación replica los 151 films nativos de 60 con error exacto cero en `rw`, `dw`
y firmeza. Cuatro de los trece films largos cambian de outcome. Por eso los AUC de salud de
Gate B quedan retirados y los siguientes los sustituyen.

### Resultado con horizonte fijo

Hay 8 sanos a 60: 6 transported y 2 fresh.

| predictor temprano `[0,8]` | total | transported | fresh |
|---|---:|---:|---:|
| `rho` observada | 0.883 | 0.956 | 0.698 |
| `rho_pred = |chi|F/A_comp` | **0.944** | **0.979** | **0.918** |
| error complejo menor | 0.800 | 0.862 | 0.560 |

Los valores son AUC descriptivos; fresh tiene sólo 2 positivos. La mejora
`rho_observada→rho_pred` es la evidencia concreta de que la constitución del receptor agrega
información: no basta medir cuánta señal llegó, importa cuánto puede responder ese onion a
esa frecuencia.

En transported, los 6/6 sanos tienen cierre complejo temprano; 0/34 sin cierre complejo es
sano a 60. Pero 31 no sanos también cierran: es condición necesaria en esta muestra, no
suficiente. La conjunción no ajustada `rho_pred>1 AND cierre_complejo` da 3/4 sanos, pero
omite otros tres sanos con `rho_pred<1`: alta pureza, mala cobertura.

Fresh muestra otra cronología. Sus dos sanos a 60 no tienen cierre complejo en `[0,8]` y
poseen errores de fase iniciales de ~143–146°: el canal nace después. Por eso una medición
única en el arranque identifica **captura ya formada**, no supervivencia universal.

## Qué significa ahora “link sano”

La regla mínima compatible con los datos ya no es un escalar único:

1. **Elegibilidad/ocupación:** `rho_pred` pregunta si fuerza × susceptibilidad puede vencer
   al competidor interno.
2. **Captura actual:** `R≈1` pregunta si la respuesta compleja ya obedece causalmente al
   socio.
3. **Maduración:** frecuencia y fase primarias cierran después; fresh puede llegar tarde.
4. **Supervivencia:** duración, release y recaptura todavía no están resueltos por el
   endpoint de 60.

Esto es compatible con un sistema de osciladores forzados y chirpeados, pero no se impone
como “la física conocida”. El criterio frío de Nyquist falló; la identidad de transferencia
forzada pasó. La distinción la hicieron los datos.

## Relación con S2

Estos gates trabajan sobre la línea Q y no sustituyen el hallazgo S2. Proponen una forma más
precisa de conectarlo:

> S2 puede anunciar o estabilizar el nacimiento del canal; `R_Q≈1` dice cuándo el canal Q
> ya está causalmente capturado; `rho_pred` dice si puede ocupar al receptor; el lock
> primario y la persistencia son etapas posteriores.

El test siguiente no debe correlacionar resúmenes globales. Debe medir tiempos de evento en
ventanas disjuntas: `t_cierre_S2`, `t_RQ`, `t_dominancia`, `t_lock_primario`, releases y
recapturas.

## Próxima cosecha, orden valor/CPU

1. En los 8 sanos a 60 y controles apareados, construir trayectorias móviles de `R_Q(t)` y
   `rho_pred(t)`; localizar nacimiento/release del canal. Sólo lee films existentes.
2. Sobre las mismas ventanas, calcular el cierre complejo S1/S2 y contrastar el orden
   `S2 → R_Q → dominancia → lock`; no asumirlo.
3. Extender a los films 120/600 para distinguir captura, release y recaptura de una mera
   maduración lenta.
4. Recién entonces ampliar a toda la población y clusterizar por nodo compartido.

## Reproducción

Los comandos principales son:

```bash
python3 tools/link_grumo/gate_c_validate_transfer.py --blocks BLOCKS --output logs/link_grumo/gate_c_validate_transfer.json
python3 tools/link_grumo/gate_c_validate_long.py --spec SPEC600 --series-root SERIES --output logs/link_grumo/gate_c_validate_long.json
python3 tools/link_grumo/gate_c_population.py --blocks BLOCKS --gate-b logs/link_grumo/gate_b_population.json --gate-b-evaluate logs/link_grumo/gate_b_evaluate.json --arrival logs/link_grumo/gate_b_arrival.json --output logs/link_grumo/gate_c_population.json
python3 tools/link_grumo/gate_d_nyquist.py --blocks BLOCKS --gate-c logs/link_grumo/gate_c_population.json --output logs/link_grumo/gate_d_nyquist.json
python3 tools/link_grumo/gate_d_phase_transfer.py --blocks BLOCKS --arrival logs/link_grumo/gate_b_arrival.json --output logs/link_grumo/gate_d_phase_transfer.json
python3 tools/link_grumo/gate_d_population_phase.py --blocks BLOCKS --gate-c logs/link_grumo/gate_c_population.json --output logs/link_grumo/gate_d_population_phase.json
python3 tools/link_grumo/gate_e_fixed_horizon.py --tables-root TABLES --gate-d logs/link_grumo/gate_d_population_phase.json --output logs/link_grumo/gate_e_fixed_horizon.json
```
