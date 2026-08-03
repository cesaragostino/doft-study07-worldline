# Auditoría basal — apertura del frente link/grumo

Base Git: `6c2e92e27f7f40d1084c2094f96ee83bc88eaeca`.

Este documento registra el punto de partida del branch paralelo. Los cálculos son una
revisión exploratoria reproducible con `tools/link_grumo/baseline_census.py`; no reemplazan
`POOLED.json` ni se incorporan todavía a la bitácora canónica.

## Veredicto inicial

1. **La ventaja transported–fresh es grande y no parece una fluctuación.** Sin embargo,
   `P(primer t_lock <= 60)` mide exactamente la primera coherencia del detector, no
   necesariamente la primera captura física.
2. **La rodilla W4 coincide con la zona analítica de falso-firme del instrumento.** El
   umbral `R_W=0.95` da `1.1/W`: 0.275 para W4 y 0.1375 para W8. El angostamiento W8 no es
   por sí solo una réplica física independiente.
3. **W8 está anidado en W4.** En la celda principal, transported pasa 82→64 locks y fresh
   26→8: ambos pierden exactamente 18. Por eso el delta apareado queda idéntico; es
   robustez de umbral, no una nueva muestra.
4. **La tendencia global no describe la cola.** El estadístico de covarianza es negativo
   al incluir el núcleo, pero queda aproximadamente cero desde `dw>=0.3`. La cola requiere
   mecanismo propio.
5. **La biografía sigue ayudando bajo filtros diagnósticos de cierre.** Exigir cierre
   tardío reduce el delta, pero no lo elimina. Es un control retrospectivo, no un nuevo
   estimando sellado.
6. **Existe un banco remoto más pequeño y más fuerte.** Con W8, detuning temprano fuera de
   falso-firme y detuning tardío dentro, quedan nueve candidatos transported y cero fresh:
   siete en `dw aislado 1–10` y dos en `10–50`.
7. **Energía inicial es un predictor importante en la cola 1–10.** Entre transported W8,
   la mediana de `E0` es aproximadamente 0.273 en locks contra `1.83e-4` en fallos; AUC
   descriptiva ≈0.79. Esto apunta al presupuesto de drive como primer mecanismo a medir.
8. **No hay enriquecimiento poblacional claro de racionales pequeños.** Casos individuales
   5:4 y profundos siguen siendo valiosos, pero controles remotos tienen residuales p:q
   comparables. Para Q≤6, los éxitos están incluso más lejos en mediana y el control de
   permutación da `p=0.933`; para Q≤8 aparece una ventaja pequeña, pero no concluyente
   (`p=0.115`, una cola, 20.000 permutaciones). El instrumento Q actual tampoco mide
   directamente la fase p:q.
9. **El grafo remoto no es todavía un grumo.** Los 19 éxitos W8 en `dw>=1` ocupan 31 nodos
   y 12 componentes; el mayor componente tiene 5 nodos. Es un mapa de candidatos para
   motivos simultáneos.

## Bloqueo conceptual

El POOLED resolvió correctamente el confusor de horizontes, el clustering por nodo y la
censura de `t_lock`. Falta resolver la validez física del endpoint: una deriva constante
puede sostener `R_W>=0.95` indefinidamente. El manifiesto de `par_link` advierte que debe
cruzarse firmeza con cierre de frecuencia; `lock60` usa sólo `t_lock`.

Hasta esa relectura, la formulación honesta es:

> El census midió una curva poblacional de coherencia de fase condicionada por historia y
> detuning aislado. Demuestra una ventaja biográfica fuerte y descubre candidatos remotos;
> todavía no fija la frontera física de una lengua de Arnold.

## Prioridad

La primera tarea no es ajustar otra curva. Es validar los episodios localmente y separar:

- falso-firme sinc;
- seguimiento forzado lineal;
- convergencia real 1:1;
- entrada p:q;
- link que transporta o devuelve energía;
- cierre colectivo de tres o más onions.

El documento canónico permanece intacto hasta que esta auditoría tenga arbitraje y decisión
de merge.

## Ejecución reproducible

La corrida basal validada leyó 170 pares no-self por brazo desde el checkout principal y
escribió únicamente el derivado ignorado `logs/link_grumo/baseline_census.json` de este
worktree. Insumos:

- `tabla_tanda1.json`: `0b4b4ff27c218a84966a8b0ed0f6c760d2d5ce17be146ef5c7ac097464037293`
- `tabla_tanda2.json`: `d5e65e28966ca5a7f7eaedd9d814dfdcd4abba311c70811cd9a83cc2e693cac4`

El control negativo intentó dirigir la salida a `/Volumes/ExternalDisk` y el lector la
rechazó antes de abrir los insumos. No se creó ningún archivo en el volumen externo.
