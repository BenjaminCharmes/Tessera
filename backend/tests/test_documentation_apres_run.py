"""Documentation after every approved run, on its branch — ticket-198.

La documentation ne se mettait à jour qu'à la fin d'une file ou d'un run
autonome — jamais après un run simple — et restait sur le disque sans commit :
le run suivant refusait l'arbre sale. Et pour le projet bootstrap, elle
cherchait `README.md` sous `projects/ide-core/`.
"""
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import TicketStatus
from tessera.services.documentation import DocumentationService, ResultatDocumentation
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tests.test_orchestrator import (
    _FakeGit,
    _make_agent_result,
    _make_orchestrator,
    _make_ticket,
    _make_ticket_service_for,
    _noop,
)
from tests.test_providers_base import FakeProvider


def _runner(approuve: bool = True) -> Any:
    async def fake_run(**kwargs: Any) -> AgentResult:
        role = kwargs["role"]
        verdict = "APPROVED" if approuve else "CHANGES_REQUESTED: non"
        return _make_agent_result(verdict if role == AgentRole.reviewer else "code", role)

    runner = MagicMock()
    runner.run = fake_run
    return runner


def _documenteur(fichiers: list[str]) -> AsyncMock:
    return AsyncMock(return_value=ResultatDocumentation(fichiers, [], ["ticket-001"]))


async def test_un_run_simple_approuve_documente_une_fois(tmp_path: Path) -> None:
    documenter = _documenteur(["README.md"])
    orc = _make_orchestrator(tmp_path, runner=_runner(), git_workspace=_FakeGit())
    orc._documenter = documenter
    await orc.run_pipeline("proj", "ticket-001", _noop)
    documenter.assert_awaited_once()


async def test_un_run_non_approuve_ne_documente_pas(tmp_path: Path) -> None:
    documenter = _documenteur(["README.md"])
    orc = _make_orchestrator(tmp_path, runner=_runner(approuve=False), max_review_rounds=1)
    orc._documenter = documenter
    await orc.run_pipeline("proj", "ticket-001", _noop)
    documenter.assert_not_awaited()


async def test_la_documentation_est_commitee_sur_la_branche_du_run(tmp_path: Path) -> None:
    # À la fin d'une file, elle restait sur le disque : arbre sale, run
    # suivant refusé (ADR-018). Sur la branche, elle part dans la PR.
    git = _FakeGit()
    orc = _make_orchestrator(tmp_path, runner=_runner(), git_workspace=git)
    orc._documenter = _documenteur(["README.md", "docs/architecture.md"])
    await orc.run_pipeline("proj", "ticket-001", _noop)
    assert any(m.startswith("docs: update documentation for ticket-001") for m in git.commits)
    # Le commit du travail vient avant celui de la documentation.
    assert git.commits[0].startswith("feat: ticket-001")


async def test_rien_a_documenter_ne_commite_rien(tmp_path: Path) -> None:
    git = _FakeGit()
    orc = _make_orchestrator(tmp_path, runner=_runner(), git_workspace=git)
    orc._documenter = _documenteur([])
    await orc.run_pipeline("proj", "ticket-001", _noop)
    assert not any(m.startswith("docs:") for m in git.commits)


async def test_doc_updated_porte_les_fichiers_et_les_refus(tmp_path: Path) -> None:
    orc = _make_orchestrator(tmp_path, runner=_runner(), git_workspace=_FakeGit())
    orc._documenter = AsyncMock(
        return_value=ResultatDocumentation(["README.md"], ["doc-fonctionnelle : ancien absent"], ["ticket-001"])
    )
    events: list[OrchestratorEvent] = []

    async def capture(ev: OrchestratorEvent) -> None:
        events.append(ev)

    await orc.run_pipeline("proj", "ticket-001", capture)
    [doc] = [e for e in events if e.type is EventType.DOC_UPDATED]
    assert doc.data["fichiers"] == ["README.md"]
    assert doc.data["refus"] == ["doc-fonctionnelle : ancien absent"]


async def test_une_documentation_qui_leve_ne_change_pas_le_resultat(tmp_path: Path) -> None:
    orc = _make_orchestrator(tmp_path, runner=_runner(), git_workspace=_FakeGit())
    orc._documenter = AsyncMock(side_effect=RuntimeError("Ollama absent"))
    result = await orc.run_pipeline("proj", "ticket-001", _noop)
    assert result.approved is True
    assert result.final_status == TicketStatus.done


async def test_une_file_documente_apres_chaque_ticket_approuve_et_plus_a_sa_fin(
    tmp_path: Path,
) -> None:
    tickets = [_make_ticket(id=f"ticket-00{i}") for i in (1, 2, 3)]
    documenter = _documenteur(["README.md"])
    orc = _make_orchestrator(
        tmp_path, runner=_runner(), git_workspace=_FakeGit(),
        ticket_service=_make_ticket_service_for(tickets),
    )
    orc._documenter = documenter
    await orc.run_queue("proj", [t.id for t in tickets])
    assert documenter.await_count == 3


async def test_en_git_root_ancestor_les_editions_visent_la_racine_du_depot(tmp_path: Path) -> None:
    depot = tmp_path / "depot"
    projet = depot / "projects" / "ide-core"
    (projet / "tickets" / "done").mkdir(parents=True)
    (projet / "tickets" / "done" / "ticket-001-x.md").write_text(
        "---\nid: ticket-001\ntitle: \"x\"\ntype: feat\nstatus: done\n---\n# x\n", encoding="utf-8"
    )
    (depot / "README.md").write_text("# Tessera\n\nAncien texte.\n", encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for role in ("doc-technique", "doc-fonctionnelle"):
        (prompts / f"{role}.md").write_text("doc", encoding="utf-8")
    edition = '{"editions": [{"fichier": "README.md", "ancien": "Ancien texte.", "nouveau": "Nouveau texte."}]}'
    svc = DocumentationService(FakeProvider(content=edition), prompts)

    resultat = await svc.mettre_a_jour(projet, racine_doc=depot)

    assert resultat.fichiers_modifies
    assert "Nouveau texte." in (depot / "README.md").read_text(encoding="utf-8")
    assert not (projet / "README.md").exists()
