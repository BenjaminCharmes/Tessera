"""Refusals of a documentation batch are counted, then given up — ticket-940."""
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from tessera.services.documentation.documentation import ResultatDocumentation
from tessera.services.documentation.documentation_selection import consigner_lot, enregistrer_refus, marquer_documente, tickets_a_documenter
from tests.test_documentation_apres_run import _make_orchestrator, _noop, _runner
from tests.test_orchestrator import _FakeGit


def _projet(tmp_path: Path, n: int = 4) -> Path:
    done = tmp_path / "tickets" / "done"
    done.mkdir(parents=True)
    for i in range(1, n + 1):
        (done / f"ticket-00{i}-x.md").write_text(f"title: T{i}\n", encoding="utf-8")
    return tmp_path


def _marqueur(projet: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (projet / "memory" / "documentation.json").read_text(encoding="utf-8")
    )
    return data


def _ids(projet: Path) -> list[str]:
    return [t.id for t in tickets_a_documenter(projet)]


def test_first_refusal_counts_and_keeps_tickets_to_document(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    assert consigner_lot(projet, ["ticket-001", "ticket-002"], True) == []
    assert _marqueur(projet)["refus"] == {"ticket-001": 1, "ticket-002": 1}
    assert _ids(projet)[:2] == ["ticket-001", "ticket-002"]


def test_second_refusal_abandons_and_next_batch_moves_on(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    consigner_lot(projet, ["ticket-001", "ticket-002"], True)
    assert consigner_lot(projet, ["ticket-001", "ticket-002"], True) == [
        "ticket-001",
        "ticket-002",
    ]
    assert _marqueur(projet)["abandonnes"] == ["ticket-001", "ticket-002"]
    assert _ids(projet) == ["ticket-003", "ticket-004"]


def test_applied_batch_documents_tickets_and_clears_refusals(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    enregistrer_refus(projet, ["ticket-001", "ticket-002"])
    consigner_lot(projet, ["ticket-001"], False)
    data = _marqueur(projet)
    assert data["documentes"] == ["ticket-001"]
    assert data["refus"] == {"ticket-002": 1}


def test_documenting_keeps_abandoned_tickets(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    enregistrer_refus(projet, ["ticket-001"])
    enregistrer_refus(projet, ["ticket-001"])
    marquer_documente(projet, ["ticket-002"])
    assert _marqueur(projet)["abandonnes"] == ["ticket-001"]
    assert _ids(projet) == ["ticket-003", "ticket-004"]


def test_current_and_legacy_marker_formats_are_still_read(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    memoire = projet / "memory"
    memoire.mkdir()
    (memoire / "documentation.json").write_text(
        '{"documentes": ["ticket-001"]}', encoding="utf-8"
    )
    assert _ids(projet) == ["ticket-002", "ticket-003", "ticket-004"]
    (memoire / "documentation.json").write_text(
        '{"dernier_ticket": "ticket-002"}', encoding="utf-8"
    )
    assert _ids(projet) == ["ticket-003", "ticket-004"]


async def test_refusal_reason_is_logged_on_one_line(tmp_path: Path) -> None:
    doc = ResultatDocumentation(
        [], ["doc-technique : extrait « a\nb\r\nc »"], ["ticket-001"], abandonnes=["ticket-001"]
    )
    orc = _make_orchestrator(tmp_path, runner=_runner(), git_workspace=_FakeGit())
    orc._documenter = AsyncMock(return_value=doc)
    lignes: list[str] = []
    orc._log = lignes.append  # type: ignore[method-assign]
    await orc.run_pipeline("proj", "ticket-001", _noop)
    motif = [ln for ln in lignes if "refusé :" in ln]
    assert len(motif) == 1
    assert "\n" not in motif[0] and "a b c" in motif[0]
    assert any("documentation abandonnée pour ticket-001 après 2 refus" in ln for ln in lignes)
