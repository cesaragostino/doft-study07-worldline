# Contrato conceptual v1 — motor de retardo fundamental (el espacio es lectura)

Fecha: 2026-08-05

Estado: **v1.1 — ONTOLOGÍA CERRADA (§4-§7) + ENMIENDAS DEL TAP wf_281797f0 APLICADAS
(§12 abajo; audit/DOUBLETAP_CONTRATO_V1_*); PENDIENTE: acuerdo de COA sobre candidato ℬ
y rama de signo → spec ejecutable**

Supersede como norte de diseño a `MOTOR_SIN_GRAFO_RETARDO_EVOLUTIVO.md` (v0), que se
conserva como historia del razonamiento. Los cambios de v0→v1 no son cosméticos: la
ontología geométrica se invirtió por decisión de COA («un onion no se separa del otro;
están TODOS JUNTOS; es el tiempo que tarda en afectar al otro lo que cambia; el mapa de
espacio/tiempo es DE RETARDOS»).

## 0. El norte, en una frase

> N onions idénticos nacen juntos sobre ruido remanente; un pulso global los
> re-engancha; biografías, relojes,
> detunings, locks, retardos, aristas, grumos y — si aparece — el espacio mismo, emergen
> de integrar la ley, y se leen después.

Nada de esa lista existe aguas arriba del integrador. Ninguna palabra observacional
(lock, fase, salud, captura, release, arista, distancia) habilita, pondera ni apaga un
término del RHS.

## 1. Ontología

### 1.1 Estado

\[
\text{Onion } i:\; X_i=(x_i,v_i,z_i,b_i,e_i)
\qquad\qquad
\text{Relación } \{i,j\}:\; \tau_{ij}(t)\ge 0.
\]

- `X_i` es el onion diferencial completo del motor v1-KV, sin cambios internos.
- **No existen posiciones, velocidades espaciales, dimensión ni métrica.** El estado
  relacional fundamental es el retardo τ_ij, UNO por par no ordenado (retardos por
  modo quedan DIFERIDOS salvo que la dinámica lo exija; las pieles de un par comparten
  canal causal y las diferencias internas las propaga cada onion por dentro).
- El «espacio» es una LECTURA: si la matriz τ(t) se vuelve embebible en algún R^d, la
  dimensión emergente es un OUTCOME (espectro de la matriz de Gram del embedding). La
  fase pre-geométrica (τ no-embebible) es una respuesta válida del experimento.

### 1.2 Lo que NO existe en el motor

Sin cambios respecto de v0, ampliado: sin EdgeState, sin ocupación/salud/memoria de
link, sin puertos, sin p:q a priori, sin capture()/release(), sin poda de pares, **sin
posiciones, sin c (no hay conversión distancia→tiempo), sin envolvente de atenuación
a(d)** (§3.3), sin eventos discretos de ningún tipo.

## 2. Génesis: todos juntos, todos iguales, pulso dispar

1. **Todos iguales**: el caldo génesis usa N copias de UN genoma canónico declarado por
   campaña. La diversidad NO se pone en la constitución.
2. **Todos juntos**: τ_ij(0)=0 para todo par. El nacimiento es simultaneidad, no
   singularidad (sin cuerpos no hay colisión — el «d→0» de v0 murió con el espacio).
3. **Renganche = ruido remanente + pulso (SUPUESTO de COA, registrado 2026-08-05)**:
   la textura individual NO vive en el pulso — vive en el ESTADO REMANENTE pre-pulso:
   los osciladores ya estaban en oscilación ruidosa, sin estructura, «muerta de forma
   pero con ruido interno andando, activo». El PULSO es GLOBAL (puede ser uniforme, de
   todos); el renganche (ruido remanente + pulso) inicia el ciclo nuevo.
   Operacionalmente en el caldo 1: IC por onion = realización estocástica del ruido
   remanente (streams por identidad, enmienda 9) + pulso global declarado — equivalente
   a un quench con textura, pero el supuesto ONTOLÓGICO queda registrado así. Sin
   textura (remanente idéntico), determinismo + simetría ⇒ idénticos para siempre
   (guarda §6.7). Parámetros de remanente y pulso = física declarada de la campaña;
   los detalles finos del remanente quedan DIFERIDOS por decisión de COA.
