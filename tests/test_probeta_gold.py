"""Probeta GOLD como gate CI [M2-build 2]: motor+recorder+instrumentos contra
el fixture sellado — cualquier deriva rompe ANTES de quemar campaña."""
import subprocess
import sys
from pathlib import Path

STUDY07 = Path(__file__).resolve().parents[1]


def test_probeta_gold_verde():
    r = subprocess.run([sys.executable, str(STUDY07 / "tools/probeta_gold.py"),
                        "verificar"], capture_output=True, text=True, timeout=600)
    assert "PROBETA GOLD VERDE" in r.stdout, f"GOLD ROTA:\n{r.stdout}\n{r.stderr}"
