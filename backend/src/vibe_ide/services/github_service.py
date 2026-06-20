import httpx
from pydantic import BaseModel

_BASE = "https://api.github.com"


class GitHubIssue(BaseModel):
    number: int
    title: str
    body: str
    html_url: str
    labels: list[str]


class GitHubService:
    def __init__(self, token: str, repo: str) -> None:
        self._repo = repo
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def list_agent_ready_issues(self) -> list[GitHubIssue]:
        url = f"{_BASE}/repos/{self._repo}/issues"
        params = {"labels": "agent-ready", "state": "open", "per_page": 50}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers, params=params)
            resp.raise_for_status()
        return [
            GitHubIssue(
                number=issue["number"],
                title=issue["title"],
                body=issue.get("body") or "",
                html_url=issue["html_url"],
                labels=[label["name"] for label in issue.get("labels", [])],
            )
            for issue in resp.json()
        ]

    async def add_label(self, issue_number: int, label: str) -> None:
        url = f"{_BASE}/repos/{self._repo}/issues/{issue_number}/labels"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._headers, json={"labels": [label]})
            resp.raise_for_status()

    async def remove_label(self, issue_number: int, label: str) -> None:
        url = f"{_BASE}/repos/{self._repo}/issues/{issue_number}/labels/{label}"
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=self._headers)
            if resp.status_code != 404:
                resp.raise_for_status()
