import asyncio

import httpx
import pytest
import respx

from tessera.services.github_service import (
    GitHubIssue,
    GitHubService,
    MergeabiliteTimeoutError,
    PRNonFusionnableError,
    PRStatus,
)


_TOKEN = "ghp_test_token"
_REPO = "owner/my-repo"
_BASE = "https://api.github.com"


def _make_service() -> GitHubService:
    return GitHubService(token=_TOKEN, repo=_REPO)


def _issue_payload(
    number: int = 1,
    title: str = "Fix the bug",
    body: str = "Description here.",
    html_url: str = "https://github.com/owner/my-repo/issues/1",
    labels: list[str] | None = None,
) -> dict:
    return {
        "number": number,
        "title": title,
        "body": body,
        "html_url": html_url,
        "labels": [{"name": l} for l in (labels or [])],
    }


# ------------------------------------------------------------------
# list_agent_ready_issues
# ------------------------------------------------------------------


@respx.mock
async def test_list_issues_returns_parsed_issues() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/issues").mock(
        return_value=httpx.Response(
            200,
            json=[
                _issue_payload(1, "Issue 1", labels=["agent-ready", "feat"]),
                _issue_payload(2, "Issue 2", labels=["agent-ready"]),
            ],
        )
    )
    svc = _make_service()
    issues = await svc.list_agent_ready_issues()

    assert len(issues) == 2
    assert issues[0].number == 1
    assert issues[0].title == "Issue 1"
    assert "feat" in issues[0].labels
    assert issues[1].number == 2


@respx.mock
async def test_list_issues_returns_empty_when_none() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/issues").mock(
        return_value=httpx.Response(200, json=[])
    )
    svc = _make_service()
    issues = await svc.list_agent_ready_issues()
    assert issues == []


@respx.mock
async def test_list_issues_handles_null_body() -> None:
    payload = _issue_payload(1)
    payload["body"] = None
    respx.get(f"{_BASE}/repos/{_REPO}/issues").mock(
        return_value=httpx.Response(200, json=[payload])
    )
    svc = _make_service()
    issues = await svc.list_agent_ready_issues()
    assert issues[0].body == ""


@respx.mock
async def test_list_issues_sends_correct_label_filter() -> None:
    route = respx.get(f"{_BASE}/repos/{_REPO}/issues").mock(
        return_value=httpx.Response(200, json=[])
    )
    svc = _make_service()
    await svc.list_agent_ready_issues()

    assert route.called
    request = route.calls[0].request
    assert b"agent-ready" in request.url.query


@respx.mock
async def test_list_issues_sends_auth_header() -> None:
    route = respx.get(f"{_BASE}/repos/{_REPO}/issues").mock(
        return_value=httpx.Response(200, json=[])
    )
    svc = _make_service()
    await svc.list_agent_ready_issues()

    request = route.calls[0].request
    assert request.headers["Authorization"] == f"Bearer {_TOKEN}"


@respx.mock
async def test_list_issues_raises_on_api_error() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/issues").mock(
        return_value=httpx.Response(403, json={"message": "Forbidden"})
    )
    svc = _make_service()
    with pytest.raises(httpx.HTTPStatusError):
        await svc.list_agent_ready_issues()


# ------------------------------------------------------------------
# add_label
# ------------------------------------------------------------------


@respx.mock
async def test_add_label_posts_to_correct_url() -> None:
    route = respx.post(f"{_BASE}/repos/{_REPO}/issues/42/labels").mock(
        return_value=httpx.Response(200, json=[])
    )
    svc = _make_service()
    await svc.add_label(42, "synced-to-agent")

    assert route.called
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["labels"] == ["synced-to-agent"]


@respx.mock
async def test_add_label_raises_on_error() -> None:
    respx.post(f"{_BASE}/repos/{_REPO}/issues/1/labels").mock(
        return_value=httpx.Response(422, json={"message": "Unprocessable"})
    )
    svc = _make_service()
    with pytest.raises(httpx.HTTPStatusError):
        await svc.add_label(1, "bad-label")


# ------------------------------------------------------------------
# remove_label
# ------------------------------------------------------------------


@respx.mock
async def test_remove_label_sends_delete_request() -> None:
    route = respx.delete(f"{_BASE}/repos/{_REPO}/issues/7/labels/agent-ready").mock(
        return_value=httpx.Response(200, json=[])
    )
    svc = _make_service()
    await svc.remove_label(7, "agent-ready")

    assert route.called


