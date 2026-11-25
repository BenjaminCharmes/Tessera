"""Static checks on the script that denies creation in shared folders (ticket-1020).

The script changes the ACL of system folders and needs elevation: CI cannot
run it. Only what can be read without running it is checked here.
"""

from pathlib import Path

_RACINE = Path(__file__).resolve().parents[2]
_SCRIPT = _RACINE / "scripts" / "agent-refus-creation-admin.ps1"


def _texte() -> str:
    return _SCRIPT.read_text(encoding="ascii")


def test_script_is_pure_ascii() -> None:
    _SCRIPT.read_bytes().decode("ascii")


def test_script_denies_creation_only_for_the_agent_account() -> None:
    texte = _texte()
    # Un seul refus, vise par SID : creer un fichier, creer un dossier.
    assert '/deny "*${Sid}:(CI)(WD,AD)"' in texte
    assert texte.count("/deny") == 1
    assert "/grant" not in texte
    assert "/inheritance" not in texte
    assert "/setowner" not in texte


def test_script_never_touches_the_account_itself() -> None:
    texte = _texte()
    for interdit in ("Set-LocalUser", "New-LocalUser", "Remove-LocalUser", "ConvertTo-SecureString", "net user"):
        assert interdit not in texte


def test_script_names_the_three_shared_folders() -> None:
    texte = _texte()
    for dossier in (r"'C:\Users\Public'", r"'C:\Windows\Temp'", r"'C:\ProgramData'"):
        assert dossier in texte


def test_script_can_be_undone_and_run_twice() -> None:
    texte = _texte()
    assert "[switch]$Retirer" in texte
    assert '/remove:d "*$Sid"' in texte
    # Le dossier deja dans l'etat voulu est saute : icacls doublerait l'entree.
    assert texte.index("deja fait") < texte.index("/deny")


def test_script_checks_every_folder_before_the_first_change() -> None:
    texte = _texte()
    assert texte.index("Dossier introuvable") < texte.index("/remove:d")


def test_install_page_tells_how_to_run_and_undo_it() -> None:
    page = (_RACINE / "docs" / "agent-isolation.md").read_text(encoding="utf-8")
    assert "agent-refus-creation-admin.ps1" in page
    assert "-Retirer" in page
