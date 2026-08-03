# Contrato de integración — `link_power` hacia `main`

Fecha: 2026-08-02. Preparado desde `research/link-grumo-dynamics`; no ejecutado todavía
sobre `main`.

## 1. Decisión que debe llegar a los demás

El cambio importante tiene dos partes que no deben confundirse:

1. **Medición aprobada:** `link_power` reconstruye potencia causal desde worldlines
   existentes, funciona por chunks, verifica hashes y fue cosechado en 375/375 films.
2. **Regla de salud no aprobada:** potencia temprana describe con fuerza la ruta
   transported, pero no es necesaria en fresh ni mejora materialmente coherencia y
   ocupación como predictor de salud60.

Un merge que sólo diga “potencia predice salud” transmitiría una conclusión incorrecta.
El mensaje que debe quedar en el PR, en tests y en la documentación es:

> Se agrega una coordenada energética observacional. No se cambia lock, salud, máquina
> de estados ni fitness.

## 2. Estado de ramas y riesgo actual

El branch de investigación partió de:

```text
merge-base 6c2e92e27f7f40d1084c2094f96ee83bc88eaeca
```

Al cerrar Gate K, `main` está en `1d836f9` y avanzó cinco commits. Sus cambios tocan
`campana.py`, `checkpoint.py`, `recorder.py`, herramientas de cirugía y bitácora. El
merge-tree no muestra conflictos textuales con este frente, pero eso no reemplaza la
prueba de compatibilidad: `link_power` consume justamente chunks emitidos por recorder y
sellados por checkpoint.

No conviene fusionar a ciegas los más de 9.000 renglones del frente completo para obtener
un instrumento de 300 renglones. La integración debe hacerse desde un worktree nuevo
creado sobre el `main` vigente.

## 3. Capas de commits

Los commits de potencia están separados deliberadamente:

| Capa | commits | contenido | efecto en ejecución normal |
|---|---|---|---|
| instrumento | `c97cf79`, `039a7ed` | `link_power`, streaming, runner y tests | ninguno: opt-in |
| cosecha | `8dab2c9` | auditoría de 375 films | documentación |
| contraste | `9df3313`, `4adb99b`, `f847a2c` y cierre Gate K | prerregistro, evaluador y diagnóstico de ruta | ninguno: offline |

La unidad mínima recomendable para `main` es la capa instrumento completa, nunca
`c97cf79` sin `039a7ed`: el segundo commit agrega la ruta streaming verificada y evita
cargar un film poblacional entero en memoria.

La capa contraste puede entrar en el mismo PR si se desea conservar toda la evidencia,
pero debe quedar bajo `tools/link_grumo`/`audit`; no es dependencia del runtime.

## 4. Procedimiento seguro propuesto

En la etapa de integración, y no sobre este worktree:

1. actualizar `main` y crear `integration/link-power` en un worktree nuevo;
2. aplicar primero `c97cf79` y `039a7ed`;
3. resolver contra el recorder/checkpoint vigentes sin cambiar la fórmula congelada
   `P[k,j]=drive[k,j]*sum(v[k-1,j])`;
4. correr tests unitarios de potencia y checkpoint, luego la suite completa;
5. generar un fixture pequeño con el recorder de `main` y exigir equivalencia exacta
   `run(worldline en memoria) == run_path(chunks)`;
6. hacer un smoke read-only de varias unidades ya selladas, incluyendo límites de chunk;
7. sólo después incorporar runner/auditorías y abrir un PR draft;
8. revisar el diff final contra `main` para confirmar cero cambios en bitácora, fitness,
   estados y defaults de campaña.

No se reusarán ledgers para afirmar compatibilidad si el recorder cambia bytes o hashes:
se puede reutilizar el dato físico, pero la nueva view debe declarar su nuevo
`worldline_hash`.

## 5. Contrato de compatibilidad hacia atrás

La integración debe preservar estas reglas:

* una campaña que no solicita `link_power` produce exactamente los mismos resultados;
* `view_hash_power` es opcional y aditivo en ledgers futuros;
* un ledger viejo sin ese campo significa `UNKNOWN`, no potencia cero;
* las views se direccionan por `worldline_hash/instrument_id/config_hash` y nunca
  sobrescriben una configuración previa;
* `VERSION=1.1` permanece fija mientras fórmula, alineación y canales no cambien;
* cualquier cambio de fórmula/alineación requiere nueva versión y no reetiquetar views;
* en redes multiarista se publica potencia neta nodal; queda prohibido atribuirla a un
  edge sin un canal de fuerza por arista;
* ninguna coordenada de potencia entra en fitness o en el veredicto de salud en este PR.

Si más adelante la campaña canónica quiere materializar la vista automáticamente, debe
ser otro commit y preferentemente otro PR: feature flag explícito, presupuesto de disco
medido y schema de ledger incrementado.

## 6. Pruebas que bloquean el merge

Mínimo exigible:

```text
alineación drive[k] con v[k-1]
signo sintético de inyección/extracción
caja trailing causal sin fuga
invariancia frente al hop de publicación
equivalencia run/run_path entre chunks
rechazo de SHA/chunk/manifiesto corrupto
declaración multiarista no identificable
suite checkpoint/recorder de main
suite completa del repo
```

El resultado poblacional de Gate J (`375/375`, cero fallos) es evidencia de escala, pero
no sustituye las pruebas sobre el recorder nuevo de `main`.

## 7. Cómo comunicarlo sin que cambie de significado

El PR debe incluir en la cabecera:

```text
Qué agrega: potencia causal de puerto, offline/opt-in.
Qué no cambia: dinámica, lock, salud, fitness, campañas históricas.
Resultado: útil para distinguir rutas energéticas; no es ley universal de supervivencia.
Datos: externos read-only; sólo views/ledgers locales derivados.
Rollback: revertir la capa instrumento elimina la capacidad sin migrar datos canónicos.
```

Y enlazar dos auditorías:

* `LINK_GRUMO_GATE_J_POWER.md`: validez y cosecha del instrumento;
* `LINK_GRUMO_GATE_K_POWER_HEALTH.md`: resultado positivo de mecanismo y negativo de ley
  universal.

Así los demás se enteran tanto del nuevo dato como de su límite. Evita el fallo más
peligroso: que una correlación agregada muy fuerte termine convertida en un criterio de
selección que mate precisamente las rutas fresh que el census demostró posibles.

## 8. Estado

Preparado, no integrado. Este documento no autoriza tocar `main`, publicar un PR ni
modificar campañas. Es el checklist para hacer esa operación en un worktree separado
cuando se decida la ventana de merge.
