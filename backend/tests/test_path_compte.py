"""ADR-086: the account's PATH comes from the toolchain, never from the backend's."""
from pathlib import Path

import pytest

from tessera.services.providers import path_compte
from tessera.services.providers.path_compte import ChaineAbsente, path_du_compte
from tessera.services.verification.lancement_compte import _NOMS_REPRIS, EchecLancementCompte, env_du_compte
from tests.chaine_factice import chaine_factice  # noqa: F401

SRC = Path(__file__).resolve().parents[1] / "src" / "tessera"


def _entrees(chemin: str) -> list[str]:
    return [e for e in chemin.split(";") if e]


def test_user_entries_of_the_backend_path_are_dropped(
    monkeypatch: pytest.MonkeyPatch, chaine: Path, tmp_path: Path
) -> None:
    systeme = tmp_path / "Windows" / "System32"
    systeme.mkdir(parents=True)
    monkeypatch.setenv("SystemRoot", str(tmp_path / "Windows"))
    monkeypatch.setenv("PATH", rf"C:\Users\x\scoop\shims;{systeme};{tmp_path / 'Windows' / 'absent'}")
    entrees = _entrees(path_du_compte())
    assert not [e for e in entrees if "scoop" in e]
    assert str(systeme) in entrees
    assert str(tmp_path / "Windows" / "absent") not in entrees
    assert entrees[0] == str(chaine / "node")


def test_toolchain_entries_come_first_in_order(monkeypatch: pytest.MonkeyPatch, chaine: Path) -> None:
    monkeypatch.setenv("PATH", "")
    assert _entrees(path_du_compte()) == [
        str(chaine / "node"), str(chaine / "uv"), str(chaine / "python"),
        str(chaine / "python" / "Scripts"),
    ]


def test_missing_toolchain_refuses_and_names_agent_setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(path_compte, "TOOLCHAIN", tmp_path / "vide")
    with pytest.raises(ChaineAbsente, match="agent setup"):
        path_du_compte()
    with pytest.raises(EchecLancementCompte, match="agent setup"):
        env_du_compte()


def test_no_module_builds_an_account_path_elsewhere() -> None:
    """Every ``"PATH"`` literal in src/ is the exact assignment or the allow-list."""
    permis = ('["PATH"] = path_du_compte()', '"SystemRoot", "PATH", "TEMP"')
    hors = [
        f"{p.relative_to(SRC)}:{n}"
        for p in SRC.rglob("*.py") if p.name != "path_compte.py"
        for n, ligne in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if '"PATH"' in ligne and not any(a in ligne for a in permis)
    ]
    assert hors == []


def test_backend_path_is_not_taken_over_by_the_allow_list() -> None:
    assert "path" not in {nom.lower() for nom in _NOMS_REPRIS}


def test_executable_is_found_with_the_windows_extensions(tmp_path: Path) -> None:
    (tmp_path / "uv.exe").write_bytes(b"")
    assert path_compte.resoudre_executable("uv", str(tmp_path)) == str(tmp_path / "uv.exe")
    assert path_compte.resoudre_executable("uv.exe", f"{tmp_path / 'absent'};{tmp_path}") is not None
    assert path_compte.resoudre_executable("absent", str(tmp_path)) is None
