"""Tests for the environment given to project code (ticket-888)."""

from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera.coffre import NOMS_SECRETS
from tessera.services.verification import app_du_run, captures, groupe_d_etape, process_registry, test_runner
from tessera.services.verification.env_du_code_de_projet import env_du_code_de_projet
from tessera.services.verification.test_runner import TestRunnerService

_SECRETS = ("GITHUB_TOKEN", "GH_TOKEN", *NOMS_SECRETS)


def _poser_les_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    for nom in _SECRETS:
        monkeypatch.setenv(nom, "valeur-secrete")


def test_secrets_and_github_tokens_are_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    _poser_les_secrets(monkeypatch)

    env = env_du_code_de_projet()

    assert [nom for nom in _SECRETS if nom in env] == []


def test_a_secret_name_is_removed_whatever_its_case(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("github_token", "valeur-secrete")

    env = env_du_code_de_projet()

    assert [nom for nom in env if nom.lower() == "github_token"] == []


def test_an_ordinary_variable_and_extra_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "/usr/bin")

    env = env_du_code_de_projet({"PYTHONPATH": "/worktree/src"})

    assert env["PATH"] == "/usr/bin"
    assert env["PYTHONPATH"] == "/worktree/src"


def test_extra_is_applied_over_the_inherited_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TESSERA_888_VAR", "herite")

    assert env_du_code_de_projet({"TESSERA_888_VAR": "surcharge"})["TESSERA_888_VAR"] == "surcharge"


def test_the_process_environment_is_not_modified(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    monkeypatch.setenv("GITHUB_TOKEN", "valeur-secrete")

    env_du_code_de_projet()

    assert os.environ["GITHUB_TOKEN"] == "valeur-secrete"


@pytest.mark.parametrize("env_propre", [None, {"PYTHONPATH": "/worktree/src"}])
async def test_test_runner_launches_without_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, env_propre: dict[str, str] | None
) -> None:
    _poser_les_secrets(monkeypatch)
    proc = MagicMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=(b"1 passed", b""))

    with patch("asyncio.create_subprocess_exec", return_value=proc) as lance:
        await TestRunnerService(env=env_propre).run_tests(tmp_path, test_command="make test")

    env = lance.call_args.kwargs["env"]
    assert [nom for nom in _SECRETS if nom in env] == []


async def test_process_registry_launches_without_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _poser_les_secrets(monkeypatch)

    with patch("asyncio.create_subprocess_exec", return_value=MagicMock()) as lance:
        await process_registry.ProcessRegistry()._lancer(["serveur"], tmp_path)

    assert [nom for nom in _SECRETS if nom in lance.call_args.kwargs["env"]] == []


async def test_app_du_run_launches_without_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _poser_les_secrets(monkeypatch)
    proc = MagicMock(pid=1, returncode=None)

    with patch("asyncio.create_subprocess_exec", return_value=proc) as lance:
        await app_du_run.demarrer_processus(["app"], tmp_path)

    assert [nom for nom in _SECRETS if nom in lance.call_args.kwargs["env"]] == []


async def test_captures_script_launches_without_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _poser_les_secrets(monkeypatch)
    proc = MagicMock(returncode=0)
    proc.communicate = AsyncMock(return_value=(b"", b""))
    config = MagicMock(url="http://localhost:1", largeurs=(), themes=(), ecrans=(), session=None)

    with patch("asyncio.create_subprocess_exec", return_value=proc) as lance:
        await captures._lancer_le_script(["node"], config, tmp_path, None)

    assert [nom for nom in _SECRETS if nom in lance.call_args.kwargs["env"]] == []


@pytest.mark.parametrize("module", [test_runner, process_registry, app_du_run, captures, groupe_d_etape])
def test_no_module_inherits_the_whole_environment(module: ModuleType) -> None:
    texte = Path(str(module.__file__)).read_text(encoding="utf-8")

    assert "**os.environ" not in texte
    assert "env=None" not in texte
