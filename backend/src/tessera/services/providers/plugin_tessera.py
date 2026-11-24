"""Le plugin local de Tessera, chargé selon les skills d'un rôle — ticket-293."""
from pathlib import Path

from claude_agent_sdk import SdkPluginConfig

# Chemin absolu vers le plugin Tessera, ancré sur la racine du dépôt.
# Ne jamais le résoudre depuis le cwd d'un projet : il vit dans le dépôt
# de l'IDE, pas dans celui du projet qui déclare le skill.
# backend/src/tessera/services/providers/ → parents[5] = racine du dépôt
_REPO_ROOT: Path = Path(__file__).resolve().parents[5]
TESSERA_PLUGIN_PATH: Path = _REPO_ROOT / "agents" / "plugin"


def plugins_du_role(skills: list[str] | None) -> list[SdkPluginConfig]:
    """The local plugin, only when a declared skill carries the `tessera:` prefix.

    Le chemin est absolu, ancré sur la racine du dépôt, jamais sur le cwd du
    projet (ticket-293).
    """
    if skills and any(s.startswith("tessera:") for s in skills):
        return [{"type": "local", "path": str(TESSERA_PLUGIN_PATH)}]
    return []
