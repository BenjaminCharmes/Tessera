import httpx
import pytest
import respx

from vibe_ide.services.github_service import GitHubIssue, GitHubService


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