4. **Cero causal**: antes del pulso no hay señal emitida. El HistoryBuffer NO rellena
   el pasado con t=0 (el bug-class de v0 §3.1 se hereda como prohibición). Consulta más
   antigua que la historia disponible = error, salvo prehistoria serializada explícita.

**La pregunta que desvela a COA queda REGISTRADA con su supuesto**: el ruido
preexistente (remanente) ES parte del génesis asumido; el pulso no necesita ser dispar.
Caldos con ruido sostenido (T>0 permanente) siguen siendo variante declarada futura.

## 3. Interacción: una ley por par, cuatro salidas, cero elecciones

### 3.1 La evaluación del par

Para cada par {i,j}, en cada sub-paso RK4, la MISMA evaluación produce:

\[
\mathcal J_{ij}\left(X_i(t), X_j(t),\; X^{S}_i(t-\tau_{ij}), X^{S}_j(t-\tau_{ij}),\;
\tau_{ij}(t)\right)
\longrightarrow
\left(\mathbf f^{S}_{i\leftarrow j},\; \mathbf f^{S}_{j\leftarrow i},\;
\dot\tau_{ij}\right).
\]

- La interfaz es **estrictamente la piel secundaria S = S1∪S2**. Q ni emite ni recibe
  directo (decisión D1): la penetración S→Q es la cascada interna del genoma (intra +
  direct_links + geometría χ) — outcome medible, no término.
- **Acople democrático sin elección** (D5): una sola amplitud constante por par para
  TODO (μ∈S_i, ν∈S_j); nadie elige parejas modales. La selectividad la hace la
  constitución (χ) dinámicamente — medido en cirugía y gates.
- **Ψ LINEAL** (E2): la gramática de diferencias existente, sin términos no-lineales
  inventados («limón, agua y azúcar»). Con Ψ lineal la suma sobre ν colapsa la emisión
  POR MATEMÁTICA (Σ_ν x_jν^ret − n_S·x_iμ); la identidad de RECEPCIÓN queda intacta
  (término de reacción propio por modo receptor — el pecado del v1-KV era el escalar
  nodal). La identidad de emisión importa solo si Ψ fuera no-lineal: puerta dormida,
  el buffer guarda coordenadas POR MODO igual (§5.2).
- **Suma CRUDA** (E1): sin normalización por vecinos ni por número de modos. «Más piel
  = más contacto» es física del modelo, declarada.

### 3.2 La cara geométrica: rectificación, no fórmula de atracción

\[
\dot\tau_{ij}(t) = \mathcal B\left(\text{términos INSTANTÁNEOS de la misma evaluación}
\;\mathcal J_{ij}\right)
\]

Propiedades EXIGIDAS por este contrato (la forma concreta se fija en el spec, con tap):

1. **Instantánea**: sin ventanas, sin fases estimadas, sin frecuencia extraída, sin
   detector alguno. Solo estado de sub-paso y historia retardada — lo mismo que ya
   consume Ψ.
2. **Simétrica por par**: una sola dτ/dt por {i,j} (la relación es una).
3. **Producida por la MISMA ley**: no es un término aparte — es la cara geométrica de
   la evaluación que ya existe (v0 §4 lo exigía: cuatro salidas, una ley).
4. **Rectificación como mecanismo, no como regla**: un bilineal instantáneo entre dos
   oscilaciones tiene componente neta SOLO cuando las fases se traban — fuera de lock
   oscila y su integral se cancela; bajo relación de fase sostenida deriva. Así «la
   atracción surge del lock y los retardos» (COA) LITERALMENTE, sin que lock aparezca
   en ninguna ecuación. Es la misma física por la que un oscilador forzado solo absorbe
   potencia neta cerca de resonancia.