@respx.mock
async def test_remove_label_ignores_404() -> None:
    respx.delete(f"{_BASE}/repos/{_REPO}/issues/7/labels/agent-ready").mock(
        return_value=httpx.Response(404, json={"message": "Label not found"})
    )
    svc = _make_service()
    # Should not raise
    await svc.remove_label(7, "agent-ready")


@respx.mock
async def test_remove_label_raises_on_other_error() -> None:
    respx.delete(f"{_BASE}/repos/{_REPO}/issues/7/labels/agent-ready").mock(
        return_value=httpx.Response(500, json={"message": "Server error"})
    )
    svc = _make_service()
    with pytest.raises(httpx.HTTPStatusError):
        await svc.remove_label(7, "agent-ready")


# ------------------------------------------------------------------
# create_issue
# ------------------------------------------------------------------


@respx.mock
async def test_create_issue_returns_issue_number() -> None:
    respx.post(f"{_BASE}/repos/{_REPO}/issues").mock(
        return_value=httpx.Response(201, json={"number": 99, "html_url": "https://github.com/owner/my-repo/issues/99"})
    )
    svc = _make_service()
    number = await svc.create_issue("New feature", "Description", ["enhancement"])
    assert number == 99


@respx.mock
async def test_create_issue_sends_correct_payload() -> None:
    route = respx.post(f"{_BASE}/repos/{_REPO}/issues").mock(
        return_value=httpx.Response(201, json={"number": 1, "html_url": "https://github.com/owner/my-repo/issues/1"})
    )
    svc = _make_service()
    await svc.create_issue("Title", "Body text", ["bug", "enhancement"])

    import json as _json
    body = _json.loads(route.calls[0].request.content)
    assert body["title"] == "Title"
    assert body["body"] == "Body text"
    assert body["labels"] == ["bug", "enhancement"]


@respx.mock
async def test_create_issue_raises_on_error() -> None:
    respx.post(f"{_BASE}/repos/{_REPO}/issues").mock(
        return_value=httpx.Response(422, json={"message": "Validation Failed"})
    )
    svc = _make_service()
    with pytest.raises(httpx.HTTPStatusError):
        await svc.create_issue("Bad", "Body", [])


# ------------------------------------------------------------------
# update_issue
# ------------------------------------------------------------------


@respx.mock
async def test_update_issue_sends_patch_with_title_and_body() -> None:
    route = respx.patch(f"{_BASE}/repos/{_REPO}/issues/42").mock(
        return_value=httpx.Response(200, json={"number": 42})
    )
    svc = _make_service()
    await svc.update_issue(42, "New title", "New body")

    import json as _json
    body = _json.loads(route.calls[0].request.content)
    assert body["title"] == "New title"
    assert body["body"] == "New body"


@respx.mock
async def test_update_issue_raises_on_error() -> None:
    respx.patch(f"{_BASE}/repos/{_REPO}/issues/42").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    svc = _make_service()
    with pytest.raises(httpx.HTTPStatusError):
        await svc.update_issue(42, "Title", "Body")


# ------------------------------------------------------------------
# close_issue
# ------------------------------------------------------------------


@respx.mock
async def test_close_issue_sends_state_closed() -> None:
    route = respx.patch(f"{_BASE}/repos/{_REPO}/issues/7").mock(
        return_value=httpx.Response(200, json={"number": 7, "state": "closed"})
    )
    svc = _make_service()
    await svc.close_issue(7)

    import json as _json
    body = _json.loads(route.calls[0].request.content)
    assert body["state"] == "closed"


@respx.mock
async def test_close_issue_raises_on_error() -> None:
    respx.patch(f"{_BASE}/repos/{_REPO}/issues/7").mock(
        return_value=httpx.Response(500, json={"message": "Server error"})
    )
    svc = _make_service()
    with pytest.raises(httpx.HTTPStatusError):
        await svc.close_issue(7)


# ------------------------------------------------------------------
# create_pull_request
# ------------------------------------------------------------------


@respx.mock
async def test_create_pull_request_returns_number_and_url() -> None:
    respx.post(f"{_BASE}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(
            201,
            json={"number": 15, "html_url": "https://github.com/owner/my-repo/pull/15"},
        )
    )
    svc = _make_service()
    number, url = await svc.create_pull_request("Fix bug", "Description", "my-branch")
    assert number == 15
    assert url == "https://github.com/owner/my-repo/pull/15"


