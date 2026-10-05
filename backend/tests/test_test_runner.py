"""Tests for TestRunnerService (ticket-035)."""

import asyncio
import os
import sys
from typing import Any
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import requires_symlinks

from tessera.services.test_runner import (
    TestCommandNotFound,
    TestResult,
    TestRunnerService,
)


@pytest.fixture
def python_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def node_project(tmp_path: Path) -> Path:
    (tmp_path / "package.json").write_text('{"name": "test", "scripts": {"test": "vitest run"}}', encoding="utf-8")
    return tmp_path


@pytest.fixture
def rust_project(tmp_path: Path) -> Path:
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def service() -> TestRunnerService:
    return TestRunnerService()


class TestAutoDetect:
    def test_detects_python_project(self, service: TestRunnerService, python_project: Path) -> None:
        cmd = service.detect_test_command(python_project)
        assert cmd == "uv run pytest"

    def test_detects_node_project(self, service: TestRunnerService, node_project: Path) -> None:
        cmd = service.detect_test_command(node_project)
        assert cmd == "npm test"

    def test_detects_rust_project(self, service: TestRunnerService, rust_project: Path) -> None:
        cmd = service.detect_test_command(rust_project)
        assert cmd == "cargo test"

    def test_uses_explicit_command_override(self, service: TestRunnerService, tmp_path: Path) -> None:
        cmd = service.detect_test_command(tmp_path, override="make test")
        assert cmd == "make test"

    def test_raises_when_no_test_file_found(self, service: TestRunnerService, tmp_path: Path) -> None:
        with pytest.raises(TestCommandNotFound):
            service.detect_test_command(tmp_path)

    def test_python_takes_priority_over_node(
        self, service: TestRunnerService, tmp_path: Path
    ) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "package.json").touch()
        cmd = service.detect_test_command(tmp_path)
        assert cmd == "uv run pytest"


class TestDossierEtDelaiDeclares:
    """Ticket-241 : les tests d'ide-core vivent dans `../../backend`."""

    async def test_la_commande_se_lance_dans_le_dossier_declare(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / ".git").mkdir()
        projet = tmp_path / "projects" / "ide-core"
        projet.mkdir(parents=True)
        (projet / "agents.json").write_text('{"git_root": "ancestor"}', encoding="utf-8")
        (tmp_path / "backend").mkdir()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"5 passed", b""))

        runner = TestRunnerService(cwd="../../backend")
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as lance:
            result = await runner.run_tests(projet, test_command="uv run pytest")

        assert result.passed is True
        assert Path(lance.call_args.kwargs["cwd"]) == (tmp_path / "backend").resolve()

    async def test_un_dossier_hors_perimetre_ne_demarre_pas(
        self, python_project: Path
    ) -> None:
        runner = TestRunnerService(cwd="../ailleurs")
        with patch("asyncio.create_subprocess_exec") as lance:
            result = await runner.run_tests(python_project, test_command="uv run pytest")

        lance.assert_not_called()
        assert result.passed is False
        assert result.demarree is False
        assert "../ailleurs" in result.output_summary

    async def test_le_delai_declare_s_applique_par_defaut(
        self, python_project: Path
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"5 passed", b""))
        mock_proc.returncode = 0

        runner = TestRunnerService(timeout=300)
        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.wait_for", wraps=asyncio.wait_for) as attente,
        ):
            await runner.run_tests(python_project, test_command="uv run pytest")

        # Le délai borne la commande entière : une étape reçoit ce qui reste,
        # moins les microsecondes déjà écoulées (ticket-337).
        assert attente.call_args.kwargs["timeout"] == pytest.approx(300.0, abs=1.0)


