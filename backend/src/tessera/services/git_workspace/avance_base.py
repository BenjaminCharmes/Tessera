"""Fast-forwarding the checked-out base branch, files included."""

from tessera.services import journal_en_attente
from tessera.services.git_workspace.chemins import _JOURNAL_PIPELINE
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.historique import GitHistory


class GitAvanceBase(GitHistory):
    """Fast-forwarding the checked-out base branch, files included."""

    async def _avancer_base_active(self, cible: str) -> str | None:
        """Fast-forward the checked-out base branch to ``cible``, files included.

        Uncommitted pipeline-log lines are set aside and written back after
        the fast-forward, each one once only (ticket-457): the merged ticket's
        commit carries its own log lines, so a plain merge would refuse to
        overwrite the file, and some lines may already be in it. Any other
        local change makes ``merge --ff-only`` refuse, and the sync is skipped
        rather than forced (ADR-022).
        """
        journal = _JOURNAL_PIPELINE
        lignes: list[str] = []
        if (self._project_path / journal).is_file():
            diff = await self._run("diff", "-U0", "HEAD", "--", journal)
            lignes = [
                ligne[1:]
                for ligne in diff.splitlines()
                if ligne.startswith("+") and not ligne.startswith("+++")
            ]
            if lignes:
                await self._run("checkout", "HEAD", "--", journal)
        # Journal non suivi ici, suivi sur la base distante (ticket-480) :
        # `diff HEAD` ne le voit pas, mais le merge refuserait de l'écraser.
        lignes += await journal_en_attente.mettre_de_cote_non_suivi(
            self._project_path, cible
        )
        try:
            await self._run("merge", "--ff-only", "-q", cible)
            raison = None
        except GitCommandError as exc:
            raison = f"avance rapide de la base refusée : {exc.stderr.strip()}"
        journal_en_attente.reecrire(self._project_path, lignes)
        return raison
