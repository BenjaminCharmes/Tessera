"""Seul un appel sans outil se passe du compte agent — ticket-1043, ADR-093.

Dans un projet qui déclare `worktree.compte_agent`, tout appel outillé part sous
le compte dédié. L'exception tient ici et non plus à l'oubli d'un paramètre.
"""
from pathlib import Path

from tessera.config import settings
from tessera.services.projets.manifeste import lire_valeur
from tessera.services.providers.noms import ProviderIndisponible


def projet_exige_le_compte(project_path: Path | None) -> bool:
    """True when the project declares `worktree.compte_agent` and `AGENT_USER` is set."""
    if project_path is None or not settings.agent_user:
        return False
    declaration = lire_valeur(project_path, "worktree")
    return isinstance(declaration, dict) and declaration.get("compte_agent") is True


def refuser_appel_outille_sans_compte(
    *,
    exige: bool,
    compte_agent: bool,
    allowed_tools: list[str] | None,
    skills: list[str] | None,
    signaler: object | None,
) -> None:
    """Raises `ProviderIndisponible` for a tool-bearing call that skips the account."""
    if not exige or compte_agent:
        return
    # `None` : le jeu d'outils par défaut du SDK, donc outillé.
    outille = allowed_tools != [] or bool(skills) or signaler is not None
    if outille:
        raise ProviderIndisponible(
            "appel outillé refusé hors du compte agent : le projet déclare worktree.compte_agent"
        )
