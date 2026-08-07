"""HARNESS CENSAL M2 [BUILD 5; taxonomía SELLADA en prereg §43].

`python3 tools/censo_m2.py <run_dir>` → CENSO_<run_id>.json en data/caldo/.
Población COMPLETA reportada (contrato §35): TODO onion y TODO par clasificado,
SIN-CLASIFICAR obligatoria, nada filtrado por interesante. Umbrales DECLARADOS acá
(constantes del harness, versionadas con el código — no se ajustan por corrida).
"""
import json
import sys
from pathlib import Path

import numpy as np

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

DEC = 8
VENTANAS = ((30.0, 60.0), (90.0, 120.0))     # declaradas: creep y régimen tardío
RMS_ENCENDIDO = 0.1                          # declarado (M1: piso ~0.03, encendidos ≥0.6)
RMS_LATENTE = 0.05
FRAC_CLASE = 0.5                             # mayoría de cajas para clasificar el par


def cargar(dirw: Path):
    chunks = sorted((dirw / "worldline").glob("chunk_*.npz"))
    man = json.loads((dirw / "manifest.json").read_text())
    dt = float(man["dt"])
    sig, bq = [], []
    for ch in chunks:
        f = np.load(ch, allow_pickle=False)
        E = f["estados"][::DEC]
        sig.append(E[:, :, 0:3].sum(2))
        bq.append(E[:, :, 27])
    return np.concatenate(sig), np.concatenate(bq), dt, man


