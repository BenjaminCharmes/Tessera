"""Tests for the shared bench environment (ticket-1060). No model is called."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import banc_codeur_roles as roles  # noqa: E402


def _venv(base: Path, *, interpreteur: bool = True) -> Path:
    venv = base / "banc-venv"
    (venv / "Scripts").mkdir(parents=True)
    if interpreteur:
        (venv / "Scripts" / "python.exe").write_text("", encoding="utf-8")
    return venv


def test_environnement_partage_returns_the_designated_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    venv = _venv(tmp_path)
    monkeypatch.setenv("BANC_VENV", str(venv))
    assert roles.environnement_partage() == venv


def test_environnement_partage_accepts_a_posix_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    venv = tmp_path / "v"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_text("", encoding="utf-8")
    monkeypatch.setenv("BANC_VENV", str(venv))
    assert roles.environnement_partage() == venv


def test_environnement_partage_refuses_a_missing_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BANC_VENV", raising=False)
    with pytest.raises(roles.EnvironnementRefuse):
        roles.environnement_partage()


def test_environnement_partage_refuses_a_relative_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BANC_VENV", "relatif/venv")
    with pytest.raises(roles.EnvironnementRefuse):
        roles.environnement_partage()


def test_environnement_partage_refuses_a_folder_without_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BANC_VENV", str(_venv(tmp_path, interpreteur=False)))
    with pytest.raises(roles.EnvironnementRefuse):
        roles.environnement_partage()


def test_environnement_partage_refuses_the_backend_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    venv = tmp_path / "backend" / ".venv"
    (venv / "Scripts").mkdir(parents=True)
    (venv / "Scripts" / "python.exe").write_text("", encoding="utf-8")
    monkeypatch.setattr(roles, "_DEPOT", tmp_path)
    monkeypatch.setenv("BANC_VENV", str(venv))
    with pytest.raises(roles.EnvironnementRefuse, match="backend"):
        roles.environnement_partage()


def test_environnement_partage_does_not_create_a_missing_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    absent = tmp_path / "absent"
    monkeypatch.setenv("BANC_VENV", str(absent))
    with pytest.raises(roles.EnvironnementRefuse):
        roles.environnement_partage()
    assert not absent.exists()


def test_env_des_commandes_sets_the_variable_without_touching_os_environ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    env = roles.env_des_commandes(tmp_path)
    assert env["UV_PROJECT_ENVIRONMENT"] == str(tmp_path)
    assert "UV_PROJECT_ENVIRONMENT" not in os.environ


def test_lancer_passes_env_to_subprocess_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vus: list[dict[str, str]] = []

    def faux_run(commande: list[str], **kw: object) -> subprocess.CompletedProcess[bytes]:
        env = kw["env"]
        assert isinstance(env, dict)
        vus.append(env)
        return subprocess.CompletedProcess(commande, 0)

    monkeypatch.setattr(roles.subprocess, "run", faux_run)
    env = roles.env_des_commandes(tmp_path)
    for commande in (roles.COMMANDE_ENV, roles.COMMANDE_TESTS):
        assert asyncio.run(roles._lancer(commande, tmp_path, env)) is True
    assert [v["UV_PROJECT_ENVIRONMENT"] for v in vus] == [str(tmp_path)] * 2


def test_bench_sources_never_create_a_venv() -> None:
    for source in _SCRIPTS_DIR.glob("banc_codeur*.py"):
        texte = source.read_text(encoding="utf-8")
        assert '"venv"' not in texte and "uv venv" not in texte, source.name
