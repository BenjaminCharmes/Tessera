"""A PR in conflict stops the CI watcher and says so — ticket-452.

Couverture :
- `etat_ci` rend `conflicting` pour une PR `dirty`, quel que soit l'état de CI.
- Seul `dirty` arrête : `unknown`, `blocked`, absent ne changent rien.
- Bout en bout : livraison réelle + CIWatcher, sans attendre le délai de CI,
  ligne dans `pipeline-log.md` avec le numéro de PR et « conflit »,
  `attendre_merge` rend False, ticket en blocked.
"""
import asyncio
import json
from pathlib import Path

import pytest

from tessera.models.ticket import TicketStatus
from tessera.services.ci_watcher import CIWatcher
from tessera.services.github_workflow import GitHubWorkflowService
from tessera.services.livraison import LivraisonService
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tests.test_github_workflow import _FakeGit, _FakeGitHub


class _FauxGit:
    async def rejouer_sur(self, base, resolveur=None):  # type: ignore[no-untyped-def]
        return ()

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        return None

    async def commit_bookkeeping(self) -> None:
        pass


async def _dormir_interdit(secondes: float) -> None:
    raise AssertionError(f"la surveillance a attendu {secondes}s malgré le conflit")


def _workflow(
    ci_status: str,
    mergeable_state: str | None,
    github: _FakeGitHub | None = None,
) -> GitHubWorkflowService:
    github = github or _FakeGitHub(ci_status=ci_status, mergeable_state=mergeable_state)
    return GitHubWorkflowService(
        git_workspace=_FakeGit(), github=github, base_branch="develop"
    )


@pytest.mark.parametrize("ci_status", ["passing", "pending", "none", "failing"])
async def test_etat_ci_rend_conflicting_pour_une_pr_dirty(ci_status: str) -> None:
    assert await _workflow(ci_status, "dirty").etat_ci(7) == "conflicting"


@pytest.mark.parametrize("mergeable_state", [None, "unknown", "blocked", "clean"])
async def test_etat_ci_ignore_les_autres_etats_de_fusion(
    mergeable_state: str | None,
) -> None:
    assert await _workflow("passing", mergeable_state).etat_ci(7) == "passing"


def _livraison(tmp_path: Path, workflow: GitHubWorkflowService) -> LivraisonService:
    (tmp_path / "agents.json").write_text(
        json.dumps({"autonomy": "merge"}), encoding="utf-8"
    )
    return LivraisonService(
        git_workspace=_FauxGit(),
        workflow=workflow,
        project_path=tmp_path,
        base_branch="develop",
        attente_ci_max_s=100_000,
        intervalle_ci_s=10,
        grace_ci_s=20,
        dormir=_dormir_interdit,
    )


async def test_livrer_phase_2_s_arrete_sur_conflit_sans_merger(tmp_path: Path) -> None:
    github = _FakeGitHub(ci_status="pending", mergeable_state="dirty")
    workflow = _workflow("pending", "dirty", github)

    livraison = await _livraison(tmp_path, workflow).livrer_phase_2(7)

    assert livraison.merged is False
    assert livraison.pr_number == 7
    assert livraison.arret is not None
    assert "PR #7 en conflit avec develop : à rebaser" in livraison.arret
    assert github.merged == []


async def test_pr_dirty_arrete_la_surveillance_et_ecrit_le_log(tmp_path: Path) -> None:
    log_path = tmp_path / "memory" / "pipeline-log.md"
    livraison = _livraison(tmp_path, _workflow("pending", "dirty"))
    events: list[OrchestratorEvent] = []

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    watcher = CIWatcher()
    await watcher.surveiller(
        "proj", "ticket-002", 14, livraison.livrer_phase_2, collect,
        pipeline_log_path=log_path,
    )

    # Le test échoue par `_dormir_interdit` si la surveillance attend le délai.
    assert await asyncio.wait_for(watcher.attendre_merge("proj", "ticket-002"), 5) is False

    contenu = log_path.read_text(encoding="utf-8")
    assert "#14" in contenu
    assert "conflit" in contenu
    assert "ticket-002" in contenu
    statuts = [e for e in events if e.type is EventType.TICKET_STATUS_CHANGED]
    assert [e.data["status"] for e in statuts] == [TicketStatus.blocked.value]
    fins = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(fins) == 1 and fins[0].data["merged"] is False
    assert "conflit" in str(fins[0].data["arret"])
    assert watcher.en_attente("proj") == ()
