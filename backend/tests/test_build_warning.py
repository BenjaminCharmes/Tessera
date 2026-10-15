"""A test command that skips the project's build is flagged — ticket-454."""
import json
from pathlib import Path
from unittest.mock import AsyncMock

from tessera.services.build_warning import build_warnings, folders_with_build_script
from tessera.services.orchestrator import Orchestrator


def _package_json(folder: Path, scripts: dict[str, str] | None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    content: dict[str, object] = {"name": "demo"}
    if scripts is not None:
        content["scripts"] = scripts
    (folder / "package.json").write_text(json.dumps(content), encoding="utf-8")


def test_warns_when_build_script_and_test_command_skips_it(tmp_path: Path) -> None:
    _package_json(tmp_path, {"build": "vite build", "test": "vitest"})

    warnings = build_warnings(tmp_path, "npm test")

    assert len(warnings) == 1
    assert f"test_command ne lance pas le build de {tmp_path.name}" in warnings[0]
    assert "une erreur de build passera jusqu'à la CI" in warnings[0]


def test_no_warning_when_test_command_runs_build(tmp_path: Path) -> None:
    _package_json(tmp_path, {"build": "vite build"})

    assert build_warnings(tmp_path, "npm --prefix . run build && npm test") == []


def test_no_warning_when_test_command_runs_check_build(tmp_path: Path) -> None:
    _package_json(tmp_path, {"build": "vite build"})

    assert build_warnings(tmp_path, "npm run check:build") == []


def test_no_warning_without_package_json(tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()

    assert build_warnings(tmp_path, "npm test") == []


def test_no_warning_when_package_json_has_no_build_script(tmp_path: Path) -> None:
    _package_json(tmp_path, {"test": "vitest"})
    _package_json(tmp_path / "web", None)

    assert build_warnings(tmp_path, "npm test") == []


def test_warns_for_first_level_subfolder_and_names_it(tmp_path: Path) -> None:
    _package_json(tmp_path / "frontend", {"build": "vite build"})

    warnings = build_warnings(tmp_path, "pytest")

    assert len(warnings) == 1
    assert "build de frontend" in warnings[0]


def test_warns_when_test_command_is_unset(tmp_path: Path) -> None:
    _package_json(tmp_path, {"build": "vite build"})

    assert len(build_warnings(tmp_path, None)) == 1


def test_ignores_node_modules_hidden_and_nested_folders(tmp_path: Path) -> None:
    _package_json(tmp_path / "node_modules" / "dep", {"build": "x"})
    _package_json(tmp_path / "node_modules", {"build": "x"})
    _package_json(tmp_path / ".cache", {"build": "x"})
    _package_json(tmp_path / "frontend" / "deep", {"build": "x"})

    assert folders_with_build_script(tmp_path) == []


def test_unreadable_package_json_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{ pas du json", encoding="utf-8")

    assert build_warnings(tmp_path, "npm test") == []


def test_orchestrator_writes_the_warning_to_the_pipeline_log(tmp_path: Path) -> None:
    _package_json(tmp_path / "frontend", {"build": "vite build"})
    log_path = tmp_path / "memory" / "pipeline-log.md"
    orch = Orchestrator(
        runner=AsyncMock(),
        ticket_service=AsyncMock(),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log_path,
        test_command="npm test",
        project_path=tmp_path,
    )

    orch._avertir_du_build("ticket-001")

    content = log_path.read_text(encoding="utf-8")
    assert "[ticket-001] test_command ne lance pas le build de frontend" in content


def test_orchestrator_stays_silent_without_project_path(tmp_path: Path) -> None:
    log_path = tmp_path / "memory" / "pipeline-log.md"
    orch = Orchestrator(
        runner=AsyncMock(),
        ticket_service=AsyncMock(),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log_path,
    )

    orch._avertir_du_build("ticket-001")

    assert not log_path.exists()
