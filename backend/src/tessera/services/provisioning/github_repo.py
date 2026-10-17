"""The numeric id of a GitHub repository, read from the GitHub API — ticket-489.

Vercel's ``gitSource`` wants ``repoId``, which a Tessera project does not store:
it only knows ``owner/repo``. A public repository reads without a token; for a
private one the token of ``Settings`` is sent. It appears in no error: a failure
only carries the HTTP status and the API's error code (`ServiceError`).
"""
import re
from typing import Optional, Protocol

import httpx

from tessera.config import Settings
from tessera.services.provisioning.errors import ServiceError
from tessera.services.provisioning.jsonview import as_dict

SERVICE = "github"
_BASE_URL = "https://api.github.com"
_TIMEOUT_S = 30.0
_SLUG = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class RepoIdSource(Protocol):
    """Where a step reads the id of the repository ``owner/repo``."""

    async def repo_id(self, repo: str) -> Optional[int]:
        """Return the id, ``None`` when the repository cannot be read."""
        ...


class GitHubRepoLookup:
    """`RepoIdSource` over ``GET /repos/{owner}/{repo}``."""

    def __init__(self, token: str = "", transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self._token = token
        self._transport = transport

    @classmethod
    def from_settings(
        cls, settings: Settings, transport: Optional[httpx.AsyncBaseTransport] = None
    ) -> "GitHubRepoLookup":
        """Build the lookup from the GitHub token of ``Settings``."""
        return cls(settings.github_token, transport)

    async def repo_id(self, repo: str) -> Optional[int]:
        """Return the repository id; ``None`` for a malformed slug, a 404 or no id."""
        if not _SLUG.match(repo):
            return None
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token.strip():
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=_TIMEOUT_S) as http:
                reponse = await http.get(f"{_BASE_URL}/repos/{repo}", headers=headers)
        except httpx.HTTPError:
            # Le message d'une erreur réseau peut citer la requête : on le coupe.
            raise ServiceError(SERVICE, 0, "unreachable") from None
        if reponse.status_code == 404:
            return None
        if reponse.status_code >= 400:
            raise ServiceError.from_response(SERVICE, reponse.status_code, reponse.content)
        identifiant = as_dict(reponse.json()).get("id")
        if isinstance(identifiant, int) and not isinstance(identifiant, bool):
            return identifiant
        return None
