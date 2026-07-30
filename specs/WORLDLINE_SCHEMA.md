# WORLDLINE_SCHEMA — la película como fuente primaria [BORRADOR — Fase 1]

## Sellado (COA 2026-07-29)
- **Fila 0 = estado PRE-step** (los films de Study06 arrancaban post-step: defecto conocido).
- **float64** en el artefacto científico primario.
- **DOS PERFILES declarados por corrida** (decisión COA por costo de disco):
  `conformidad` = worldline completa float64 (corridas cortas, gates) ·
  `campaña` = retención DECLARADA en el prereg (qué va completo, qué downsampleado, qué sólo
  checkpoint). Nada se recorta en silencio.
- **I/O en dos niveles**: el recorder escribe CHUNKED al disco interno durante la corrida
  (~0.2-1 MB/s medidos — trivial); al CERRAR: copiar al archivo externo + verificar hash + podar
  el interno según retención. **"Guardar a medias" no es un artefacto**: el marcador `COMPLETE`
  sólo existe tras cierre+verificación; un film sin COMPLETE no entra al catálogo.
- Contenido mínimo: estado inicial + todos los ticks + drives por nodo + incrementos de ruido +
  estado del RNG + topología/params por hash + historia causal inicial + reloj + linaje.
- **Intervención ⇒ worldline HIJA** (parent_run + parent_checkpoint + evento declarado); la madre
  jamás se sobreescribe.
