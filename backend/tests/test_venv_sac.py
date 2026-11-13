"""ticket-948: repairing a uv venv whose launcher Smart App Control refuses."""
from pathlib import Path

import pytest

from tessera.services.verification.venv_sac import VenvIrreparable, reparer_venv

FICHIERS = ["python.exe", "pythonw.exe", "python3.dll", "python311.dll", "vcruntime140.dll", "vcruntime140_1.dll"]


def _interpreteur(dossier: Path) -> Path:
    dossier.mkdir(parents=True)
    for nom in FICHIERS:
        (dossier / nom).write_bytes(b"base " + nom.encode())
    (dossier / "autre.dll").write_bytes(b"jamais copie")
    return dossier


def _venv(racine: Path, home: Path | str) -> Path:
    scripts = racine / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_bytes(b"lanceur uv")
    (racine / ".venv" / "pyvenv.cfg").write_text(f"home = {home}\nversion = 3.11\n", encoding="utf-8")
    return racine / ".venv"


def _noms(venv: Path) -> list[str]:
    return sorted(p.name for p in (venv / "Scripts").iterdir())


@pytest.fixture
def uv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    racine = tmp_path / "uvroot"
    monkeypatch.setenv("UV_PYTHON_INSTALL_DIR", str(racine))
    return _interpreteur(racine / "cpython-3.11")


def _lien(cible: Path, vers: Path) -> None:
    try:
        cible.symlink_to(vers, target_is_directory=vers.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not allowed here")


def test_repair_copies_files_and_keeps_the_original(tmp_path: Path, uv: Path) -> None:
    venv = _venv(tmp_path / "run", uv)
    ecrits = reparer_venv(venv, tmp_path / "run")
    scripts = venv / "Scripts"
    assert sorted(ecrits) == sorted(FICHIERS)
    assert (scripts / "python.exe").read_bytes() == b"base python.exe"
    assert (scripts / "python.exe.lanceur-uv").read_bytes() == b"lanceur uv"
    assert not (scripts / "autre.dll").exists()


def test_second_repair_changes_nothing(tmp_path: Path, uv: Path) -> None:
    venv = _venv(tmp_path / "run", uv)
    reparer_venv(venv, tmp_path / "run")
    avant = {p.name: p.read_bytes() for p in (venv / "Scripts").iterdir()}
    assert reparer_venv(venv, tmp_path / "run") == []
    assert {p.name: p.read_bytes() for p in (venv / "Scripts").iterdir()} == avant


def test_cfg_without_home_is_refused(tmp_path: Path, uv: Path) -> None:
    venv = _venv(tmp_path / "run", uv)
    (venv / "pyvenv.cfg").write_text("version = 3.11\n", encoding="utf-8")
    with pytest.raises(VenvIrreparable):
        reparer_venv(venv, tmp_path / "run")
    assert _noms(venv) == ["python.exe"]


def test_home_outside_uv_root_is_refused_even_with_uv_and_python_in_path(
    tmp_path: Path, uv: Path
) -> None:
    faux = _interpreteur(tmp_path / "ailleurs" / "uv" / "python" / "cpython-3.11")
    venv = _venv(tmp_path / "run", faux)
    with pytest.raises(VenvIrreparable):
        reparer_venv(venv, tmp_path / "run")
    assert _noms(venv) == ["python.exe"]


def test_home_that_is_a_link_outside_uv_root_is_refused(tmp_path: Path, uv: Path) -> None:
    faux = _interpreteur(tmp_path / "ailleurs" / "cpython")
    lien = uv.parent / "cpython-lien"
    _lien(lien, faux)
    venv = _venv(tmp_path / "run", lien)
    with pytest.raises(VenvIrreparable):
        reparer_venv(venv, tmp_path / "run")
    assert _noms(venv) == ["python.exe"]


def test_scripts_linked_outside_write_root_is_refused(tmp_path: Path, uv: Path) -> None:
    racine = tmp_path / "run"
    (racine / ".venv").mkdir(parents=True)
    (racine / ".venv" / "pyvenv.cfg").write_text(f"home = {uv}\n", encoding="utf-8")
    dehors = tmp_path / "dehors"
    dehors.mkdir()
    _lien(racine / ".venv" / "Scripts", dehors)
    with pytest.raises(VenvIrreparable):
        reparer_venv(racine / ".venv", racine)
    assert list(dehors.iterdir()) == []


def test_venv_outside_write_root_is_refused(tmp_path: Path, uv: Path) -> None:
    venv = _venv(tmp_path / "autre", uv)
    with pytest.raises(VenvIrreparable):
        reparer_venv(venv, tmp_path / "run")
    assert _noms(venv) == ["python.exe"]


def test_a_source_that_is_a_link_is_refused(tmp_path: Path, uv: Path) -> None:
    (uv / "pythonw.exe").unlink()
    cible = tmp_path / "cible.exe"
    cible.write_bytes(b"x")
    _lien(uv / "pythonw.exe", cible)
    venv = _venv(tmp_path / "run", uv)
    with pytest.raises(VenvIrreparable):
        reparer_venv(venv, tmp_path / "run")
    assert _noms(venv) == ["python.exe"]
