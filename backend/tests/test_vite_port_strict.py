"""Port 5173 must not be shared with a foreign page (ticket-942)."""
from __future__ import annotations

import re
from pathlib import Path

_RACINE = Path(__file__).resolve().parent.parent.parent


def test_vite_config_sets_strict_port() -> None:
    config = (_RACINE / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
    assert re.search(r"server:\s*\{[^}]*strictPort:\s*true", config, re.DOTALL)


def test_doctor_checks_port_5173() -> None:
    script = (_RACINE / "scripts" / "tessera.ps1").read_text(encoding="utf-8")
    doctor = script.split("function Invoke-Doctor", 1)[1].split("\nfunction ", 1)[0]
    assert "Test-Port5173Libre" in doctor
    verif = script.split("function Test-Port5173Libre", 1)[1].split("\nfunction ", 1)[0]
    assert "-LocalPort 5173" in verif
