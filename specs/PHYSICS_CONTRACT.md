# PHYSICS_CONTRACT — la ley, transcripta del oráculo (v1, 2026-07-29)

**Fuente**: Study06 @ `study06-freeze-20260729`. Cada sección cita su rango exacto. Esto NO es
diseño: es transcripción disciplinada de la ley que generó la población v4 y toda la física
firmada. Toda desviación futura es enmienda numerada con panel.
**Verificación**: los 5 fixtures de conformidad (`tests/fixtures/study07_*` del oráculo) a
tolerancia **≤ 3.8579e-11** (piso medido dt-vs-dt/2, §93-C3). Estados en float64.
**Ley v1 = `direct-only`**: el kernel histórico `inter_couplings.taus0/amps0` NO entra a la
fuerza (igual que en TODA la historia del programa — ambos integradores de Study06 lo descartan;
medido perturbativo 0.2-4.4% en trayectoria real, §93-C5). Si se evalúa: experimento on/off M1
en este motor, jamás activación silenciosa.

## 0. Estado causal de un onion

```
X = (x[n], v[n], z[nz], b[nl], e[nl])          # float64
```
`n` = modos (capas Q/S1/S2, cada una con sus modos), `nz` = términos de memoria activa por capa,
`nl` = capas presentes en orden canónico Q→S1→S2 (physics_core `_layer_order`; S3 se RECHAZA
fail-loud — el oráculo v4 sólo tiene Q/S1/S2). Constantes por modo: `omega0, gamma, mass`.
Estructurales por capa: `tau_e, tau_b, alpha_b, e_ref`. Memoria por capa (v2 serializada, se
hereda EXACTA sin re-sorteo): `tau0[k], beta_tau[k], beta[k], a[k], g[k], kappa[k]` + matriz `W`
(capa×capa) + `mem_index[(layer,k)]→idx_z`.

## 1. RHS del onion — `derivatives()` [oráculo: physics_core.py:464-592]

Orden de acumulación SELLADO (self → intra → direct → memoria → drive → b/e). El orden importa
para la conformidad bit-cercana; no se reordena.

```
dx = v                                                              # :499

# (1) on-site + fricción                                            # :501-504
omega_eff2_p = omega0_p² · (1 + eps_omega · b[capa(p)])
dv_p += −omega_eff2_p · x_p − gamma_p · v_p                         # NOTA: sin /mass (así es la ley)

# (2) acoples intra-capa                                            # :506-510
k_eff = k0 · (1 + eps_k · b[capa])
dv_i += −k_eff · (x_i − x_j) / mass_i        (y simétrico en j)

# (3) links directos inter-capa (g0 — lo ÚNICO que cruza capas como resorte)  # :512-520
g_eff = g0 · (1 + eps_k · b[capa_shallow])   # la b del canal es la de la capa SHALLOW del link
dv_shallow += −g_eff · (x_shallow − x_deep) / mass_shallow   (y simétrico en deep)

# (4) memoria activa por capa                                       # :522-568
E_mem[capa]  = Σ_k ½·kappa[k]·z[(capa,k)]²                          # :527
E_inst[capa] = Σ_p∈capa ½·mass·v² + ½·mass·omega_eff2·x²  + E_mem[capa]   # :529-532 y :448-449
señal[capa]  = mean(x_p : p∈capa)                                   # :538
input        = W @ señal_vec  (orden de capas canónico)             # :546
tau_eff      = max(tau0[k]·(1 + beta_tau[k]·E_inst[capa]), 1e-9)    # :557-558
u_clamped    = clip(beta[k]·input[capa], ±clamp_tanh_arg)           # :560
dz[(capa,k)] = −z/tau_eff + a[k]·tanh(u_clamped)                    # :561
F_mem[capa]  = Σ_k mfs · g[k] · z[(capa,k)]                         # :562  (mfs=1.0 producción)
dv_p += −F_mem[capa(p)] / mass_p   ∀ p∈capa                         # :564-568

# (5) recepción del campo externo (drive_ext = fuerza KV de red, ver §3)     # :570-582
dv_p += drive_ext / mass_p         ∀ modo p (superposición: TODOS los modos reciben)

# (6) variables lentas                                              # :584-590
de[capa] = (E_inst[capa] − e[capa]) / tau_e[capa]
db[capa] = (−b[capa] + alpha_b·(e[capa] − e_ref[capa])) / tau_b[capa]
```

