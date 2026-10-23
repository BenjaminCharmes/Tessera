"""Settling the trivial blocks of a rebase conflict by rule (ticket-548)."""

from pathlib import Path

from tessera.services.git_workspace.chemins import _relatif_au_projet
from tessera.services.git_workspace.conflits import GitConflicts
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.regles_conflit import resoudre_fichier
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitConflictsRegles(GitConflicts):
    """Rules applied before the resolver agent is called."""

    async def _resoudre_par_regles(
        self, conflits: tuple[str, ...], prefixe: str
    ) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
        """Résout et indexe les fichiers dont chaque bloc a une règle.

        Rend les fichiers qui restent en conflit et les (fichier, règle)
        appliqués. Un fichier sans règle pour un de ses blocs est remis tel
        que git l'avait écrit : le résolveur le reçoit intact.
        """
        restants: list[str] = []
        appliquees: list[tuple[str, str]] = []
        for chemin in conflits:
            regles = await self._resoudre_un_fichier(chemin, prefixe)
            if regles is None:
                restants.append(chemin)
            else:
                appliquees.extend((chemin, regle) for regle in regles)
        return tuple(restants), tuple(appliquees)

    async def _resoudre_un_fichier(self, chemin: str, prefixe: str) -> tuple[str, ...] | None:
        """Les règles appliquées au fichier, ou `None` s'il reste en conflit."""
        relatif = _relatif_au_projet(chemin, prefixe)
        if relatif is None:
            return None
        pathspec = f":/{chemin}"
        dest: Path = self._project_path / relatif
        try:
            # L'ancêtre n'est dans le fichier qu'en style diff3 ; un côté
            # supprimé n'a pas de version à recréer, et git refuse.
            await self._run("checkout", "--conflict=diff3", "--", pathspec)
            resolu = self._lire_et_resoudre(dest)
            if resolu is None:
                # Style du dépôt, comme avant : le résolveur ne voit pas la différence.
                await self._run("checkout", "--merge", "--", pathspec)
                return None
            dest.write_bytes(resolu[0].encode("utf-8"))
            await self._run("add", "--", pathspec)
        except GitCommandError:
            await self._remettre_en_conflit(pathspec)
            return None
        _logger.info("conflit_resolu_par_regle", extra={"fichier": chemin, "regles": resolu[1]})
        return resolu[1]

    def _lire_et_resoudre(self, fichier: Path) -> tuple[str, tuple[str, ...]] | None:
        """Lit sans traduire les fins de ligne ; un fichier illisible n'a pas de règle."""
        try:
            texte = fichier.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        return resoudre_fichier(texte)

    async def _remettre_en_conflit(self, pathspec: str) -> None:
        """Après un échec, rend au fichier ses marqueurs d'origine si git le permet."""
        try:
            await self._run("checkout", "--merge", "--", pathspec)
        except GitCommandError:
            _logger.warning("regle_conflit_restauration_echec", extra={"pathspec": pathspec})
