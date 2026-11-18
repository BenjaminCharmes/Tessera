"""Push of a branch to `origin`, with recovery from a lost race (ticket-539)
and from a passing GitHub server error (ticket-787)."""

import asyncio

from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.socle import GitCore
from tessera.utils.logger import get_logger

_logger = get_logger("tessera.services.git_workspace")

# Nombre maximal de noms dérivés essayés (`-2` … `-9`) avant de laisser le refus remonter.
_MAX_NOMS_DERIVES = 8

# Signatures d'une erreur serveur passagère de GitHub (ticket-787), en minuscules.
_SIGNES_ERREUR_SERVEUR = (
    "internal server error",
    "fatal error in commit_refs",
    "bad gateway",
    "service unavailable",
    "gateway time-out",
    "gateway timeout",
    "http 500",
    "http 502",
    "http 503",
    "http 504",
    "error: 500",
    "error: 502",
    "error: 503",
    "error: 504",
)


def _est_erreur_serveur(stderr: str) -> bool:
    """True when git's error output reports a server-side (5xx) failure."""
    texte = stderr.lower()
    return any(signe in texte for signe in _SIGNES_ERREUR_SERVEUR)


class GitPoussee(GitCore):
    """Push of a branch to `origin`."""

    # Délai avant le second essai après une erreur serveur (ticket-787).
    _delai_reessai_serveur_s: float = 5.0

    async def push_branch(self, branch_name: str) -> str:
        """Pousse `branch_name` sur `origin`, en suivi de branche.

        Retourne le nom distant réellement poussé : `branch_name`, ou un nom
        dérivé (`<branche>-2`…) quand la branche distante a divergé.

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

        Une erreur serveur de GitHub (`Internal Server Error`, 502…) suit le
        même principe (ticket-787) : le distant est relu, puis un seul
        nouvel essai après un court délai, toujours sans force. Un second
        refus remonte.

        Une branche distante divergente (la tête locale n'en descend pas)
        n'est ni écrasée ni supprimée : la tête locale part sous un nom neuf,
        `<branche>-2`, puis `-3`… (`_pousser_sous_nom_derive`).
        """
        try:
            await self._run("push", "--set-upstream", "origin", branch_name)
        except GitCommandError as refus:
            if _est_erreur_serveur(refus.stderr):
                await self._rejouer_apres_erreur_serveur(branch_name, refus)
                return branch_name
            if not await self._distant_rattrapable(branch_name):
                if await self._distant_diverge(branch_name):
                    return await self._pousser_sous_nom_derive(branch_name, refus)
                raise
            if await self._distant_a_jour(branch_name):
                return branch_name
            await self._run("push", "--set-upstream", "origin", branch_name)
            _logger.warning(
                "push_rejoue_apres_course",
                extra={"branche": branch_name, "erreur": refus.stderr.strip()},
            )
        return branch_name

    async def _distant_diverge(self, branch: str) -> bool:
        """True when the remote branch exists and the local head is not its descendant."""
        return (
            await self._sha_distant_lu(branch) is not None
            and await self._sha_local(branch) is not None
        )

    async def _pousser_sous_nom_derive(
        self, branch: str, refus: GitCommandError
    ) -> str:
        """Pushes the local head as `<branch>-N`, the first name that takes it.

        A derived name that already exists is reused when the local head
        descends from it (a later push of the same work); otherwise the next
        number is tried. Never forced, nothing on the remote is deleted.
        """
        local = await self._sha_local(branch)
        for numero in range(2, _MAX_NOMS_DERIVES + 2):
            nom = f"{branch}-{numero}"
            distant = await self._sha_distant_lu(nom)
            if distant is not None and not await self._tete_descend_de(local, distant):
                continue
            if distant != local:
                await self._run("push", "--set-upstream", "origin", f"{branch}:{nom}")
            _logger.warning(
                "push_sous_nom_derive",
                extra={"branche": branch, "nom": nom, "erreur": refus.stderr.strip()},
            )
            return nom
        raise refus

    async def _tete_descend_de(self, local: str | None, ancetre: str) -> bool:
        """True when `local` is `ancetre` or one of its descendants."""
        if local is None:
            return False
        try:
            await self._run("merge-base", "--is-ancestor", ancetre, local)
        except GitCommandError:
            return False
        return True

    async def _rejouer_apres_erreur_serveur(
        self, branch: str, refus: GitCommandError
    ) -> None:
        """Re-reads the remote after a 5xx, then pushes once more if it is behind."""
        if await self._distant_a_jour(branch):
            return
        await asyncio.sleep(self._delai_reessai_serveur_s)
        await self._run("push", "--set-upstream", "origin", branch)
        _logger.warning(
            "push_rejoue_apres_erreur_serveur",
            extra={"branche": branch, "erreur": refus.stderr.strip()},
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
