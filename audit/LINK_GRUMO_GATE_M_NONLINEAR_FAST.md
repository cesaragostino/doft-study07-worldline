# Gate M — lectura `NONLINEAR_FAST / SLOW_FROZEN`

Fecha: 2026-08-03. Estado: **EJECUTADO** después del preregistro
`LINK_GRUMO_GATE_M_NONLINEAR_FAST_PREREG.md`, sellado en el commit `ccb390a` antes de
calcular resultados.

## Veredicto primario

**NO CIERRA.** El RHS rápido no lineal completo, manteniendo `b/e` clavados en la
llegada, no explica el residuo del nodo ignitor compartido por `par133_t` y `par134_t`.
En la ventana primaria `[2,10]`:

| film | `E_Q` lineal, nodo 0 | `E_Q` no lineal, nodo 0 | razón |
|---|---:|---:|---:|
| `par133_t` | 1.3299454 | 1.3337123 | 1.0028324 |
| `par134_t` | 1.3299119 | 1.3336873 | 1.0028388 |

El umbral preregistrado de **NO CIERRA** era mediana de razón `>=0.80`; la mediana
observada es `1.0028356`. La corrección no sólo queda lejos del cierre fuerte
(`E_Q<=0.10` y razón `<=0.25`): empeora el error alrededor de `0.28%` en ambos films.
La identidad entre las dos worldlines persiste hasta el detalle: el nodo 0 cruza
`E_Q={0.01,0.1,0.5,1}` en `{0.316,0.908,2.012,3.572}` u.t. en los dos.

La negativa ya aparece en `[0.2,2]`, donde la razón es `1.1374070/1.1374054`, y se
mantiene en `[10,20]`, con `1.0032928/1.0032953`. No es un artefacto de elegir sólo la
ventana primaria.

## El control positivo que impide leerlo como fracaso del instrumento

En cada una de las tres ventanas mejoran **13 de los 15 films numéricamente resueltos**.
Los únicos resueltos que empeoran son, siempre, `par133_t` y `par134_t`. En `[2,10]`, la
mediana de todo el panel da razón `0.0880`; en los sanos, `0.0594`; en los no-sanos,
`0.2371`. Son descripciones de un panel outcome-selected, no estimaciones poblacionales.

Los fresh apareados del mismo par y genoma también mejoran:

| film | `E_Q` lineal | `E_Q` no lineal | razón | control tensionado |
|---|---:|---:|---:|---|
| `par133_f` | 0.000156765 | 0.000045923 | 0.292944 | no |
| `par134_f` | 0.000118037 | 0.000027991 | 0.237135 | no |

Por eso el resultado fino no es «la no linealidad rápida no importa». Importa mucho
para reproducir la dinámica ordinaria a amplitud finita, pero no toca la anomalía común
del ignitor transported. Tampoco parece una falla genérica de ese genoma: sus controles
fresh se mueven en la dirección correcta.

## Interpretación permitida

Gate L ya había mostrado que agregar el lazo recíproco compra trayectoria, pero no la
worldline del ignitor activo. Gate M elimina la explicación inmediata siguiente:
linealización rápida alrededor de amplitud cero. El mecanismo que falta está asociado al
estado transported y es compartido a través de dos socios distintos.

El próximo corte autorizado por el preregistro es inyectar la trayectoria observada de
`b/e(t)` dentro del RHS rápido. Ese replay puede responder si la evolución lenta
observada es **suficiente para reconstruir** la worldline, pero no si es causal ni si
predice salud: usa información futura del propio outcome. Si cierra, todavía habrá que
separar `b`, `e`, historia de llegada y cualquier forcing omitido mediante intervenciones
propias.

No se concluye que `b/e` sea «el mecanismo» y mucho menos una regla evolutiva. Gate M
solamente localiza la insuficiencia: no está en el lazo recíproco lineal ni en la
no-linealidad rápida con estado lento congelado.

## Calzones sucios y límites

- Panel retrospectivo y seleccionado por outcome: sin p-values, AUC ni prevalencia.
- RHS v1 `direct-only`; no prueba kernels diferidos que no existen en estos films.
- La comparación hereda integradores distintos: Gate L usa `expm+ZOH`, Gate M usa el
  RK4 productivo. La convergencia independiente de los dos primarios es muy holgada
  (`7.46e-7` y `7.36e-7`), y `b/e` derivan exactamente `0`, pero eso no vuelve los
  modelos bit-exactos.
- `par043_f` queda publicado como **NUMERICALLY_UNRESOLVED**: error coarse/fine máximo
  `0.03843 > 0.02`. No se sustituye ni se borra; queda fuera de los conteos resueltos.
- La primera prueba unitaria falló porque el fixture sintético omitía
  `schema_version`; se corrigió el fixture usando `NodeSpec` tipado. No se relajó el
  parser productivo.
- La primera ejecución serial se interrumpió después de `1/16` al medir unas cuatro
  minutos por unidad y no escribió salida. Se reraneó todo el panel en cuatro shards
  exhaustivos por índice módulo 4, declarados antes de ver resultados. El merge exige
  exactamente shards `0..3`, índices de panel `1..16`, 16 `run_id` únicos, mismos pins
  y deriva lenta nula.
- El gran descenso de `E_Q` no se replica necesariamente en `E_emit/E_drive` en todos
  los casos; Gate M se juzgó por `E_Q` tal como estaba preregistrado. Esos desacoples
  quedan como diagnóstico, no se esconden mediante un score compuesto post-hoc.

## Custodia

- salida canónica: `audit/LINK_GRUMO_GATE_M_NONLINEAR_FAST.json`;
- SHA-256 salida: `230381973ce113db05e2bdae08d89d790b11b0c5fede61df79ff99cf1cf8e9b8`;
- simulador: `tools/link_grumo/gate_m_nonlinear_fast.py`, SHA-256
  `43317c0856d5c9cec1ff32215a2c7326b95d404e2105dcb52ed5640f0886b49e`;
- merge: `tools/link_grumo/gate_m_merge.py`, SHA-256
  `f27f31641d8e1edf5bee05f63d64ec294f9fd7712d48e23ad7ea2b35cd4a8806`;
- preregistro: SHA-256
  `31c77dc3dc8a4afedddf217e5d8f90703a5c816b3179cd999f0e8a348e15d623`;
- Gate L comparado: SHA-256
  `e92276d77189b7804ed82f40a4ff0782fd9002149f034ac6de1bd40b50b94c53`.

Los insumos del disco externo se verificaron y leyeron sin escribir en él.
