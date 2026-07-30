"""Worldlines HIJAS — intervenciones como specs de corrida (F6, EXPERIMENT_CONTRACT [M1]).

Una intervención NO es un instrumento: es una spec de corrida hija (WORLDLINE_SCHEMA sellado).
La hija nace de un checkpoint de la madre (parent_run_id + parent_checkpoint_sha256 + tick),
con su timeline de eventos DECLARADO ANTES de correr (pre-registro fail-loud) y ejecutado
entre steps — el motor jamás sabe que fue intervenido: la cirugía es estado/aristas desde
afuera, entre integraciones. La madre JAMÁS se toca.

Tipos de evento v1 (aditivos y exactos — el estado post-cirugía es DERIVABLE del film):
  kick          {tick_hija, nodo, canal: x|v, delta[n_modes]}   → state.canal += delta
  escala_arista {tick_hija, arista, factor_w_k, factor_w_gamma} → pesos *= factor
                (hotcut = factor 0.0)
  gemela        eventos=[] — la hija SIN intervención: el control apareado (intervenida=False)

Semántica de reloj: el evento con tick_hija=k se aplica sobre el estado POST step k-1
(= fila k-1 del film hijo) y el step k integra el estado intervenido. Fila 0 del film hijo =
estado restaurado del checkpoint (= fila tick_madre del film madre).

events.jsonl: un renglón por evento EJECUTADO, con lo aplicado EXACTO y sha256 del estado
pre/post cirugía del objetivo — TODO verificable desde el film + el manifiesto
(verificar_hija recomputa; adulterar events.jsonl es detectable sin sellos extra).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np

from .checkpoint import load_checkpoint, network_from_checkpoint
from .recorder import WorldlineRecorder

TIPOS_VALIDOS = ("kick", "escala_arista")
CANALES_KICK = ("x", "v")


def _sha_estado(vector: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(vector, dtype=np.float64).tobytes()).hexdigest()


def _flat(st) -> np.ndarray:
    return np.concatenate([st.x, st.v, st.z, st.b, st.e])


def validar_eventos(eventos: Sequence[Mapping[str, Any]], net, ticks: int) -> List[Dict]:
    """Pre-registro fail-loud: TODO evento se valida ANTES de crear nada en disco."""
    norm = []
    for i, ev in enumerate(eventos):
        tipo = ev.get("tipo")
        if tipo not in TIPOS_VALIDOS:
            raise RuntimeError(f"evento {i}: tipo desconocido {tipo!r} — válidos "
                               f"{TIPOS_VALIDOS} (pre-registro F6)")
        tk = int(ev.get("tick_hija", -1))
        if not (1 <= tk <= int(ticks)):
            raise RuntimeError(f"evento {i}: tick_hija={ev.get('tick_hija')} fuera de "
                               f"[1, {ticks}] (pre-registro F6)")
        if tipo == "kick":
            nodo = int(ev.get("nodo", -1))
            if not (0 <= nodo < len(net.specs)):
                raise RuntimeError(f"evento {i}: nodo={ev.get('nodo')} fuera de rango "
                                   f"[0, {len(net.specs)}) (pre-registro F6)")
            canal = ev.get("canal")
            if canal not in CANALES_KICK:
                raise RuntimeError(f"evento {i}: canal={canal!r} — válidos {CANALES_KICK}")
            delta = np.asarray(ev.get("delta"), dtype=np.float64)
            n = net.specs[nodo].n_modes
            if delta.shape != (n,):
                raise RuntimeError(f"evento {i}: delta con forma {delta.shape} != ({n},) "
                                   f"del nodo {nodo} (pre-registro F6)")
            if not np.all(np.isfinite(delta)):
                raise RuntimeError(f"evento {i}: delta no finito (pre-registro F6)")
            norm.append({"tipo": "kick", "tick_hija": tk, "nodo": nodo, "canal": canal,
                         "delta": [float(v) for v in delta]})
        else:
            ar = int(ev.get("arista", -1))
            if not (0 <= ar < len(net.edge_ij)):
                raise RuntimeError(f"evento {i}: arista={ev.get('arista')} fuera de rango "
                                   f"[0, {len(net.edge_ij)}) (pre-registro F6)")
            fk = float(ev.get("factor_w_k", 1.0))
            fg = float(ev.get("factor_w_gamma", 1.0))
            if not (np.isfinite(fk) and np.isfinite(fg)):
                raise RuntimeError(f"evento {i}: factor no finito (pre-registro F6)")
            norm.append({"tipo": "escala_arista", "tick_hija": tk, "arista": ar,
                         "factor_w_k": fk, "factor_w_gamma": fg})
    return sorted(norm, key=lambda e: e["tick_hija"])


def _aplicar(ev: Dict, net, tick_madre: int) -> Dict:
    """Aplica UN evento (entre steps) y devuelve el registro ejecutado con lo aplicado
    EXACTO + sha del estado pre/post del objetivo."""
    reg = dict(ev)
    reg["tick_global"] = int(tick_madre) + int(ev["tick_hija"])
    if ev["tipo"] == "kick":
        st = net.states[ev["nodo"]]
        reg["estado_pre_sha256"] = _sha_estado(_flat(st))
        canal = getattr(st, ev["canal"])
        canal += np.asarray(ev["delta"], dtype=np.float64)
        reg["estado_post_sha256"] = _sha_estado(_flat(st))
    else:
        ar = ev["arista"]
        antes = (float(net.edge_w_k[ar]), float(net.edge_w_g[ar]))
        reg["estado_pre_sha256"] = _sha_estado(np.array(antes))
        net.edge_w_k[ar] = antes[0] * ev["factor_w_k"]
        net.edge_w_g[ar] = antes[1] * ev["factor_w_gamma"]
        despues = (float(net.edge_w_k[ar]), float(net.edge_w_g[ar]))
        reg["aplicado"] = {"w_k_antes": antes[0], "w_gamma_antes": antes[1],
                           "w_k_despues": despues[0], "w_gamma_despues": despues[1]}
        reg["estado_post_sha256"] = _sha_estado(np.array(despues))
    return reg


def correr_hija(specs, checkpoint_path: Path, out_dir: Path, manifest: Dict,
                eventos: Sequence[Mapping[str, Any]], ticks: int,
                chunk_ticks: int = 4096, finite_check_every: int = 256):
    """Crea la worldline HIJA: checkpoint → red restaurada (constitución verificada por
    huella) → eventos declarados aplicados entre steps → film propio con linaje EXIGIDO.
    La madre no se toca jamás (la hija sólo LEE el checkpoint). Devuelve (run_dir,
    sha_total, ejecutados)."""
    for clave in ("parent_run_id", "parent_worldline_hash"):
        if clave not in manifest:
            raise RuntimeError(f"manifiesto de hija sin {clave}: el linaje se declara al "
                               "nacer, no se reconstruye después (F6)")
    ck = load_checkpoint(checkpoint_path)
    net = network_from_checkpoint(specs, ck)
    norm = validar_eventos(eventos, net, ticks)     # ANTES de crear nada en disco
    man = dict(manifest)
    man.update({
        "parent_checkpoint_sha256": ck["sha256"],
        "tick_madre": int(ck["meta"]["tick"]),
        "eventos_declarados": norm,
        "intervenida": bool(norm),
    })
    rec = WorldlineRecorder(Path(out_dir), net, man, chunk_ticks=chunk_ticks)
    eventos_path = Path(out_dir) / "events.jsonl"
    eventos_path.write_text("")                     # existe SIEMPRE (gemela: vacío)
    por_tick: Dict[int, List[Dict]] = {}
    for ev in norm:
        por_tick.setdefault(ev["tick_hija"], []).append(ev)
    ejecutados = []
    with eventos_path.open("a") as fh:
        for tick in range(1, int(ticks) + 1):
            for ev in por_tick.get(tick, []):
                reg = _aplicar(ev, net, int(ck["meta"]["tick"]))
                ejecutados.append(reg)
                fh.write(json.dumps(reg) + "\n")
            net.step()
            rec.record_step()
            if finite_check_every and tick % finite_check_every == 0:
                for j, st in enumerate(net.states):
                    if not np.all(np.isfinite(_flat(st))):
                        raise FloatingPointError(
                            f"blow-up: no-finito en nodo {j} al tick {tick} de la hija — "
                            "aborta fail-loud sin COMPLETE (contrato §8)")
    sha_total = rec.close()
    return Path(out_dir), sha_total, ejecutados


def verificar_hija(run_dir: Path, wl: Dict | None = None) -> List[Dict]:
    """Verificador: los eventos EJECUTADOS (events.jsonl) coinciden con los DECLARADOS
    (manifiesto, sellado por el COMPLETE) y son CONSISTENTES con el film — el estado pre
    cirugía ES la fila tick_hija-1 y el post es derivable exacto (pre + delta / pesos ×
    factor). Adulterar events.jsonl se detecta sin sellos extra."""
    from .recorder import load_worldline
    run_dir = Path(run_dir)
    if wl is None:
        wl = load_worldline(run_dir)
    man = wl["manifest"]
    declarados = man.get("eventos_declarados")
    if declarados is None:
        raise RuntimeError(f"{run_dir}: el manifiesto no declara eventos — no es una hija "
                           "F6 (o es pre-esquema)")
    ev_path = run_dir / "events.jsonl"
    if not ev_path.exists():
        raise RuntimeError(f"{run_dir}: sin events.jsonl — la hija debe llevar su timeline "
                           "ejecutado (aunque sea vacío)")
    ejecutados = [json.loads(l) for l in ev_path.read_text().splitlines() if l.strip()]
    if len(ejecutados) != len(declarados):
        raise RuntimeError(f"eventos ejecutados ({len(ejecutados)}) != declarados "
                           f"({len(declarados)}) — el timeline no coincide (F6)")
    tick_madre = int(man["tick_madre"])
    # estados intermedios POR TICK para eventos encadenados en el mismo tick
    encadenado: Dict[int, np.ndarray] = {}
    for i, (dec, ej) in enumerate(zip(declarados, ejecutados)):
        for clave, val in dec.items():
            if ej.get(clave) != val:
                raise RuntimeError(f"evento {i}: campo {clave!r} ejecutado "
                                   f"{ej.get(clave)!r} != declarado {val!r} (F6)")
        if int(ej["tick_global"]) != tick_madre + int(dec["tick_hija"]):
            raise RuntimeError(f"evento {i}: tick_global inconsistente con el linaje")
        tk = int(dec["tick_hija"])
        if dec["tipo"] == "kick":
            nodo = int(dec["nodo"])
            clave_ch = (tk, nodo)
            if clave_ch in encadenado:
                pre = encadenado[clave_ch]
            else:
                fila = wl["estados"][nodo][tk - 1]
                pre = np.array(fila, dtype=np.float64)
            if _sha_estado(pre) != ej["estado_pre_sha256"]:
                raise RuntimeError(f"evento {i}: estado_pre_sha256 no es la fila "
                                   f"{tk - 1} del film — events.jsonl miente (F6)")
            n = len(dec["delta"])
            post = pre.copy()
            base = 0 if dec["canal"] == "x" else n
            post[base:base + n] = post[base:base + n] + np.asarray(dec["delta"])
            if _sha_estado(post) != ej["estado_post_sha256"]:
                raise RuntimeError(f"evento {i}: estado_post_sha256 no es pre+delta — "
                                   "lo aplicado no es lo declarado (F6)")
            encadenado[clave_ch] = post
        else:
            ap = ej.get("aplicado") or {}
            for k in ("w_k_antes", "w_gamma_antes", "w_k_despues", "w_gamma_despues"):
                if k not in ap:
                    raise RuntimeError(f"evento {i}: aplicado sin {k} (F6)")
            if (ap["w_k_despues"] != ap["w_k_antes"] * dec["factor_w_k"]
                    or ap["w_gamma_despues"] != ap["w_gamma_antes"] * dec["factor_w_gamma"]):
                raise RuntimeError(f"evento {i}: los pesos aplicados no son "
                                   "antes×factor EXACTO (F6)")
            if _sha_estado(np.array([ap["w_k_despues"], ap["w_gamma_despues"]])) \
                    != ej["estado_post_sha256"]:
                raise RuntimeError(f"evento {i}: estado_post_sha256 de la arista no "
                                   "coincide con lo aplicado (F6)")
    if bool(man["intervenida"]) != bool(ejecutados):
        raise RuntimeError("intervenida no refleja los eventos ejecutados (F6)")
    return ejecutados
