"""The one place a provider is built for a role — ticket-188.

Le provider se déclare par rôle dans `agents.json`, avec un repli explicite.
Les routeurs passent tous par ici : un point d'appel qui construirait le
sien resterait sur le provider global, et le manifeste serait ignoré sans
que rien ne le dise. Un test le vérifie.
"""
from collections.abc import Callable
from pathlib import Path

from tessera.config import settings
from tessera.models.agent import AgentConfig
from tessera.services.project_loader import load_agents_config
from tessera.services.providers import get_provider
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.base import LLMProvider
from tessera.services.providers.declaration import (
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI,
    resoudre_cle,
)
from tessera.services.providers.refus_garde import JournalDesRefus
from tessera.services.providers.repli import ProviderAvecRepli
from tessera.services.providers.repli_direct import ProviderRepliDirect

#: Ce qu'un rôle déclaré `web` reçoit en plus (ticket-245).
OUTILS_WEB = ["WebFetch", "WebSearch"]

#: Les rôles qui rendent du texte ou du JSON, et dont un appel a une durée
#: totale maximale (ticket-518). Le codeur et le reviewer en sont exclus : un
#: tour légitime de codeur dure longtemps, et c'est le silence qui le borne.
ROLES_TEXTE = frozenset({"validateur", "securite", "doc-technique", "doc-fonctionnelle"})


def outils_du_role(
    config: AgentConfig | None, allow_tools: bool, tools: list[str] | None
) -> list[str] | None:
    """The tools the role gets once `web` is applied; `tools` unchanged otherwise.

    Une page lue peut porter des instructions, et on ne sait pas filtrer une
    page. On sait retirer le shell : sans `Bash`, l'agent n'a ni `curl` pour
    envoyer vers l'extérieur ni script à lancer. Un rôle sans outils ne gagne
    rien : le web est un outil de plus, pas une permission à part.
    """
    if config is None or not config.web or not allow_tools:
        return tools
    base = tools if tools is not None else ClaudeAgentSDKProvider.ALLOWED_TOOLS
    return [outil for outil in base if outil != "Bash"] + OUTILS_WEB


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


def connexion_du_role(config: AgentConfig | None, nom: str) -> tuple[str | None, str]:
    """The endpoint an `openai_compatible` role declares: its URL, and the key
    read from the environment variable `api_key_env` names. `(None, "")`
    otherwise, so no other provider ever receives either (ticket-669)."""
    if config is None or nom != PROVIDER_OPENAI or not config.base_url:
        return None, ""
    return config.base_url, resoudre_cle(config.api_key_env)


def seuil_du_role(config: AgentConfig | None, nom: str) -> int | None:
    """The prompt size above which `config` goes straight to its fallback.
    Only a local (`ollama`) principal has one: a cloud provider has no
    read timeout to dodge, so the key is ignored for it (ticket-714)."""
    if config is None or nom != PROVIDER_OLLAMA:
        return None
    return config.fallback_above_chars


def provider_pour_role(
    project_path: Path | None,
    role: str,
    *,
    allow_tools: bool = True,
    tools: list[str] | None = None,
    racine_ecriture: Path | None = None,
    project_id: str | None = None,
    max_turns: int | None = None,
    journal_refus: JournalDesRefus | None = None,
    journal_repli: Callable[[str], None] | None = None,
    rapide: bool = False,
) -> LLMProvider:
    """Builds the provider `role` declares, wrapped in its fallback if any.

    `rapide` (ticket-578) : un rôle qui déclare un repli est construit
    directement avec lui, sans principal ; un rôle sans repli ne change pas.

    Rôle absent du manifeste, ou projet sans manifeste : le provider global
    de `settings.llm_provider`, comme avant ce ticket. Le repli reçoit les
    mêmes restrictions d'outils que le principal — un audit sans outils ne
    doit pas en gagner parce qu'Ollama est tombé.

    Un rôle texte (`ROLES_TEXTE`) reçoit, pour le principal comme pour le
    repli, une durée totale maximale par appel (ticket-518). `journal_repli`
    reçoit la ligne que `ProviderAvecRepli` écrit quand le repli joue.
    """
    config = config_du_role(project_path, role)
    tools = outils_du_role(config, allow_tools, tools)
    nom = config.provider if config is not None else settings.llm_provider
    tours = max_turns if max_turns is not None else settings.llm_max_turns
    skills = config.skills if config is not None else []
    effort = config.effort if config is not None else None
    # Transmis seulement quand il y en a un : un appel sans journal reste
    # identique à ce qu'il était avant ticket-476.
    journal: dict[str, JournalDesRefus] = (
        {"journal_refus": journal_refus} if journal_refus is not None else {}
    )
    # Un rôle qui n'est pas du texte seul ne reçoit aucune borne (None).
    duree = settings.llm_duree_max_role_texte_s if role in ROLES_TEXTE else None
    # Le point d'accès ne sert que le principal : le repli n'en porte pas
    # (`agents.json` refuse `openai_compatible` comme repli).
    url, cle = connexion_du_role(config, nom)

    def _construire(fournisseur: str) -> LLMProvider:
        principal = fournisseur == nom
        return get_provider(
            fournisseur, settings.anthropic_api_key,
            max_turns=tours, max_budget_usd=settings.llm_max_budget_usd,
            allow_tools=allow_tools, tools=tools, racine_ecriture=racine_ecriture,
            skills=skills, duree_max_s=duree, effort=effort,
            base_url=url if principal else None,
            endpoint_key=cle if principal else "", **journal,
        )

    if rapide and config is not None and config.fallback is not None:
        return ProviderRepliDirect(
            _construire(config.fallback.provider), modele=config.fallback.model
        )
    principal = _construire(nom)
    if config is None or config.fallback is None:
        return principal
    repli = _construire(config.fallback.provider)
    return ProviderAvecRepli(
        principal, repli, modele_repli=config.fallback.model, role=role,
        project_id=project_id, journal=journal_repli,
        seuil_caracteres=seuil_du_role(config, nom),
    )
