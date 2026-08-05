# PREREG — Piloto i del caldo τ (gate de ENTRADA al caldo 1)

Fecha: 2026-08-05. SELLADO ANTES de correr piloto alguno (spec §12.15).

## Predicciones analíticas (derivación: data/caldo/PREREG_PILOTO_I_derivacion.json)

Genoma canónico 61b48428, 7 modos S (2 S1 ω=43.45/44.57 + 5 S2 ω=275.7-315.7), masas 1.
Pesos térmicos relativos w_ν ∝ 1/(m·ω²): **S1 concentra 94.75%** (0.486+0.462).

1. **Peine multi-modo** ⟨ℬ⟩(τ) ∝ Σ_ν w_ν cos(ω_ν τ): conchas (ceros descendentes) en
   **τ = 0.0351, 0.1793, 0.3219, 0.4636, 0.6061, 0.7498, ...** (paso ≈ período S1
   0.1434). Corrimiento vs T/4 monomodo del S1 dominante: **−0.0010** (el vestido S2
   apenas corre la concha — H3 del caldo 1 se lee contra ESTA lista, no contra T/4).
2. **ℬ(0) con textura**: signo 50/50 (producto de gaussianas independientes;
   verificado numéricamente en el tap: frac<0 = 0.498). Escape de τ≡0 ESTADÍSTICO.
3. **Reclutamiento de anticoherentes**: escala del período S1 dominante ≈ 0.145 u.t.
   (rotación de fase relativa) + sesgo expansivo de s cerca de τ=0.
4. **Estabilidad de τ=0**: punto fijo SOLO del caldo sin textura (guarda 7); con
   textura, deriva neta ≠ 0 par a par desde t=0+.

## Diseño del piloto i (N=2, según spec §7)

Barrido log: K ∈ {1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 0.018·(24·7)/(1·7·κ·A)} — el techo se
recalcula para N=2 con la fórmula sellada (§12.7: K ≤ 3/((N−1)·n_S·κ·A_pulso), κ=3.5,
A_pulso = sqrt(Σ T_pulso/(m ω²))); λ ∈ {1e-3, 1e-2, 1e-1, 1, 10} × (normalización por
Var(S) declarada al correr). T_pulso/ticks_pulso del bracketing H2 (dw_∞=0.0073·ΔE
cruza 0.275 ⇒ ΔE≈38-100 entre caldos declarados). Por corrida (120 u.t.): |dτ/dt| máx,
F̂ por par, τ_final vs concha predicha (1), estabilidad dt vs dt/2, retención
(max|dτ/dt|×600 < 120 u.t. o política de escalamiento).

## Criterios (sellados)

- (K, λ) DECLARADOS = los que ponen la deriva de τ en rango observable en ≤600 u.t.
  respetando el cero causal (sin episodios de consulta pre-ventana).
- τ_final del par coherente cae en una concha de la lista (1) ± τ_s ⇒ H3-piloto PASA.
- TODO el barrido con τ clavado en 0 o rigidez ⇒ PRIMER RESULTADO FALSABLE — se
  reporta, no se ajusta.
