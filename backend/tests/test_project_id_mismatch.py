"""A project_id that drifts from the folder name is flagged at load (ticket-481)."""
import json
from pathlib import Path

from tessera.services.project_loader import load_project
from tessera.services.project_overview import build_overview, clear_overview_cache


def _project_dir(tmp_path: Path, manifest: dict[str, object] | None) -> Path:
    folder = tmp_path / "devinoo"
    folder.mkdir()
    (folder / "CLAUDE.md").write_text("# Devinoo\n", encoding="utf-8")
    if manifest is not None:
        (folder / "agents.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def test_warns_when_project_id_differs_from_folder(tmp_path: Path) -> None:
    folder = _project_dir(tmp_path, {"project_id": "make-your-call"})

    project = load_project(folder)

    assert len(project.avertissements) == 1
    assert "make-your-call" in project.avertissements[0]
    assert "devinoo" in project.avertissements[0]


def test_no_warning_when_project_id_matches_folder(tmp_path: Path) -> None:
    folder = _project_dir(tmp_path, {"project_id": "devinoo"})

    assert load_project(folder).avertissements == []


def test_no_warning_when_project_id_is_absent(tmp_path: Path) -> None:
    assert load_project(_project_dir(tmp_path, {"autonomy": "pr"})).avertissements == []


def test_no_warning_without_manifest(tmp_path: Path) -> None:
    assert load_project(_project_dir(tmp_path, None)).avertissements == []


def test_folder_name_stays_the_identifier(tmp_path: Path) -> None:
    folder = _project_dir(tmp_path, {"project_id": "make-your-call"})

    assert load_project(folder).id == "devinoo"


async def test_overview_exposes_the_warnings(tmp_path: Path) -> None:
    clear_overview_cache()
    folder = _project_dir(tmp_path, {"project_id": "make-your-call"})

    overview = await build_overview(load_project(folder), run_actif=False)

    assert overview.id == "devinoo"
    assert overview.avertissements == load_project(folder).avertissements
    assert overview.avertissements != []
