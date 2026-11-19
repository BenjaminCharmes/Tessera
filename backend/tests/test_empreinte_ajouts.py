"""A protected file created in a subfolder during a call blocks the run — ticket-1021."""
import subprocess
from pathlib import Path

from tessera.models.ticket import TicketStatus
from tessera.services.noyau.pipeline_events import PipelineResult
from tessera.services.pipeline.pipeline_empreinte import gardee
from tests.test_empreinte_run import _Orch, _run


def _depot(chemin: Path) -> None:
    for args in (("init", "-q"), ("config", "user.email", "a@b.c"), ("config", "user.name", "t")):
        subprocess.run(["git", *args], cwd=chemin, check=True, capture_output=True)


def _commiter(chemin: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=chemin, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"], cwd=chemin, check=True, capture_output=True
    )


async def _cree(chemin: Path) -> str:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("x", encoding="utf-8")
    return "fait"


async def test_claude_md_created_in_a_subfolder_blocks_the_run(tmp_path: Path) -> None:
    _depot(tmp_path)
    orch = _Orch(tmp_path)

    arret = await gardee(  # type: ignore[arg-type]
        orch, _run([]), _cree(tmp_path / "sous" / "dossier" / "CLAUDE.md")
    )

    assert isinstance(arret, PipelineResult)
    assert arret.final_status is TicketStatus.blocked
    assert "sous/dossier/CLAUDE.md" in (arret.arret or "")


async def test_mcp_json_created_in_a_subfolder_blocks_the_run(tmp_path: Path) -> None:
    _depot(tmp_path)
    orch = _Orch(tmp_path)

    arret = await gardee(orch, _run([]), _cree(tmp_path / "a" / ".mcp.json"))  # type: ignore[arg-type]

    assert isinstance(arret, PipelineResult)
    assert arret.final_status is TicketStatus.blocked
    assert "a/.mcp.json" in (arret.arret or "")


async def test_an_ordinary_added_file_changes_nothing(tmp_path: Path) -> None:
    _depot(tmp_path)
    orch = _Orch(tmp_path)

    resultat = await gardee(orch, _run([]), _cree(tmp_path / "sous" / "app.py"))  # type: ignore[arg-type]

    assert resultat == "fait"


async def test_a_tracked_unchanged_claude_md_triggers_nothing(tmp_path: Path) -> None:
    _depot(tmp_path)
    (tmp_path / "sous").mkdir()
    (tmp_path / "sous" / "CLAUDE.md").write_text("regles", encoding="utf-8")
    _commiter(tmp_path)
    orch = _Orch(tmp_path)

    resultat = await gardee(orch, _run([]), _cree(tmp_path / "app.py"))  # type: ignore[arg-type]

    assert resultat == "fait"
