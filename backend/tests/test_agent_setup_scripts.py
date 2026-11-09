"""Static checks on the agent account setup scripts (ticket-896).

The scripts create an account and cannot run in CI: only what can be checked
without elevation is checked here.
"""

from pathlib import Path

import pytest

_RACINE = Path(__file__).resolve().parents[2]
_SCRIPTS = _RACINE / "scripts"
_ADMIN = _SCRIPTS / "agent-setup-admin.ps1"
_UTILISATEUR = _SCRIPTS / "agent-setup.ps1"


def _scripts_agent() -> list[Path]:
    return sorted(_SCRIPTS.glob("agent-setup*.ps1"))


def test_both_setup_scripts_exist() -> None:
    assert set(_scripts_agent()) == {_ADMIN, _UTILISATEUR}


@pytest.mark.parametrize("script", _scripts_agent(), ids=lambda p: p.name)
def test_setup_scripts_are_pure_ascii(script: Path) -> None:
    script.read_bytes().decode("ascii")


def test_admin_script_never_touches_the_user_profile() -> None:
    texte = _ADMIN.read_text(encoding="ascii")
    assert "USERPROFILE" not in texte.upper()
    assert "APPDATA" not in texte.upper()
    assert "[string]$Proprietaire" in texte


def test_user_script_refuses_to_run_as_administrator() -> None:
    texte = _UTILISATEUR.read_text(encoding="ascii")
    assert "WindowsBuiltInRole]::Administrator" in texte
    assert "throw" in texte.split("IsInRole", 1)[1].split("}", 1)[0]


def test_tessera_ps1_lists_the_agent_verbs() -> None:
    texte = (_SCRIPTS / "tessera.ps1").read_text(encoding="utf-8-sig")
    assert "'agent'" in texte
    for verbe in ("setup", "jeton", "doctor"):
        assert f"tessera.ps1 agent {verbe}" in texte
        assert f"'{verbe}' {{" in texte


def test_agent_doctor_compares_shared_and_sdk_cli_versions() -> None:
    texte = (_SCRIPTS / "tessera.ps1").read_text(encoding="utf-8-sig")
    assert r"C:\ProgramData\Tessera\bin\claude.exe" in texte
    assert "claude_agent_sdk" in texte
    assert "Copy-Item" in texte


def test_install_page_covers_the_non_administrator_case() -> None:
    page = (_RACINE / "docs" / "agent-isolation.md").read_text(encoding="utf-8")
    assert "pas** administrateur" in page
    assert "agent-setup-admin.ps1" in page
