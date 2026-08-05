# Contrato conceptual v1 — motor de retardo fundamental (el espacio es lectura)

Fecha: 2026-08-05

Estado: **ONTOLOGÍA CERRADA EN CHARLA (bitácora 2026-08-05 §4-§7); PENDIENTE: tap de
diseño + forma concreta de Ψ (única decisión abierta) → spec ejecutable**

Supersede como norte de diseño a `MOTOR_SIN_GRAFO_RETARDO_EVOLUTIVO.md` (v0), que se
conserva como historia del razonamiento. Los cambios de v0→v1 no son cosméticos: la
ontología geométrica se invirtió por decisión de COA («un onion no se separa del otro;
están TODOS JUNTOS; es el tiempo que tarda en afectar al otro lo que cambia; el mapa de
espacio/tiempo es DE RETARDOS»).

## 0. El norte, en una frase

> N onions idénticos nacen juntos; un pulso dispar los enciende; biografías, relojes,
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
3. **Pulso dispar**: UNA perturbación GLOBAL (de todos, no propia de uno) con TEXTURA
   INDIVIDUAL — realización estocástica por onion de una misma ley de excitación
   (maquinaria FDT existente: quench a T_pulso durante ticks_pulso declarados, luego
   T=0). Sin textura, determinismo + simetría perfecta ⇒ idénticos para siempre (guarda
   §6.7). Parámetros del pulso = física declarada de la campaña.
4. **Cero causal**: antes del pulso no hay señal emitida. El HistoryBuffer NO rellena
   el pasado con t=0 (el bug-class de v0 §3.1 se hereda como prohibición). Consulta más
   antigua que la historia disponible = error, salvo prehistoria serializada explícita.

**La pregunta que desvela a COA queda REGISTRADA, no resuelta**: ¿ruido preexistente o
pulso dispar? El caldo 1 corre con pulso dispar. Caldos con ruido sostenido (T>0
permanente) son una variante declarada futura — es física a explorar, no un default.

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
