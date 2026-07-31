"""EXPRIMIR OLA2-C1 [M1-análisis]: los 144 films del disco externo, mirados con la lente
«el link es de a dos» (COA 2026-07-30).

QUÉ BUSCA (pre-registrado acá, bitácora §12):
  1. LOCK POR PAR (Arnold de integración): Δθ_ij(t) por arista con ventana deslizante —
     R_w = |⟨e^{iΔθ}⟩|_W. Umbral NO elegido: se guardan los perfiles y el agregador mide
     la separación empírica. t_lock = primer sostén (2 ventanas consecutivas).
  2. FRICCIÓN: P_damp medio pre-lock vs post-lock (la predicción de COA: trabarse = menos
     fricción — el damper γ_c disipa ∝ Δv de emisión).
  3. LIGADURA: E_coup pre/post y ventana final (¿energía retenida en el acople?).
  4. SIN-RUPTURA: lock INTERNO por nodo desde el raw (θ_m = atan2(v_m/ω0_m, x_m), R sobre
     los 10 modos propios) — ¿la unión rompe la coherencia interna del onion?
  5. APAGADO: decaimiento de E por nodo (la red apaga el fuego importado, §61).
  6. Todo con el control fresh APAREADO del mismo archivo donde existe (el fresh no trae raw).

READ-ONLY ABSOLUTO sobre /Volumes/ExternalDisk (es el respaldo verificado del freeze).
Salida: data/c1_exprimido/<eval_id>.json (uno por film) + _indice.json.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
DISK = Path("/Volumes/ExternalDisk/doft-study06-fundamental-lock-dynamics")
SWEEP = DISK / "data/processed/ola1_v4_c1/ola2/sweep"
ORACLE_LOCAL = Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"
BLOCKS = ORACLE_LOCAL / "data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json"
OUT = STUDY07 / "data/c1_exprimido"

SUB = 100          # submuestreo temporal (dt_ef = 8e-3 u.t.; periodo ~1 u.t. => 125 pts)
W_VENT = 125       # ventana deslizante en muestras submuestreadas = 1.0 u.t.
UMBRALES = (0.90, 0.95, 0.99)


def _pares_lock(theta, edges):
    """Por arista: perfil R_w(t) de Δθ, t_lock por umbral, Δθ* final."""
    n_t = theta.shape[0]
    salida = []
    for (i, j) in edges:
        dphi = theta[:, i] - theta[:, j]
        z = np.exp(1j * dphi)
        # media móvil compleja (convolución) => R_w por ventana
        kern = np.ones(W_VENT) / W_VENT
        zm = np.convolve(z, kern, mode="valid")
        rw = np.abs(zm)
        reg = {"i": int(i), "j": int(j),
               "rw_final": float(np.mean(rw[-W_VENT:])),
               "rw_max": float(np.max(rw)), "rw_min": float(np.min(rw)),
               "rw_perfil_p": [float(np.percentile(rw, p)) for p in (5, 25, 50, 75, 95)],
               "dphi_final": float(np.angle(np.mean(zm[-W_VENT:]))),
               "t_lock": {}}
        for u in UMBRALES:
            sobre = rw >= u
            t_ini = None
            # sostén: 2 ventanas consecutivas (2*W_VENT muestras seguidas sobre umbral)
            corr = 0
            for k, s in enumerate(sobre):
                corr = corr + 1 if s else 0
                if corr >= 2 * W_VENT:
                    t_ini = k - 2 * W_VENT + 1
                    break
            reg["t_lock"][str(u)] = (None if t_ini is None
                                     else float(t_ini * SUB * 8e-5))   # en u.t.
            reg[f"frac_sobre_{u}"] = float(np.mean(sobre))
        salida.append(reg)
    return salida


def _lock_interno(raw_x, raw_v, offs, omega0):
    """R interno por nodo (proxy declarado: θ_m = atan2(v/ω0, x) sobre los modos propios)."""
    nodos = []
    for a, b in zip(offs[:-1], offs[1:]):
        x = raw_x[:, a:b].astype(np.float64)
        v = raw_v[:, a:b].astype(np.float64) / omega0[a:b]
        th = np.arctan2(v, x)
        r = np.abs(np.mean(np.exp(1j * th), axis=1))
        nodos.append({"r_ini_5ut": float(np.mean(r[:625])),      # primeras 5 u.t.
                      "r_final_W": float(np.mean(r[-1250:])),    # última ventana 10 u.t.
                      "r_min": float(np.min(r)), "r_medio": float(np.mean(r))})
    return nodos


def _apagado(E):
    """Por nodo: energía inicial, tiempos de caída a 1/2 y 1/10, final."""
    salida = []
    for j in range(E.shape[1]):
        e = E[:, j]
        e0 = float(np.mean(e[:13]))                # ~0.1 u.t. inicial
        def t_bajo(frac):
            idx = np.where(e < frac * e0)[0]
            return float(idx[0] * SUB * 8e-5) if idx.size else None
        salida.append({"E0": e0, "t_mitad": t_bajo(0.5), "t_decimo": t_bajo(0.1),
                       "E_final_W": float(np.mean(e[-1250:]))})
    return salida


def exprimir(ev):
    m = ev["metrics_raw"]
    film = SWEEP / "lock_band_series" / Path(m["lock_band_series_path"]).name
    receipt_path = SWEEP / "transfer_receipts" / Path(m["transport_receipt_path"]).name
    receipt = json.loads(receipt_path.read_text())
    nodos_recibo = receipt.get("nodes", receipt.get("node_receipts", []))
    bloques = {int(n["target_node_index"]): n["block_id"] for n in nodos_recibo}

    with np.load(film, allow_pickle=False) as f:
        edges = f["meta_edges"][:]
        offs = f["meta_node_mode_offsets"][:]
        om0 = f["meta_mode_omega0"][:].astype(np.float64)
        theta = f["theta_nodes"][::SUB]
        E = f["E_nodes"][::SUB]
        p_damp = f["ep_P_damp"][::SUB]
        e_coup = f["ep_E_coup"][::SUB]
        R_red = f["R"][::SUB]
        raw_x = f["raw_x"][::SUB]
        raw_v = f["raw_v"][::SUB]
        th_f = f["control_formation_fresh_theta_nodes"][::SUB]
        E_f = f["control_formation_fresh_E_nodes"][::SUB]
        pd_f = f["control_formation_fresh_ep_P_damp"][::SUB]
        ec_f = f["control_formation_fresh_ep_E_coup"][::SUB]
        masc_her = f["transport_inherited_history_window"][::SUB]
        tau_edges = f["meta_edge_tau"][:].tolist()

    pares = _pares_lock(theta, edges)
    pares_fresh = _pares_lock(th_f, edges)
    # fricción pre/post usando el t_lock 0.95 del primer par trabado (si lo hay)
    t_locks = [p["t_lock"]["0.95"] for p in pares if p["t_lock"]["0.95"] is not None]
    fric = {"p_damp_medio": float(np.mean(p_damp)),
            "p_damp_final_W": float(np.mean(p_damp[-1250:])),
            "p_damp_fresh_medio": float(np.mean(pd_f)),
            "p_damp_fresh_final_W": float(np.mean(pd_f[-1250:]))}
    if t_locks:
        k0 = int(min(t_locks) / (SUB * 8e-5))
        if 10 < k0 < len(p_damp) - 10:
            fric["p_damp_pre_lock"] = float(np.mean(p_damp[:k0]))
            fric["p_damp_post_lock"] = float(np.mean(p_damp[k0:]))
    return {
        "eval_id": ev["eval_id"], "entity_id": ev["entity_id"], "seed": ev["seed"],
        "kappa_global": ev["engine_params"]["kappa_global"],
        "tau_field": ev["engine_params"]["tau_field"],
        "tau_edges": tau_edges,
        "topologia": {"n": m["hydration_node_count"], "aristas": m["hydration_edge_count"]},
        "bloques_por_nodo": bloques,
        "R_red_final_W": float(np.mean(R_red[-1250:])),
        "R_mean_lastW_metrica": m.get("R_mean_lastW"),
        "slips": m.get("anat_slips"),
        "pares": pares, "pares_fresh": pares_fresh,
        "friccion": fric,
        "ligadura": {"e_coup_medio": float(np.mean(e_coup)),
                     "e_coup_final_W": float(np.mean(e_coup[-1250:])),
                     "e_coup_fresh_final_W": float(np.mean(ec_f[-1250:]))},
        "interno": _lock_interno(raw_x, raw_v, offs, om0),
        "apagado": _apagado(E), "apagado_fresh": _apagado(E_f),
        "frac_ventana_heredada": float(np.mean(masc_her)),
        "film": film.name,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    evs = [json.loads(l) for l in open(SWEEP / "evaluations.jsonl")]
    listos = {p.stem for p in OUT.glob("*.json")} - {"_indice"}
    t0 = time.time()
    hechos = 0
    for k, ev in enumerate(evs):
        if ev["eval_id"] in listos:
            continue
        reg = exprimir(ev)
        cuerpo = json.dumps(reg, indent=1)
        (OUT / f"{ev['eval_id']}.json").write_text(cuerpo)
        hechos += 1
        print(f"[{k+1}/{len(evs)}] {ev['eval_id'][:12]} "
              f"n={reg['topologia']['n']} a={reg['topologia']['aristas']} "
              f"rw_finales={[round(p['rw_final'], 3) for p in reg['pares']]} "
              f"({time.time()-t0:.0f}s)", flush=True)
    indice = {"n_evals": len(evs), "procesados_ahora": hechos,
              "sub": SUB, "w_ventana": W_VENT, "umbrales": list(UMBRALES),
              "fuente": str(SWEEP), "nota": "read-only del respaldo verificado"}
    (OUT / "_indice.json").write_text(json.dumps(indice, indent=1))
    print(f"[fin] {hechos} nuevos, total {len(evs)}, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
