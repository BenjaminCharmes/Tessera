"""Chat tooling policy for a project that requires the agent account — ticket-1051 (ADR-094)."""
from pathlib import Path

from tessera.services.providers.base import LLMProvider
from tessera.services.providers.compte_exige import projet_exige_le_compte
from tessera.services.providers.par_role import provider_pour_role

#: Ce que le chat reçoit dans un projet à compte agent : rien d'outillé.
MESSAGE_SANS_OUTILS = (
    "Ce projet exige le compte agent : le chat y répond sans accès aux "
    "fichiers. Lance un ticket depuis le pipeline pour modifier le projet."
)


def chat_sans_outils(project_path: Path) -> bool:
    """True when the chat of this project must run without any tool (ADR-094)."""
    return projet_exige_le_compte(project_path)


def provider_du_chat(
    project_path: Path, project_id: str, role: str, tools: list[str]
) -> LLMProvider:
    """The chat provider: tooled by default, bare in an account-agent project.

    Sans outil, skill ni `signaler`, et sans `compte_agent` : ADR-093 ne refuse
    que les appels outillés, et celui-ci ne l'est pas. Les skills et le drapeau
    `web` du rôle `chat` sont donc ignorés.
    """
    if chat_sans_outils(project_path):
        return provider_pour_role(
            project_path, role, allow_tools=False, project_id=project_id, sans_skill=True
        )
    return provider_pour_role(project_path, role, tools=tools, project_id=project_id)