5. **Sin signo impuesto**: que rectifique hacia τ menor (acercar), mayor (alejar), u
   orbite, es OUTCOME. No se programa atracción.

### 3.3 Sin atenuación: la única distancia es la fase

**No existe envolvente a(d)/a(τ).** La amplitud de interacción no depende del retardo
(«retardo no equivale a atenuación», v0 §3.2, elevado a decisión). Un par lejano no es
más débil: está en OTRA relación de fase. Los ceros posibles son dos: causal (aún no
llegó nada) y dinámico (el intercambio neto se cancela por incoherencia). El cero
asintótico NO existe en v1.

Consecuencia declarada: la auto-regulación del caldo descansa ENTERAMENTE en (a) la
cancelación de fase de los pares incoherentes y (b) la saturación biográfica (el único
canal no-lineal verificado: b = filtro pasabajos de dos polos QUE OLVIDA, τ_e/τ_b
medidos). **Hipótesis H1 (pre-registrada, falsable): el caldo se auto-regula en la
escala τ_b. Si explota o sincroniza trivialmente, a(τ) se revisita como enmienda — no
se agrega en silencio.**

### 3.4 Exclusividad: 100% biográfica

Con τ por par, las relaciones NO se hablan entre sí salvo A TRAVÉS de los onions (no
existe el efecto colateral del espacio compartido: acercarse a j no aleja de k). La
exclusividad posible viene de que el compromiso sostenido con j REESCRIBE al onion (b),
y esa reescritura la ven todos sus pares — está MEDIDO (el ignitor cambia su reloj para
todos sus socios). Declarado como cambio real vs v0 §5 y como MÁS consistente con la
ontología: el onion es lo único real; las relaciones no tienen sustancia propia.

## 4. RHS estructural

\[
\dot X_i = F_i(X_i) + \sum_{j\ne i}\mathbf f^{S}_{i\leftarrow j}(t)
\qquad\qquad
\dot\tau_{ij} = \mathcal B_{ij}(t)\quad\forall\, i<j
\]

- `F_i` = RHS interno v1 del onion, sin cambios (contrato §1 vigente).
- Todo par se evalúa en cada sub-paso desde el mismo estado de etapa; las cuatro
  salidas del par nacen juntas; acumulación por suma; ningún resultado depende del
  orden de recorrido.
- τ_ij ≥ 0 se preserva por la dinámica o por proyección DECLARADA (τ=0 es
  simultaneidad, no error); qué pasa físicamente en τ=0 sostenido (fusión aparente,
  rebote dinámico) es OUTCOME.

## 5. Contrato de integración y registro

1. Integrar X y τ conjuntamente en cada etapa RK4; interpolación de historia por
   TIEMPO FÍSICO (τ_ij(t) continuo, sin grupos fijos).
2. **El buffer causal guarda las coordenadas secundarias POR MODO** (x_ν, v_ν de S de
   cada onion), no sumas — aunque Ψ lineal solo consuma la suma: la puerta no-lineal y
   los instrumentos por modo no se cierran por arquitectura.
3. Registrar en la worldline: X (como v1), τ_ij(t), las contribuciones causales usadas
   (f^S por par, dτ/dt por par) — un solo RHS: trending/ledgers consumen lo emitido,
   jamás reimplementan la fuerza.
4. Checkpoint y continuación entre olas portan τ y la ventana de historia necesaria;
   una cápsula de caldo declara su matriz τ y las historias igual que hoy declara ring
   e IC (extensión de schema con versión propia; nada sobrescribe el significado de
   una worldline v1).
5. Motor v1-KV queda CONGELADO como baseline histórico (población, controles,
   regresión). El motor nuevo no lo reproduce ni lo maquilla: es otra física declarada.
6. Instrumentos, clasificación, filesystem y selección viven FUERA del integrador.

## 6. Guardas contra física fabricada (batería mínima pre-implementación)

