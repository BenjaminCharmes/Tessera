"""Retry of GitHub 502/503/504 during phase 2 — ticket-461."""
import httpx
import pytest
import respx

from tessera.services.github_retry import reessayer_5xx
from tessera.services.github_service import GitHubService

_REPO = "owner/my-repo"
_BASE = "https://api.github.com"
_PR = f"{_BASE}/repos/{_REPO}/pulls/15"
_MERGE = f"{_PR}/merge"
_RUNS = f"{_BASE}/repos/{_REPO}/actions/runs"


class _Attentes:
    """Replaces `asyncio.sleep`: records the waits instead of sleeping."""

    def __init__(self) -> None:
        self.valeurs: list[float] = []

    async def __call__(self, secondes: float) -> None:
        self.valeurs.append(secondes)


def _service(attentes: _Attentes) -> GitHubService:
    return GitHubService(token="ghp_test_token", repo=_REPO, dormir=attentes)


def _pr_ouverte(mergeable: bool = True) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "state": "open",
            "merged": False,
            "mergeable": mergeable,
            "html_url": "https://github.com/owner/my-repo/pull/15",
            "head": {"sha": "abc123"},
        },
    )


def _runs(conclusion: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"workflow_runs": [{"status": "completed", "conclusion": conclusion}]},
    )


@respx.mock
async def test_ci_read_503_then_200_gives_the_verdict_of_the_200() -> None:
    attentes = _Attentes()
    respx.get(_PR).mock(return_value=_pr_ouverte())
    route = respx.get(_RUNS).mock(
        side_effect=[httpx.Response(503), _runs("success")]
    )

    statut = await _service(attentes).get_pull_request_status(15)

    assert statut.ci_status == "passing"
    assert route.call_count == 2
    assert attentes.valeurs == [1.0]


@respx.mock
async def test_ci_read_503_then_failure_is_not_read_as_green() -> None:
    attentes = _Attentes()
    respx.get(_PR).mock(return_value=_pr_ouverte())
    respx.get(_RUNS).mock(side_effect=[httpx.Response(502), _runs("failure")])

    statut = await _service(attentes).get_pull_request_status(15)

    assert statut.ci_status == "failing"


@respx.mock
async def test_merge_503_then_success_merges_the_pr() -> None:
    attentes = _Attentes()
    respx.get(_PR).mock(return_value=_pr_ouverte())
    merge = respx.put(_MERGE).mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"merged": True})]
    )

    await _service(attentes).merge_quand_fusionnable(15)

    assert merge.call_count == 2
    assert attentes.valeurs == [1.0]


@respx.mock
async def test_mergeability_read_504_then_200_is_retried() -> None:
    attentes = _Attentes()
    respx.get(_PR).mock(side_effect=[httpx.Response(504), _pr_ouverte()])
    merge = respx.put(_MERGE).mock(return_value=httpx.Response(200, json={}))

    await _service(attentes).merge_quand_fusionnable(15)

    assert merge.call_count == 1
    assert attentes.valeurs == [1.0]


@respx.mock
async def test_merge_503_every_time_keeps_the_current_failure() -> None:
    attentes = _Attentes()
    merge = respx.put(_MERGE).mock(return_value=httpx.Response(503))

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        await _service(attentes).merge_pull_request(15)

    assert excinfo.value.response.status_code == 503
    # Un appel initial puis trois réessais, attente croissante.
    assert merge.call_count == 4
    assert attentes.valeurs == [1.0, 2.0, 4.0]


@respx.mock
async def test_ci_read_503_every_time_keeps_the_current_none() -> None:
    attentes = _Attentes()
    respx.get(_RUNS).mock(return_value=httpx.Response(503))

    assert await _service(attentes).get_ci_status("abc123") == "none"
    assert attentes.valeurs == [1.0, 2.0, 4.0]


@respx.mock
async def test_merge_403_is_not_retried() -> None:
    attentes = _Attentes()
    merge = respx.put(_MERGE).mock(return_value=httpx.Response(403))

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        await _service(attentes).merge_pull_request(15)

    assert excinfo.value.response.status_code == 403
    assert merge.call_count == 1
    assert attentes.valeurs == []


@respx.mock
async def test_pull_request_read_403_is_not_retried() -> None:
    attentes = _Attentes()
    route = respx.get(_PR).mock(return_value=httpx.Response(403))

    with pytest.raises(httpx.HTTPStatusError):
        await _service(attentes).get_pull_request_state(15)

    assert route.call_count == 1
    assert attentes.valeurs == []


async def test_reessayer_5xx_returns_a_500_without_retrying() -> None:
    attentes = _Attentes()
    appels: list[int] = []

    async def appel() -> httpx.Response:
        appels.append(1)
        return httpx.Response(500)

    reponse = await reessayer_5xx(appel, attentes)

    assert reponse.status_code == 500
    assert len(appels) == 1
    assert attentes.valeurs == []
