import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from tessera.models.agent import AgentConfig, AgentResult, AgentRole
from tessera.models.ticket import Ticket, TicketStatus
from tessera.services.adr import adr_pertinents
from tessera.services.agent_registry import AgentNotFoundError, AgentRegistryService
from tessera.services.cost_calculator import calculate_cost
from tessera.services.database import save_agent_call
from tessera.services.providers.base import (
    LLMProvider,
    ProviderResult,
    ToolEventCallback,
)
from tessera.services.prompt_loader import MissingPromptError
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 8192

#: Ce que le reviewer peut faire : lire. Son prompt dit « tu ne modifies
#: rien » ; il recevait pourtant les outils du codeur, et la règle tenait à
#: sa bonne volonté. Comme pour ADR-027, ce qui n'est pas retiré n'est pas
#: interdit.
OUTILS_DE_RELECTURE: list[str] = ["Read", "Glob", "Grep"]

#: Construit un provider limité aux outils nommés — `get_provider(tools=…)`
#: chez le produit, un double dans les tests.
FabriqueProvider = Callable[[list[str]], LLMProvider]

_INSTRUCTIONS: dict[str, str] = {
    AgentRole.codeur.value: (
        "Implémente le ticket selon les critères d'acceptation. "
        "Fournis le code complet et les tests."
    ),
    AgentRole.reviewer.value: (
        "Relis le code produit. Indique CHANGES_REQUESTED ou APPROVED avec justification."
    ),
    AgentRole.orchestrateur.value: (
        "Décompose ce ticket en sous-tickets si nécessaire. Assigne les rôles appropriés."
    ),
    AgentRole.architect.value: (
        "Analyse les implications architecturales et propose une solution détaillée."
    ),
    AgentRole.project_creator.value: (
        "Crée la structure complète du projet demandé avec ses fichiers de base."
    ),
}


