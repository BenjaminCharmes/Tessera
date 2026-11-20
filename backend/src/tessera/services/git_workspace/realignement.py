"""Reading the fetched remote base, and realigning a base that only differs in history."""

import asyncio

from tessera.services.git_workspace.avance_base import GitAvanceBase
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.noyau.git_commande import build_command
from tessera.utils.logger import get_logger

_logger = get_logger("tessera.services.git_workspace")


class GitRealignement(GitAvanceBase):
    """Reading the fetched remote base, and realigning a base that only differs in history."""

    async def _sha_base_distante(self, base_branch: str) -> str:
        """SHA of the remote base right after a fetch of ``base_branch``.

        Lit `refs/remotes/origin/<base>` et non `FETCH_HEAD` : ce fichier est
        écrasé par tout autre fetch du dépôt, et un `fetch origin <branche du
        ticket>` entre les deux lectures y laissait la pointe du ticket, que la
        base locale rejoignait alors par avance rapide (ticket-970). `FETCH_HEAD`
        ne sert plus que si la référence de suivi n'existe pas.
        """
        try:
            return (await self._run("rev-parse", f"refs/remotes/origin/{base_branch}")).strip()
        except GitCommandError:
            return (await self._run("rev-parse", "FETCH_HEAD")).strip()

    async def _est_ancetre(self, ancetre: str, descendant: str) -> bool:
        """True when ``ancetre`` is an ancestor of (or equal to) ``descendant``."""
        proc = await asyncio.create_subprocess_exec(
            *build_command(("merge-base", "--is-ancestor", ancetre, descendant)),
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def _realigner_si_memes_arbres(
        self, base_branch: str, sha_locale: str, sha_distant: str
    ) -> bool:
        """Point the local base at the remote one when only the history differs.

        Après un squash, la base locale porte les commits d'origine et la
        distante leur version écrasée : même contenu, histoire différente. Le
        réalignement exige la base active, un arbre propre et deux arbres égaux ;
        rien n'est perdu puisque le contenu est déjà sur la distante. `update-ref`
        suffit : l'index et les fichiers portent déjà cet arbre. Ailleurs, False.
        """
        if await self.branche_courante() != base_branch:
            return False
        if (await self._run("status", "--porcelain")).strip():
            return False
        try:
            await self._run("diff", "--quiet", sha_locale, sha_distant)
            await self._run(
                "update-ref", f"refs/heads/{base_branch}", sha_distant, sha_locale
            )
        except GitCommandError:
            return False
        _logger.info(
            "base_realignee",
            extra={"branch": base_branch, "ancien": sha_locale, "nouveau": sha_distant},
        )
        return True
