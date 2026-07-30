# INSTRUMENT_CONTRACT — vistas, no actores (v1, sellado tras double tap F4)

Un instrumento: instrument_id+versión · required_channels (falla si falta un canal, jamás
sustituye) · observation_config (ventana/settle/stride/umbral DECLARADOS, claves con WHITELIST:
un typo es error de contrato, no una config nueva) · worldline_hash → vista con hash y
procedencia. NO muta ni ejecuta el motor. Recalculable y comparable contra su caché. Distingue
dato / inferencia / veredicto. Cláusula 2 de COA: las vistas existen POR NIVEL (onion / grumo /
cluster) sobre la misma worldline — incluido el individuo embebido vs su rama aislada
[PENDIENTE: F4 sólo cubre el nivel red]. Un kick/hotcut NO es un instrumento: es una spec de
corrida hija. Migración: cada fórmula de Study06 se porta UNA por una con fixture
entrada/salida del oráculo.

## Cláusulas ejecutables (endurecidas por el double tap F4 — antes eran prosa)

- **Identidad del film** = `sha256(sha_total ‖ manifest_sha)` del COMPLETE. Los chunks solos no
  identifican la física observable: dt y el layout por nodo viven en el manifiesto que los
  instrumentos LEEN (la colisión dt×2 compartía hash y ruta de vista — A4).
- **Ventana validada, no wrapeada**: `0 ≤ t0 ≤ t1 < len(ticks)`, `stride ≥ 1`, en la capa
  compartida (`api.ventana`). t0 negativo re-etiquetaba el final del film como principio (A8).
- **Sólo COMPLETE se observa** por defecto; auditoría de restos = `permitir_incompleto=True`
  EXPLÍCITO, que entra a la config y por lo tanto al config_hash (A8).
- **view_hash** hashea manifiesto SIN su propia clave + arrays: estable ante write
  (idempotente) y atado al CONTENIDO (A3).
- **write() con cierre**: data.npz primero, manifest.json (con view_hash) al final como marca;
  un path ocupado con OTRO view_hash es rechazo fuerte — corrección de instrumento ⇒ nueva
  versión ⇒ nueva ruta, jamás pisado silencioso (A3).
- **load_view()** relee y RECOMPUTA el hash desde disco, fail-loud: «comparable con su caché»
  es código, no prosa (A3).
- **Constitución verificada por huella**: una vista que consume constitución (energía) la
  verifica contra los `spec_fingerprints` del manifiesto del film — masa×2 o nodos permutados
  fallan fuerte, jamás energías silenciosamente distintas (A5; espíritu de F3 A4).
- **Taxonomía de canales en el manifiesto de la vista**: cada canal declarado como
  dato / inferencia / veredicto (p.ej. theta=dato, j=inferencia, omega_valid=veredicto).
- **Estimadores dependientes de la config, declarados**: J/omega con stride>1 usan
  dt_ef=dt·stride (OTRO estimador, no decimación); el primer tick de toda ventana tiene J=0
  por construcción. Ambos declarados en el manifiesto de la vista.
- **Espejo exacto = espejo de la MICRO-RUTA aritmética** (lección F4): escalares numpy
  indexados del array, acumulación escalar por tick, memoria por capa sumada una vez — la
  equivalencia matemática no alcanza para el gate de 0.0 exacto.
