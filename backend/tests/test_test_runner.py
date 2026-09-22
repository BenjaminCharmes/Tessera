"""Tests for TestRunnerService (ticket-035)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
