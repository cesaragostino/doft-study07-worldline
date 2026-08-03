# Link/grumo — cola ordenada al 2026-08-03

Este documento ordena trabajo ya abierto. No convierte hipótesis en resultados ni
reemplaza los preregistros de cada gate. Prioridad = valor físico por costo, con datos
existentes antes de pedir nuevas campañas.

## 1. Cerrado: Gate M — `NONLINEAR_FAST / SLOW_FROZEN`

Pregunta: ¿el gran residuo temprano del ignitor compartido de `par133_t/par134_t` nace
porque Gate L linealizó alrededor de amplitud cero una órbita de amplitud finita?

Acción: integrar el RHS completo de `(x,v,z)` con `b/e` clavados en su valor real de
llegada, la misma historia causal y el mismo KV recíproco. Panel: los mismos 16 films de
Gate F, con `par133/134` como casos prioritarios declarados y los fresh como controles.
No requiere films nuevos. Contrato separado:
`LINK_GRUMO_GATE_M_NONLINEAR_FAST_PREREG.md`.

Resultado: **NO CIERRA** para el ignitor de `par133_t/par134_t`, aunque mejora 13/15
films resueltos. Lectura: `LINK_GRUMO_GATE_M_NONLINEAR_FAST.md`.

## 2. En ejecución: Gate N — replay observado mínimo de `b(t)`

Gate M no cerró y habilitó este corte. Es diagnóstico, no simulación causal: el RHS
rápido recibe la trayectoria estructural observada del propio film. `e(t)` no entra en
ninguna ecuación rápida: sólo genera `db/dt`, que queda anulado al prescribir `b(t)`.
Por eso un replay de `e` con `b` fijo sería algebraicamente idéntico a Gate M y no se
corre como rama decorativa. El factorial mínimo es `b_Q` del emisor, todo `b` del emisor
y todo `b` de ambos nodos. Usar el futuro observado impide llamarlo predictor o fitness.
Contrato: `LINK_GRUMO_GATE_N_SLOW_REPLAY_PREREG.md`.

## 3. Postproceso barato: coherencia cruzada y residuo sobre la nula

Idea motivada por `Coherence Scaling in Quantum Communication Protocols`
(`2601.12516v1`), trasladada como descriptor clásico de señales, nunca como evidencia de
cuántica:

1. matriz de coherencia de Q/S1/S2 en base operacional fija y con guard de mudez;
2. separar coherencia intra-onion de los bloques cruzados entre onions;
3. ejecutar versión `phase_only` y versión que conserva potencia;
4. restar la coherencia cruzada producida por la nula causal correspondiente;
5. preguntar, con ventanas temprana/tardía disjuntas, si el residuo colectivo agrega
   información a ocupación Q, biografía y potencia ya medidas.

No usar pico de coherencia, PLV o entropía como salud por sí solos: Gates F/H/L ya
muestran que un link pasivo o muerto puede ser muy coherente.

La entropía de competencia entre canales `p:q` queda como sub-punto posterior. Antes
necesita una asignación de canales exclusiva y preregistrada; las lenguas candidatas se
solapan y una normalización post-hoc fabricaría el resultado.

## 4. Arnold — tres objetos distintos que no deben mezclarse

### 4.1 Antecedente histórico del simulador superconductivo

Study06 conserva referencias narrativas al detector que habría visto lenguas/lock-jumps
en una simulación SC:

- `docs/paper4/STUDY06_P04_PhaseSlip_Exploration_Spec_1.md`;
- `docs/paper5/bitacora/TEMA_JOSEPHSON.md`;
- `docs/paper5/RUPTURE_BATTERY_Spec_v0_1.md`.

Al 2026-08-03 no se encontró el código ni el dato crudo de esa simulación en los dos
repositorios ni en el archivo externo. Estado: **ANTECEDENTE NO AUDITABLE**. Lo único
heredable hoy es higiene instrumental: corriente de fase directa, guard duro de amplitud
y separación entre colapso de amplitud y slip. No se cita como réplica de onions.

Si aparece el material antiguo, la primera tarea es reconstruir eje, fuerza, frecuencia,
ventana, definición de lock y nulo; recién después se compara la forma de la lengua.

### 4.2 Census Arnold C1 actual — cerrado en su alcance

No es la simulación antigua. Resultado vigente: lengua monótona bajo la nula por nodo y
ventaja biográfica fuerte, pero W8 está anidado en W4; la rodilla `dw≈0.3–0.6` coincide
con el falso-firme `1.1/W`; `lock60` no es todavía captura cinemática en el núcleo; la
cola `dw>=0.3` es plana; el enriquecimiento `p:q` pequeño fue negativo. Estos límites
viajan con cualquier reutilización.

### 4.3 Pendientes Arnold/campañas

1. validación cinemática del núcleo `dw<0.275` con el estimador corregido;
2. census de emergencia sólo con `k_eff` y frontera `chi*F/A_S` calibrados en el mismo
   estimador de banda;
3. ola C para el mecanismo de la cola plana, no para volver a medir la rodilla;
4. lenguas `p:q` generalizadas sólo después de declarar portadora en-film y guard de
   armónicos/mudez.

## 5. Campañas más caras, diferidas

1. **2x9 real / lazo vivo**: D1 negativo y Gate L impiden vender `det[I-XK]` como salud.
   E2 ya no tiene un factor dos físico pendiente: el transitorio finito cerró las
   resonancias profundas. La 2x9 sólo vuelve cuando Gate M/replay diga qué dinámica viva
   falta y con qué observable leerla.
2. **Ola C**: conserva prioridad sobre la cola remota, pero no antecede a los postprocesos
   sin films nuevos.
3. **Nueva población/grumos N>2**: después de fijar el descriptor de link; toda coherencia
   o potencia deberá normalizarse por modos activos, nodos y simultaneidad de eventos.

## 6. Deuda transversal

- glosario canónico `salud_60` (estado) / `lock60` (evento) / cobertura-v2;
- validación cinemática del núcleo;
- máquina H como lector de trayectoria y `link_power` como vista consumida, no duplicada;
- corregir en un cambio separado el bloque prereg obsoleto de
  `gate_b_population.py`; no mezclar esa cirugía documental con Gates M/N;
- nunca promover a fitness una coordenada nacida en este panel retrospectivo.
