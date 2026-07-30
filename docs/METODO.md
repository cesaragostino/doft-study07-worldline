# MÉTODO — doctrina del programa (COA, 2026-07-25; documento vivo)

**Companion**: INVENTARIO_ESPECIMENES.md — registro vivo de especímenes [M2] por ola (fichas,
destinos, genealogía mamushka) + los TRES MIEDOS COA (pimienta/selección, matemática del
instrumento, CPU como censor) con sus consecuencias operativas. Se actualiza al cierre de cada
campaña M2. Regla COA sellada 2026-07-27: **no proponer pruebas simples para ahorrar cómputo —
si funciona se hace, sino paramos en seco; cosas a medias no sirven.**

## Doctrina del método ingeniero-físico (COA, 2026-07-29 — sellada en §93, GOBIERNA sobre todo lo demás)

1. **La medición vale más que el análisis.**
2. **El proceso natural de evolución física va antes que cualquier corset teórico.** Un
   experimento cuyo único producto es caracterizar un formalismo ya falsado NO se corre («si las
   pruebas son para medir el corset teórico y ponerlo en un marco, no sirve para nada»).
3. **Probemos: tenemos el modelo para probar; si no anda, todos a casa y todos contentos.** El
   veredicto lo da el experimento, no el marco.
Aplicación registrada el mismo día: la escalera settle/measure fue descartada por este filtro
(§93) — caracterizaba G(ω), la reducción estacionaria que la sección 18 del audit ya falsó.

## Definiciones (vinculantes)

**MÉTODO 1 (lab/clones)**: sirve para corregir herramientas, ver algún comportamiento especial y
mapear dinámica PUNTUAL. Requisitos: tiene que tener un PORQUÉ definido antes de correr, y **no se
itera mucho sobre él generando ideas que parezcan física** — método 1 produce instrumento y
mecanismo, no física general. Riesgo característico: enamorarse del método y confundir el mapa del
mecanismo con la física.

**MÉTODO 2 (gimnasio/emergente)**: sirve para ver FÍSICA EMERGENTE. La dinámica general EMERGE, no
se busca. Las conclusiones REALES del programa salen de acá. Requisitos: variación real (genomas,
configuraciones), población COMPLETA reportada (los "aburridos" son datos), reglas de clasificación
selladas ANTES de mirar con balde SIN-CLASIFICAR explícito, y cero expectativas importadas como
gates (los hallazgos de método 1 son *predicciones a chequear*, nunca filtros).

**Regla de tagging (obligatoria desde hoy)**: todo experimento/sprint se etiqueta [M1] o [M2] en el
prereg y en el commit. La bitácora declara el método al abrir cada sección.

## Censo retroactivo de métodos

| Etapa | Método | Qué dio |
|---|---|---|
| Ola1 redes/medio, melts n=20, precursor, zoológico | **M2** | La física fundacional: gradiente, precursor, protección del medio, fenotipos |
| Ola1 clones/gimnasio 1.5, cirugías | **M1** | Instrumentos, pasaporte, autonomía del latente |
| **Ola2 §72-§83 completa** | **M1** | El mecanismo del enlace (2-A/2-B causales), el instrumento (atlas 4 niveles, checksums, contrafactual apareado), el mapa del par y el trío gold. TODO con alcance genoma-gold |
| Ola3 (diseño) | — | Solo docs; no corrió |
| **GIM-OLA2 (§84-§86, corrida 2026-07-26/27)** | **M2-calificado** | Fenomenología de la muestra observada: 67/150 probados; roster §86 elegido por λ_E/σ_cat = filtro M1 — NO censo poblacional (audit 2026-07-28 CODE-PHY-001; matriz §6: «§86 fue M2 sin filtro → Falso») |

## Lección registrada (COA, verbatim en espíritu)
"Nos emocionamos: habíamos terminado la etapa clones de Ola2 y en vez de empezar el GIMNASIO de
Ola2 pasamos a clones de Ola3." La escalera correcta por ola: clones (M1, armar instrumento) →
gimnasio (M2, ver la física) → recién entonces la ola siguiente. **La medición es en dinámica
emergente; método 1 arma la probeta, método 2 mide el mundo.**

