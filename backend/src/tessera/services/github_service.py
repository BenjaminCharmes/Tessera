from dataclasses import dataclass
from typing import Any, Literal

import httpx

from tessera.config import settings
from pydantic import BaseModel

_BASE = "https://api.github.com"


class GitHubIssue(BaseModel):
    number: int
    title: str
    body: str
    html_url: str
    labels: list[str]


@dataclass
class PRStatus:
    state: Literal["open", "closed", "merged"]
    ci_status: Literal["pending", "passing", "failing", "none"]
    pr_url: str
    pr_number: int


@dataclass
class RepositoryInfo:
    """Ce qu'il faut savoir d'un dépôt distant avant d'y attacher un projet."""

    exists: bool
    is_empty: bool = False
    default_branch: str = "main"


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
        params: dict[str, str | int] = {"labels": "agent-ready", "state": "open", "per_page": 50}
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

    async def create_issue(self, title: str, body: str, labels: list[str]) -> int:
        """Crée une issue et retourne son numéro."""
        url = f"{_BASE}/repos/{self._repo}/issues"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, headers=self._headers, json={"title": title, "body": body, "labels": labels}
            )
            resp.raise_for_status()
        return int(resp.json()["number"])

    async def update_issue(self, number: int, title: str, body: str) -> None:
        """Met à jour le titre et le body d'une issue."""
        url = f"{_BASE}/repos/{self._repo}/issues/{number}"
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                url, headers=self._headers, json={"title": title, "body": body}
            )
            resp.raise_for_status()

    async def close_issue(self, number: int) -> None:
        """Ferme une issue."""
        url = f"{_BASE}/repos/{self._repo}/issues/{number}"
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                url, headers=self._headers, json={"state": "closed"}
            )
            resp.raise_for_status()

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str | None = None,
    ) -> tuple[int, str]:
        """Crée une PR et retourne (pr_number, pr_url).

        `base` non fourni retombe sur `settings.github_base_branch`
        (`develop`) : une PR de ticket vise l'intégration, jamais `main`.
        """
        base = base or settings.github_base_branch
        url = f"{_BASE}/repos/{self._repo}/pulls"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=self._headers,
                json={"title": title, "body": body, "head": head, "base": base},
            )
            resp.raise_for_status()
        data = resp.json()
        return int(data["number"]), str(data["html_url"])

    async def get_pull_request_status(self, pr_number: int) -> PRStatus:
        """Retourne le statut d'une PR avec son état CI agrégé."""
        url = f"{_BASE}/repos/{self._repo}/pulls/{pr_number}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
        pr_data = resp.json()

        if pr_data.get("merged"):
            state: Literal["open", "closed", "merged"] = "merged"
        elif pr_data["state"] == "closed":
            state = "closed"
        else:
            state = "open"

        head_sha: str = pr_data["head"]["sha"]
        ci_status = await self._get_ci_status(head_sha)

        return PRStatus(
            state=state,
            ci_status=ci_status,
            pr_url=str(pr_data["html_url"]),
            pr_number=pr_number,
        )

    async def merge_pull_request(
        self,
        pr_number: int,
        method: str = "squash",
        commit_title: str | None = None,
    ) -> None:
        """Merge la PR avec la méthode déclarée par le projet — ticket-265.

        `method` vaut `squash` par défaut, ce qui correspond à la convention
        ticket → develop de ce dépôt (CLAUDE.md, section Git). La PR de
        release `develop → main` n'est pas concernée : la livraison ne
        l'ouvre pas.

        `commit_title` n'est transmis à GitHub que s'il est fourni ; en son
        absence, GitHub construit lui-même `"{PR title} (#{N})"` pour un
        squash, ce qui est identique au résultat attendu.

        L'erreur remonte telle quelle. Un 405 veut dire que GitHub refuse le
        merge — conflit, branche protegee, revue manquante — et l'avaler
        ferait passer le ticket pour termine alors que rien n'a bouge.
        """
        url = f"{_BASE}/repos/{self._repo}/pulls/{pr_number}/merge"
        payload: dict[str, str] = {"merge_method": method}
        if commit_title is not None:
            payload["commit_title"] = commit_title
        async with httpx.AsyncClient() as client:
            resp = await client.put(url, headers=self._headers, json=payload)
            resp.raise_for_status()

    async def _get_ci_status(
        self, sha: str
    ) -> Literal["pending", "passing", "failing", "none"]:
        url = f"{_BASE}/repos/{self._repo}/commits/{sha}/check-runs"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers)
            if resp.status_code != 200:
                return "none"
        runs: list[dict[str, Any]] = resp.json().get("check_runs", [])
        if not runs:
            return "none"
        conclusions = [r.get("conclusion") for r in runs]
        if any(c in (None, "action_required") for c in conclusions):
            return "pending"
        if any(c in ("failure", "timed_out", "cancelled") for c in conclusions):
            return "failing"
        return "passing"

    async def get_repository_info(self) -> RepositoryInfo:
        """Inspecte le dépôt distant : existe-t-il, et a-t-il un historique ?

        Un dépôt inexistant et un dépôt sans droits se présentent tous deux en
        404 : l'appelant doit pouvoir distinguer ce cas d'un dépôt simplement
        vide, sur lequel une liaison est sans danger.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{_BASE}/repos/{self._repo}", headers=self._headers)
            if resp.status_code != 200:
                return RepositoryInfo(exists=False)
            data = resp.json()

            # `size` vaut 0 sur un dépôt vide, mais aussi sur un dépôt dont les
            # objets ne sont pas encore comptés : la liste des commits tranche.
            commits = await client.get(
                f"{_BASE}/repos/{self._repo}/commits",
                headers=self._headers,
                params={"per_page": 1},
            )
            is_empty = commits.status_code == 409 or (
                commits.status_code == 200 and not commits.json()
            )

        return RepositoryInfo(
            exists=True,
            is_empty=is_empty,
            default_branch=str(data.get("default_branch") or "main"),
        )
