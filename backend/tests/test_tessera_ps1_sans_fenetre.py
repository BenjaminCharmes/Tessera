"""`tessera.ps1 run` starts the backend and Vite without console windows (ticket-901).

Le script ne tourne pas en CI (Windows, WMI) : on vérifie son texte.
"""

from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "tessera.ps1"


def _fonction(texte: str, nom: str) -> str:
    debut = texte.index(f"function {nom}")
    fin = texte.find("\nfunction ", debut + 1)
    return texte[debut:] if fin == -1 else texte[debut:fin]


def test_start_cache_hides_the_window_through_win32_process_create() -> None:
    corps = _fonction(_SCRIPT.read_text(encoding="utf-8-sig"), "Start-Cache")
    assert "Win32_Process -MethodName Create" in corps
    assert "ProcessStartupInformation" in corps
    assert "ShowWindow = [uint16]0" in corps


def test_backend_and_frontend_both_start_hidden() -> None:
    texte = _SCRIPT.read_text(encoding="utf-8-sig")
    assert "Start-Cache" in _fonction(texte, "Start-Backend")
    frontend = _fonction(texte, "Start-Frontend")
    assert "Start-Cache" in frontend
    assert "Start-Process" not in frontend


def test_console_logs_go_under_localappdata() -> None:
    corps = _fonction(_SCRIPT.read_text(encoding="utf-8-sig"), "Get-DossierJournaux")
    assert "$env:LOCALAPPDATA 'Tessera\\logs'" in corps
