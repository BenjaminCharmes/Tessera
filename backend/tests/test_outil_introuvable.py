"""Tests for the missing-tool detection (ticket-496)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from tessera.services.outil_introuvable import outil_introuvable
from tessera.services.test_runner import TestRunnerService

_PNPM_TSC = (
    "undefined\n"
    " ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL  Command \"tsc\" not found\n"
)


class TestOutilIntrouvable:
    def test_pnpm_command_not_found_returns_the_tool(self, tmp_path: Path) -> None:
        assert outil_introuvable(_PNPM_TSC, tmp_path) == "tsc"

    def test_windows_not_recognized_returns_the_tool(self, tmp_path: Path) -> None:
        sortie = "'vitest' is not recognized as an internal or external command,\n"
        assert outil_introuvable(sortie, tmp_path) == "vitest"

    def test_sh_not_found_returns_the_tool(self, tmp_path: Path) -> None:
        assert outil_introuvable("sh: 1: next: not found", tmp_path) == "next"
        assert outil_introuvable("sh: eslint: command not found", tmp_path) == "eslint"

    def test_module_under_node_modules_outside_the_project_is_recognised(
        self, tmp_path: Path
    ) -> None:
        projet = tmp_path / "devinoo"
        projet.mkdir()
        ancien = tmp_path / "make-your-call" / "node_modules" / "vitest" / "vitest.mjs"
        sortie = f"Error: Cannot find module '{ancien}'\n"

        assert outil_introuvable(sortie, projet) == "vitest"

    def test_missing_module_inside_the_project_node_modules_is_recognised(
        self, tmp_path: Path
    ) -> None:
        mort = tmp_path / "node_modules" / "@scope" / "pkg" / "index.js"
        sortie = f"Error: Cannot find module '{mort}'"

        assert outil_introuvable(sortie, tmp_path) == "@scope/pkg"

    def test_existing_module_inside_the_project_is_not_recognised(
        self, tmp_path: Path
    ) -> None:
        present = tmp_path / "node_modules" / "x" / "index.js"
        present.parent.mkdir(parents=True)
        present.write_text("", encoding="utf-8")

        assert outil_introuvable(f"Cannot find module '{present}'", tmp_path) is None

    def test_project_file_module_is_not_recognised(self, tmp_path: Path) -> None:
        sortie = "Error: Cannot find module './brand'\nRequire stack:\n- a.ts"
        assert outil_introuvable(sortie, tmp_path) is None

    def test_bare_specifier_is_not_recognised(self, tmp_path: Path) -> None:
        assert outil_introuvable("Cannot find module 'react'", tmp_path) is None

    def test_ordinary_red_test_is_not_recognised(self, tmp_path: Path) -> None:
        assert outil_introuvable("1 failed, 4 passed in 0.6s", tmp_path) is None


class TestTestRunnerPanneDEnvironnement:
    async def test_recognised_step_is_not_started(self, tmp_path: Path) -> None:
        proc = MagicMock()
        proc.returncode = 1
        proc.communicate = AsyncMock(return_value=(b"", _PNPM_TSC.encode()))

        runner = TestRunnerService()
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await runner.run_tests(tmp_path, test_command="pnpm tsc")

        assert result.passed is False
        assert result.demarree is False
        assert "panne d'environnement" in result.output_summary
        assert "`tsc`" in result.output_summary
        assert result.etapes[-1].code == 1

    async def test_ordinary_failure_stays_started(self, tmp_path: Path) -> None:
        proc = MagicMock()
        proc.returncode = 1
        proc.communicate = AsyncMock(return_value=(b"1 failed, 4 passed in 0.6s", b""))

        runner = TestRunnerService()
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await runner.run_tests(tmp_path, test_command="pnpm vitest")

        assert result.demarree is True
        assert "panne d'environnement" not in result.output_summary
