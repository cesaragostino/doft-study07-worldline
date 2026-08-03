# Gate K — potencia temprana sí ve una ruta; no define salud universal

Fecha: 2026-08-02. Branch `research/link-grumo-dynamics`.

## 1. Veredicto corto

El instrumento de potencia era necesario y debe conservarse. La hipótesis más fuerte,
en cambio, queda rechazada:

> El intercambio energético temprano no es una condición necesaria ni una coordenada
> universal de supervivencia. Es, sobre todo, la firma energética de la ruta
> `transported`.

La potencia aporta física que coherencia/ocupación no contienen: distingue si los dos
extremos están intercambiando energía neta, perdiéndola juntos o conservando sólo una
relación geométrica. Pero no mejora de manera material la predicción de salud una vez
que la dinámica temprana ya se observa, y los links `fresh` pueden consolidarse sin
mostrar intercambio temprano.

Consecuencia operacional:

* **sí** incluir `link_power` en la instrumentación poblacional;
* **no** añadir todavía potencia a fitness, al veredicto de lock o a la máquina de
  estados universal;
* tratarla como coordenada de mecanismo/ruta, no como sinónimo de vida.

## 2. Integridad de la lectura

La corrida citable cruzó 340 films no-self de Gate F con las 375 views de Gate J:

* 340/340 `run_id` encontrados;
* 340/340 `worldline_hash` y `view_hash_power` verificados;
* 340/340 pares de una arista identificables;
* 337 films limpios y tres banderas conservadas como sensibilidad;
* predictor `[2,20]`, outcome sellado `[50,60]`, sin soporte compartido;
* sólo se abrieron views locales; el disco externo no fue releído ni escrito.

Ledger derivado ignorado por git:

```text
logs/link_grumo/gate_k_power_health.json
sha256 7164732187b887cb7a0b04e24a53cff0bdae20a5dd9ac329467d581d9231f030
```

Población limpia: 71 sanos y 266 no sanos; 55 pares discordantes
transported/fresh.

## 3. La señal agregada es fuerte y no es mera fuerza

En los 337 films limpios:

| Medición `[2,20]` | AUC salud60 | mediana sano | mediana no sano |
|---|---:|---:|---:|
| fracción de cajas con signos opuestos | 0.825 | 0.575 | 0.192 |
| eficiencia `intercambio/force²` | 0.741 | 0.322 | 0.0152 |
| tasa de intercambio | 0.738 | `2.88e-7` | `6.69e-9` |
| `force²` | 0.578 | `2.34e-6` | `1.24e-6` |

La tasa mediana es unas 43 veces mayor entre sanos, pero la fuerza sola apenas separa.
En el contraste apareado de los 55 outcomes discordantes:

| Medición | sano mayor | no sano mayor | empate |
|---|---:|---:|---:|
| fracción de signos opuestos | 51 | 3 | 1 |
| eficiencia de intercambio | 50 | 4 | 1 |
| tasa de intercambio | 46 | 8 | 1 |
| `force²` | 31 | 24 | 0 |

Esto demuestra que no basta con “el acoplamiento empuja fuerte”. Importa la geometría
energética: un extremo entrega mientras el otro recibe. La potencia mide un fenómeno
real distinto de la amplitud del drive.

## 4. La trampa: el agregado mezcla salud con biografía

La aparente regla se rompe al separar la ruta:

| Estrato | AUC intercambio | AUC signos opuestos |
|---|---:|---:|
| `transported`: 59 sanos / 110 no sanos | 0.697 | 0.826 |
| `fresh`: 12 sanos / 156 no sanos | 0.537 | 0.568 |

Y el contraste apareado revela la inversión sin ambigüedad:

| Brazo del sobreviviente | pares | signos: sano mayor | no sano mayor | empate |
|---|---:|---:|---:|---:|
| `transported` | 51 | 50 | 0 | 1 |
| `fresh` | 4 | 1 | 3 | 0 |

Para eficiencia ocurre lo mismo: `49–1–1` cuando sobrevive transported y `1–3–0`
cuando sobrevive fresh. La muestra de fresh sano es pequeña, pero alcanza para refutar
la necesidad universal: una sola ruta válida sin la señal ya basta; aquí hay varias.

Después de quitar de `rank(intercambio)` lo explicable por brazo, `log1p(dw)` y
`rank(force²)`, el AUC residual queda en 0.591. No es cero, pero está lejos de la señal
agregada de 0.825. La mayor parte de la aparente brújula era biografía y estructura de
encuentro.

La lectura física más económica es:

> `transported` hereda una relación de fase/energía que permite transferencia dirigida
> desde el comienzo. `fresh` puede construir el lock por otra ruta —captura disipativa,
> consolidación tardía o ambos extremos perdiendo energía al acoplamiento— sin que haya
> un donante y un receptor netos en la primera ventana.

Esto no degrada a la biografía a un confusor estadístico: probablemente identifica el
mecanismo por el que la biografía habilita canales remotos. Sí impide convertir ese
mecanismo particular en ley de salud de todos los links.

## 5. Coherencia/ocupación ya contienen casi todo el destino a 60

En el banco Gate G de 60 films, leave-one-pair-out y sin ajustar hiperparámetros:

| Modelo | AUC | log-loss |
|---|---:|---:|
| M0: brazo + `dw` + coherencia Q + ocupación | 0.939 | 0.310 |
| M1: M0 + fuerza | 0.935 | 0.319 |
| M2: M1 + potencia | 0.942 | 0.315 |

Respecto de M1, potencia recupera `+0.0067` de AUC y reduce log-loss en `0.0040`.
Corrige una clasificación y empeora una. Respecto del mejor baseline M0, M2 queda con
AUC apenas mayor pero log-loss todavía peor.

Gate G es case-control seleccionado por outcome, de modo que no es validación
prospectiva independiente. Aun así responde la pregunta mecánica: una vez visibles la
línea ganadora y su coherencia, la potencia no agrega un segundo orden de salud de peso
comparable.

## 6. El tiempo confirma que es memoria de ruta, no destino tardío

Los rankings apareados no se fortalecen al acercarse al outcome:

| Ventana | intercambio sano/no sano/empate | eficiencia | signos opuestos |
|---|---:|---:|---:|
| `[2,10]` | 46/8/1 | 50/4/1 | 50/4/1 |
| `[2,20]` | 46/8/1 | 50/4/1 | 51/3/1 |
| `[10,20]` | 45/7/3 | 41/11/3 | 44/7/4 |
| `[20,40]` | 40/15/0 | 28/27/0 | 42/13/0 |

La eficiencia pierde casi toda dirección en `[20,40]`. Eso es lo contrario de una
variable de salud que se consolida uniformemente: la señal más fuerte ya estaba al
comienzo y luego las rutas convergen, liberan o se reorganizan.

Hay 85 films con intercambio exactamente cero en `[2,20]`; seis llegan sanos a 60:

* `par130_f_k03_tau02`;
* `olaB_par008_f_k03_tau02`;
* `olaB_par010_f_k03_tau02`;
* `olaB_par012_t_k03_tau02`;
* `olaB_par013_f_k03_tau02`;
* `olaB_par024_f_k03_tau02`.

No son todos links tardíos o mudos. En Gate G, por ejemplo, `par130_f` ya tiene
ocupación observada `1.94`, Q W4 `0.966` y episodio Q confirmado a `6.99`; aun así sus
dos extremos no muestran transferencia neta de signo opuesto en las cajas tempranas.
`olaB_par012_t` ya tiene Q primaria W8 `0.995` y también intercambio cero. La condición
“lock sano implica donante→receptor neto” queda falsada directamente.

El contraejemplo inverso es `par130_t`: intercambio `0.0204`, signos opuestos en 82% de
las cajas y `force²=8.43`, pero no llega sano a 60; su fresh correspondiente sí llega con
intercambio cero. Mucha transferencia puede ser pulling, tránsito o disipación durante
un intento fallido, no supervivencia.

## 7. Qué dice la contabilidad física

En las 94.580 cajas causales completas de 2 u.t., ninguna tuvo potencia neta suavizada
positiva: `P0_mean + P1_mean <= 0` en toda la población. Esto no significa que el
acoplamiento jamás devuelva energía. A tasa instantánea:

* 336/340 films tienen alguna muestra de potencia neta positiva;
* 11.516/97.300 muestras son positivas;
* rango instantáneo observado: `[-2877.77, 17.84]`.

La caja de 2 u.t. promedia la devolución reversible del resorte y deja visible el balance
disipativo de más largo plazo. Por eso `intercambio` debe leerse exactamente como fue
definido: redistribución neta entre extremos dentro de un link globalmente disipativo en
esa escala. No es “energía creada por el link” ni una medida total de actividad del
onion.

Éste es el aporte físico durable de Gate J/K: ahora podemos separar tres casos que antes
parecían el mismo lock espectral:

1. transferencia dirigida entre extremos;
2. captura/coherencia con ambos extremos entregando energía al acoplamiento;
3. fuerza e intercambio grandes sin consolidación futura.

## 8. Regla resultante para link y grumo

La máquina de estados no necesita otra puerta universal. La regla mínima sigue siendo:

```text
línea compartida gana -> coherencia se consolida -> persistencia/recaptura decide salud
```

`link_power` se incorpora al costado como anotación mecánica:

```text
estado del canal:      UNKNOWN / ABSENT / PROVISIONAL / COHERENT / RELEASED
modo energético:      UNKNOWN / TRANSFER / JOINT_DISSIPATION / WEAK_SUPPORT
```

Los nombres del segundo eje son semántica, no thresholds ya aprobados. No se deben
codificar aún como estados discretos ni usar para eliminar links. Primero deben
observarse alineados al nacimiento/release de cada ruta, especialmente en fresh y en
horizontes largos.

Para grumos, la potencia puede responder quién alimenta a quién y dónde se disipa la
energía en el cluster. La existencia del edge debe seguir saliendo de ocupación,
coherencia y persistencia; el flujo energético describe la función del edge dentro del
grumo.

## 9. Reproducción

```bash
PYTHONPATH=src:tools/link_grumo python3 tools/link_grumo/gate_k_power_health.py \
  --power-ledger logs/link_grumo/gate_j_power_population.json \
  --health logs/link_grumo/gate_f_health_coordinates.json \
  --gate-g logs/link_grumo/gate_g_evaluate.json \
  --output logs/link_grumo/gate_k_power_health.json
```

La salida es determinista y sólo depende de hashes declarados. No se tocaron
`docs/bitacora`, resultados canónicos ni fitness.
