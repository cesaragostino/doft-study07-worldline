# Gate L — preregistro de la nula transitoria bidireccional

Fecha: 2026-08-02. Estado al escribir este archivo: **PRERREGISTRADO para una relectura
retrospectiva**; los outcomes del banco F ya son conocidos, pero todavía no se calculó
ninguna trayectoria de la nula bidireccional ni sus residuos. No es un test ciego ni
autoriza una campaña nueva.

## 1. Pregunta

¿Cuánto de la trayectoria temprana de un par real explica el sistema rápido lineal de
los DOS onions, partiendo de sus estados e historias de llegada reales y cerrando la
retroalimentación Kelvin–Voigt en ambos sentidos?

No se pregunta si `det[I−ΧK]=0` define salud. Gate D ya volvió negativa esa hipótesis
fría. Se pregunta si cerrar el lazo mejora la predicción causal respecto de dos onions
lineales independientes, durante cuánto tiempo, y si el residuo que queda se organiza
por ruta y por salud.

## 2. Población congelada

Panel de calibración Gate F: 8 pares / 16 films. Es deliberadamente rico en outcomes y
por eso **no representa la población** ni produce p-values citables:

```text
olaB_par008_f  olaB_par008_t
olaB_par013_f  olaB_par013_t
olaB_par093_t  olaB_par093_f
olaB_par094_t  olaB_par094_f
par043_t       par043_f
par101_t       par101_f
par133_t       par133_f
par134_t       par134_f
```

Los sufijos completos son `_k03_tau02`. Fuente sellada:

- `gate_f_bank.json`: `3e31e9439f0ac1b5ce226b7d5cf2bbf29d51ae66865db7d2949dc4638e4f9612`;
- `gate_f_evaluate.json`: `1a0d8998329c90607126d57b0965b350f22862932a337f563cae1000c9281162`;
- inventario v4: `1fb29af2e58475c2175dd5d8bb7ad4090fb386cbf21bec01f653dc04b4e28a67`;
- bloques canónicos: `adf8d436ef5da468a8ecaecf4c170e983b36f1599e439f8e23502b9801a5da9a`.

Films y cápsulas se leen del archivo externo en modo read-only. Se exige `COMPLETE`,
hash de manifiesto y hash de todos los chunks. No se ejecuta el motor ni se escribe en
`/Volumes/ExternalDisk`.

## 3. Nulas, sin parámetros ajustados

Estado rápido por nodo: `y=(x,v,z)`. Las variables lentas `b/e` no se evolucionan.

1. **INDEPENDENT-FROZEN:** cada nodo evoluciona con su Jacobiano rápido aislado,
   congelado en el `b/e` real de llegada. No recibe fuerza del vecino.
2. **COUPLED-FROZEN (primaria):** mismos Jacobianos e IC, más la arista KV recíproca
   exacta del manifiesto:

   `F_i(t)=k[X_j(t−τ)−X_i(t)]+γ[V_j(t−τ)−V_i(t)]`.

3. **COUPLED-COLD (sensibilidad):** igual a 2, pero `b=e=0`.

`X,V` son la emisión declarada `0.1·Σ(x,v)`. Las historias `[-τ,0]` son parte de la IC:
quench exacto de la cápsula en transported y relleno uniforme de la emisión inicial en
fresh. No se usa el drive observado como condición de frontera.

La evolución numérica usa transición local exacta por exponencial matricial con el
drive retardado sostenido en cada paso (ZOH), `dt_model=8e-4`. No es bit-exacta al RK4
de producción. Toda unidad se repite a `dt_model=4e-4`; la convergencia se publica, no
se filtra. Horizonte: 20 u.t.; se excluye `[0,τ]` de todo resumen porque transported
lleva quench topológico declarado.

## 4. Observables congelados

Ventanas: `[τ,2]`, `[2,10]`, `[10,20]` u.t. Para cada nodo y ventana:

- error simétrico de la emisión `(X,V)`:
  `E=2·RMS(pred−film)/(RMS(pred)+RMS(film))`;
- mismo error para los tres modos Q conjuntos;
- error simétrico del drive KV;
- mejora por feedback: `ΔE = E_independent − E_coupled_frozen` (positivo ayuda);
- sensibilidad estructural: `E_cold − E_frozen` (positivo favorece congelar biografía);
- error de convergencia entre `dt=8e-4` y `4e-4`.

Se publican también series agregadas cada 0.008 u.t.; no se elige una frecuencia desde
el outcome ni se optimiza un umbral después de mirar.

## 5. Lectura y criterios de fracaso

Esto es calibración mecánica, no clasificación:

- el lazo bidireccional **compra trayectoria** sólo si la mediana de `ΔE` es positiva;
- una separación sano/no-sano se informa descriptivamente por brazo y ruta, sin AUC ni
  p-value como claim;
- si `ΔE≈0` aunque la nula acople, `det[I−ΧK]` queda como geometría espectral sin poder
  causal observable en este horizonte;
- si el coupled mejora temprano y pierde ventaja después, el punto de ruptura —no el
  error final— es el dato físico;
- si `E_frozen` y `E_cold` coinciden, la biografía actúa por IC/historia y no por vestir
  el Jacobiano; si difieren, se publica dirección y casos;
- si la convergencia numérica supera 0.02 de error simétrico en alguna unidad/ventana,
  esa unidad queda marcada `NUMERICALLY_UNRESOLVED`; no se descarta ni se reemplaza por
  el paso que dé el resultado más lindo.

## 6. Límites que deben viajar con cualquier conclusión

- panel seleccionado después de outcomes;
- ley v1 `direct-only`: kernels diferidos del genoma fuera de alcance;
- `b/e` congelados: no es una nula de plasticidad estructural;
- 20 u.t. sólo decide mecánica temprana, no supervivencia a 60/600;
- el ZOH del drive retardado no es el RK4 productivo; la doble resolución cuantifica esa
  aproximación, no la vuelve bit-exacta;
- aun un ajuste perfecto de trayectoria lineal no autoriza usar un polo/determinante
  como fitness.

## 7. Salida prevista

Herramienta: `tools/link_grumo/gate_l_bidirectional_transient.py`.
Salida: `audit/LINK_GRUMO_GATE_L_BIDIRECTIONAL_TRANSIENT.json` más lectura narrativa
separada. Este preregistro se committea antes de abrir esa salida.