def main():
    from study07.instruments.caldo_lecturas import (fases_banda, grafo_lock,
                                                    matriz_tau, mds_espectro,
                                                    residual_afinidad,
                                                    tracker_componentes)
    dirw = Path(sys.argv[1])
    sig, bq, dt, man = cargar(dirw)
    n = sig.shape[1]
    iu = np.triu_indices(n, 1)
    dtd = dt * DEC
    run_id = man.get("run_id", dirw.name)
    censo = {"run_id": run_id, "N": n, "n_pairs": len(iu[0]),
             "manifest_sha_prefix": man.get("git_hash", "")[:12],
             "umbrales": {"rms_encendido": RMS_ENCENDIDO, "rms_latente": RMS_LATENTE,
                          "frac_clase": FRAC_CLASE, "dec": DEC},
             "ventanas": {}}
    # ── por onion (ventana final): ENCENDIDO / LATENTE / SIN-CLASIFICAR ──
    t1a, t1b = VENTANAS[-1]
    i0, i1 = int(t1a / dtd), int(t1b / dtd)
    rms_fin = np.sqrt((sig[i0:i1] ** 2).mean(0))
    clase_onion = np.where(rms_fin > RMS_ENCENDIDO, "ENCENDIDO",
                           np.where(rms_fin < RMS_LATENTE, "LATENTE",
                                    "SIN-CLASIFICAR"))
    censo["onions"] = {"clase": clase_onion.tolist(),
                       "rms_final": [float(r) for r in rms_fin],
                       "conteo": {c: int((clase_onion == c).sum())
                                  for c in ("ENCENDIDO", "LATENTE", "SIN-CLASIFICAR")}}
    # ── por ventana: grafos, E, MDS, componentes ──
    grafos_1ut = []
    for (ta, tb) in VENTANAS:
        i0, i1 = int(ta / dtd), int(tb / dtd)
        ph = fases_banda(sig[i0:i1], dtd)
        A_phi, frac_phi, grado = grafo_lock(ph, dtd)
        E, f_mas, f_menos, racha = residual_afinidad(ph, bq[i0:i1], dtd)
        # clase por par (taxonomía §43): A^b explícito por mayoría de cajas
        phi_l = frac_phi >= FRAC_CLASE
        ncajas = E.shape[0]
        clase_par = np.full(len(iu[0]), "SIN-CLASIFICAR", dtype=object)
        frac_b = np.zeros(len(iu[0]))
        caja = int(round(1.0 / dtd))
        from study07.instruments.caldo_lecturas import omega_reloj, LENGUA
        for a in range(ncajas):
            w = omega_reloj(bq[i0 + a * caja:i0 + (a + 1) * caja].mean(0))
            frac_b += ((np.abs(w[:, None] - w[None, :]) < LENGUA)[iu]).astype(float)
        frac_b /= ncajas
        b_l = frac_b >= FRAC_CLASE
        clase_par[phi_l & b_l] = "LOCK_AFÍN"
        clase_par[f_mas >= FRAC_CLASE] = "LOCK_RESIDUAL"
        clase_par[(~phi_l) & b_l & (f_menos >= FRAC_CLASE)] = "AFÍN_SUELTO"
        clase_par[(~phi_l) & (~b_l) & (frac_phi < 0.1) & (frac_b < 0.1)] = "DESACOPLADO"
        conteo = {c: int((clase_par == c).sum())
                  for c in ("LOCK_AFÍN", "LOCK_RESIDUAL", "AFÍN_SUELTO",
                            "DESACOPLADO", "SIN-CLASIFICAR")}
        censo["ventanas"][f"[{ta:.0f},{tb:.0f}]"] = {
            "pares_conteo": conteo,
            "densidad_grafo": float(phi_l.mean()),
            "grado": {"mediana": float(np.median(grado)), "max": int(grado.max())},
            "E": {"frac_mas_max": float(f_mas.max()), "racha_mas_max": int(racha.max()),
                  "pares_con_residuo_persistente": int((f_mas >= FRAC_CLASE).sum())},
        }
        grafos_1ut.append(A_phi)
    # ── MDS del τ final (del último checkpoint) + tracker entre ventanas ──
    cks = sorted((dirw / "checkpoints").glob("ck_*.npz"))
    if cks:
        tau = np.load(cks[-1], allow_pickle=False)["tau"]
        ev, dstar, no_eucl = mds_espectro(matriz_tau(tau, n))
        censo["mds_final"] = {"dstar": int(dstar), "no_eucl": float(no_eucl),
                              "ev_top5": [float(x) for x in ev[:5]],
                              "tau_mediana": float(np.median(tau)),
                              "tau_max": float(tau.max())}
    # ── d* LOCAL por componente vs GLOBAL (lectura declarada §44b: «mundos por
    # bloques» — grupos con espacio propio de baja dimensión separados por edad) ──
    if cks:
        from study07.instruments.caldo_lecturas import componentes as _comp
        A_fin = grafos_1ut[-1]
        et = _comp(A_fin)
        M_tau = matriz_tau(tau, n)
        locales = []
        for cid in np.unique(et):
            miembros = np.where(et == cid)[0]
            if len(miembros) >= 4:                    # MDS local con sentido
                sub = M_tau[np.ix_(miembros, miembros)]
                _, d_loc, ne_loc = mds_espectro(sub)
                locales.append({"n_miembros": int(len(miembros)),
                                "dstar_local": int(d_loc),
                                "no_eucl_local": float(ne_loc)})
        censo["mundos"] = {"dstar_global": censo.get("mds_final", {}).get("dstar"),
                           "componentes_locales": locales}
    tr = tracker_componentes(grafos_1ut)
    censo["componentes"] = {"fragmentacion": tr["fragmentacion"],
                            "episodios": len(tr["episodios"]),
                            "relevos_totales": sum(e["relevos"] for e in tr["episodios"]),
                            "muertes": sum(1 for e in tr["episodios"]
                                           if e["muere"] is not None)}
    out = STUDY07 / f"data/caldo/CENSO_{run_id}.json"
    out.write_text(json.dumps(censo, indent=1, ensure_ascii=False))
    print(f"[censo] {run_id}: onions {censo['onions']['conteo']} · "
          f"ventana final {censo['ventanas'][list(censo['ventanas'])[-1]]['pares_conteo']} "
          f"→ {out.name}", flush=True)


if __name__ == "__main__":
    main()
