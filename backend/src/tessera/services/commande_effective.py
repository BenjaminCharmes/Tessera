"""The test command and environment a run uses inside a worktree — ticket-524.

`uv` is refused by the application control inside a worktree: the project
declares, under `worktree`, a command and an environment that avoid it (the main
`.venv` interpreter, `PYTHONPATH` on the worktree). Both may name the two
places with `{worktree}` and `{repo}`. Pure functions: nothing here launches
a process or reads the disk.
"""
import re
from collections.abc import Mapping
from pathlib import Path

from tessera.models.worktree_config import ConfigWorktree
from tessera.services.politique_run import PolitiqueRun

#: `{nom}` but not `${nom}`, which a shell expands itself.
_PLACEHOLDER = re.compile(r"(?<!\$)\{([A-Za-z_][A-Za-z0-9_]*)\}")


class PlaceholderInconnu(ValueError):
    """A `{name}` in a worktree declaration that is neither `{worktree}` nor `{repo}`."""


def _remplacer(texte: str, valeurs: Mapping[str, str]) -> str:
    """Substitute every known placeholder; raise on the first unknown one."""

    def un_remplacement(correspondance: re.Match[str]) -> str:
        nom = correspondance.group(1)
        if nom not in valeurs:
            connus = ", ".join(f"{{{k}}}" for k in valeurs)
            raise PlaceholderInconnu(
                f"placeholder inconnu `{{{nom}}}` dans la déclaration du worktree "
                f"(connus : {connus})"
            )
        return valeurs[nom]

    return _PLACEHOLDER.sub(un_remplacement, texte)


def _valeurs(racine_worktree: Path, depot: Path) -> dict[str, str]:
    # Barres obliques : la commande passe par `shlex`, qui mange les `\` d'un
    # chemin Windows. Python et les outils courants acceptent les deux formes.
    return {"worktree": racine_worktree.as_posix(), "repo": depot.as_posix()}


def commande_effective(
    politique: PolitiqueRun, racine_worktree: Path, depot: Path
) -> str | None:
    """The `worktree.test_command` if declared, else `test_command`, placeholders resolved.

    `None` when the project declares no command at all. Raises
    `PlaceholderInconnu` when the command names a placeholder that does not exist:
    the run must refuse it, not launch a literal `{typo}`.
    """
    declaree = politique.worktree.test_command if politique.worktree else None
    commande = declaree if declaree and declaree.strip() else politique.test_command
    if not commande:
        return None
    return _remplacer(commande, _valeurs(racine_worktree, depot))


def environnement_effectif(
    config: ConfigWorktree, racine_worktree: Path, depot: Path
) -> dict[str, str]:
    """The `worktree.env` values with placeholders resolved, keys untouched.

    Raises `PlaceholderInconnu` like `commande_effective`.
    """
    valeurs = _valeurs(racine_worktree, depot)
    return {cle: _remplacer(valeur, valeurs) for cle, valeur in config.env.items()}
