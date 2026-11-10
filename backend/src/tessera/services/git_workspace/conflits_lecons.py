"""Rebase resolution of a ``memory/lecons.md`` conflict (ticket-907)."""

from tessera.services.git_workspace.chemins import _LECONS, _relatif_au_projet
from tessera.services.git_workspace.conflits import GitConflicts
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.textes import _resoudre_lecons
from tessera.utils.logger import get_logger

_logger = get_logger("tessera.services.git_workspace")


class GitConflictsLecons(GitConflicts):
    """Keeps the base's lessons file plus the run's own additions."""

    async def _resoudre_lecons_au_rebase(self, conflits: tuple[str, ...], prefixe: str) -> bool:
        """Resolve a lone ``lecons.md`` conflict; False leaves it to the resolver.

        Au rebase, l'étage 2 est la base et le 3 la branche (l'inverse du merge).
        """
        if len(conflits) != 1 or _relatif_au_projet(conflits[0], prefixe) != _LECONS:
            return False
        chemin = conflits[0]
        resolu = _resoudre_lecons(
            await self._etage_de_conflit(1, chemin),
            await self._etage_de_conflit(2, chemin),
            await self._etage_de_conflit(3, chemin),
        )
        if resolu is None:
            _logger.warning("lecons_conflit_refuse", extra={"chemin": chemin})
            return False
        try:
            destination = self._project_path / (_relatif_au_projet(chemin, prefixe) or chemin)
            destination.write_text(resolu, encoding="utf-8")
            await self._run("add", "--", f":/{chemin}")
            await self._run("-c", "core.editor=true", "rebase", "--continue")
            return True
        except GitCommandError:
            return False
