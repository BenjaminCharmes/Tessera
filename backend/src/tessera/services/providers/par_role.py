"""The one place a provider is built for a role — ticket-188.

Le provider se déclare par rôle dans `agents.json`, avec un repli explicite.
Les routeurs passent tous par ici : un point d'appel qui construirait le
sien resterait sur le provider global, et le manifeste serait ignoré sans
que rien ne le dise. Un test le vérifie.
"""
from pathlib import Path

from tessera.config import settings
from tessera.models.agent import AgentConfig
from tessera.services.project_loader import load_agents_config
from tessera.services.providers import get_provider
from tessera.services.providers.base import LLMProvider
from tessera.services.providers.repli import ProviderAvecRepli


def config_du_role(project_path: Path | None, role: str) -> AgentConfig | None:
    """The manifest entry for `role`, or None when the project does not declare it."""
    if project_path is None or not (project_path / "agents.json").is_file():
        return None
    for config in load_agents_config(project_path):
        if config.role == role:
            return config
    return None


def modele_du_role(project_path: Path | None, role: str) -> str | None:
    """The model the manifest declares for `role`, or None — the service keeps
    its own default then, so nothing changes for projects that say nothing."""
    config = config_du_role(project_path, role)
    return config.model if config is not None else None


def provider_pour_role(
    project_path: Path | None,
    role: str,
    *,
    allow_tools: bool = True,
    tools: list[str] | None = None,
    racine_ecriture: Path | None = None,
    project_id: str | None = None,
) -> LLMProvider:
    """Builds the provider `role` declares, wrapped in its fallback if any.

    Rôle absent du manifeste, ou projet sans manifeste : le provider global
    de `settings.llm_provider`, comme avant ce ticket. Le repli reçoit les
    mêmes restrictions d'outils que le principal — un audit sans outils ne
    doit pas en gagner parce qu'Ollama est tombé.
    """
    config = config_du_role(project_path, role)
    nom = config.provider if config is not None else settings.llm_provider
    principal = get_provider(
        nom, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=allow_tools, tools=tools, racine_ecriture=racine_ecriture,
    )
    if config is None or config.fallback is None:
        return principal
    repli = get_provider(
        config.fallback.provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=allow_tools, tools=tools, racine_ecriture=racine_ecriture,
    )
    return ProviderAvecRepli(
        principal, repli, modele_repli=config.fallback.model, role=role, project_id=project_id
    )
