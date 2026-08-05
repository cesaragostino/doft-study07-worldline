# SPEC ejecutable — motor de retardo fundamental (caldo τ) v1

Fecha: 2026-08-05. Estado: **ESCRITO CON GO DE COA (forma ℬ del juez + rama λ>0);
PENDIENTE: tap de spec → implementación completa (D3: sin versiones parciales)**.

Implementa `audit/MOTOR_RETARDO_FUNDAMENTAL_CONTRATO_V1.md` (v1.1, enmiendas §12).
Toda desviación respecto del contrato es BLOQUEA. Este spec cierra la única decisión
abierta (forma de Ψ y ℬ) y clava las semánticas que el tap wf_281797f0 exigió.

## 1. La ley, escrita

### 1.1 Ψ — acople de piel (spring-only, la gramática interna existente)

La gramática interna del onion (intra_pairs, direct_links en rhs.py) es de RESORTES de
diferencias — la disipación vive SOLO onsite (γ por modo). Ψ la continúa inter-onion:

```text
f_{i←j, μ}(t) = (K / m_iμ) · Σ_{ν ∈ S_j} [ x_jν(t − τ_ij) − x_iμ(t) ]
             = (K / m_iμ) · [ S_j(t − τ_ij) − n_S^(j) · x_iμ(t) ]
para todo μ ∈ S_i;    S_k(t) ≡ Σ_{ν ∈ S_k} x_kν(t)
```

- Sin término en v (sin damper inter-onion): declarado, coherente con la gramática
  interna; la disipación es onsite.
- S = S1∪S2 (Q ni emite ni recibe — D1). n_S^(j) = modos secundarios del EMISOR
  (enmienda 13; genoma canónico: n_S=7 = 2 S1 + 5 S2).
- K: UNA constante por campaña, calibrada (§4). Suma CRUDA sobre pares (E1).
- Recepción POR MODO (cada μ conserva su término −x_iμ); el buffer guarda x,v POR MODO
  (contrato §5.2) aunque Ψ lineal solo consuma S_j y la puerta no-lineal duerma.

### 1.2 ℬ — la cara geométrica (candidato del juez, GO de COA)

```text
dτ_ij/dt = ℬ_ij(t) · s(τ_ij)
ℬ_ij(t)  = λ · [ S_i(t) · S_j(t − τ_ij)  +  S_j(t) · S_i(t − τ_ij) ]
```

- **λ > 0 (rama de EXPANSIÓN, declarada por COA)**: en el génesis ℬ(0)=2⟨S²⟩>0
  puntual ⇒ el caldo expande desde τ=0 determinísticamente (escapa de la muerte τ≡0).
- Bilineal PAR simetrizado, instantáneo, simétrico por par, cero lecturas nuevas
  (consume exactamente lo que Ψ ya consultó). Cumple las 5 propiedades del contrato
  §3.2.
- Física pre-registrada (verificada en juguete corregido; el spec la RE-DERIVA
  analítica con el genoma real de 7 modos ANTES del caldo — enmienda 5): peine
  ⟨ℬ⟩ ∝ cos(ωτ) por modo S; conchas estables en ωτ = π/2 + 2πn (τ_final ≈ T/4);
  bajo lock el par se sienta en un cero de ⟨ℬ⟩ (LA GEOMETRÍA SE CONGELA AL LOCKEAR);
  pares en antifase → contacto τ=0.
- **s(τ): proyección SUAVE C¹ en la ley** (enmienda 10): s(τ)=1 si ℬ≥0;
  si ℬ<0: s(τ) = min(1, τ/τ_s) con τ_s = dt (una rampa lineal C⁰... NO: C¹ exigida)
  → s(τ) = smoothstep(τ/τ_s) = 3(τ/τ_s)²−2(τ/τ_s)³ para τ<τ_s, 1 después; τ_s = 10·dt
  DECLARADO. RHS continuo, sin eventos. τ≥0 garantizado por construcción (ℬ<0 se apaga
  suave en τ→0).
- τ SIN inercia (enmienda 7): primer orden, constitutivo.

### 1.3 Cero causal (enmienda 1 — regla, no error)