@respx.mock
async def test_create_pull_request_sends_correct_payload() -> None:
    route = respx.post(f"{_BASE}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(
            201,
            json={"number": 7, "html_url": "https://github.com/owner/my-repo/pull/7"},
        )
    )
    svc = _make_service()
    await svc.create_pull_request("My title", "My body", "feature-branch", base="develop")

    import json as _json
    body = _json.loads(route.calls[0].request.content)
    assert body["title"] == "My title"
    assert body["body"] == "My body"
    assert body["head"] == "feature-branch"
    assert body["base"] == "develop"


@respx.mock
async def test_create_pull_request_raises_on_error() -> None:
    respx.post(f"{_BASE}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(422, json={"message": "Validation Failed"})
    )
    svc = _make_service()
    with pytest.raises(httpx.HTTPStatusError):
        await svc.create_pull_request("Title", "Body", "branch")


# ------------------------------------------------------------------
# get_pull_request_status
# ------------------------------------------------------------------


def _pr_payload(
    number: int = 15,
    state: str = "open",
    merged: bool = False,
    html_url: str = "https://github.com/owner/my-repo/pull/15",
    head_sha: str = "abc123",
) -> dict:
    return {
        "number": number,
        "state": state,
        "merged": merged,
        "html_url": html_url,
        "head": {"sha": head_sha},
    }


def _check_runs_payload(
    conclusions: list[str | None],
) -> dict:
    return {
        "check_runs": [
            {"conclusion": c, "name": f"check-{i}"}
            for i, c in enumerate(conclusions)
        ]
    }


@respx.mock
async def test_get_pr_status_open_ci_passing() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/15").mock(
        return_value=httpx.Response(200, json=_pr_payload())
    )
    respx.get(f"{_BASE}/repos/{_REPO}/commits/abc123/check-runs").mock(
        return_value=httpx.Response(200, json=_check_runs_payload(["success", "success"]))
    )
    svc = _make_service()
    status = await svc.get_pull_request_status(15)
    assert status.state == "open"
    assert status.ci_status == "passing"
    assert status.pr_url == "https://github.com/owner/my-repo/pull/15"
    assert status.pr_number == 15


@respx.mock
async def test_get_pr_status_merged() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/15").mock(
        return_value=httpx.Response(200, json=_pr_payload(state="closed", merged=True))
    )
    respx.get(f"{_BASE}/repos/{_REPO}/commits/abc123/check-runs").mock(
        return_value=httpx.Response(200, json=_check_runs_payload(["success"]))
    )
    svc = _make_service()
    status = await svc.get_pull_request_status(15)
    assert status.state == "merged"


@respx.mock
async def test_get_pr_status_closed_not_merged() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/15").mock(
        return_value=httpx.Response(200, json=_pr_payload(state="closed", merged=False))
    )
    respx.get(f"{_BASE}/repos/{_REPO}/commits/abc123/check-runs").mock(
        return_value=httpx.Response(200, json=_check_runs_payload([]))
    )
    svc = _make_service()
    status = await svc.get_pull_request_status(15)
    assert status.state == "closed"


@respx.mock
async def test_get_pr_status_ci_pending_when_running() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/15").mock(
        return_value=httpx.Response(200, json=_pr_payload())
    )
    respx.get(f"{_BASE}/repos/{_REPO}/commits/abc123/check-runs").mock(
        return_value=httpx.Response(200, json=_check_runs_payload([None, "success"]))
    )
    svc = _make_service()
    status = await svc.get_pull_request_status(15)
    assert status.ci_status == "pending"


@respx.mock
async def test_get_pr_status_ci_failing() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/15").mock(
        return_value=httpx.Response(200, json=_pr_payload())
    )
    respx.get(f"{_BASE}/repos/{_REPO}/commits/abc123/check-runs").mock(
        return_value=httpx.Response(200, json=_check_runs_payload(["success", "failure"]))
    )
    svc = _make_service()
    status = await svc.get_pull_request_status(15)
    assert status.ci_status == "failing"


