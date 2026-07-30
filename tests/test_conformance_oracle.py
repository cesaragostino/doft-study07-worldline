"""GATE F2 — el motor mínimo de Study07 reproduce los fixtures de conformidad del oráculo.

ENDURECIDO por el double tap wf_27f75f06 (bitácora §3): la v1 de este gate dejaba 24 mutantes de
ley en verde porque los 5 fixtures heredados viven en régimen frío/degenerado. Cambios:
  1. GATE DE DOS NIVELES: en el entorno del generador (numpy+machine coinciden con el meta) se
     exige residuo EXACTO 0.0; fuera de él, ≤ TOL=3.8579e-11 (piso medido §93-C3). El cero es
     diseño (transcripción operación-por-operación de la misma aritmética IEEE-754), no un
     assert universal.
  2. f6 RÉGIMEN CALIENTE (self-contained, generado por tools/gen_f6_from_oracle.py corriendo el
     oráculo read-only): masas≠1 por nodo, kappa=0.7, gamma_c explícito, emission='mean'
     (producción v1), T=0.05 multi-nodo con stream PROPIO, aristas mixtas dict+tupla, IC×100.
  3. f5 pinea la DERIVACIÓN de la semilla (assert del estado inicial del RNG) y corre una
     segunda pasada SIN inyección.
  4. FAIL-LOUD: oráculo ausente = FAIL (skip sólo con STUDY06_ORACLE_OPTIONAL=1); hashes del
     sidecar SELLADOS como constantes y verificados antes de np.load; head0 comparado.
  5. Gates de arquitectura por AST y regex con límite de palabra real (la v1 se cazó a sí misma
     con «sOLA» y los mutantes JM7a-d la evadían).
"""
import ast
import hashlib
import json
import os
import re
import unittest
from pathlib import Path

import numpy as np

from study07.compat.study06_v4 import (birth_state, load_canonical_blocks, parse_theta_v2)
from study07.engine.network import Network
from study07.physics.state import Layer, NodeState

REPO = Path(__file__).resolve().parents[1]
ORACLE = Path(os.environ.get(
    "STUDY06_ORACLE_PATH",
    Path.home() / "code" / "doft-study06-fundamental-lock-dynamics"))
FIXTURES = ORACLE / "tests" / "fixtures"
BLOCKS_JSON = ORACLE / "data/processed/ola1_v4_c1/ola1/simple_blocks_canonical.json"
LOCAL_FIXTURES = REPO / "tests" / "fixtures"

TOL = 3.8579e-11   # piso medido §93-C3 del oráculo

# HASHES SELLADOS de los fixtures del oráculo (sidecar @ study06-freeze-20260729, commit 39f8df6)
ORACLE_FIXTURE_SHA = {
    "f1_gold_aislado": "c8c9d7ac65984ccec8f49072c33d0b2499d04ebd1e2d616c2c3b8aa34c580713",
    "f2_par_sin_delay": "a6dceb6ddad1aca9d81d6eda4a5c90a2b179a46a53a82ac35360e6b06844571b",
    "f3_par_delay_fraccional": "7a8c92a7a1772e8813108c569ac4fe158f274f54e982cec866aeea04af4698d6",
    "f4_red_heterogenea": "849750b3b59524993fe277801d5b1837c862fce65cc3c36d4b9edc3aca96b40e",
    "f5_ruido_rng": "6ba976b8af0682794cee2ab86273b65711601f2e4dd4d7ef87f34f45ed507b48",
}


def _flat(state: NodeState) -> np.ndarray:
    return np.concatenate([state.x, state.v, state.z, state.b, state.e])


def _pinned_env(meta: dict) -> bool:
    """¿Estamos en el entorno del generador? => se exige residuo EXACTO."""
    import platform
    return (np.__version__ == meta.get("numpy") and platform.machine() == meta.get("machine"))


def _load_oracle_fixture(nombre: str):
    path = FIXTURES / f"study07_{nombre}.npz"
    if not path.exists():
        if os.environ.get("STUDY06_ORACLE_OPTIONAL") == "1":
            raise unittest.SkipTest(f"oráculo ausente (declarado opcional): {path}")
        raise AssertionError(
            f"ORÁCULO AUSENTE: {path} — el gate F2 no puede dar verde-vacío. "
            "Exportá STUDY06_ORACLE_PATH o declarás STUDY06_ORACLE_OPTIONAL=1 a sabiendas.")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != ORACLE_FIXTURE_SHA[nombre]:
        raise AssertionError(f"fixture {nombre}: sha256 {sha[:16]} != sellado "
                             f"{ORACLE_FIXTURE_SHA[nombre][:16]} — el oráculo cambió")
    return np.load(path, allow_pickle=False)