**Identidad clave**: la `b` entra por DOS canales (omega_eff2 vía eps_omega; k_eff/g_eff vía
eps_k) — misma `b` en ambos en producción. La energía on-site usa la MISMA b que la fuerza.

## 2. Constantes congeladas del contrato de simulación

`eps_omega = eps_k = 0.1` · `clamp_tanh_arg = 5.0` · `mem_force_scale = 1.0` — en el oráculo
viven como defaults de `SimulationParams` NO expuestos por engine_params en producción
(hallazgo §21.2 del audit). Acá son PARTE DEL CONTRATO, explícitas, y el censo v4 las verifica
(150/150: eps 0.1/0.1/0.1/0.1, clamp 5.0, T=0). Las perillas de laboratorio
(`b_omega/b_kcoup/mem_force_scale≠1`, máscaras hotcut, `memory_exclude_idx`) NO son física:
son INTERVENCIONES (van a interventions/, invalidan naturalidad, generan worldline hija).

## 3. Acople de red — Kelvin-Voigt retardado POR ARISTA [differential_engine.py:82-138]

```
F_i(t) = k_spring · Σ_{e∋i} w_k[e]·(x_other(t−τ_e) − x_i(t)) / Σ_{e∋i} w_k[e]
       + k_damp   · Σ_{e∋i} w_g[e]·(v_other(t−τ_e) − v_i(t)) / Σ_{e∋i} w_g[e]
```
- Media PONDERADA por canal; τ por arista SIMÉTRICO (reciprocidad estructural).
- `x/v` del otro nodo = su coordenada EMITIDA retardada (§4), leída del HistoryBuffer.
- **Acumulación secuencial en orden de aristas**: bit-exacto sólo grado ≤ 7 (comentario sellado
  :113-117). Gate de conformidad: red con nodo grado ≥ 8 acepta ≤ 1 ulp o replica secuencial.
- `drive_ext` del RHS (§1.5) = `F_i` — UNA fuerza escalar por nodo, recibida por superposición.

## 4. Emisión y fase [differential_engine.py:348-373]

- **Emitida**: `xv_total = emission_scale · (Σ_p x_p, Σ_p v_p)` — superposición de TODOS los
  modos. `emission_norm`: "sum" ⇒ scale=1 (legacy, loop gain ~n_modes²) · "mean" ⇒ 1/n_modes.
  **La población v4 está sellada con `mean` + emission_scale efectivo 0.1** (censo §21) — v1
  usa `mean`; "sum" queda como legacy declarado.
- **Fase de lock**: θ_Q sobre la capa Q SOLAMENTE — el observable R se mide en Q; la emisión
  sigue siendo la superposición completa. (Esto es INSTRUMENTO, no fuerza — en Study07 se
  calcula offline desde la worldline, no dentro del motor.)

## 5. Integrador — RK4 de red + kick FDT [differential_engine.py:647-719]

```
para cada sub-paso s ∈ {0 (c=0), 1 (c=½), 2 (c=½), 3 (c=1)}:
    xv_s     = emisión de states_s (todos los nodos)
    del_ep_s = endpoints retardados a (τ_e − offset_s), offset = [0, ½, ½, 1]
               · si τ_e − offset_s ≤ 0 ⇒ usa xv_s del SUB-PASO ACTUAL          [de:564-577]
               · si no ⇒ HistoryBuffer.get_delayed_steps(τ_e − offset_s):
                 base=floor, frac; interpolación LINEAL entre (head−base) y (head−base−1)
    f_inter_s = KV(xv_s, del_ep_s)                                   (§3)
    k_{s+1}   = derivatives(states_s, f_inter_s)   por nodo          (§1)
    states_{s+1} = states_0 + dt·c·k_{s+1}   con c = ½, ½, 1         [de:657,665,673]
combinación: X_next = X_0 + dt/6 · (k1 + 2k2 + 2k3 + k4)   campo a campo (x,v,z,b,e)

si T > 0 (termostato FDT/Langevin, split de operador: RK4 determinista + Euler estocástico):
    v_next += sqrt(2·gamma_p·T·dt / mass_p) · N(0,1)     POR MODO    [de:693-698]
    orden de consumo del RNG: nodos en orden de índice, modos en orden del vector
push al HistoryBuffer: xv_next (UNA vez por paso, al final)          [de:718]
```