@respx.mock
async def test_get_pr_status_ci_none_when_no_checks() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/15").mock(
        return_value=httpx.Response(200, json=_pr_payload())
    )
    respx.get(f"{_BASE}/repos/{_REPO}/commits/abc123/check-runs").mock(
        return_value=httpx.Response(200, json={"check_runs": []})
    )
    svc = _make_service()
    status = await svc.get_pull_request_status(15)
    assert status.ci_status == "none"


@respx.mock
async def test_get_pr_status_ci_none_when_checks_endpoint_fails() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/15").mock(
        return_value=httpx.Response(200, json=_pr_payload())
    )
    respx.get(f"{_BASE}/repos/{_REPO}/commits/abc123/check-runs").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    svc = _make_service()
    status = await svc.get_pull_request_status(15)
    assert status.ci_status == "none"


@respx.mock
async def test_get_pr_status_raises_on_pr_not_found() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/15").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    svc = _make_service()
    with pytest.raises(httpx.HTTPStatusError):
        await svc.get_pull_request_status(15)


@respx.mock
async def test_create_pull_request_cible_develop_par_defaut() -> None:
    # Le flux du dépôt est ticket -> develop -> main (ticket-049) : une PR de
    # ticket qui ne précise pas sa base doit viser l'intégration, jamais main.
    route = respx.post(f"{_BASE}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(
            201,
            json={"number": 42, "html_url": "https://github.com/owner/my-repo/pull/42"},
        )
    )
    svc = _make_service()
    await svc.create_pull_request("Titre", "Corps", "ticket-050-slug")

    import json as _json

    assert _json.loads(route.calls[0].request.content)["base"] == "develop"


# ------------------------------------------------------------------
# Inspection d'un dépôt avant liaison — ticket-061
# ------------------------------------------------------------------


@respx.mock
async def test_repository_info_signale_un_depot_vide() -> None:
    # Un dépôt fraîchement créé sur GitHub n'a aucun commit : on peut y
    # attacher un projet local sans risque de conflit.
    respx.get(f"{_BASE}/repos/{_REPO}").mock(
        return_value=httpx.Response(200, json={"size": 0, "default_branch": "main"})
    )
    respx.get(f"{_BASE}/repos/{_REPO}/commits").mock(return_value=httpx.Response(409))

    info = await _make_service().get_repository_info()

    assert info.exists is True
    assert info.is_empty is True


@respx.mock
async def test_repository_info_signale_un_depot_avec_historique() -> None:
    respx.get(f"{_BASE}/repos/{_REPO}").mock(
        return_value=httpx.Response(200, json={"size": 120, "default_branch": "main"})
    )
    respx.get(f"{_BASE}/repos/{_REPO}/commits").mock(
        return_value=httpx.Response(200, json=[{"sha": "abc"}])
    )

    info = await _make_service().get_repository_info()

    assert info.exists is True
    assert info.is_empty is False
    assert info.default_branch == "main"


@respx.mock
async def test_repository_info_signale_un_depot_inaccessible() -> None:
    # Dépôt inexistant, ou token sans accès : les deux se présentent en 404,
    # et l'utilisateur doit pouvoir distinguer ça d'un dépôt vide.
    respx.get(f"{_BASE}/repos/{_REPO}").mock(return_value=httpx.Response(404))

    info = await _make_service().get_repository_info()

    assert info.exists is False


# ------------------------------------------------------------------
# merge_pull_request — ticket-082
# ------------------------------------------------------------------


@respx.mock
async def test_merge_pull_request_squash_envoie_squash_method() -> None:
    # Les PR de ticket → develop sont mergées en squash : c'est la convention
    # du dépôt (CLAUDE.md, section Git) et le défaut de ticket-265.
    route = respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        return_value=httpx.Response(200, json={"merged": True, "sha": "abc"})
    )

    await _make_service().merge_pull_request(7, method="squash")

    assert route.called
    import json as _json

    envoye = _json.loads(route.calls[0].request.content)
    assert envoye["merge_method"] == "squash"
    assert "commit_title" not in envoye


@respx.mock
async def test_merge_pull_request_merge_envoie_merge_method() -> None:
    # Un projet déclarant merge_method: "merge" dans agents.json obtient un
    # merge commit (ticket-265).
    route = respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        return_value=httpx.Response(200, json={"merged": True, "sha": "abc"})
    )

    await _make_service().merge_pull_request(7, method="merge")

    import json as _json

    envoye = _json.loads(route.calls[0].request.content)
    assert envoye["merge_method"] == "merge"