class AgentRunner:
    def __init__(
        self,
        provider: LLMProvider,
        registry: AgentRegistryService,
        db_path: Path | str | None = None,
        project_path: Path | None = None,
        fabrique_provider: FabriqueProvider | None = None,
        provider_par_role: Callable[[str], LLMProvider] | None = None,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._db_path = db_path
        self._project_path = project_path
        self._fabrique_provider = fabrique_provider
        self._provider_relecture: LLMProvider | None = None
        # Le provider se déclare par rôle dans le manifeste (ticket-188) : la
        # fabrique le construit, le runner le garde pour la durée du run.
        self._provider_par_role = provider_par_role
        self._providers: dict[str, LLMProvider] = {}

    async def run(
        self,
        role: str,
        ticket: Ticket,
        project_context: str,
        agent_config: AgentConfig | None = None,
        stream_callback: Callable[[str], Awaitable[None]] | None = None,
        tool_callback: ToolEventCallback | None = None,
        run_id: str | None = None,
        ask_user: Callable[[str], Awaitable[str]] | None = None,
        session: str | None = None,
    ) -> AgentResult:
        role_str = role.value if isinstance(role, AgentRole) else role
        t0 = time.monotonic()
        system_prompt = self._load_system_prompt(role_str, agent_config)
        # En reprise de session, `project_context` ne porte que ce que le
        # tour ajoute — le reste est déjà dans la conversation (ticket-187).
        user_prompt = (
            self._build_user_prompt(ticket, role_str, project_context)
            if session is None
            else self._build_reprise_prompt(project_context)
        )

        model = agent_config.model if agent_config else _DEFAULT_MODEL
        max_tokens = agent_config.max_tokens if agent_config else _DEFAULT_MAX_TOKENS
        # Chemin long obligatoire : un chemin court Windows fait refuser les
        # écritures côté SDK (cf. spike ticket-044).
        cwd = self._project_path.resolve() if self._project_path else None

        # `ask_user` n'est transmis que s'il existe : un provider doublé dans
        # un test n'a aucune raison de connaître un paramètre qui ne le
        # concerne pas, et le lui passer à vide casserait chaque double
        # (ticket-066).
        extra: dict[str, Any] = {"ask_user": ask_user} if ask_user is not None else {}
        if session is not None:
            extra["session"] = session

        provider = self._provider_pour(role_str)
        provider_result: ProviderResult
        if stream_callback is not None:
            provider_result = await provider.stream(
                system=system_prompt,
                user=user_prompt,
                model=model,
                max_tokens=max_tokens,
                cwd=cwd,
                on_token=stream_callback,
                on_tool_use=tool_callback,
                **extra,
            )
        else:
            provider_result = await provider.complete(
                system=system_prompt,
                user=user_prompt,
                model=model,
                max_tokens=max_tokens,
                cwd=cwd,
                **extra,
            )

        content = provider_result.content
        duration_ms = int((time.monotonic() - t0) * 1000)

        input_tokens = provider_result.input_tokens
        output_tokens = provider_result.output_tokens
        cache_read_tokens = provider_result.cache_read_tokens

        _logger.info(
            "agent_call",
            extra={
                "role": role_str,
                "ticket_id": ticket.id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "duration_ms": duration_ms,
            },
        )

        # Calculé dans tous les cas : l'orchestrateur en a besoin pour
        # borner la dépense d'un run, même sans `run_id` (mode autonome).
        cost_usd = (
            provider_result.cost_usd
            if provider_result.cost_usd is not None
            else calculate_cost(model, input_tokens, output_tokens, cache_read_tokens)
        )

        # Ce qui a réellement tourné : un repli répond avec un autre modèle
        # que celui demandé (ticket-188).
        modele_utilise = provider_result.model or model

        if run_id and self._db_path:
            try:
                await save_agent_call(
                    self._db_path,
                    run_id,
                    ticket.id,
                    role_str,
                    modele_utilise,
                    input_tokens,
                    output_tokens,
                    cache_read_tokens,
                    cost_usd,
                    duration_ms,
                    provider=provider_result.provider_name,
                )
            except Exception as exc:
                _logger.warning("agent_call_save_failed", extra={"error": str(exc)})

        return AgentResult(
            role=role_str,
            ticket_id=ticket.id,
            content=content,
            suggested_status=_parse_suggested_status(content),
            duration_ms=duration_ms,
            cost_usd=cost_usd,
            session_id=provider_result.session_id,
        )

    def _provider_pour(self, role: str) -> LLMProvider:
        """Le provider commun, sauf pour le reviewer qui n'a que la lecture.

        Sans fabrique — les tests, les doubles — tout le monde partage le
        provider reçu : le produit distingue deux jeux d'outils, pas deux
        façons de construire un runner.
        """
        if self._provider_par_role is not None:
            if role not in self._providers:
                self._providers[role] = self._provider_par_role(role)
            return self._providers[role]
        if role != AgentRole.reviewer.value or self._fabrique_provider is None:
            return self._provider
        if self._provider_relecture is None:
            self._provider_relecture = self._fabrique_provider(list(OUTILS_DE_RELECTURE))
        return self._provider_relecture

    def _load_system_prompt(
        self, role: str, agent_config: AgentConfig | None = None
    ) -> str:
        """Le prompt système du rôle, ou celui que le projet lui substitue.

        Le pipeline appelle toujours les mêmes rôles : `codeur` est l'étape
        « quelqu'un écrit », `reviewer` l'étape « quelqu'un relit ». Ce que ces
        étapes doivent produire, lui, dépend du projet — du code ici, une
        analyse de contrat ailleurs. `prompt_file` est ce qui permet de le dire
        (ticket-097). Il existait dans le modèle et n'était lu nulle part :
        chaque `agents.json` en déclarait un pour rien.
        """
        nom = _nom_de_prompt(agent_config) or role
        try:
            prompt = self._registry.get_prompt(nom)
        except AgentNotFoundError as exc:
            if nom != role:
                # Un prompt déclaré mais absent ne retombe pas sur le rôle : le
                # run produirait du code là où on attendait une analyse, sans
                # que rien ne le signale.
                raise
            raise MissingPromptError(
                self._registry.prompts_dir, f"{role}.md", "rôle absent du registre"
            ) from exc
        # Le registre peut renvoyer un fichier vide : aussi inexploitable
        # qu'un fichier absent, et plus trompeur puisqu'il existe.
        if not prompt.strip():
            raise MissingPromptError(
                self._registry.prompts_dir, f"{nom}.md", "fichier vide"
            )
        return prompt

    def _build_user_prompt(self, ticket: Ticket, role: str, project_context: str) -> str:
        instruction = _INSTRUCTIONS.get(role, "Traite le ticket assigné.")
        return (
            f"## Contexte projet\n{adr_pertinents(project_context, role)}\n\n"
            f"## Ticket assigné\n{ticket.body}\n\n"
            f"## Ta mission\n{instruction}"
        )

    def _build_reprise_prompt(self, complements: str) -> str:
        """The prompt of a resumed round: only what this round adds (ticket-187).

        The ticket, the project's decisions and the files the agent read are
        already in the resumed conversation. Repeating them would pay twice
        for what resuming exists to pay once.
        """
        return (
            f"## Retours à traiter\n{complements or '_Aucun retour._'}\n\n"
            "## Ta mission\n"
            "Reprends ton travail du tour précédent, sur cette même branche, "
            "et corrige-le selon ces retours. Ne recommence pas depuis zéro : "
            "ce que tu as déjà lu et écrit est toujours là."
        )


def _parse_suggested_status(content: str) -> TicketStatus:
    """Extracts the suggested status from the agent's dedicated response section."""
    in_section = False
    for line in content.splitlines():
        if re.search(r"statut\s+sugg[eé]r[eé]", line, re.IGNORECASE):
            in_section = True
            continue
        if in_section and line.strip():
            upper = line.upper()
            if "IN_REVIEW" in upper or "IN-REVIEW" in upper:
                return TicketStatus.in_review
            if "BLOCKED" in upper:
                return TicketStatus.blocked
            if "DONE" in upper:
                return TicketStatus.done
            if "TODO" in upper:
                return TicketStatus.todo
            break
    return TicketStatus.in_review


def _nom_de_prompt(agent_config: "AgentConfig | None") -> str | None:
    """Le nom du prompt déclaré par le projet, sans son dossier ni son suffixe.

    `agents/prompts/analyste-carriere.md`, `prompts/analyste-carriere.md` et
    `analyste-carriere.md` désignent la même chose : le dossier des prompts est
    déjà connu du registre, le préfixe n'est qu'une commodité d'écriture.
    """
    if agent_config is None or not agent_config.prompt_file:
        return None
    return Path(agent_config.prompt_file).stem or None