def _build_from_oracle_fixture(fx):
    meta = json.loads(str(fx["meta_json"]))
    blocks = load_canonical_blocks(BLOCKS_JSON)
    specs, states = [], []
    for idx, bid in enumerate(meta["block_ids"]):
        theta = blocks[bid]["theta_internal"]
        n_modes = len(theta.get("modes", []))
        scale = 1.0 / max(n_modes, 1) if meta["emission_norm"] == "mean" else 1.0
        spec, _ = parse_theta_v2(theta, emission_scale=scale)
        specs.append(spec)
        states.append(birth_state(spec, meta["seed"], idx,
                                  e_ref_policy=meta.get("e_ref_policy",
                                                        "receiver_initial_energy")))
    return specs, states, meta


def _make_net(specs, states, meta):
    ep = meta["engine_params"]
    return Network(
        specs, states, meta["edges"], dt=float(meta["dt"]), seed=int(meta["seed"]),
        k_global=float(ep.get("kappa_global", ep.get("K_global", 0.0))),
        coupling_damp_ratio=float(ep.get("coupling_damp_ratio", 0.0)),
        coupling_gamma_c=(float(ep["coupling_gamma_c"]) if "coupling_gamma_c" in ep else None),
        tau_field=float(ep.get("tau_field", 0.0)),
        temperature=float(ep.get("temperature", 0.0)),
    )


def _replay(net, fx, meta, inject_rng: bool):
    n_nodes = len(net.specs)
    esperados = [fx[f"estados_nodo{j}"] for j in range(n_nodes)]
    max_d0 = max(float(np.max(np.abs(_flat(net.states[j]) - esperados[j][0])))
                 for j in range(n_nodes))
    d_buf = float(np.max(np.abs(net.history.buffer - fx["buffer0"])))
    d_head = abs(int(net.history.head_idx) - int(fx["head0"]))
    rng_states = ([json.loads(s) for s in fx["rng_states_json"]]
                  if inject_rng and "rng_states_json" in fx.files else None)
    ticks = int(meta["ticks"])
    max_d, peor = 0.0, (0, -1)
    for tick in range(1, ticks + 1):
        if rng_states is not None:
            net.noise_rng.bit_generator.state = rng_states[tick - 1]
        net.step()
        for j in range(n_nodes):
            d = float(np.max(np.abs(_flat(net.states[j]) - esperados[j][tick])))
            if d > max_d:
                max_d, peor = d, (tick, j)
    return {"max_d0": max_d0, "d_buf": d_buf, "d_head": d_head, "max_d": max_d,
            "peor": peor, "ticks": ticks}


