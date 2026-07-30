# INSTRUMENT_CONTRACT — vistas, no actores [BORRADOR — Fase 1]
Un instrumento: instrument_id+versión · required_channels (falla si falta un canal, jamás
sustituye) · observation_config (ventana/settle/stride/umbral DECLARADOS) · worldline_hash →
vista con hash y procedencia. NO muta ni ejecuta el motor. Recalculable y comparable contra su
caché. Distingue dato / inferencia / veredicto. Cláusula 2 de COA: las vistas existen POR NIVEL
(onion / grumo / cluster) sobre la misma worldline — incluido el individuo embebido vs su rama
aislada. Un kick/hotcut NO es un instrumento: es una spec de corrida hija.
Migración: cada fórmula de Study06 se porta UNA por una con fixture entrada/salida del oráculo.
