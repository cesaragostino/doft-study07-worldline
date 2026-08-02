#!/usr/bin/env python3
"""Auditoría basal read-only del census Arnold para el frente link/grumo.

Lee tablas, reportes y views existentes. Sólo puede escribir debajo de
``logs/link_grumo`` del worktree que contiene este archivo. No modifica ni copia datos
crudos y rechaza explícitamente salidas en el disco externo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[2]
SAFE_OUTPUT_ROOT = REPO / "logs" / "link_grumo"
EXTERNAL_ROOT = Path("/Volumes/ExternalDisk")
FALSE_ZONE = {"W4": 1.1 / 4.0, "W8": 1.1 / 8.0}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_output(path: Path) -> Path:
    root = SAFE_OUTPUT_ROOT.resolve()
    out = path.expanduser()
    if not out.is_absolute():
        out = (REPO / out)
    resolved = out.resolve()
    if resolved.is_relative_to(EXTERNAL_ROOT.resolve()):
        raise SystemExit("La salida bajo /Volumes/ExternalDisk está prohibida")
    if not resolved.is_relative_to(root):
        raise SystemExit(f"La salida debe quedar bajo {root}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def cargar_filas(source: Path) -> tuple[list[dict], dict[str, str]]:
    paths = [source / "tabla_tanda1.json", source / "tabla_tanda2.json"]
    if not all(p.is_file() for p in paths):
        raise SystemExit(f"Faltan tablas bajo {source}")
    filas: list[dict] = []
    for path, tanda in zip(paths, (1, 2)):
        prefix = f"t{tanda}_"
        for raw in json.loads(path.read_text()):
            if raw.get("celda", "k03_tau02") != "k03_tau02":
                continue
            f = dict(raw)
            f["_tanda"] = tanda
            f["_par"] = prefix + str(f["par_idx"])
            f["_self"] = bool(f.get("self_par", False))
            f["_dw"] = 0.0 if f["_self"] else float(
                f.get("dw_fina_prereg", f.get("dw_fina")))
            filas.append(f)
    return filas, {p.name: sha256(p) for p in paths}


def lock60(f: dict, window: str) -> bool:
    t_lock = f[window]["t_lock_ut"]
    return t_lock is not None and float(t_lock) <= 60.0


def delta_apareado(filas: list[dict], predicate) -> float:
    por_par: dict[str, dict[str, dict]] = {}
    for f in filas:
        if not f["_self"]:
            por_par.setdefault(f["_par"], {})[f["brazo"]] = f
    pares = [x for x in por_par.values() if "t" in x and "f" in x]
    return float(np.mean([predicate(x["t"]) - predicate(x["f"]) for x in pares]))


def tendencia(filas: list[dict], lo: float, hi: float = 50.0) -> dict:
    sel = [f for f in filas if f["brazo"] == "t" and not f["_self"]
           and lo <= f["_dw"] < hi]
    x = np.log([f["_dw"] for f in sel])
    y = np.array([lock60(f, "W4") for f in sel], dtype=float)
    cov = float(np.mean(x * y) - x.mean() * y.mean())
    corr = float(np.corrcoef(x, y)[0, 1]) if y.std() > 0 else float("nan")
    return {"n": len(sel), "rate": float(y.mean()), "cov_logdw_lock": cov,
            "corr_logdw_lock": corr}


def indexar_reportes(source: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in source.rglob("REPORTE.json"):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for unit in data.get("unidades", []):
            run_id = unit.get("run_id")
            if run_id:
                out[run_id] = unit
    return out


def indexar_views_w8(source: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for manifest in source.rglob("par_link/*/manifest.json"):
        try:
            man = json.loads(manifest.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if float(man.get("observation_config", {}).get("w_ut", -1)) != 8.0:
            continue
        data = manifest.with_name("data.npz")
        if data.is_file():
            out[str(man["worldline_hash"])[:16]] = data
    return out


def nearest_rational(ratio: float, max_order: int) -> tuple[float, int, int]:
    candidates = []
    for p in range(2, max_order + 1):
        for q in range(1, p):
            if math.gcd(p, q) == 1:
                candidates.append((abs(ratio / (p / q) - 1.0), p, q))
    return min(candidates)


def auc(pos: list[float], neg: list[float]) -> float | None:
    if not pos or not neg:
        return None
    greater = sum(a > b for a in pos for b in neg)
    equal = sum(a == b for a in pos for b in neg)
    return float((greater + 0.5 * equal) / (len(pos) * len(neg)))


def componentes(edges: list[tuple[str, str]]) -> list[int]:
    adjacency: dict[str, set[str]] = {}
    for a, b in edges:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    seen: set[str] = set()
    sizes = []
    for start in adjacency:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        size = 0
        while stack:
            node = stack.pop()
            size += 1
            for other in adjacency[node]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def enriquecer_remotos(filas: list[dict], reports: dict[str, dict],
                       views: dict[str, Path]) -> list[dict]:
    out = []
    for f in filas:
        if f["brazo"] != "t" or f["_self"] or f["_dw"] < 1.0:
            continue
        report = reports.get(f["run_id"])
        if not report:
            continue
        view = views.get(str(report["worldline_hash"])[:16])
        if not view:
            continue
        with np.load(view) as npz:
            omega = np.asarray(npz["omega_nodo"], dtype=float)
        early = omega[:, 1]
        late = omega[:, 2]
        ratio = float(max(early) / max(min(early), 1e-300))
        early_dw = float(abs(early[0] - early[1]))
        late_dw = float(abs(late[0] - late[1]))
        strict = bool(lock60(f, "W8") and early_dw > FALSE_ZONE["W8"]
                      and late_dw < FALSE_ZONE["W8"])
        metrics = report.get("metricas", {})
        e0 = float(metrics.get("E0_nodo0", 0.0) + metrics.get("E0_nodo1", 0.0))
        out.append({"run_id": f["run_id"], "block_i": f["block_i"],
                    "block_j": f["block_j"], "dw_isolated": f["_dw"],
                    "early_omega": early.tolist(), "late_omega": late.tolist(),
                    "early_dw": early_dw, "late_dw": late_dw,
                    "early_ratio": ratio, "lock60_W8": lock60(f, "W8"),
                    "strict_remote": strict, "E0": e0,
                    "nearest_Q6": nearest_rational(ratio, 6),
                    "nearest_Q8": nearest_rational(ratio, 8)})
    return out


def rational_control(remotos: list[dict], order: int, seed: int = 20260802,
                     n_perm: int = 20_000) -> dict:
    eligible = [r for r in remotos if r["early_dw"] > FALSE_ZONE["W8"]]
    successes = np.array([r[f"nearest_Q{order}"][0] for r in eligible
                          if r["strict_remote"]])
    controls = np.array([r[f"nearest_Q{order}"][0] for r in eligible
                         if not r["strict_remote"]])
    if not len(successes) or not len(controls):
        return {"n_success": len(successes), "n_control": len(controls)}
    observed = float(np.median(controls) - np.median(successes))
    all_values = np.r_[successes, controls]
    rng = np.random.default_rng(seed + order)
    exceed = 0
    for _ in range(n_perm):
        idx = rng.choice(len(all_values), len(successes), replace=False)
        mask = np.ones(len(all_values), dtype=bool)
        mask[idx] = False
        stat = float(np.median(all_values[mask]) - np.median(all_values[idx]))
        exceed += stat >= observed
    return {"n_success": len(successes), "n_control": len(controls),
            "median_residual_success": float(np.median(successes)),
            "median_residual_control": float(np.median(controls)),
            "frac_below_1pct_success": float(np.mean(successes < 0.01)),
            "frac_below_1pct_control": float(np.mean(controls < 0.01)),
            "p_perm_one_sided_add_one": float((exceed + 1) / (n_perm + 1)),
            "n_perm": n_perm}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path,
                        help="data/census_arnold existente; se abre sólo para lectura")
    parser.add_argument("--output", required=True, type=Path,
                        help="debe quedar bajo logs/link_grumo del worktree")
    args = parser.parse_args()

    source = args.source_root.expanduser().resolve()
    output = safe_output(args.output)
    filas, input_hashes = cargar_filas(source)
    reports = indexar_reportes(source)
    views = indexar_views_w8(source)

    counts = {}
    nesting = {}
    for window in ("W4", "W8"):
        counts[window] = {}
        for arm in ("t", "f"):
            sel = [f for f in filas if not f["_self"] and f["brazo"] == arm]
            counts[window][arm] = {"n": len(sel),
                                   "lock60": sum(lock60(f, window) for f in sel),
                                   "rate": float(np.mean([lock60(f, window) for f in sel]))}
    for arm in ("t", "f"):
        sel = [f for f in filas if not f["_self"] and f["brazo"] == arm]
        nesting[arm] = {"W8_without_W4": sum(lock60(f, "W8") and not lock60(f, "W4")
                                                 for f in sel),
                        "W4_without_W8": sum(lock60(f, "W4") and not lock60(f, "W8")
                                                 for f in sel)}

    diagnostic = {}
    for window in ("W4", "W8"):
        zone = FALSE_ZONE[window]
        diagnostic[window] = {
            "delta_first": delta_apareado(filas, lambda f, w=window: lock60(f, w)),
            "delta_first_plus_late_close": delta_apareado(
                filas, lambda f, w=window, z=zone: lock60(f, w)
                and float(f[w]["dw_tardia"]) < z),
            "delta_final_plus_late_close": delta_apareado(
                filas, lambda f, w=window, z=zone: int(f[w]["estado"]) == 2
                and float(f[w]["dw_tardia"]) < z),
        }

    remotos = enriquecer_remotos(filas, reports, views)
    strict = [r for r in remotos if r["strict_remote"]]
    remote_locks = [r for r in remotos if r["lock60_W8"]]
    edges = [(r["block_i"], r["block_j"]) for r in remote_locks]
    component_sizes = componentes(edges)

    middle = [r for r in remotos if 1.0 <= r["dw_isolated"] < 10.0]
    e_lock = [r["E0"] for r in middle if r["lock60_W8"]]
    e_fail = [r["E0"] for r in middle if not r["lock60_W8"]]

    result = {
        "_meta": {"script": str(Path(__file__).relative_to(REPO)),
                  "source_root": str(source), "input_sha256": input_hashes,
                  "policy": "source read-only; output restricted to logs/link_grumo"},
        "false_firm_zone": FALSE_ZONE,
        "counts_nonself": counts,
        "W_nesting": nesting,
        "trend_W4_transported": {"dw_0.02_50": tendencia(filas, 0.02),
                                  "dw_0.30_50": tendencia(filas, 0.30),
                                  "dw_1_50": tendencia(filas, 1.0)},
        "paired_diagnostics": diagnostic,
        "remote_W8": {
            "n_lock_isolated_dw_ge_1": len(remote_locks),
            "n_strict": len(strict),
            "n_strict_1_10": sum(1.0 <= r["dw_isolated"] < 10.0 for r in strict),
            "n_strict_10_50": sum(10.0 <= r["dw_isolated"] < 50.0 for r in strict),
            "strict_cases": strict,
            "graph": {"edges": len(edges),
                      "nodes": len({n for edge in edges for n in edge}),
                      "component_sizes": component_sizes},
            "E0_1_10": {"n_lock": len(e_lock), "n_fail": len(e_fail),
                         "median_lock": float(np.median(e_lock)),
                         "median_fail": float(np.median(e_fail)),
                         "auc": auc(e_lock, e_fail)},
            "rational_Q6": rational_control(remotos, 6),
            "rational_Q8": rational_control(remotos, 8),
        },
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[link-grumo] fuente abierta sólo lectura: {source}")
    print(f"[link-grumo] salida: {output}")
    print(f"[link-grumo] remotos W8={len(remote_locks)} · estrictos={len(strict)}")


if __name__ == "__main__":
    main()
