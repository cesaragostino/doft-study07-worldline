# STUDY06 COMO ORÁCULO (read-only)

- **Repo**: `~/code/doft-study06-fundamental-lock-dynamics` · GitHub `cesaragostino/doft-study06-fundamental-lock-dynamics`
- **Tag de freeze**: `study06-freeze-20260729` (main, única rama). NO se le agregan features ni campañas.
- **Fixtures de conformidad**: `tests/fixtures/study07_f{1..5}_*.npz` + sidecar sha256 — float64,
  fila 0 PRE-step, historia causal inicial, estado del RNG por tick (f5). Generador commiteado:
  `logs/s93_genera... (ver logs/s93_c4_fixtures.py)`.
- **Tolerancia de conformidad (MEDIDA, §93-C3)**: max|Δ| dt-vs-dt/2 = **3.8579e-11** (GOLD, 10 u.t.).
- **Mapa de la ley** (verificada idéntica entre ambos integradores; audit §21 + lente núcleo):
  `src/paper5/olar/physics_core.py:464-592` (derivatives, 129) · `differential_engine.py:647-719`
  (RK4 de red + kick FDT) · `:82-138` (acople KV; bit-exacto sólo grado≤7) · `:141-168,564-577`
  (buffer retardado + interpolación lineal, sa=τ−offset) · `physics_core.py:694-720` (rk4 genérico)
  · `:426-454` (energías). Las **8 perillas** y las **4 decisiones de contorno**: audit §21.2 y
  PHYSICS_CONTRACT.
- **Base física**: `data/processed/ola1_v4_c1/ola1/` (150 cápsulas, 71M, LOCAL) — capsule_path
  cuelga del set borrado: resolver por `<blocks>.parent/specimen_capsules/` + verificación de
  `capsule_sha256` (contrato en su README_SET_ACTIVO.md). dt se lee de
  `capsule.json → engine_contract.dt` (state.npz NO trae dt).
- **Oráculo de ola2**: el rerun corregido §88/§89 —
  `data/campaigns/dead_passive_20260713/c4b/c4b_s88_v0_rerun_b2ea7265.json` (666213ab…) y
  `c4b_s89_v02_rerun_b2ea7265.json` (97ee291d…).
- **Datos pesados**: respaldo verificado en `/Volumes/ExternalDisk/doft-study06-fundamental-lock-dynamics/`
  (rutas repo-relativas; `shasum -c logs/DATA_MANIFEST.sha256` desde el root del backup). Los films
  de ola2 (69G) viven SOLO en el backup.
- **Entorno del oráculo**: Python 3.13.9 **x86_64**, numpy==2.3.4, BLAS Accelerate
  (`audit/ENV_FREEZE_2026-07-29.txt`). Los streams del RNG exigen numpy pineado.
- **Consulta típica**: cualquier duda de conformidad se arbitra corriendo el oráculo
  (`PYTHONPATH=src python3 ...` desde su raíz) — es más barato que discutir.
