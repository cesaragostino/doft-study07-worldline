"""M2-build 1 — motor heterogéneo: certificación + re-certificación guardas 1/2 het
y regresión integral het≡hom [§35 bitácora 2026-08-06; doble gate del kernel]."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

STUDY07 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY07 / "src"))

from study07.engine.caldo import RedCaldo
from study07.engine.network import Network
from study07.physics.rhs import derivatives
from study07.physics.rhs_apilado import derivatives_apilado
from study07.physics.rhs_apilado_het import derivatives_apilado_het
from study07.physics.spec_lote import SpecLote
from study07.physics.state import NodeState

DT = 8e-5


def _specs(k=3):
    from study07.compat.study06_v4 import parse_theta_v2
    spec_j = json.loads((STUDY07 / "data/lote_suelto_120/lote/SPEC.json").read_text())
    out = []
    for u in spec_j["unidades"][:k]:
        s, _ = parse_theta_v2(u["constituyentes"][0]["theta"], emission_scale=0.1)
        out.append((s, u["run_id"][:12]))
    return [s for s, _ in out], [g for _, g in out]


def test_certificacion_kernel_het_diff_cero():
    """Gate 1: diff==0 POR GENOMA vs rhs.py (la referencia intocada)."""
    specs, gids = _specs(3)
    lote = SpecLote(specs, gids)
    rng = np.random.default_rng(20260807)
    n, nm = 3, specs[0].n_modes
    x = 0.1 * rng.standard_normal((n, nm)); v = 0.1 * rng.standard_normal((n, nm))
    z = 0.1 * rng.standard_normal((n, specs[0].n_z))
    b = 0.1 * rng.standard_normal((n, specs[0].n_layers))
    e = np.abs(0.1 * rng.standard_normal((n, specs[0].n_layers)))
    het = derivatives_apilado_het(lote, x, v, z, b, e, np.zeros((n, nm)))
    for i in range(n):
        ref = derivatives(specs[i], NodeState(x=x[i], v=v[i], z=z[i], b=b[i], e=e[i]), 0.0)
        for a_h, a_r in zip(het, (ref.x, ref.v, ref.z, ref.b, ref.e)):
            assert np.array_equal(a_h[i], a_r), f"certificación het: genoma {i} difiere"


def test_gate2_n_identicos_bit_exacto_kernel():
    """Gate 2: het con N specs idénticos == kernel homogéneo, bit a bit."""
    specs, gids = _specs(1)
    lote = SpecLote(specs * 4, gids * 4)
    rng = np.random.default_rng(7)
    nm = specs[0].n_modes
    args = (0.1 * rng.standard_normal((4, nm)), 0.1 * rng.standard_normal((4, nm)),
            0.1 * rng.standard_normal((4, specs[0].n_z)),
            0.1 * rng.standard_normal((4, specs[0].n_layers)),
            np.abs(0.1 * rng.standard_normal((4, specs[0].n_layers))),
            np.zeros((4, nm)))
    het = derivatives_apilado_het(lote, *args)
    hom = derivatives_apilado(specs[0], *args)
    for a_h, a_o in zip(het, hom):
        assert np.array_equal(a_h, a_o)


KW = dict(dt=DT, seed=11, K=1e-3, lam=1e-2, tau_s=8e-4,
          T_pulso=0.05, ticks_pulso=100, T_rem=0.05, ticks_rem=200)


def test_regresion_integral_het_igual_hom():
    """Motor COMPLETO (pares, τ, pulso, kicks): het N-idénticos == hom, bit a bit."""
    specs, gids = _specs(1)
    a = RedCaldo(specs[0], 3, **KW)
    b = RedCaldo(specs * 3, 3, genoma_ids=gids * 3, **KW)
    for _ in range(400):
        a.step(); b.step()
    for m_, s_, nom in ((a.x, b.x, "x"), (a.v, b.v, "v"), (a.z, b.z, "z"),
                        (a.b, b.b, "b"), (a.e, b.e, "e"), (a.tau, b.tau, "tau")):
        assert np.array_equal(m_, s_), f"regresión integral het≡hom: canal {nom}"


def test_guarda1_het_aislado_bit_exacto_vs_v1_por_genoma():
    """Guarda 1 het: K=λ=0, DOS genomas DISTINTOS — cada onion bit-exacto 1500 ticks
    contra el motor v1 (Network) corriendo SU genoma."""
    specs, gids = _specs(2)
    caldo = RedCaldo(specs, 2, dt=DT, seed=7, K=0.0, lam=0.0, tau_s=8e-4,
                     T_pulso=0.0, ticks_pulso=0, T_rem=0.05, ticks_rem=300,
                     genoma_ids=gids)
    redes = []
    for i in range(2):
        st0 = NodeState(x=caldo.x[i].copy(), v=caldo.v[i].copy(), z=caldo.z[i].copy(),
                        b=caldo.b[i].copy(), e=caldo.e[i].copy())
        redes.append(Network([specs[i]], [st0], [], dt=DT, seed=7, k_global=0.0,
                             coupling_gamma_c=0.0, tau_field=0.0, temperature=0.0))
    for _ in range(1500):
        caldo.step()
        for r in redes:
            r.step()
    for i in range(2):
        for mio, suyo, nom in ((caldo.x[i], redes[i].states[0].x, "x"),
                               (caldo.v[i], redes[i].states[0].v, "v"),
                               (caldo.z[i], redes[i].states[0].z, "z"),
                               (caldo.b[i], redes[i].states[0].b, "b"),
                               (caldo.e[i], redes[i].states[0].e, "e")):
            assert np.array_equal(mio, suyo), \
                f"guarda 1 het: onion {i} ({gids[i]}) canal {nom} difiere de v1"


def test_guarda2_het_permutacion_identidad_completa():
    """Guarda 2 het: permutar slots moviendo (id, stream, GENOMA) juntos ⇒
    trayectorias por identidad iguales al redondeo."""
    specs, gids = _specs(3)
    perm = [2, 0, 1]
    a = RedCaldo(specs, 3, ids=[0, 1, 2], genoma_ids=gids, **KW)
    b = RedCaldo([specs[p] for p in perm], 3, ids=perm,
                 genoma_ids=[gids[p] for p in perm], **KW)
    for _ in range(300):
        a.step(); b.step()
    for k in range(3):
        sb = int(np.where(b.ids == k)[0][0])
        assert np.allclose(a.x[k], b.x[sb], rtol=1e-9, atol=1e-12), \
            f"guarda 2 het: identidad {k} difiere más allá del redondeo"


def test_fail_loud_sin_genoma_ids():
    specs, gids = _specs(2)
    with pytest.raises(ValueError, match="genoma_ids"):
        RedCaldo(specs, 2, **KW)


def test_checkpoint_het_gate_a_caballo(tmp_path):
    """Artifacts het: checkpoint con población heterogénea — directa vs restore
    BIT-EXACTA cruzando el fin del pulso; fail-loud con genomas permutados."""
    from study07.artifacts.caldo_artifacts import (guardar_checkpoint,
                                                   restaurar_checkpoint)
    specs, gids = _specs(2)
    a = RedCaldo(specs, 2, genoma_ids=gids, **KW)
    for _ in range(100):
        a.step()
    ck = guardar_checkpoint(a, tmp_path / "ck.npz", seed=11, genoma_id="lote2",
                            run_id="t", manifest_sha="m")
    b = restaurar_checkpoint(specs, ck, seed=11, genoma_id="lote2", genoma_ids=gids,
                             K=KW["K"], lam=KW["lam"], tau_s=KW["tau_s"],
                             T_pulso=KW["T_pulso"], ticks_pulso=KW["ticks_pulso"])
    for _ in range(300):
        a.step(); b.step()
    for m_, s_, nom in ((a.x, b.x, "x"), (a.v, b.v, "v"), (a.tau, b.tau, "tau"),
                        (a.b, b.b, "b"), (a.e, b.e, "e")):
        assert np.array_equal(m_, s_), f"checkpoint het: canal {nom} no bit-exacto"
    with pytest.raises(RuntimeError, match="fingerprint"):
        restaurar_checkpoint(specs, ck, seed=11, genoma_id="lote2",
                             genoma_ids=[gids[1], gids[0]],
                             K=KW["K"], lam=KW["lam"], tau_s=KW["tau_s"],
                             T_pulso=KW["T_pulso"], ticks_pulso=KW["ticks_pulso"])
