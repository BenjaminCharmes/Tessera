"""The shared Python a worktree venv points at under the agent account — ticket-984.

A venv made by `uv` records, in `pyvenv.cfg`, the interpreter that made it. The
worktree setup runs under the backend's account (ADR-085) and alone decides
where that interpreter lives: under `%APPDATA%\\uv\\python` it would be
unreadable to the agent account. With `worktree.compte_agent`, the setup is
given the shared toolchain (ADR-086); without it, nothing changes.
"""
from collections.abc import Mapping
from pathlib import Path

from tessera.models.worktree_config import ConfigWorktree

#: Where `agent setup` installs the managed Pythons, readable by the agent account.
CHAINE_PYTHON = Path(r"C:\ProgramData\Tessera\toolchain\python")


class ChaineAbsente(Exception):
    """The shared Python folder does not exist: `agent setup` has not run."""


def env_du_setup(config: ConfigWorktree) -> dict[str, str]:
    """The uv variables of the setup: two with an agent account, none without."""
    if not config.compte_agent:
        return {}
    return {
        "UV_PYTHON_INSTALL_DIR": str(CHAINE_PYTHON),
        "UV_PYTHON_PREFERENCE": "only-managed",
    }


def fusionner_env(config: ConfigWorktree, env: Mapping[str, str] | None) -> dict[str, str] | None:
    """`env` with the setup variables on top; `env` itself when there are none."""
    ajout = env_du_setup(config)
    if not ajout:
        return None if env is None else dict(env)
    return {**(env or {}), **ajout}


def verifier_chaine(config: ConfigWorktree) -> None:
    """Raise `ChaineAbsente` when an agent-account setup has no shared Python."""
    if config.compte_agent and not CHAINE_PYTHON.is_dir():
        raise ChaineAbsente(
            f"La chaîne Python partagée est absente ({CHAINE_PYTHON}) : lancer `agent setup`."
        )
