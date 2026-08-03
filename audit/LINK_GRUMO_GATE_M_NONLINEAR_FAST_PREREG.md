# Gate M — preregistro `NONLINEAR_FAST / SLOW_FROZEN`

Fecha: 2026-08-03. Estado de este archivo: **PRERREGISTRADO para calibración
retrospectiva**. Los outcomes y el resultado de Gate L son conocidos; todavía no se
calculó ninguna trayectoria de esta nula no lineal. Este preregistro debe quedar en un
commit anterior a la salida canónica.

## 1. Pregunta única

¿Cuánto del residuo de Gate L —en particular el residuo casi idéntico del ignitor
`1bc9dccc...` en `par133_t/par134_t`— se explica conservando la dinámica rápida no
lineal exacta del onion a amplitud finita, sin permitir evolución de las variables lentas
`b/e`?

No pregunta si la no-linealidad define salud, ni estima fitness, ni decide causalidad de
`b/e`.

## 2. Población e insumos congelados

Mismo panel Gate F de Gate L: 8 pares / 16 films, seleccionado retrospectivamente por
outcome. Casos prioritarios declarados antes de calcular: `par133_t`, `par134_t` y sus
fresh apareados. El resultado se publica igualmente para los 16; no se filtra por esos
cuatro.

Pins heredados de Gate L:

- banco F: `3e31e9439f0ac1b5ce226b7d5cf2bbf29d51ae66865db7d2949dc4638e4f9612`;
- evaluación F: `1a0d8998329c90607126d57b0965b350f22862932a337f563cae1000c9281162`;
- inventario v4: `1fb29af2e58475c2175dd5d8bb7ad4090fb386cbf21bec01f653dc04b4e28a67`;
- bloques: `adf8d436ef5da468a8ecaecf4c170e983b36f1599e439f8e23502b9801a5da9a`;
- salida Gate L: `e92276d77189b7804ed82f40a4ff0782fd9002149f034ac6de1bd40b50b94c53`.

Se vuelven a verificar `COMPLETE`, manifiesto y todos los chunks. Films y cápsulas se
leen del disco externo en modo read-only. Se prohíbe escribir allí.

## 3. Nula primaria

Estado completo inicial real por nodo: `(x,v,z,b,e)` en `t=0`.

`COUPLED-NONLINEAR-FAST/SLOW-FROZEN`:

- usa `study07.physics.rhs.derivatives` para `(x,v,z)`, incluyendo `tanh`, memoria
  dependiente de energía, dressing de frecuencia/acoples por `b0` y amplitud finita;
- fija `b(t)=b0` y `e(t)=e0` exactamente en todos los subpasos;
- usa el integrador RK4 y la semántica de delay del `Network` productivo;
- conserva la arista KV recíproca, pesos, `k`, `gamma`, `tau` e historia de llegada del
  manifiesto;
- temperatura cero, igual que los films del panel;
- no usa `drive` observado como frontera ni hace replay de ninguna variable del film.

Comparador congelado: `COUPLED-LINEAR-FROZEN` ya publicado por Gate L. El cambio entre
ambos mundos es sólo linealización rápida versus RHS rápido completo; ambos congelan
`b/e` y parten de la misma llegada.

## 4. Integración y convergencia

Horizonte 20 u.t. Ventanas `[0.2,2]`, `[2,10]`, `[10,20]`. Se excluye `[0,tau]` del
primer resumen por la historia transported.

- corrida primaria: `dt=8e-4`;
- convergencia: `dt=4e-4`;
- comparación sólo sobre la grilla común;
- si el error simétrico coarse/fine de Q o emisión supera `0.02` en alguna ventana, la
  unidad queda `NUMERICALLY_UNRESOLVED`; se publica y no se reemplaza por el paso que dé
  el resultado preferido.

## 5. Observables congelados

Misma métrica de Gate L, conjunta y por nodo:

`E=2*RMS(pred-film)/(RMS(pred)+RMS(film))`.

Se publica por ventana:

- `E_Q`, `E_emit`, `E_drive` de la nula no lineal;
- `linear_to_nonlinear_gain = E_linear_frozen - E_nonlinear_frozen`;
- razón `E_nonlinear/E_linear`, con división protegida;
- convergencia coarse/fine;
- series de error cada 0.008 u.t.;
- verificación exacta de que `b/e` no cambiaron durante la integración.

## 6. Lectura predeclarada

Primario: nodo ignitor de `par133_t/par134_t` en `[2,10]`.

- **CIERRE FUERTE por amplitud finita**: ambos casos resueltos tienen
  `E_Q_nonlinear<=0.10` y razón no-lineal/lineal `<=0.25`;
- **MEJORA MATERIAL, no cierre**: mediana de la razón en los dos casos `<=0.50`, sin
  satisfacer cierre fuerte;
- **NO CIERRA**: mediana de la razón `>=0.80`;
- valores intermedios se informan como parciales, sin forzarlos a una categoría.

Secundarios descriptivos:

1. mismo criterio en `[0.2,2]` y `[10,20]`;
2. fresh apareados: si la no-linealidad aumenta `E_Q` en más de `0.02` absoluto o cinco
   veces respecto del lineal, se declara control tensionado y se inspecciona antes de
   interpretar el ignitor;
3. sanos/no-sanos, transported/fresh y ruta: sólo medianas y casos, sin AUC ni p-values;
4. identidad entre par133/par134: se compara el tiempo de cruce de errores
   `{0.01,0.1,0.5,1}` sin exigir que siga siendo idéntico.

Si Gate M cierra, no se concluye “la no-linealidad es salud”: sólo que Gate L fallaba por
linealizar una órbita grande. Si no cierra, el próximo corte autorizado es replay
diagnóstico de `b/e(t)` observado. No se lanza 2x9 ni campaña nueva desde este resultado.

## 7. Límites que acompañan todo resultado

- panel retrospectivo y outcome-selected;
- horizonte temprano, no supervivencia a 60/600;
- variables lentas artificialmente congeladas;
- RHS direct-only v1;
- comparar con Gate L mezcla integradores distintos (`expm+ZOH` versus RK4 productivo),
  por eso se publica convergencia propia y no se exige bit-exactitud entre modelos;
- cualquier error de implementación, corrida descartada o cambio de contrato se registra
  antes de canonizar la salida.

Salida prevista:

- `tools/link_grumo/gate_m_nonlinear_fast.py`;
- `audit/LINK_GRUMO_GATE_M_NONLINEAR_FAST.json`;
- lectura narrativa y bitácora después del cálculo.