1. **Onion aislado**: con interacción cero reproduce el RHS interno v1 de referencia
   (bit-exacto al redondeo declarado).
2. **Permutación**: renombrar/reordenar onions no cambia trayectorias.
3. **Todos los pares**: ningún par desaparece por umbral alguno.
4. **Cero causal**: antes de la primera llegada posible no se inyecta estado t=0.
5. **Identidad de recepción**: cada modo secundario receptor conserva su término
   propio; ninguna contribución entra como escalar nodal uniforme.
6. **Reciprocidad constitutiva**: ambos sentidos del par usan la misma ley/parámetros;
   τ único por par.
7. **Simetría sin textura** (nueva): N onions idénticos con pulso IDÉNTICO (sin
   textura) permanecen idénticos al redondeo — el determinismo no fabrica diversidad.
8. **Rectificación no impuesta** (nueva): par forzado a intercambio INCOHERENTE
   (frecuencias inconmensurables, construido) ⇒ deriva neta de τ compatible con cero
   (la atracción no está en la fórmula; solo emerge con coherencia).
9. **Un solo RHS / sin eventos ocultos / refinamiento dt**: como v0.
10. **Regresión de invariantes internos** (herencia medida): reloj C√(1+0.1·b) (resid
    ≤1.5%), b = filtro 2 polos (picos reproducidos R²=1.000), χ/notches del Jacobiano —
    ninguno depende de la interfaz y TODOS deben sobrevivir al motor nuevo.
11. **Calibrador χ^S**: la cirugía (capacidad M1, clamp programado) se recicla sobre la
    ENTRADA SECUNDARIA nueva → χ^S por genoma → identidad r≡1 con c=1 como nula sin
    parámetro libre de toda lectura del caldo (lección §14: F_th SIEMPRE con estimador
    de banda).

## 7. Lecturas (aguas abajo, jamás aguas arriba)

Grafo observado, grumos, episodios (máquina H), potencia por par/modo (desde las
contribuciones emitidas), espacio emergente (embedding de τ(t): dimensión, estrés,
espectro — INSTRUMENTO nuevo a construir), reloj/biografías, detunings dinámicos.
Cambiar un instrumento cambia la lectura, nunca la trayectoria.

## 8. Hipótesis pre-registradas del caldo 1 (N=16-25, física completa o nada — D3)

- **H1 — auto-regulación biográfica**: el caldo no explota ni sincroniza trivialmente;
  la escala de organización es compatible con τ_b (el filtro que olvida como regulador).
- **H2 — génesis de detunings**: de dw≡0 inicial, el pulso dispar hace divergir
  biografías → los relojes se separan según la ley medida C√(1+0.1·b) → detunings
  DINÁMICOS emergen y estructuran locks. La diversidad de frecuencias no se pone:
  emerge.
- **Criterio mínimo de éxito** (COA): dinámica coherente observable — «algo, al menos».

## 9. Decisiones: cerradas y la única abierta

**Cerradas** (charla 2026-08-05, §4-§7): onion completo como unidad · τ_ij por par como
único estado relacional · espacio/dimensión = lectura · génesis todos-juntos/todos-
iguales/pulso-dispar · Q interior (interfaz solo-S) · Ψ lineal democrática · suma cruda
· sin a(τ) (H1 como red) · dτ/dt = cara geométrica de la misma ley (rectificación) ·
A_propia no existe (no hay espacio) · exclusividad biográfica · N=16-25 sin recortes ·
sin versiones parciales de software.

**Abierta (ÚNICA, se cierra en el spec con tap): la forma concreta de Ψ y del bilineal
ℬ** — con las propiedades de §3.1-§3.2 como jaula. Nada más queda por decidir antes del
spec ejecutable.

## 10. Criterio de cierre

v1 pasa a spec cuando Ψ y ℬ estén escritas cumpliendo §3 sin observables de ventana, y
la batería §6 esté especificada como tests ejecutables. No hace falta predecir qué
emergerá: eso es el experimento.