## Probeta de referencia (regla de calibración M2)
En toda corrida M2 se incluyen configuraciones GOLD (clones calibrados en M1) como probeta: el
instrumento debe medirlas igual que en lab — si la probeta no reproduce lo firmado, el instrumento
no está midiendo bien la población y NADA de la corrida se interpreta.

**Regla de arbitraje (§84, sellada)**: cuando un check del driver se desvía de la letra del
prereg, arbitra la LETRA + recompute independiente — nunca el check tal como quedó implementado.

**Regla del reloj (§85, sellada)**: todo enunciado causal de efecto-de-enlace declara su RELOJ
(absoluto t=0 vs propio del burn t−tFC) — dos firmados de signo opuesto pueden ser el mismo
mecanismo leído en relojes distintos.

**Regla de constantes leídas (§88-t⊥, sellada; caso ejemplar s88_tperp_deep.py:30 — death
fabricado 142.245 cazado por COA)**: toda constante de un análisis read-only (tFC, death,
tFC_pred) se LEE del JSON sellado DENTRO del propio script; si se copia un literal por
conveniencia, el script imprime al lado el valor leído y el log muestra la comparación. Misma
familia que enmienda-como-código (§86).

**Convención única de splitting (§87, sellada)**: todo Δω de programa se reporta como
Δω = ω̂₋ − ω̂₊ (la convención §79-d, receipt sellado en c4b_s79d_dw_check.py). Un driver que use
la convención opuesta imprime AMBOS valores en su salida. Un signo «−» que parezca inversión
física y sea de convención es hallazgo de proceso y va a panel.

**Regla de procedencia de modelos (§92, sellada por COA 2026-07-28)**: el modelo que ejecuta un
panel es **otra variable del experimento** y se registra como tal. Toda sección de bitácora que
cite un panel declara los modelos del **HOST** (main loop), de los **JURADOS** y del **JUEZ** —
del mismo modo que se registra al pie de un commit quién lo escribió. Registro vivo y método de
reconstrucción: **PROCEDENCIA_MODELOS.md**. Tres precisiones que salen de medir, no de suponer:
1. **Ningún script de panel fija modelo** (0 ocurrencias de `model:` en opts de `agent()` sobre
   146 scripts) ⇒ el subagente **hereda el modelo de la sesión**. El banco es del modelo que
   estuviera seleccionado en el host, y eso nunca se declaró en un prereg.
2. **Se registra el modelo OBSERVADO en el transcript, no el declarado en la metadata** — la
   metadata está mal en 5 casos del registro histórico (un panel entero declarado `fable-5` que
   corrió `opus-5` en sus tres agentes).
3. El modelo puede cambiar **dentro de un mismo agente** (24 casos, uno de ellos un juez) ⇒ el
   registro admite valores compuestos (`A+B`), no fuerza un modelo único por jurado.
Estos datos pueden tener **divergencia** y por eso se registran: un veredicto arbitrado por banco
mixto es un dato de procedencia del veredicto. **Prohibido** usar el registro para rankear modelos:
cada banco arbitró material distinto y no hay contrafáctico.

**Regla de enmienda-como-código (§86, sellada)**: un check re-especificado por enmienda sellada se
implementa UNA sola vez como función compartida en src/ con test clavado, y los drivers la
IMPORTAN; re-implementar a mano un check ya enmendado es hallazgo de proceso y va a panel.
(Origen: tercera desviación check-vs-letra — §83 χ≡0, §84 parseval absoluto, §86 parseval absoluto
OTRA VEZ, recidiva exacta de una enmienda ya sellada.) Se completa la re-especificación §84 que
quedó ambigua y es load-bearing: **G1 relativo = resid / ΣE_m de TODAS las capas (S2+Q+S1) del
MISMO sample, umbral <1e-12** (con solo-S2 el máx §86 sería 2.31e-12 y FALLARÍA por muestras frías
con E decimada; todas-las-capas es lo único consistente con los números sellados §84).