```text
si  t − τ_ij(t) < t_pulso:   J_ij ≡ 0 COMPLETA
    (f_{i←j} = f_{j←i} = 0, INCLUIDO el término de reacción −n_S·x_iμ, y ℬ_ij = 0)
```

Par causalmente desconectado. ERROR queda solo para consultas más viejas que la
ventana RETENIDA del buffer (fail-loud de implementación). Trending obligatorio:
`min_ij(t − τ_ij − t_pulso)`, `max_ij |dτ_ij/dt|`, high-water de retención.

## 2. El paso — pseudocódigo NORMATIVO (cierra BLOQUEA-2)

Estado de caldo: `{X_i}` (N onions, apilados eje-nodo), `{τ_ij}` (N(N−1)/2, float64
en U.T. — representación CANÓNICA; steps solo como conversión interna por consulta).

```text
step(t):                                      # dt = 8e-5, RK4 clásico c=(0, ½, ½, 1)
  para k in (1..4):                           # etapas
    t_k   = t + c_k·dt
    X^k   = estado de etapa (Euler parcial estándar RK4 sobre X)
    τ^k   = estado de etapa de τ (MISMO esquema: τ es variable de etapa — se propaga
            con k1..k4 propios, NO congelada en τ(t))
    para cada par i<j:
      t_src = t_k − τ^k_ij
      si t_src < t_pulso:  J_ij ≡ 0 (cero causal §1.3)
      sino:
        (x,v)_ret = HISTORIA(t_src)           # §3: Hermite en x; la historia contiene
                                              # SOLO pasos COMPLETOS (< t) + los
                                              # estados de etapa del paso ACTUAL para
                                              # la rama solapada t_src ∈ [t, t_k]
        f^S ambas direcciones + ℬ_ij          # §1.1-§1.2, desde X^k y (x,v)_ret
    dX^k = F_interno(X^k) + Σ_pares f^S       # RHS onion v1 sin cambios + piel
    dτ^k = ℬ·s(τ^k)
  combinar k1..k4 → X(t+dt), τ(t+dt)          # rk4_combine estándar, X y τ juntos
  kicks FDT por onion (streams POR IDENTIDAD, §5) si T(t)>0 (calendario del pulso)
  push HISTORIA(t+dt)                          # POST-kick — lo que se emite es lo real
```

Semánticas CLAVADAS (eran las 4 libres):
1. **τ de etapa**: τ^k evoluciona dentro del paso como cualquier variable RK4.
2. **Rama solapada** (t_src > t, consulta "dentro" del paso actual — el RÉGIMEN de
   TODOS los pares en el génesis, τ < c_k·dt): se sirve con los estados de etapa del
   paso actual interpolados de forma CONTINUA (sin conmutación discontinua). La
   recuperación sub-dt es parte de HISTORIA, no un caso especial del RHS.
3. **Interpolación**: Hermite cúbica en x (usa el v almacenado — gratis, error O(dt⁴)
   consistente con RK4); v retardada por diferencia del Hermite (O(dt³)) — v solo
   entra a ℬ=0 (no la usa) y al buffer; DECLARADO. El ORDEN GLOBAL efectivo se MIDE
   (guarda 9) y se declara en el manifiesto — no se asume 4.
4. **Push post-kick, uno por paso.**

## 3. Historia causal (buffer nuevo — reemplaza HistoryBuffer, guarda 4)

- Por onion: ring de (x_ν, v_ν) de TODOS los modos S, por tick, timestamps ABSOLUTOS
  en u.t. **PROHIBIDO pre-llenar con t=0** (delay.py:21-22 muere con el motor viejo).
- Ventana DINÁMICA amortizada; tope por campaña (caldo 1: 120 u.t. = 4.2 GB con
  n_S=7, N=25 a 2.800 B/tick); fail-loud al exceder; high-water registrado.
- Consulta: Hermite en x (§2.3); más viejo que la ventana = EXCEPCIÓN (no silencio).

## 4. Constantes de campaña y calibración PRE-REGISTRADA