---

## 12. Enmiendas v1.1 (tap wf_281797f0 — BLOQUEA aplicado; textos del juez)

1. **Semántica ÚNICA del cero causal (cierra BLOQUEA-1, corrige §2.4/§3.3):** si
   t − τ_ij(t) < t_pulso, la evaluación J_ij vale **CERO COMPLETA** — las cuatro
   salidas, incluido el término de reacción −n_S·x_iμ y ℬ. Un par con τ_ij > t−t_pulso
   está causalmente DESCONECTADO: es el cero causal hecho regla, no un error. ERROR
   queda reservado para consultas más viejas que la VENTANA RETENIDA (guarda de
   implementación). Trending obligatorio: min_ij(t−τ_ij−t_pulso), max_ij|dτ_ij/dt|,
   high-water de retención. [Alternativa |dτ/dt|<1 descartada: J≡0 hace la cota finita
   por construcción sin restringir la ley.]
2. **Pseudocódigo del paso (cierra BLOQUEA-2, reemplaza §5.1):** el spec ESCRIBE el
   paso completo: τ_ij variable de etapa RK4; consulta (t+c_k·dt)−τ^(k) con τ DE ETAPA;
   ℬ por sub-paso; rama τ<c_k·dt (el RÉGIMEN de todos los pares en el génesis) con
   recuperación sub-dt CONTINUA (Hermite en x con el v ya almacenado — gratis); push
   post-kick; ORDEN DE CONVERGENCIA MEDIDO y declarado (lineal ⇒ orden 2).
3. **Retención dinámica del buffer (§5.4):** ventana amortizada con tope declarado,
   fail-loud, high-water registrado. Dimensión real (n_S=7): 2.800 B/tick, 35 MB/u.t.,
   peor caso 600 u.t. = 21 GB. Gate permanente: directa-vs-restore bit-exacta CON
   pulso a caballo del checkpoint.
4. **Calibración de K (§3.1, heredera de la D4 muerta):** K = física declarada con
   calibración PRE-REGISTRADA: F̂ del par dentro del bracket medido del census
   [1.5e-7, 3.75] y bajo el techo lineal F̂=3 (§14) ⇒ K ≲ 3/((N−1)·n_S·A) ≈ 0.018 con
   A~1. Con suma cruda, K vale para UN (N, genoma) y SE RE-DECLARA al cambiar N. F̂
   por par entra al trending. [F3: la rigidez del término de reacción es SIEMPRE
   coherente — la incoherencia no la cancela; H1 llega tarde para inestabilidad rápida
   (0.34 vs 540 u.t.); el riesgo vivo es el colapso trivial, no la explosión.]
5. **Estabilidad de τ=0 pre-registrada (§10):** el spec incluye ANTES de correr el
   cálculo analítico de ℬ(τ=0) y la estabilidad lineal del caldo simétrico-con-textura
   (genoma real, 7 modos S). ADVERTENCIA MEDIDA: los bilineales que se anulan con la
   diferencia tienen τ≡0 como punto fijo EXACTO para ambos signos (la muerte du/dt≡0
   en lenguaje τ); en los pares, el signo de la constante ES el destino a τ=0 —
   **el signo NO es outcome en el génesis: se declara como rama** (decisión de COA).
6. **Bracketing de H2 (§8):** dw_∞ previsto = 0.0073·ΔE (genoma canónico); escapar de
   la lengua 0.275 exige ΔE>38, escala 152-540 u.t. El pulso se elige para CRUZAR la
   frontera predicha (2-3 caldos declarados si hace falta) — la lógica de la cirugía.
7. **τ sin inercia (§1.1):** dτ/dt = ℬ es constitutivo de PRIMER ORDEN. Agregar
   inercia a τ = enmienda de física, no implementación.
