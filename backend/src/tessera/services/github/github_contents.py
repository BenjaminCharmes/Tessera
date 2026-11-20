"""Contents API of GitHub: one file on one branch, no checkout — ticket-905."""
import base64
from dataclasses import dataclass

import httpx

from tessera.services.github.github_service import _BASE, GitHubService


class ConflitContenu(Exception):
    """The `sha` sent with a PUT is stale (409 or 422)."""


class ErreurContenu(Exception):
    """GitHub refused or failed a Contents API call."""


@dataclass(frozen=True)
class FichierDistant:
    contenu: str
    sha: str


class GitHubContents(GitHubService):
    """Reads and writes a file of the repository through the Contents API."""

    async def lire_fichier(self, chemin: str, branche: str) -> FichierDistant | None:
        """The file on the branch, or None when the file or the branch is absent."""
        url = f"{_BASE}/repos/{self._repo}/contents/{chemin}"
        async with httpx.AsyncClient() as client:
            resp = await self._requete(client, "GET", url, params={"ref": branche})
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise ErreurContenu(f"read refused: {resp.status_code}")
        data = resp.json()
        texte = base64.b64decode(str(data["content"])).decode("utf-8")
        return FichierDistant(contenu=texte, sha=str(data["sha"]))

    async def ecrire_fichier(
        self, chemin: str, branche: str, contenu: str, message: str, sha: str | None
    ) -> None:
        """PUT the file; `ConflitContenu` when `sha` is stale."""
        corps: dict[str, str] = {
            "message": message,
            "branch": branche,
            "content": base64.b64encode(contenu.encode("utf-8")).decode("ascii"),
        }
        if sha is not None:
            corps["sha"] = sha
        url = f"{_BASE}/repos/{self._repo}/contents/{chemin}"
        async with httpx.AsyncClient() as client:
            resp = await self._requete(client, "PUT", url, json=corps)
        if resp.status_code in (409, 422):
            raise ConflitContenu(str(resp.status_code))
        if resp.status_code not in (200, 201):
            raise ErreurContenu(f"write refused: {resp.status_code}")

    async def creer_branche(self, branche: str) -> None:
        """Create the branch from the default branch head; no-op when it exists."""
        base = (await self.get_repository_info()).default_branch
        url = f"{_BASE}/repos/{self._repo}/git/ref/heads/{base}"
        async with httpx.AsyncClient() as client:
            tete = await self._requete(client, "GET", url)
            if tete.status_code != 200:
                raise ErreurContenu(f"head unreadable: {tete.status_code}")
            sha = str(tete.json()["object"]["sha"])
            resp = await self._requete(
                client,
                "POST",
                f"{_BASE}/repos/{self._repo}/git/refs",
                json={"ref": f"refs/heads/{branche}", "sha": sha},
            )
        if resp.status_code not in (201, 422):  # 422 : la branche existe déjà
            raise ErreurContenu(f"branch refused: {resp.status_code}")