| constante | valor caldo 1 | procedencia |
|---|---|---|
| genoma canónico | 61b48428 (el mejor caracterizado: χ, σ, notches, A0 medidos) | declarado |
| N | 25 | D3 |
| dt | 8e-5 | continuidad v1 |
| K | del PILOTO i (§7), techo K ≤ 3/((N−1)·n_S·A_pulso) ≈ 0.018/A_pulso | enmienda 4 |
| λ | del PILOTO i: deriva de τ observable en ≤600 u.t. sin violar §1.3 | enmienda 14 |
| τ_s (proyección) | 10·dt | §1.2 |
| pulso | T_pulso/ticks_pulso del bracketing H2: ΔE tal que dw_∞ = 0.0073·ΔE CRUCE 0.275 (ΔE>38 para escapar; 2-3 caldos declarados si hace falta) | enmienda 6 |
| remanente | IC por onion = realización del ruido remanente (streams §5); forma: estado térmico de T_rem·ticks_rem declarados (supuesto §9 bitácora 2026-08-05) | COA |

K y λ se RE-DECLARAN al cambiar (N, genoma) — suma cruda. F̂ por par al trending.

## 5. RNG (enmienda 9)

Streams POR ONION derivados de identidad estable: `node_seed(seed_campaña, id_onion)`
(existe: compat/study06_v4.py). El remanente y los kicks del pulso consumen el stream
del onion, JAMÁS un stream de red por índice. Guarda 2 permuta (id, stream) juntos;
guarda 7 corre con el MISMO key para todos (config de test). Checkpoint porta N
estados de bit_generator.

## 6. Registro (WORLDLINE_CALDO_SCHEMA v1) y custodia

- **Canales**: X por onion (como v1, chunked); τ_ij float64 por par; contribuciones
  causales del SUB-PASO 0 (f^S por par, ℬ por par) — convención drive[n] heredada.
- **Retención POR CANAL declarada** (enmienda 8): X a tasa completa; τ a tasa
  completa (barato: 300 float64/tick); f^S/ℬ decimados ×32 (justificación: banda S2
  ω≈316 rad/u.t. ⇒ ~3.9× sobre Nyquist) + segmentos completos declarados (génesis
  [0, 5 u.t.] y ventanas de eventos re-derivables desde checkpoints cada 10 u.t.).
- **Ledgers derivados** (un solo RHS — consumo de lo emitido): W_ij(t)=∫(f·v)dt por
  par (atribución H1: con retardo el par puede BOMBEAR o disipar); los tres números
  causales de §1.3; F̂ por par.
- **CHECKPOINT_SCHEMA v2**: + matriz τ (u.t.), ventanas de historia por onion/modo con
  timestamps absolutos, N estados RNG, T(t) por tramos + tick de consumo del pulso,
  fingerprint EXTENDIDO = constitución ∪ {K, λ, τ_s, calendario_pulso, semillas}
  (bug-class kappa_global cerrado acá — enmienda 11). Gate permanente: directa-vs-
  restore BIT-EXACTA con pulso a caballo del checkpoint.
- **CÁPSULA_CALDO v1**: artefacto nuevo (no extensión) — para continuar caldos entre
  olas: X + τ + historias + RNG + fingerprint. Versionado propio; nada re-significa
  worldlines v1-KV.

## 7. Pilotos M1 pre-registrados (enmienda 14 — ANTES del caldo 1)

- **(i) Par aislado N=2**: barrido log de K ∈ [1e-4, 0.05] × λ ∈ [rango log declarado
  en el prereg del piloto], midiendo |dτ/dt|, F̂ por par, estabilidad dt vs dt/2, y el
  peine (τ_final vs predicción T/4). Criterio: (K, λ) que ponen la deriva de τ en
  rango observable en ≤600 u.t. respetando §1.3.
- **(ii) Caldo corto N=25 × 5 u.t.**: la ventana de génesis (expansión desde τ=0,
  cero causal activo, ningún par en error).
- Si TODO el barrido da τ clavado o rigidez: PRIMER RESULTADO FALSABLE — se reporta,
  no se “arregla”.

## 8. Batería de guardas (tests ejecutables; presupuesto medido por el juez)

