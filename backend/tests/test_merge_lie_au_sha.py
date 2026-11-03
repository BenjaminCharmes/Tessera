"""Le merge est lié au commit poussé — ticket-492.

Couverture :
- `merge_pull_request` envoie `sha` à GitHub quand il est donné, et seulement alors ;
- `livrer_phase_2` relit la tête de la PR après le verdict de la CI : une tête qui a
  bougé pendant l'attente empêche le merge, une tête illisible aussi ;
- une tête inchangée laisse le merge se faire, lié au SHA attendu ;
- bout en bout avec `CIWatcher` : un push pendant l'attente de la CI bloque le ticket.
"""
import asyncio
import json
from pathlib import Path

import httpx
import respx

from tessera.models.ticket import TicketStatus
from tessera.services.ci_watcher import CIWatcher, ControleTete
from tessera.services.github_service import GitHubService
from tessera.services.livraison import Livraison, LivraisonService
from tessera.services.pipeline_events import EventType, OrchestratorEvent

_BASE = "https://api.github.com"
_REPO = "owner/repo"
_POUSSE = "a" * 40
_INTRUS = "c" * 40


@respx.mock
async def test_merge_sends_sha_when_given() -> None:
    route = respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        return_value=httpx.Response(200, json={"merged": True})
    )

    await GitHubService(token="t", repo=_REPO).merge_pull_request(7, sha=_POUSSE)

    assert json.loads(route.calls[0].request.content)["sha"] == _POUSSE


@respx.mock
async def test_merge_sends_no_sha_by_default() -> None:
    route = respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        return_value=httpx.Response(200, json={"merged": True})
    )

    await GitHubService(token="t", repo=_REPO).merge_pull_request(7)

    assert "sha" not in json.loads(route.calls[0].request.content)


class _Workflow:
    """Workflow dont la tête de PR suit un script, et qui note ses merges."""

    def __init__(self, tetes: list[str | None], bouge_pendant_la_ci: str | None = None) -> None:
        self.tetes = tetes
        self.bouge_pendant_la_ci = bouge_pendant_la_ci
        self.merges: list[str | None] = []

    async def etat_ci(self, pr_number: int) -> str:
        if self.bouge_pendant_la_ci is not None:
            # Un push humain arrive pendant que la CI tourne.
            self.tetes[:] = [self.bouge_pendant_la_ci]
        return "passing"

    async def has_workflows(self) -> bool:
        return True

    async def tete_pr(self, pr_number: int) -> str | None:
        return self.tetes[0] if len(self.tetes) == 1 else self.tetes.pop(0)

    async def merge_si_la_ci_est_verte(
        self, pr_number: int, sha_attendu: str | None = None
    ) -> bool:
        self.merges.append(sha_attendu)
        return True


async def _ne_dort_pas(_s: float) -> None:
    return None


def _service(tmp_path: Path, wf: _Workflow) -> LivraisonService:
    (tmp_path / "agents.json").write_text(json.dumps({"autonomy": "merge"}), encoding="utf-8")
    return LivraisonService(
        git_workspace=object(),  # type: ignore[arg-type]
        workflow=wf,  # type: ignore[arg-type]
        project_path=tmp_path,
        base_branch="main",
        grace_ci_s=0,
        dormir=_ne_dort_pas,
    )


async def test_head_moved_during_ci_wait_prevents_merge(tmp_path: Path) -> None:
    wf = _Workflow([_POUSSE], bouge_pendant_la_ci=_INTRUS)

    livraison = await _service(tmp_path, wf).livrer_phase_2(7, sha_attendu=_POUSSE)

    assert livraison.merged is False
    assert wf.merges == []
    assert livraison.arret is not None
    assert "n'est plus le commit poussé" in livraison.arret
    assert "reste ouverte" in livraison.arret


async def test_unreadable_head_prevents_merge(tmp_path: Path) -> None:
    wf = _Workflow([None])

    livraison = await _service(tmp_path, wf).livrer_phase_2(7, sha_attendu=_POUSSE)

    assert livraison.merged is False
    assert wf.merges == []


async def test_unchanged_head_merges_bound_to_the_sha(tmp_path: Path) -> None:
    wf = _Workflow([_POUSSE])

    livraison = await _service(tmp_path, wf).livrer_phase_2(7, sha_attendu=_POUSSE)

    assert livraison.merged is True
    assert wf.merges == [_POUSSE]


async def test_without_expected_sha_head_is_not_read(tmp_path: Path) -> None:
    wf = _Workflow([_INTRUS])

    livraison = await _service(tmp_path, wf).livrer_phase_2(7)

    assert livraison.merged is True
    assert wf.merges == [None]


async def test_watcher_blocks_ticket_when_head_moves_during_ci(tmp_path: Path) -> None:
    """The reviewer's scenario: the watcher check passes, then a push lands."""
    # Le premier appel (contrôle du watcher) voit `_POUSSE` ; la CI déplace ensuite la tête.
    wf = _Workflow([_POUSSE], bouge_pendant_la_ci=_INTRUS)
    service = _service(tmp_path, wf)
    lectures = 0

    async def lire_tete(pr_number: int) -> str | None:
        nonlocal lectures
        lectures += 1
        return _POUSSE if lectures == 1 else await service.tete_pr(pr_number)

    async def phase_2(pr: int) -> Livraison:
        return await service.livrer_phase_2(pr, sha_attendu=_POUSSE)

    watcher = CIWatcher()
    events: list[OrchestratorEvent] = []

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    await watcher.surveiller(
        "proj", "ticket-001", 7, phase_2, collect,
        controle_tete=ControleTete(pushed_sha=_POUSSE, lire_tete=lire_tete),
    )
    merge = await asyncio.wait_for(watcher.attendre_merge("proj", "ticket-001"), 5.0)

    assert merge is False
    assert wf.merges == []
    statuts = [e.data["status"] for e in events if e.type is EventType.TICKET_STATUS_CHANGED]
    assert statuts == [TicketStatus.blocked.value]