@respx.mock
async def test_merge_pull_request_avec_commit_title_le_transmet() -> None:
    # Quand l'appelant fournit un commit_title, il est transmis à GitHub.
    route = respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        return_value=httpx.Response(200, json={"merged": True, "sha": "abc"})
    )

    await _make_service().merge_pull_request(
        7, method="squash", commit_title="feat: ticket-007 — Mon ticket (#7)"
    )

    import json as _json

    envoye = _json.loads(route.calls[0].request.content)
    assert envoye["merge_method"] == "squash"
    assert envoye["commit_title"] == "feat: ticket-007 — Mon ticket (#7)"


@respx.mock
async def test_un_merge_refuse_par_github_remonte() -> None:
    # 405 = la PR n'est pas mergeable (conflit, branche protégée). Avaler
    # l'erreur ferait croire le ticket terminé alors que rien n'a bougé.
    respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        return_value=httpx.Response(405, json={"message": "Pull Request is not mergeable"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await _make_service().merge_pull_request(7)


# ------------------------------------------------------------------
# merge_quand_fusionnable — ticket-315
# ------------------------------------------------------------------


@respx.mock
async def test_merge_attend_null_puis_fusionne_quand_true() -> None:
    # GitHub retourne d'abord mergeable: null (calcul en cours), puis true.
    # Le service doit attendre et merger quand la valeur est disponible.
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/7").mock(
        side_effect=[
            httpx.Response(200, json={"mergeable": None}),
            httpx.Response(200, json={"mergeable": True}),
        ]
    )
    merge_route = respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        return_value=httpx.Response(200, json={"merged": True, "sha": "abc"})
    )

    svc = _make_service()
    await svc.merge_quand_fusionnable(
        7,
        attente_max_s=10.0,
        intervalle_s=5.0,
        dormir=lambda _: asyncio.sleep(0),
    )

    assert merge_route.call_count == 1


@respx.mock
async def test_merge_non_fusionnable_ne_tente_pas_le_merge() -> None:
    # Une PR avec mergeable: false (conflit) ne doit pas appeler l'endpoint
    # de merge. L'exception doit décrire la raison.
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/7").mock(
        return_value=httpx.Response(200, json={"mergeable": False})
    )
    merge_route = respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        return_value=httpx.Response(200, json={"merged": True})
    )

    svc = _make_service()
    with pytest.raises(PRNonFusionnableError) as exc_info:
        await svc.merge_quand_fusionnable(7, dormir=lambda _: asyncio.sleep(0))

    assert merge_route.call_count == 0
    assert "7" in str(exc_info.value)


@respx.mock
async def test_merge_attente_bornee_quand_null_persiste() -> None:
    # Si GitHub ne calcule jamais la fusionnabilité, l'attente s'arrête au
    # délai maximal et l'exception décrit le dépassement.
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/7").mock(
        return_value=httpx.Response(200, json={"mergeable": None})
    )
    merge_route = respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        return_value=httpx.Response(200, json={"merged": True})
    )

    svc = _make_service()
    with pytest.raises(MergeabiliteTimeoutError) as exc_info:
        await svc.merge_quand_fusionnable(
            7,
            attente_max_s=0.0,  # délai nul : la première lecture nulle déclenche le timeout
            intervalle_s=5.0,
            dormir=lambda _: asyncio.sleep(0),
        )

    assert merge_route.call_count == 0
    assert "7" in str(exc_info.value)


@respx.mock
async def test_merge_retente_sur_405_et_reussit() -> None:
    # Un 405 immédiat (GitHub encore en calcul côté interne) est retenté une
    # fois. Si le second appel réussit, le merge est considéré comme effectué.
    respx.get(f"{_BASE}/repos/{_REPO}/pulls/7").mock(
        return_value=httpx.Response(200, json={"mergeable": True})
    )
    merge_route = respx.put(f"{_BASE}/repos/{_REPO}/pulls/7/merge").mock(
        side_effect=[
            httpx.Response(405, json={"message": "Method Not Allowed"}),
            httpx.Response(200, json={"merged": True, "sha": "abc"}),
        ]
    )

    svc = _make_service()
    await svc.merge_quand_fusionnable(
        7,
        intervalle_s=0.0,
        dormir=lambda _: asyncio.sleep(0),
    )

    assert merge_route.call_count == 2