| # | guarda | test | costo |
|---|---|---|---|
| 1 | onion aislado | K=λ=0 ⇒ bit-exacto vs RHS interno v1 (10k ticks) | CI |
| 2 | permutación | permutar (id, stream) ⇒ trayectorias idénticas al redondeo | CI |
| 3 | todos los pares | grep estructural: sin poda; N(N−1)/2 evaluaciones/etapa | CI |
| 4 | cero causal | buffer nuevo: consulta pre-pulso ⇒ J≡0; pre-ventana ⇒ excepción | CI |
| 5 | identidad de recepción | f^S por modo con su −x_iμ propio (vs oráculo a mano) | CI |
| 6 | reciprocidad | τ único por par; misma ley ambos sentidos (fórmula vs manual) | CI |
| 7 | simetría sin textura | mismo key para todos ⇒ idénticos al redondeo (1k ticks) | CI |
| 8 | rectificación no impuesta | par inconmensurable construido: pendiente log-log ≤ −0.8 de la deriva vs T/2T/4T; control conmensurado apareado NO cae | CI |
| 9 | refinamiento dt | dt vs dt/2 en ventana génesis (τ<dt) y en concha; orden MEDIDO declarado | tarde |
| 10 | invariantes internos | reloj C√(1+0.1b) (resid ≤1.5%), b-filtro (picos R²), χ/notches del Jacobiano — sobre corridas del motor nuevo | tarde |
| 11 | calibrador χ^S | port del clamp M1 a la entrada S por modo → χ^S por genoma → identidad r≡1 (c=1, estimador DE BANDA — lección §14) | noche |

## 9. Arquitectura e implementación (D3: completa, sin parciales)

- **Módulos nuevos**: `src/study07/engine/caldo.py` (RedCaldo: paso §2, apilado
  (N, dim) eje-nodo — habilitado por todos-iguales; orden de reducción CANÓNICO
  declarado para la suma sobre pares), `src/study07/physics/historia_tau.py` (buffer
  §3), `src/study07/physics/interaccion_tau.py` (J: f^S + ℬ + cero causal + s(τ)),
  `src/study07/artifacts/{recorder_caldo,checkpoint_caldo,capsula_caldo}.py`,
  `tools/caldo_pilotos.py`, `tests/test_caldo_guardas.py` (§8).
- **Motor v1-KV: INTOCADO y congelado** (baseline histórico); el caldo no comparte
  Network (comparte physics/rhs.py del onion interno, sin modificarlo).
- Costo esperado: ~una noche/caldo de 600 u.t. con apilado (baseline medido 48-77 h
  mono-proceso); 16 cores ENTRE unidades (pilotos/guardas/réplicas). Kernel compilado
  = decisión aparte con certificación bit-contra-referencia (NO en v1).
- Word-gate: vocabulario nuevo (caldo, τ, renganche, remanente) — sin «ola» en
  physics/engine; instrumentos fuera del integrador (INSTRUMENT_CONTRACT).

## 10. Hipótesis del caldo 1 (pre-registradas — se leen DESPUÉS, jamás alimentan el RHS)

- **H1**: auto-regulación biográfica (escala τ_b; ni explosión ni sincronía trivial).
  Atribución por W_ij + ledgers (enmienda 8). Si falla ⇒ a(τ) se revisita como
  enmienda declarada.
- **H2**: génesis de detunings (bracketing §4: el pulso cruza la frontera predicha
  dw_∞ = 0.0073·ΔE vs lengua 0.275).
- **H3 (nueva, del tap)**: el peine de conchas — τ de pares lockeados se acumula en
  ωτ ≈ π/2 + 2πn (predicción cuantitativa del candidato ℬ; leída del τ(t) registrado).
- Criterio mínimo (COA): dinámica coherente observable.

## 11. Criterio de cierre del spec

Implementación aceptada cuando: batería §8 completa en verde (11/11), pilotos §7
corridos y sus (K, λ) declarados, y el primer caldo N=25 integrado 600 u.t. con
worldline v1 conforme al schema §6. Recién entonces: lecturas (máquina H, trending τ,
embedding espectral de τ como instrumento nuevo de espacio emergente).
