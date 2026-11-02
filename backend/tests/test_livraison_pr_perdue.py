"""A PR opened despite a lost response is found again — ticket-455."""
import json
from pathlib import Path

import httpx
import pytest
import respx

from tessera.services.livreur_run import livraison_interrompue
from tessera.services.github_service import GitHubService
from tessera.services.github_workflow import GitHubWorkflowService
from tessera.services.livraison import LivraisonInterrompue, LivraisonService

_BASE = "https://api.github.com"
_REPO = "owner/my-repo"
_BRANCH = "ticket-001-x"


class _FauxGit:
    async def rejouer_sur(self, base, resolveur=None):  # type: ignore[no-untyped-def]
        return ()

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        return None

    async def commit_bookkeeping(self) -> None:
        pass


class _WorkflowAReponsePerdue:
    """Opening the PR times out; the search answers as configured."""

    def __init__(self, trouvee: int | None, recherche_en_echec: bool = False) -> None:
        self._trouvee = trouvee
        self._echec = recherche_en_echec
        self.recherches: list[str] = []

    async def open_pull_request(self, **kwargs: object) -> object:
        raise httpx.ReadTimeout("réponse perdue")

    async def pr_ouverte_de(self, branch: str) -> int | None:
        self.recherches.append(branch)
        if self._echec:
            raise httpx.ConnectError("recherche impossible")
        return self._trouvee


def _service(tmp_path: Path, workflow: _WorkflowAReponsePerdue) -> LivraisonService:
    (tmp_path / "agents.json").write_text(
        json.dumps({"autonomy": "pr"}), encoding="utf-8"
    )
    return LivraisonService(
        git_workspace=_FauxGit(),
        workflow=workflow,  # type: ignore[arg-type]
        project_path=tmp_path,
        base_branch="develop",
    )


async def _phase_1(svc: LivraisonService) -> object:
    return await svc.livrer_phase_1(
        ticket_id="ticket-001",
        ticket_title="T",
        ticket_body="",
        branch=_BRANCH,
        approuve=True,
    )


async def test_read_timeout_with_an_open_pr_carries_its_number(tmp_path: Path) -> None:
    workflow = _WorkflowAReponsePerdue(trouvee=20)

    with pytest.raises(LivraisonInterrompue) as info:
        await _phase_1(_service(tmp_path, workflow))

    assert workflow.recherches == [_BRANCH]
    livraison = livraison_interrompue(info.value)
    assert livraison.pr_number == 20
    assert livraison.pr_orpheline is True
    assert "ReadTimeout" in (livraison.arret or "")


async def test_read_timeout_without_an_open_pr_stays_a_plain_stop(
    tmp_path: Path,
) -> None:
    workflow = _WorkflowAReponsePerdue(trouvee=None)

    with pytest.raises(httpx.ReadTimeout) as info:
        await _phase_1(_service(tmp_path, workflow))

    livraison = livraison_interrompue(info.value)
    assert livraison.pr_number is None
    assert livraison.pr_orpheline is False
    assert "ReadTimeout" in (livraison.arret or "")


async def test_a_failing_search_keeps_the_original_stop(tmp_path: Path) -> None:
    workflow = _WorkflowAReponsePerdue(trouvee=20, recherche_en_echec=True)

    with pytest.raises(httpx.ReadTimeout) as info:
        await _phase_1(_service(tmp_path, workflow))

    livraison = livraison_interrompue(info.value)
    assert livraison.pr_number is None
    assert "ReadTimeout" in (livraison.arret or "")


async def test_a_non_transport_error_does_not_trigger_the_search(
    tmp_path: Path,
) -> None:
    workflow = _WorkflowAReponsePerdue(trouvee=20)

    async def _refus(**kwargs: object) -> object:
        raise RuntimeError("refus")

    workflow.open_pull_request = _refus  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        await _phase_1(_service(tmp_path, workflow))

    assert workflow.recherches == []


@respx.mock
async def test_find_open_pull_request_filters_on_owner_and_branch() -> None:
    route = respx.get(f"{_BASE}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(200, json=[{"number": 20}])
    )

    numero = await GitHubService(token="t", repo=_REPO).find_open_pull_request(_BRANCH)

    assert numero == 20
    params = route.calls.last.request.url.params
    assert params["head"] == f"owner:{_BRANCH}"
    assert params["state"] == "open"


@respx.mock
async def test_find_open_pull_request_returns_none_when_no_pr() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(200, json=[])
    )

    assert await GitHubService(token="t", repo=_REPO).find_open_pull_request(_BRANCH) is None


async def test_workflow_without_github_finds_nothing() -> None:
    workflow = GitHubWorkflowService(git_workspace=None, github=None, base_branch="develop")

    assert await workflow.pr_ouverte_de(_BRANCH) is None
