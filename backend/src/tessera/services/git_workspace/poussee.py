"""Push of a branch to `origin`, with recovery from a lost race (ticket-539)."""

from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.socle import GitCore
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitPoussee(GitCore):
    """Push of a branch to `origin`."""

    async def push_branch(self, branch_name: str) -> None:
        """Pousse `branch_name` sur `origin`, en suivi de branche.

        C'était le maillon manquant : `create-pr` demandait à GitHub une
        branche `head` que rien n'avait jamais poussée, et GitHub refusait une
        référence qu'il ne connaissait pas.

        **Jamais de push forcé.** Cette branche part dans le dépôt de
        l'utilisateur, parfois celui d'un client : écraser une référence
        distante peut détruire du travail qui n'est pas le nôtre. Si le push
        est refusé, c'est à l'utilisateur de trancher.

        Un refus `cannot lock ref … reference already exists` est une course
        perdue contre un autre push de la même branche (ticket-539). Le distant
        est alors relu : à jour, le push a réussi ; en retard sur la branche
        locale, un seul nouvel essai, sans force ; ailleurs, le refus remonte.
        """
        try:
            await self._run("push", "--set-upstream", "origin", branch_name)
        except GitCommandError as refus:
            if not await self._distant_rattrapable(branch_name):
                raise
            if await self._distant_a_jour(branch_name):
                return
            await self._run("push", "--set-upstream", "origin", branch_name)
            _logger.warning(
                "push_rejoue_apres_course",
                extra={"branche": branch_name, "erreur": refus.stderr.strip()},
            )

    async def _sha_distant_lu(self, branch: str) -> str | None:
        """Head of `refs/heads/<branch>` on `origin` via `ls-remote`, or None."""
        ref = f"refs/heads/{branch}"
        try:
            sortie = await self._run("ls-remote", "origin", ref)
        except GitCommandError:
            return None
        for ligne in sortie.splitlines():
            sha, _, nom = ligne.partition("\t")
            if nom.strip() == ref and sha:
                return sha.strip()
        return None

    async def _sha_local(self, branch: str) -> str | None:
        """Full SHA of the local branch, or None when git cannot say."""
        try:
            sortie = await self._run("rev-parse", "--verify", f"refs/heads/{branch}")
        except GitCommandError:
            return None
        return sortie.strip() or None

    async def _distant_a_jour(self, branch: str) -> bool:
        """True when `origin/<branch>` already points at the local branch head."""
        distant = await self._sha_distant_lu(branch)
        return distant is not None and distant == await self._sha_local(branch)

    async def _distant_rattrapable(self, branch: str) -> bool:
        """True when the remote branch is the local head or one of its ancestors.

        Only then can the refused push be tried again without forcing anything.
        A remote branch that is absent, unreadable or diverged is not ours to
        decide on: the refusal stands.
        """
        distant = await self._sha_distant_lu(branch)
        local = await self._sha_local(branch)
        if distant is None or local is None:
            return False
        if distant == local:
            return True
        try:
            await self._run("merge-base", "--is-ancestor", distant, local)
        except GitCommandError:
            return False
        return True