class TestRunTests:
    async def test_returns_passed_result_on_success(
        self, service: TestRunnerService, python_project: Path
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"5 passed in 0.5s", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await service.run_tests(python_project, test_command="uv run pytest")

        assert result.passed is True
        assert isinstance(result.total, int)
        assert result.duration_ms >= 0

    async def test_returns_failed_result_on_nonzero_exit(
        self, service: TestRunnerService, python_project: Path
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"1 failed, 4 passed in 0.6s", b"AssertionError: ...")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await service.run_tests(python_project, test_command="uv run pytest")

        assert result.passed is False
        assert result.failed >= 0

    async def test_handles_timeout(
        self, service: TestRunnerService, python_project: Path
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await service.run_tests(
                python_project, test_command="uv run pytest", timeout=1
            )

        assert result.passed is False
        assert "timeout" in result.output_summary.lower()

    async def test_le_processus_tue_est_attendu(
        self, service: TestRunnerService, python_project: Path
    ) -> None:
        # Après `proc.kill()` sans `await proc.wait()`, asyncio se plaignait
        # d'un transport fermé sur un processus encore vivant, et le zombie
        # restait jusqu'à la fin du serveur (ticket-122).
        mock_proc = MagicMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await service.run_tests(python_project, test_command="uv run pytest", timeout=1)

        mock_proc.kill.assert_called_once()
        mock_proc.wait.assert_awaited_once()

    async def test_aucun_test_collecte_n_est_pas_un_echec(
        self, service: TestRunnerService, python_project: Path
    ) -> None:
        # pytest sort 5 quand il n'a rien collecté. Lu comme rouge, un projet
        # neuf sans test renvoyait le codeur corriger des tests inexistants.
        mock_proc = MagicMock()
        mock_proc.returncode = 5
        mock_proc.communicate = AsyncMock(
            return_value=(b"no tests ran in 0.01s", b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await service.run_tests(python_project, test_command="uv run pytest")

        assert result.passed is True
        assert result.total == 0
        assert result.failed == 0
        assert "aucun test" in result.output_summary.lower()

    async def test_raises_when_no_command_detectable(
        self, service: TestRunnerService, tmp_path: Path
    ) -> None:
        with pytest.raises(TestCommandNotFound):
            await service.run_tests(tmp_path)

    async def test_never_uses_shell_true(
        self, service: TestRunnerService, python_project: Path
    ) -> None:
        """Security: subprocess must never use shell=True."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"1 passed", b""))
        captured_kwargs: dict = {}

        async def mock_exec(*args: object, **kwargs: object) -> MagicMock:
            captured_kwargs.update(kwargs)
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            await service.run_tests(python_project, test_command="uv run pytest")

        assert captured_kwargs.get("shell") is not True

    async def test_uses_custom_command(
        self, service: TestRunnerService, python_project: Path
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))
        captured_args: list = []

        async def mock_exec(*args: object, **kwargs: object) -> MagicMock:
            captured_args.extend(args)
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            await service.run_tests(python_project, test_command="make test")

        assert "make" in captured_args


class TestTestResult:
    def test_default_values(self) -> None:
        result = TestResult(
            passed=True,
            total=5,
            failed=0,
            output_summary="5 passed",
            errors=[],
            duration_ms=100,
        )
        assert result.passed is True
        assert result.errors == []


# ---------------------------------------------------------------------------
# Lancer une commande qui est un script Windows — ticket-157
# ---------------------------------------------------------------------------


class TestCommandeNonDemarree:
    """The runner must tell a command that never started from failing tests."""

    async def test_npm_se_resout_en_npm_cmd_sous_windows(self) -> None:
        # Le premier ticket du projet démineur a été rendu `blocked` avec
        # « changes requested » alors que le code produit était juste : le
        # testeur lance sans shell, et `npm` n'existe pas sous Windows — c'est
        # `npm.cmd`. La reprise existait dans `ProcessRegistry` depuis le
        # ticket-149 et n'avait pas été portée ici (ticket-157).
        from tessera.services.lancement import essais_de_commande

        essais = essais_de_commande(["npm", "run", "test"])

        assert essais[0] == ["npm", "run", "test"]
        if os.name == "nt":
            assert ["npm.cmd", "run", "test"] in essais
        else:
            assert essais == [["npm", "run", "test"]]

    async def test_une_commande_deja_suffixee_n_est_pas_redoublee(self) -> None:
        from tessera.services.lancement import essais_de_commande

        assert essais_de_commande(["npm.cmd", "test"]) == [["npm.cmd", "test"]]

    async def test_une_commande_introuvable_n_est_pas_un_test_rouge(
        self, tmp_path: Path
    ) -> None:
        # Deux tours de revue ont été dépensés à corriger du code qui n'était
        # pas en cause, parce que rien ne distinguait « la commande n'a pas
        # démarré » de « les tests ont échoué ».
        runner = TestRunnerService()

        result = await runner.run_tests(
            tmp_path, test_command="cette-commande-nexiste-pas --run"
        )

        assert result.passed is False
        assert result.demarree is False
        assert "cette-commande-nexiste-pas" in result.output_summary

    async def test_des_tests_qui_echouent_restent_demarres(
        self, tmp_path: Path
    ) -> None:
        # Le pendant du test précédent : `demarree` ne doit pas devenir un
        # synonyme de `passed`, sinon il ne distingue plus rien.
        runner = TestRunnerService()

        result = await runner.run_tests(
            tmp_path,
            test_command=f'"{sys.executable}" -c "import sys; sys.exit(1)"',
        )

        assert result.passed is False
        assert result.demarree is True


class TestCheminSymlinke:
    """A project reached through a symlink must still run its tests."""

    @requires_symlinks
    async def test_le_cwd_est_resolu_avant_de_lancer(self, tmp_path: Path) -> None:
        # `projects/` ne contient que des liens symboliques vers les vrais
        # dépôts. Lancer avec le chemin du lien fait résoudre à Vite une
        # racine réelle qu'il ne retrouve plus : les tests échouaient sous le
        # pipeline et passaient à la main, au même instant et au même endroit
        # (ticket-158). ADR-017 pose déjà « cwd résolu » — pas ici.
        reel = tmp_path / "projet-reel"
        reel.mkdir()
        (reel / "temoin.txt").write_text("ici", encoding="utf-8")
        lien = tmp_path / "lien-vers-projet"
        lien.symlink_to(reel, target_is_directory=True)

        runner = TestRunnerService()
        vus: list[str] = []

        async def faux_lancer(args: list[str], dossier: Path) -> Any:
            vus.append(str(dossier))
            raise FileNotFoundError(args[0])

        runner._lancer = faux_lancer  # type: ignore[method-assign]
        await runner.run_tests(lien, test_command="peu-importe")

        assert vus == [str(reel)], f"cwd non résolu : {vus}"
