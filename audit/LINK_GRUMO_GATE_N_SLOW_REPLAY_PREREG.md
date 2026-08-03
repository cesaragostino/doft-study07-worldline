# Gate N — preregistro `OBSERVED_B_REPLAY`

Fecha: 2026-08-03. Estado de este archivo: **PRERREGISTRADO para diagnóstico
retrospectivo**. Gate M y todos los outcomes son conocidos. Todavía no se calculó
ninguna trayectoria con `b(t)` observado inyectado. Este archivo debe quedar en un
commit anterior a la salida canónica.

## 1. Pregunta única

¿La trayectoria estructural lenta observada `b(t)` es suficiente para reconstruir la
worldline rápida que Gate M no pudo explicar en el ignitor compartido por
`par133_t/par134_t`?

Esto no pregunta si `b` es causa, predictor ni salud. El replay usa una variable del
mismo outcome futuro; sólo localiza suficiencia dinámica dentro de la ley conocida.

## 2. Por qué no hay una rama `e(t)`

En `rhs.py`, `e` sólo aparece en la ecuación lenta de `db/dt`. No entra en las ecuaciones
de `(x,v,z)`. Si `b(t)` está prescrita y `db/de` se anulan, cambiar `e(t)` no puede
alterar la trayectoria rápida: sería una rama idéntica a Gate M por álgebra, no un
control independiente. Se registra esta degeneración antes de correr y se prueba en
unitario; no se gasta CPU en una comparación decorativa.

## 3. Población y jerarquía congeladas

Base: mismo panel outcome-selected de Gate F/L/M, 8 pares / 16 films.

1. `ALL_B`: los 16 films; replay de todas las capas de ambos nodos.
2. `SOURCE_ALL_B`: sólo `par133_t`, `par134_t` y sus fresh; replay de todas las capas
   del nodo 0, con receptor congelado.
3. `SOURCE_Q_B`: los mismos cuatro; replay exclusivo de la capa Q del nodo 0.

El orden `SOURCE_Q_B → SOURCE_ALL_B → ALL_B` no es selección por resultado: las tres
ramas de los cuatro prioritarios se publican siempre. `ALL_B` se publica en los 16 para
exponer controles y casos fuera del patrón. Nodo 0 se denomina «source» sólo en esta
intervención: para los primarios es el ignitor `1bc9dccc...`; no se generaliza el rol al
resto de la población.

## 4. Mundo contrafactual

Estado inicial e historia causal: idénticos a Gate M. Arista KV recíproca, delay, pesos,
`k`, `gamma`, `tau`, temperatura cero y RHS rápido completo: idénticos a Gate M.

En cada etapa RK4 (`t`, `t+dt/2`, `t+dt/2`, `t+dt`) se reemplazan las coordenadas `b`
marcadas por interpolación lineal de la worldline observada a resolución productiva
`8e-5`. Las coordenadas no marcadas permanecen en su valor de llegada. `e` se fija en
la llegada. Las derivadas lentas se anulan con `tau_b=tau_e=inf`; el estado final de
cada paso se vuelve a proyectar a la prescripción exacta antes de emitir y empujar la
historia.

La implementación reutiliza la fuerza, la semántica de delay y las funciones de estado
productivas. El adaptador de paso RK4 se audita porque prescribe estados también en los
subpasos; sobrescribir sólo al comienzo de cada paso queda prohibido.

## 5. Integración, convergencia y observables

Iguales a Gate M:

- horizonte 20 u.t.; ventanas `[0.2,2]`, `[2,10]`, `[10,20]`;
- primaria `dt=8e-4`, convergencia `dt=4e-4`, comparación en grilla común;
- `NUMERICALLY_UNRESOLVED` si el máximo de `E_Q/E_emit` coarse-fine supera `0.02`;
- error simétrico `E=2*RMS(pred-film)/(RMS(pred)+RMS(film))`, conjunto y por nodo;
- `E_Q`, `E_emit`, `E_drive`, series cada `0.008` u.t. y cruces de error;
- comparadores publicados: Gate M frozen y, para contexto, Gate L lineal frozen.

Se verifica que las coordenadas replay coincidan con la interpolación observada y que
las coordenadas frozen no deriven. Una unidad no convergente se publica y no se cambia
de paso para obtener el resultado preferido.

## 6. Lectura predeclarada

Primario: nodo 0 de `par133_t/par134_t`, `[2,10]`, rama `ALL_B`, comparado contra Gate M.

- **CIERRE FUERTE LENTO**: ambos resueltos tienen `E_Q<=0.10` y
  `E_Q_replay/E_Q_M<=0.25`;
- **MEJORA MATERIAL, no cierre**: mediana de razón `<=0.50` sin cierre fuerte;
- **NO CIERRA**: mediana de razón `>=0.80`;
- intermedio: se informa sin forzar categoría.

Localización jerárquica, sólo si `ALL_B` cierra fuerte:

1. si `SOURCE_Q_B` también satisface cierre fuerte: `SOURCE_Q_B_SUFFICIENT`;
2. si no, pero `SOURCE_ALL_B` sí: `SOURCE_NON_Q_B_REQUIRED`;
3. si sólo `ALL_B` cierra: `RECEIVER_B_REQUIRED`;
4. si ninguna cierra: `OBSERVED_B_NOT_SUFFICIENT`.

«Required» significa requerido dentro de este replay jerárquico, no causalidad física.
Los fresh prioritarios quedan tensionados si `E_Q` empeora contra Gate M más de `0.02`
absoluto o cinco veces. Los demás films, sanos/no-sanos, brazos y rutas son descriptivos
sin AUC, p-values ni claim poblacional.

## 7. Qué puede venir después

Si `SOURCE_Q_B` cierra, el corte siguiente barato es confrontar la ley de dressing
`omega_Q^2=omega_0^2(1+0.1 b_Q)` contra la fase/frecuencia residual y probar una versión
causal donde `b_Q` evolucione desde información temprana, no reinyectada desde el futuro.
Si requiere otras capas o receptor, se separan mediante ablaciones nuevas y
prerregistradas. Si `ALL_B` no cierra, la hipótesis lenta simple cae y se revisan estado
de memoria `z`, historia no resumida o física omitida antes de lanzar campañas.

En ningún desenlace Gate N produce una regla de supervivencia.

## 8. Pins

- Gate M JSON:
  `230381973ce113db05e2bdae08d89d790b11b0c5fede61df79ff99cf1cf8e9b8`;
- Gate M simulador:
  `43317c0856d5c9cec1ff32215a2c7326b95d404e2105dcb52ed5640f0886b49e`;
- banco F: `3e31e9439f0ac1b5ce226b7d5cf2bbf29d51ae66865db7d2949dc4638e4f9612`;
- evaluación F: `1a0d8998329c90607126d57b0965b350f22862932a337f563cae1000c9281162`;
- inventario v4: `1fb29af2e58475c2175dd5d8bb7ad4090fb386cbf21bec01f653dc04b4e28a67`;
- bloques: `adf8d436ef5da468a8ecaecf4c170e983b36f1599e439f8e23502b9801a5da9a`.

Films y cápsulas: read-only. Salida sólo local en `audit/`.
