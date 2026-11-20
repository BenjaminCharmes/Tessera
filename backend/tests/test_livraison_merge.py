"""Rereading a PR after a doubtful merge call — window, 5xx, 405 in progress."""
import json
from pathlib import Path

import httpx
import pytest

from tessera.services.github.github_workflow import GitHubWorkflowService
from tessera.services.livraison.livraison_merge import IssueMerge, arret_de_merge, tenter_le_merge


class _Workflow:
    def __init__(self, erreur: Exception, etats: list[str]) -> None:
        self._erreur = erreur
        self._etats = etats
        self.merges = 0
        self.relectures = 0

    async def pr_state(self, pr_number: int) -> str:
        self.relectures += 1
        return self._etats[min(self.relectures - 1, len(self._etats) - 1)]

    async def tete_pr(self, pr_number: int) -> str | None:
        return None

    async def merge_si_la_ci_est_verte(
        self, pr_number: int, sha_attendu: str | None = None
    ) -> bool:
        self.merges += 1
        raise self._erreur


class _Horloge:
    def __init__(self) -> None:
        self.pauses: list[float] = []

    async def __call__(self, secondes: float) -> None:
        self.pauses.append(secondes)


def _statut(code: int, corps: str = "") -> httpx.HTTPStatusError:
    requete = httpx.Request("PUT", "https://api.github.com/repos/o/r/pulls/7/merge")
    reponse = httpx.Response(code, text=corps, request=requete)
    return httpx.HTTPStatusError(str(code), request=requete, response=reponse)


async def _tenter(workflow: _Workflow, horloge: _Horloge) -> IssueMerge:
    return await tenter_le_merge(workflow, 7, None, 30.0, 10.0, horloge)


async def test_timeout_then_open_open_merged_is_confirmed() -> None:
    wf = _Workflow(httpx.ReadTimeout("lent"), ["open", "open", "merged"])
    horloge = _Horloge()

    issue = await _tenter(wf, horloge)

    assert issue == IssueMerge(merged=True, confirme_apres_reseau=True)
    assert horloge.pauses == [10.0, 10.0]
    assert wf.merges == 1


async def test_timeout_then_open_to_the_end_stops_with_duration() -> None:
    wf = _Workflow(httpx.ReadTimeout("lent"), ["open"])
    horloge = _Horloge()

    issue = await _tenter(wf, horloge)

    assert issue.merged is False
    assert issue.relu_pendant_s == 30.0
    arret = arret_de_merge(7, issue)
    assert "ReadTimeout" in arret
    assert "30 s" in arret


async def test_502_then_merged_is_confirmed() -> None:
    wf = _Workflow(_statut(502), ["merged"])

    issue = await _tenter(wf, _Horloge())

    assert issue.merged is True
    assert issue.confirme_apres_reseau is True


async def test_405_merge_in_progress_then_merged_is_confirmed() -> None:
    wf = _Workflow(_statut(405, "Merge already in progress"), ["open", "merged"])

    issue = await _tenter(wf, _Horloge())

    assert issue.merged is True


async def test_405_not_mergeable_is_a_refusal_without_reread() -> None:
    wf = _Workflow(_statut(405, "Pull Request is not mergeable"), ["merged"])

    issue = await _tenter(wf, _Horloge())

    assert issue == IssueMerge(merged=False)
    assert wf.relectures == 0


@pytest.mark.parametrize("code", [409, 422])
async def test_other_statuses_are_refusals(code: int) -> None:
    wf = _Workflow(_statut(code), ["merged"])

    issue = await _tenter(wf, _Horloge())

    assert issue.merged is False
    assert wf.relectures == 0


async def test_closed_stops_without_waiting() -> None:
    wf = _Workflow(httpx.ReadTimeout("lent"), ["closed"])
    horloge = _Horloge()

    issue = await _tenter(wf, horloge)

    assert issue.merged is False
    assert horloge.pauses == []
    assert "closed" in (issue.erreur_reseau or "")


class _Statut:
    ci_status = "passing"
    mergeable_state = None


class _GitHubQuiRefuse:
    """GitHub client whose merge call raises `erreur`; the PR then reads `etat`."""

    def __init__(self, erreur: httpx.HTTPStatusError, etat: str) -> None:
        self._erreur = erreur
        self._etat = etat
        self.merges = 0

    async def get_pull_request_status(self, pr_number: int) -> _Statut:
        return _Statut()

    async def merge_quand_fusionnable(self, pr_number: int, **kwargs: object) -> None:
        self.merges += 1
        raise self._erreur

    async def pr_state(self, pr_number: int) -> str:
        return self._etat


def _vrai_workflow(
    tmp_path: Path, github: _GitHubQuiRefuse
) -> GitHubWorkflowService:
    (tmp_path / "agents.json").write_text(
        json.dumps({"autonomy": "merge"}), encoding="utf-8"
    )

    class _Passerelle:
        async def pr_state(self, pr_number: int) -> str:
            return await github.pr_state(pr_number)

    service = GitHubWorkflowService(
        git_workspace=object(),  # type: ignore[arg-type]
        github=github,  # type: ignore[arg-type]
        base_branch="develop",
        project_path=tmp_path,
    )
    service.pr_state = _Passerelle().pr_state  # type: ignore[attr-defined]
    return service


@pytest.mark.parametrize(
    ("erreur", "attendu"),
    [
        (_statut(502), True),
        (_statut(405, "Merge already in progress"), True),
        (_statut(405, "Pull Request is not mergeable"), False),
        (_statut(409), False),
    ],
)
async def test_real_workflow_lets_a_doubtful_status_reach_the_reread(
    tmp_path: Path, erreur: httpx.HTTPStatusError, attendu: bool
) -> None:
    github = _GitHubQuiRefuse(erreur, "merged")
    service = _vrai_workflow(tmp_path, github)

    issue = await tenter_le_merge(service, 7, None, 30.0, 10.0, _Horloge())

    assert issue.merged is attendu
    assert github.merges == 1