class TestConformidad(unittest.TestCase):

    def _assert_gate(self, nombre, r, meta):
        exacto = _pinned_env(meta)
        nivel = "EXACTO(0.0)" if exacto else f"TOL({TOL:.2e})"
        print(f"\n[gate:{nombre}] d0={r['max_d0']:.3e} buf={r['d_buf']:.3e} "
              f"head={r['d_head']} max|d|={r['max_d']:.3e} "
              f"(tick {r['peor'][0]}, nodo {r['peor'][1]}) nivel={nivel}")
        self.assertEqual(r["max_d0"], 0.0, "estado PRE-step debe ser bit-exacto")
        self.assertEqual(r["d_buf"], 0.0, "historia causal inicial debe ser bit-exacta")
        self.assertEqual(r["d_head"], 0, "head del buffer debe coincidir")
        if exacto:
            self.assertEqual(r["max_d"], 0.0,
                             f"en el entorno del generador el residuo debe ser 0.0 EXACTO "
                             f"(midió {r['max_d']:.3e}) — dos niveles, double tap arreglo 1")
        else:
            self.assertLessEqual(r["max_d"], TOL)

    def _gate_oracle(self, nombre, inject_rng=False):
        fx = _load_oracle_fixture(nombre)
        specs, states, meta = _build_from_oracle_fixture(fx)
        net = _make_net(specs, states, meta)
        r = _replay(net, fx, meta, inject_rng)
        self._assert_gate(nombre, r, meta)
        return fx, meta

    def test_f1_gold_aislado(self):
        self._gate_oracle("f1_gold_aislado")

    def test_f2_par_sin_delay(self):
        self._gate_oracle("f2_par_sin_delay")

    def test_f3_par_delay_fraccional(self):
        self._gate_oracle("f3_par_delay_fraccional")

    def test_f4_red_heterogenea(self):
        self._gate_oracle("f4_red_heterogenea")

    def test_f5_ruido_rng_stream_propio(self):
        """Arreglo 3 del double tap: pinea la DERIVACIÓN de la semilla (JM6) — el estado inicial
        del RNG propio debe SER el primero del fixture, y el replay corre SIN inyección."""
        fx = _load_oracle_fixture("f5_ruido_rng")
        specs, states, meta = _build_from_oracle_fixture(fx)
        net = _make_net(specs, states, meta)
        propio = net.noise_rng.bit_generator.state
        grabado = json.loads(str(fx["rng_states_json"][0]))
        self.assertEqual(json.dumps(propio, default=str), json.dumps(grabado, default=str),
                         "la semilla derivada (seed*1000003+99991) no reproduce el stream del "
                         "oráculo — contrato §6 roto")
        r = _replay(net, fx, meta, inject_rng=False)
        self._assert_gate("f5_stream_propio", r, meta)

    def test_f5_ruido_rng_inyectado(self):
        """El replay con inyección por-step sigue siendo un modo válido de auditoría."""
        self._gate_oracle("f5_ruido_rng", inject_rng=True)

    def test_f6_regimen_caliente(self):
        """Arreglo 2 del double tap: el fixture NO degenerado (masas≠1, kappa=0.7, gamma_c
        explícito, emission='mean' = PRODUCCIÓN, T>0 multi-nodo con stream propio, aristas
        dict+tupla, IC×100 ⇒ b fuera del piso). SELF-CONTAINED: corre sin el oráculo."""
        path = LOCAL_FIXTURES / "study07_f6_regimen_caliente.npz"
        self.assertTrue(path.exists(), "f6 falta: tools/gen_f6_from_oracle.py lo genera")
        sha_line = (LOCAL_FIXTURES / "study07_f6.sha256").read_text().split()[0]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), sha_line,
                         "f6 no coincide con su sidecar")
        fx = np.load(path, allow_pickle=False)
        meta = json.loads(str(fx["meta_json"]))

        specs, states = [], []
        for idx, theta in enumerate(meta["thetas_embebidos"]):
            n_modes = len(theta["modes"])
            spec, _ = parse_theta_v2(theta, emission_scale=1.0 / max(n_modes, 1))
            # e_ref del ORÁCULO (la política ya corrió allá): se aplica tal cual
            for lname, val in meta["e_ref_por_nodo"][idx].items():
                spec.struct.e_ref[Layer[lname]] = float(val)
            specs.append(spec)
            # estado inicial DESDE el fixture (pre-step, ya escalado) — no birth
            fila0 = fx[f"estados_nodo{idx}"][0]
            n = spec.n_modes
            states.append(NodeState(
                x=fila0[:n].copy(), v=fila0[n:2 * n].copy(),
                z=fila0[2 * n:2 * n + spec.n_z].copy(),
                b=fila0[2 * n + spec.n_z:2 * n + spec.n_z + spec.n_layers].copy(),
                e=fila0[2 * n + spec.n_z + spec.n_layers:].copy()))
        net = _make_net(specs, states, meta)
        propio = net.noise_rng.bit_generator.state
        self.assertEqual(json.dumps(propio, default=str),
                         json.dumps(json.loads(meta["rng_state0"]), default=str))
        r = _replay(net, fx, meta, inject_rng=False)
        self._assert_gate("f6_regimen_caliente", r, meta)
        # el fixture debe SEGUIR siendo caliente: si b no sale del piso, no protege nada
        b_final = max(float(np.max(np.abs(s.b))) for s in net.states)
        self.assertGreater(b_final, 1e-7, "f6 dejó de ser caliente — regenerar con IC mayor")


