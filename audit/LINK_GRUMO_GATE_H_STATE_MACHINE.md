# Gate H — cosecha de la máquina de estados del link

Fecha: 2026-08-02. Branch `research/link-grumo-dynamics`.

Gate H ejecutó el preregistro `LINK_GRUMO_GATE_H_STATE_MACHINE_PREREG.md` sin releer
worldlines. Usó el lector modal v2 y las cuatro series pequeñas producidas por el tap de
transferencia. El resultado completo quedó localmente en
`logs/link_grumo/gate_h_state_machine.json` (SHA-256
`66578d75e476f1441414dbe8a4765226c9180be9523ab69e41db0bcbc50f5836`).

## 1. Resultado principal: una máquina escalar era físicamente incorrecta

La separación `estado del canal x vitalidad` no fue un adorno. Produjo al final de los
600 u.t. dos clases que un único booleano habría mezclado:

| par | cobertura canal+gracia | estado final del canal | vitalidad final | modos finales |
|---|---:|---|---|---|
| 129 | 0.906 | `DOMINANT` | `SOURCE_FADED` | Q0/Q1/Q2 |
| 131 | 0.869 | `DOMINANT` | `SOURCE_FADED` | Q0/Q1/Q2 |
| 132 | 0.188 | `RELEASED` | `SOURCE_FADED` | ninguno |
| 134 | 0.475 | `RELEASED` | `SOURCE_FADED` | ninguno |

Los pares 129/131 conservan un cable espectral extremadamente limpio cuando la fuente ya
cayó a `4.1e-7/4.4e-7` de su máximo causal y la línea recibida a
`3.3e-7/3.5e-7`. Por tanto:

> `DOMINANT` describe conectividad espectral presente; no autoriza a llamarla
> supervivencia energética.

Ésta es la conciliación entre Gate G y los films largos. Gate G detecta muy bien la
formación/persistencia de un edge hasta 60 u.t.; Gate H muestra que el mismo edge puede
continuar mientras toda la actividad se extingue a horizontes mayores.

## 2. Las trayectorias, ya sin confundir modo y unidad

### par134

Captura de unidad en 28.25. Q1 tiene cicatriz y recaptura modal, pero Q2 cubre el link;
no hay muerte de unidad. El único release de unidad ocurre en 312.25, 8 u.t. después de
terminar Q2. Confirma que AND-3Q era incorrecto y que la cobertura por al menos un modo
es la agregación adecuada.

### par129

Captura en 57.25, un único hueco corto recuperado y cero releases de unidad. Q0 recaptura
en 487.75, pero Q2 ya mantenía cobertura continua. El preregistro decía “par129 debe
registrar recaptura” sin fijar la escala; tomada como recaptura del link, la predicción
falla. Tomada como recaptura modal, sostiene.

La corrección no es semántica menor:

* `mode_recapture`: vuelve un camino dentro de un link todavía vivo;
* `recapture`: vuelve el link después de un release real.

### par131

Captura en 68.75, dos releases breves de unidad y dos recapturas antes de 113 u.t.; luego
la cobertura queda continua mediante varios modos. Es el ejemplo limpio de que una
captura tardía no debe prohibirse y un release no es irreversible.

### par132

Cuatro releases y tres recapturas de unidad; el release final queda en 213.25. El pico
posterior de `b_S1` no contradice la máquina: `b` es memoria filtrada del episodio, no
salud presente.

## 3. Estados a 60 u.t. versus destino largo

| par | estado cerca de 60 | vitalidad cerca de 60 | estado a 600 |
|---|---|---|---|
| 129 | `DOMINANT(Q0)` | `DECAYING` | conectado, fuente apagada |
| 131 | `APPROACH` | `DECAYING` | conectado, fuente apagada |
| 132 | `APPROACH` | `DECAYING` | liberado |
| 134 | `DOMINANT(Q0/Q1/Q2)` | `SUSTAINED` | liberado |

Esto conserva dos contraejemplos que una selección en t=60 perdería:

* par131 todavía no consolidó pero termina con cobertura;
* par134 parece el más sano a 60 y termina liberado.

La máquina no intenta adivinar el destino desde una foto. Actualiza el estado a medida
que la trayectoria cambia.

## 4. Sensibilidades baratas

La identidad final es robusta al tiempo de gracia:

* `h=4, 8, 12`: par129/131 terminan `DOMINANT`; par132/134 terminan `RELEASED`.
* El número de releases sí cambia: con `h=12`, los dos huecos tempranos de par131 se
  absorben como gracia. Por eso los bordes de episodios no son física universal.

La fuente termina apagada para los cuatro con pisos relativos `1e-3, 1e-4, 1e-5`.
Sólo se mueve el tiempo de cruce:

| familia de líder | piso 1e-3 | piso 1e-4 | piso 1e-5 |
|---|---:|---:|---:|
| débil, par129/131 | 269–270 | 354–355 | 443–445 |
| fuerte, par132/134 | 248 | 304 | 368 |

La conclusión “conectado pero apagándose” no depende del decimal del piso.

## 5. Qué entra y qué no entra en la máquina

Entra como estado físico mínimo:

* dominancia modal concordante y sostenida;
* cobertura/relevo/hueco/release/recaptura;
* amplitud causal y tendencia de actividad;
* potencia cuando haya una serie temporal válida.

Queda diagnóstico, no puerta:

* coherencia de fase total Q;
* `R≈1`, que identifica seguimiento lineal;
* S1/S2, que describen ruta y maduración;
* `b`, que conserva biografía;
* `chi`, que explica susceptibilidad y mecanismos de eventos.

Así no se descartan esas pistas: se evita pedirles que decidan algo que los controles ya
mostraron que no deciden.

## 6. Límite abierto

La pata de potencia queda `UNKNOWN` en esta ejecución porque el tap existente sólo tiene
spot-checks, no una serie temporal continua incorporable causalmente. Los spots ya
establecen que `rho` es ciego al signo del transporte, pero Gate H no imputa valores
entre ellos.

Por eso Gate H cierra la ontología y el mecanismo de transiciones, no la regla final de
selección evolutiva. Antes de promover `vitalidad` a fitness se necesita una serie barata
de potencia/energía o, como mínimo, una tendencia de actividad sellada en ventanas
disjuntas.

## 7. Reproducción

Entradas de sólo lectura:

* `LECTURA_v2.json`: SHA-256
  `8d6db2f8257c5eb4ddd0242454f376462b4564812dde21e07a8b18973f41672d`;
* series par129/131/132/134: SHA-256 `ee185875...`, `49c7eddc...`,
  `d7623134...`, `c97fa87d...` respectivamente (hashes completos en la salida).

```bash
pytest -q tests/test_link_state_machine.py

PYTHONPATH=src:tools/link_grumo python3 tools/link_grumo/gate_h_state_machine.py \
  --long-reader /Users/cagostino/code/doft-study07-worldline/data/film_largo_600/LECTURA_v2.json \
  --series-root /private/tmp/claude-501/-Users-cagostino-code-doft-study06-fundamental-lock-dynamics/a013d8a0-cafd-49d8-9f07-ba0ef540402e/scratchpad/tap_chi/juez \
  --output logs/link_grumo/gate_h_state_machine.json
```
