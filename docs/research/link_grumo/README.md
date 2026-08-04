# Dinámica de link y grumo — frente paralelo

Este directorio es el registro de trabajo de la rama `research/link-grumo-dynamics`.
No reemplaza ni modifica `docs/bitacora`: sus conclusiones sólo pasan al registro canónico
después de arbitraje y merge documental explícito.

## Alcance

El objetivo es fijar la dinámica física del link y del grumo antes de convertirla en una
regla evolutiva. El orden de preguntas es:

1. ¿El instrumento ve coherencia por geometría de ventana o captura física?
2. ¿El receptor copia pasivamente una señal, cambia su estado o aporta energía?
3. ¿Qué parte de la ventaja transported proviene de energía, memoria estructural,
   susceptibilidad o fase de llegada?
4. ¿Los encuentros remotos son convergencia 1:1, entrada p:q, transferencia armónica o
   creación de una línea colectiva?
5. ¿Un conjunto de links cierra un modo colectivo que ninguna pareja sostiene sola?

No se buscará una fórmula compacta antes de distinguir esos mecanismos.

## Comentario de cierre — retardo/espacio y puertos

El frente experimental `research/k150-emergent-links` se cerró el 2026-08-04
**inconcluso como modelo evolutivo del link**. No produjo una ley causal para
`tau(t)`, una atenuación asociada al retardo ni un mecanismo físico por el cual una
arista nazca o sobreviva. La propuesta posterior de puertos finitos tampoco se
trasladó: hacía depender la existencia de la arista de un árbitro externo de locks,
repitiendo con otro nombre el problema del clasificador de salud.

Sí quedaron dos límites medidos y reproducibles: el `tau` fijo del motor es el
retardo causal exacto de la arista, y todas las capas internas empiezan a responder
dentro del primer tick observable. Además, acortar `tau` adelanta el primer episodio
en muchos pares, pero no ordena la persistencia; existe al menos un contraejemplo
directo donde el retardo largo conserva mejor la organización ciclo a ciclo. El
tiempo de vuelta del lazo no quedó identificado con los films periódicos disponibles.
Estos resultados restringen futuros modelos, pero no son una regla de supervivencia
ni modifican el motor vigente.

## Custodia de datos

Fuentes externas declaradas **sólo lectura por política de este frente**:

- `/Volumes/ExternalDisk/study07_census_arnold`
- `/Volumes/ExternalDisk/study07_film_largo_600`
- `/Volumes/ExternalDisk/study07_lote_suelto_120`
- `/Volumes/ExternalDisk/doft-study06-fundamental-lock-dynamics`

El disco está montado escribible por macOS porque otros procesos pueden necesitarlo. No se
lo remonta ni se cambian permisos. La protección se impone por diseño:

- ningún script de este frente acepta una salida bajo `/Volumes/ExternalDisk`;
- los datos crudos se abren únicamente para lectura;
- cachés, tablas derivadas y figuras van a `logs/link_grumo/`, ignorado por Git;
- resultados pequeños revisados van a `audit/LINK_GRUMO_*`;
- no se crean symlinks escribibles hacia el archivo externo.

Los insumos ignorados por Git que estén en el checkout principal también se tratan como
fuente: se pasan por ruta explícita y se registran sus SHA-256. No se copian films ni views
masivas al worktree.

## Estructura del frente

- `docs/research/link_grumo/PREREGISTRO_DINAMICA.md`: hipótesis, firmas y reglas de decisión.
- `docs/research/link_grumo/ORDEN_COSTO_VALOR.md`: secuencia de gates por CPU e información.
- `audit/LINK_GRUMO_BASELINE.md`: auditoría inicial que abre este frente.
- `audit/LINK_GRUMO_GATE_A_CINEMATICA.md`: primer gate sobre remotos y fresh apareados.
- `audit/LINK_GRUMO_GATE_B_COSECHA.md`: llegada, dominancia temprana y endpoints separados.
- `audit/LINK_GRUMO_GATE_J_POWER.md`: instrumento causal de potencia y cosecha 375/375.
- `audit/LINK_GRUMO_GATE_K_POWER_HEALTH.md`: contraste early→late; potencia identifica
  una ruta energética, no una ley universal de salud.
- `audit/LINK_GRUMO_TIEMPOS_TICKS_S120.md`: reconstrucción bit-exacta del retardo de
  arista y límites de los cruces Q/S1/S2 como medida temporal.
- `audit/LINK_GRUMO_TAU_Y_ONSET_EXISTENTES.md`: contraste apareado de `tau`, conteo
  directo de ciclos y onset interno ON/OFF.
- `audit/LINK_POWER_MAIN_INTEGRATION.md`: contrato para llevar el instrumento a `main`
  sin cambiar lock, fitness ni resultados históricos.
- `tools/link_grumo/`: lectores reproducibles, sin escritura sobre fuentes.
- `logs/link_grumo/`: derivados locales descartables y reproducibles.

## Flujo de trabajo

1. Declarar la pregunta y su nula física antes de abrir el outcome correspondiente.
2. Registrar SHA de tablas, views y manifiestos usados.
3. Ejecutar lectores sólo sobre datos existentes; no intervenir films para rescatar una
   hipótesis.
4. Separar siempre: coherencia de fase, cierre de frecuencia, transmisión, potencia y
   persistencia energética.
5. Publicar desacuerdos y casos no decidibles; no forzar una clasificación binaria.
6. Llevar al branch principal únicamente resultados arbitrados, junto con su enmienda
   documental. La bitácora canónica no se edita desde este worktree.

## Arranque reproducible

Desde este worktree:

```bash
python3 tools/link_grumo/baseline_census.py \
  --source-root /Users/cagostino/code/doft-study07-worldline/data/census_arnold \
  --output logs/link_grumo/baseline_census.json
```

`--source-root` puede apuntar a otra copia verificada. La salida está restringida al
directorio local `logs/link_grumo`.