- **HistoryBuffer** [de:141-168]: ring de tamaño `delay_steps+1`, `delay_steps=ceil(max τ_e/dt)`;
  inicializado COMPLETO con xv(t=0); `push` avanza head. La historia causal inicial es parte del
  checkpoint (las cápsulas v4 la traen: `history_column`, ~2 u.t.).
- **dt**: configurado EXPLÍCITO (población v4 = `require_configured_dt`, dt=8e-5, sin cap de
  estabilidad). El dt JAMÁS se re-infiere de un eje temporal (causa raíz del bug del kernel §90).

## 6. Semillas y ruido — TODO reproducible [de:493,502,1323]

```
node_seed(seed, idx) = int(sha256(f"{seed}|node|{idx}")[:8], 16) & 0xFFFFFFFF   # por nodo
noise_rng            = default_rng((seed·1000003 + 99991) & 0xFFFFFFFF)          # red, único
x0, v0               = rng_nodo.normal(scale=1e-3)  ×2   # EN RUNTIME — no serializados
```
**Consecuencia sellada**: la reproducibilidad exige numpy PINEADO (2.3.4) y el estado del RNG en
la worldline (los incrementos de ruido se graban — fixture f5 del oráculo lo ejercita). Cuando
se restaura de cápsula, x/v/z/b/e vienen del checkpoint y NO se sortean.

## 7. Inicialización [physics_core.py:377-423 + differential_engine.py:171-238]

1. `theta_internal_v2` valida fail-loud (`require_v2_state`): memoria y struct_params
   SERIALIZADOS se heredan EXACTOS (sin re-sorteo). v1 legacy = re-sorteo por nodo (NO se porta
   como producción). `adaptive_couplings` ⇒ RECHAZO (generación diagnóstica).
2. `e_ref_policy` ∈ {`receiver_initial_energy` (default: e_ref := E_inst(t0) local),
   `preserve_serialized`} — se DECLARA por corrida; física distinta en el punto fijo de b.
3. `e[capa](t0) = E_inst[capa](t0)`; `z(t0)=0, b(t0)=0` (nacimiento) o del checkpoint (restore).
4. El kernel `taus0/amps0` se PARSEA y DESCARTA con warning VISIBLE (jamás suprimido — el
   supresor de Pimienta A fue el hallazgo CODE-PHY-011).

## 8. Guardas — decisión de contorno sellada

El motor NO guarda (así corrió toda la física v4/olar). El RUNNER valida finitud por chunk y
ABORTA fail-loud (jamás altera trayectoria). Los campos de guarda muertos de SimulationParams
(max_x, max_abs_z, energy_blowup...) NO se portan.

## 9. Lo que NO existe en physics/ (gates de CI)

La palabra "ola" (cláusula 1 de COA) · instrumentos (R, clusters, atlas, anatomía: offline) ·
filesystem · una segunda copia de las ecuaciones (el force_ledger duplicado fue vetado — si se
quieren contribuciones nombradas, el MISMO RHS las devuelve opcionalmente) · early_stop ·
proxies de frontera entre niveles.

## 10. Divergencias conocidas del linaje (para el oráculo de conformidad)

`state_space.py` difiere de la ley de trayectoria (on-site /mass; sin gamma/b/e) — NO es
referencia. `ola1/simulation.py` == `olar/physics_core.py` en la ley (verificado término a
término, adenda §21.3 del audit); difieren sólo en contorno: cap de dt (v4 nació sin cap),
guardas (§8), ruido (sólo olar), e_ref (ola1 siempre recalibra). Este contrato adopta:
dt explícito, guardas en runner, FDT como §6, e_ref como §7.2.