8. **Ledgers de atribución (§5.3):** W_ij(t)=∫(f_i·v_i+f_j·v_j)dt por par (consumido
   de lo emitido — con retardo la potencia del par puede BOMBEAR o disipar; sin este
   ledger una explosión no es atribuible); los tres números causales de la enmienda 1;
   convención: canales causales del sub-paso 0. Retención POR CANAL justificada contra
   la banda S2 real (ω≈316 ⇒ decimación ×32 ≈ 3.9× sobre Nyquist); a tasa completa
   serían 252-340 GB/caldo.
9. **RNG por onion (§2.3, §6.2, §6.7):** streams derivados de la IDENTIDAD estable
   (node_seed(seed, id) — ya existe), no del índice. Guarda 2 permuta (id, stream);
   guarda 7 = mismo key para todos. CHECKPOINT porta N estados de bit_generator.
10. **Proyección τ≥0 declarada (§4):** recomendada SUAVE en la ley (ℬ_eff = ℬ·s(τ),
    s C¹, s(0)=0 si ℬ<0) — RHS continuo; clamp duro solo post-combine y declarado.
    La guarda dt cubre EXPLÍCITO la ventana génesis τ<dt.
11. **CHECKPOINT_SCHEMA v2 + CÁPSULA_CALDO v1 (§5.4):** T(t) por tramos + tick de
    consumo del pulso; τ_ij float64 en U.T. CANÓNICO (steps = conversión interna — la
    mordida gemela del t_abs); fingerprint EXTENDIDO = constitución ∪ {K, params_ℬ,
    calendario_pulso, semillas por onion} (el bug-class kappa_global/K_global cerrado
    también acá); matriz τ + ventanas de historia con timestamps ABSOLUTOS.
12. **Guarda 8 reescrita (ejecutable):** par incoherente CONSTRUIDO (genomas de
    frecuencias inconmensurables — permitido: la guarda es del motor): |⟨dτ/dt⟩_T| en
    T/2T/4T cae ~1/T (log-log, pendiente ≤ −0.8) contra control coherente APAREADO
    cuya deriva NO cae.
13. **Erratas:** n_S=7 (2 S1 + 5 S2) para el genoma canónico; el colapso es
    Σ_ν x_jν^ret − n_S^(j)·x_iμ (n_S del EMISOR).
14. **Pilotos M1 pre-registrados (§6, antes del caldo 1):** (i) par aislado N=2 con
    barrido log de K y escala de ℬ; (ii) caldo corto N=25 × ~5 u.t. (ventana génesis).
    D3 prohíbe recortar física, no pilotos. Si TODO el barrido da τ clavado en 0 o
    rigidez: PRIMER RESULTADO FALSABLE, se reporta.

**Insumo del juez para la única decisión abierta (NO decisión):** candidato
ℬ_ij = λ·(S_i·S_j^ret + S_j·S_i^ret) con S = la MISMA suma secundaria que Ψ computa —
bilineal PAR simetrizado, instantáneo, cero lecturas nuevas. Física verificada
(juguete corregido): peine ⟨ℬ⟩ = C·cos(ωτ) con conchas estables en ωτ=π/2+2πn
(τ_final medido = T/4); **bajo lock el par se sienta en un CERO de ⟨ℬ⟩ ⇒ la geometría
se CONGELA al lockear** («la atracción surge del lock» con final propio: el lock
también la apaga); en el génesis ℬ(0)=2⟨S²⟩>0 puntual ⇒ **λ>0 = rama de EXPANSIÓN
determinista desde τ=0** (escapa de la muerte τ≡0 sin depender de la textura); λ<0 =
clavado en τ≡0 (medido). LA FORMA Y LA RAMA LAS DECIDE COA.

**Costo re-medido:** baseline 48-77 h/caldo (600 u.t., 1 proceso); con estados
apilados sobre el eje nodo (posible por todos-iguales): ~una noche. Batería: guardas
1-8 en CI (<1 h); 9-10 una tarde; 11 una noche; + dos tareas con nombre: port del
clamp M1 a la entrada secundaria y χ^S del Jacobiano nuevo.