class TestArquitectura(unittest.TestCase):
    """Gates ejecutables — endurecidos por el double tap (JM7a-d evadían la v1)."""

    # compat/ EXCLUIDO del gate de IO POR ESCRITO: su trabajo es leer disco (lector explícito).
    # compat/ INCLUIDO en el gate de "ola" (es parte de src/study07).
    IO_SCOPE = ("physics", "engine")
    # artifacts/ INCLUIDO (double tap F5 A7): ahí vive el composer que maneja la
    # procedencia opaca — justo donde un literal de nivel dolería más.
    OLA_SCOPE = ("physics", "engine", "compat", "instruments", "artifacts")
    IMPORTS_PROHIBIDOS = {"matplotlib", "pandas", "h5py", "PIL", "paper5", "olar"}
    CALLS_PROHIBIDAS = {"open", "load", "save", "savez", "savez_compressed", "savetxt",
                        "read_text", "write_text", "dump", "loadtxt"}

    def _archivos(self, subdirs):
        for sub in subdirs:
            base = REPO / "src" / "study07" / sub
            if base.is_dir():
                yield from sorted(base.rglob("*.py"))

    def test_niveles_no_existen_en_el_motor(self):
        """Cláusula 1 de COA. Regex con límite de palabra REAL: caza ola/olas/ola1/OLA_level,
        no caza «sola» ni «interpolación»."""
        rx = re.compile(r"(?i)(?<![A-Za-z])ola(?:s\b|\b|\d|_)")
        for p in self._archivos(self.OLA_SCOPE):
            m = rx.search(p.read_text())
            self.assertIsNone(m, f"{p.relative_to(REPO)} menciona {m.group(0) if m else ''!r}")

    def test_motor_sin_io_ni_dependencias_prohibidas(self):
        """Por AST, no por substring (JM7c evadía el gate viejo con np.load)."""
        for p in self._archivos(self.IO_SCOPE):
            tree = ast.parse(p.read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mods = ([a.name for a in node.names] if isinstance(node, ast.Import)
                            else [node.module or ""])
                    for m in mods:
                        raiz = m.split(".")[0]
                        self.assertNotIn(raiz, self.IMPORTS_PROHIBIDOS,
                                         f"{p.name}: import prohibido {m!r}")
                if isinstance(node, ast.Call):
                    nombre = (node.func.id if isinstance(node.func, ast.Name)
                              else node.func.attr if isinstance(node.func, ast.Attribute)
                              else "")
                    self.assertNotIn(nombre, self.CALLS_PROHIBIDAS,
                                     f"{p.name}: llamada prohibida {nombre!r}()")

    def test_instruments_no_importan_al_motor(self):
        """INSTRUMENT_CONTRACT: un instrumento jamás ejecuta el motor. Puede importar physics,
        artifacts (lector) y compat (parser read-only) — NUNCA engine."""
        import ast as _ast
        base = REPO / "src" / "study07" / "instruments"
        for p in sorted(base.rglob("*.py")):
            tree = _ast.parse(p.read_text())
            for node in _ast.walk(tree):
                if isinstance(node, (_ast.Import, _ast.ImportFrom)):
                    mods = ([a.name for a in node.names] if isinstance(node, _ast.Import)
                            else [node.module or ""])
                    for m in mods:
                        self.assertNotIn("engine", m.split("."),
                                         f"instruments/{p.name} importa el motor: {m!r}")

    def test_study07_no_importa_al_oraculo_en_runtime(self):
        """Higiene post-replay: correr un fixture no debe haber cargado paper5/olar."""
        import sys as _sys
        cargados = {m.split(".")[0] for m in _sys.modules}
        self.assertNotIn("paper5", cargados)
        self.assertNotIn("olar", cargados)

    def test_instruments_proceso_limpio_sin_motor(self):
        """F4 A7: el gate AST caza imports DIRECTOS; éste verifica el INVARIANTE DE PROCESO —
        importar los instrumentos no carga study07.engine ni transitivamente. «Sin re-simular»
        deja de ser sintáctico: el motor NO está en el proceso del observador."""
        import subprocess
        import sys as _sys
        code = ("import sys; sys.path.insert(0, 'src'); "
                "import study07.instruments.api, study07.instruments.phase, "
                "study07.instruments.energy; "
                "malos = [m for m in sys.modules if m.startswith('study07.engine')]; "
                "assert not malos, f'motor cargado transitivamente: {malos}'")
        r = subprocess.run([_sys.executable, "-c", code], cwd=REPO,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0,
                         f"el motor se cargó en el proceso del instrumento:\n{r.stderr}")


if __name__ == "__main__":
    unittest.main()
