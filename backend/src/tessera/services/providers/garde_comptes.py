"""Credential files of the backend's account that an agent never reads — ticket-929.

The Claude subscription session, the git ``store`` helper and the ``gh`` hosts
file give access to the subscription, to repositories and to GitHub. ADR-031
lets an agent read outside its project, so these are guarded by name.

The paths are resolved once, when the hook is built, from the backend's account:
under ``AGENT_USER``, ``~`` points elsewhere at call time. A missing file stays
guarded: its path is known, creating it later must not open it.
"""
import os
from pathlib import Path

#: What the agent reads when the path is one of these files.
COMPTE_REFUS = (
    "Lecture refusée : ce fichier porte la session de l'abonnement Claude, des "
    "identifiants git ou le jeton de `gh` du compte du backend. Aucun agent ne "
    "le lit (ADR-031). Ce refus repère les chemins nommés, `~` et variables "
    "développés, rien de plus : il attrape une erreur, pas une évasion ; le "
    "vrai plafond est le compte dédié. Un refus de hook est définitif ; si le "
    "ticket demande ce fichier, dis-le dans ton rapport."
)


def _dossier_gh() -> Path:
    """Folder of the ``gh`` configuration, as the platform and environment give it."""
    explicite = os.environ.get("GH_CONFIG_DIR")
    if explicite:
        return Path(explicite)
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "GitHub CLI"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else Path.home() / ".config") / "gh"


def fichiers_de_compte() -> tuple[Path, ...]:
    """Resolved paths of the backend account's credential files."""
    chemins = (
        Path.home() / ".claude" / ".credentials.json",
        Path.home() / ".git-credentials",
        _dossier_gh() / "hosts.yml",
    )
    return tuple(chemin.resolve() for chemin in chemins)
