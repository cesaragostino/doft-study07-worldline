# WORLDLINE_SCHEMA — la película como fuente primaria (v1, 2026-07-29)

La worldline es LA fuente de observación: los instrumentos son vistas sobre ella
(INSTRUMENT_CONTRACT), jamás cálculos dentro del motor. Cambiar una ventana o un estimador crea
otra VISTA, nunca otra simulación (la inversión arquitectónica que funda Study07).

## Sellado (COA 2026-07-29)

- **Fila 0 = estado PRE-step** (los films de Study06 arrancaban post-step: defecto conocido,
  ya corregido en los fixtures de conformidad).
- **float64** en el artefacto científico primario. Cualquier compresión/decimación es una
  DERIVADA declarada, nunca el primario.
- **DOS PERFILES declarados por corrida** (decisión COA por costo de disco):
  `conformidad` = worldline completa float64 (corridas cortas, gates) ·
  `campaña` = retención DECLARADA en el prereg (qué va completo, qué downsampleado, qué sólo
  checkpoint). Nada se recorta en silencio.
- **I/O en dos niveles** (decisión COA «al cerrar copiar»): el recorder escribe CHUNKED al disco
  interno durante la corrida (tasa medida ~0.2-1 MB/s — trivial); al CERRAR: copiar al archivo
  externo + verificar hash + podar el interno según retención (patrón ejercitado en el respaldo
  del freeze: rsync repo-relativo + shasum -c). **"Guardar a medias" no es un artefacto**: el
  marcador `COMPLETE` sólo existe tras cierre+verificación; un film sin COMPLETE no entra al
  catálogo.
- **Intervención ⇒ worldline HIJA** (parent_run_id + parent_checkpoint_hash + evento declarado);
  la madre jamás se sobreescribe. Un kick/twin/hotcut NO es un instrumento: es una spec de
  corrida hija (EXPERIMENT_CONTRACT).

## Layout de una corrida

```
runs/<run_id>/
  manifest.json        # TODO lo necesario para re-integrar: ver "Manifiesto"
  worldline/           # chunks del film (chunk_00000.npz, ...)
  checkpoints/         # CHECKPOINT_SCHEMA: continuación exacta (float64 + buffers + RNG)
  events.jsonl         # timeline de intervenciones — LLEGA CON F6 (declarado pendiente)
  COMPLETE             # sha256 del film completo; SOLO tras cierre atómico + verificación

views/<worldline_hash>/<instrument_id>/<config_hash>/
  manifest.json        # instrumento + versión + observation_config + procedencia
  data...              # la vista (cacheable, recomputable, comparable)
```

## Contenido del film (por chunk)

| Canal | Qué | Por qué |
|---|---|---|
| `tick` | reloj (t = tick·dt DERIVADO, no almacenado) | dt CONFIGURADO (jamás re-inferido) |
| `x, v, z, b, e` por nodo | estado causal completo | cláusula 2 de COA: medir al individuo EMBEBIDO |
| `drive[n]` | fuerza KV del **sub-paso 0** del step (convención sellada) | el ledger causal sin re-derivar |
| `noise_kick[n_modos]` | incremento estocástico aplicado (si T>0) | replay exacto sin depender del stream |
| `rng_state` (por chunk) | estado del bit_generator al inicio del chunk | continuación/verificación |

La fila 0 del primer chunk es el estado PRE-step; `estados[tick]` = estado POST step número
`tick` (la MISMA semántica de los fixtures de conformidad — declarada acá para que nadie la
re-derive).

## Manifiesto de corrida (PROVENANCE_CONTRACT aplicado)

`run_id` · spec de la corrida ([M1|M2], EXPERIMENT_CONTRACT) · **hashes de la base externa**
(catálogo consumido, cápsulas, bloques canónicos — el defecto de Pimienta A resuelto de
nacimiento) · git commit + dirty de study07 · entorno (python/numpy EXACTOS — los streams del
RNG exigen numpy pineado) · topología completa (aristas con w_k/w_gamma/τ) · engine params ·
semilla · perfil (conformidad|campaña) con su retención · `parent_run_id`/`parent_checkpoint`
si es hija · estado de finalización.

## Reglas de integridad

1. Chunks con hash individual (escritos tmp+rename: jamás un chunk a medias); `COMPLETE` = hash del conjunto + hash del manifiesto (adulterar el manifiesto post-cierre = rechazo). COMPLETE prueba CIERRE ÍNTEGRO, no autenticidad: el sha_total lo pinea el catálogo/manifiesto EXTERNO (quien tenga el hash detecta cualquier reemplazo coherente). Una interrupción deja chunks
   válidos y NINGÚN `COMPLETE` — la corrida se reanuda del último checkpoint o se descarta
   entera, jamás se publica a medias.
2. La worldline es INMUTABLE una vez `COMPLETE`. Corrección de instrumento ⇒ nueva vista.
   Corrección de física ⇒ nueva corrida (y la vieja queda como registro con su ley taggeada).
3. Los estados intermedios del RK4 NO se almacenan (se reconstruyen determinista); puede existir
   un modo de traza de sub-pasos para auditoría numérica, separado del contrato de producción.
4. Formato: npz por chunk en v1 (simple, verificable); si el throughput de campañas lo exige,
   spike Zarr/HDF5 detrás de la interfaz `FrameSink` — el motor no conoce el backend.
