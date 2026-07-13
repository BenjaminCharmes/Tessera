import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from anthropic import AsyncAnthropic

from vibe_ide.models.agent import AgentConfig, AgentResult, AgentRole
from vibe_ide.models.ticket import Ticket, TicketStatus
from vibe_ide.services.agent_registry import AgentNotFoundError, AgentRegistryService
from vibe_ide.services.cost_calculator import calculate_cost
from vibe_ide.services.database import save_agent_call
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 8192

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
        client: AsyncAnthropic,
        registry: AgentRegistryService,
        db_path: Path | str | None = None,
    ) -> None:
        self._client = client
        self._registry = registry
        self._db_path = db_path

    async def run(
        self,
        role: str,
        ticket: Ticket,
        project_context: str,
        agent_config: AgentConfig | None = None,
        stream_callback: Callable[[str], Awaitable[None]] | None = None,
        run_id: str | None = None,
    ) -> AgentResult:
        role_str = role.value if isinstance(role, AgentRole) else role
        t0 = time.monotonic()
        system_prompt = self._load_system_prompt(role_str)
        user_prompt = self._build_user_prompt(ticket, role_str, project_context)

        model = agent_config.model if agent_config else _DEFAULT_MODEL
        max_tokens = agent_config.max_tokens if agent_config else _DEFAULT_MAX_TOKENS

        if stream_callback is not None:
            content, usage = await self._stream(
                system_prompt, user_prompt, model, max_tokens, stream_callback
            )
        else:
            content, usage = await self._complete(
                system_prompt, user_prompt, model, max_tokens
            )

        duration_ms = int((time.monotonic() - t0) * 1000)

        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)
        cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0)

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

        if run_id and self._db_path:
            cost_usd = calculate_cost(model, input_tokens, output_tokens, cache_read_tokens)
            try:
                await save_agent_call(
                    self._db_path,
                    run_id,
                    ticket.id,
                    role_str,
                    model,
                    input_tokens,
                    output_tokens,
                    cache_read_tokens,
                    cost_usd,
                    duration_ms,
                )
            except Exception as exc:
                _logger.warning("agent_call_save_failed", extra={"error": str(exc)})

        return AgentResult(
            role=role_str,
            ticket_id=ticket.id,
            content=content,
            suggested_status=_parse_suggested_status(content),
            duration_ms=duration_ms,
        )

    def _load_system_prompt(self, role: str) -> str:
        try:
            return self._registry.get_prompt(role)
        except AgentNotFoundError:
            _logger.warning("prompt_file_missing", extra={"role": role})
            return f"Tu es un agent {role} de vibe-ide. Aide à implémenter le ticket assigné."

    def _build_user_prompt(self, ticket: Ticket, role: str, project_context: str) -> str:
        instruction = _INSTRUCTIONS.get(role, "Traite le ticket assigné.")
        return (
            f"## Contexte projet\n{project_context}\n\n"
            f"## Ticket assigné\n{ticket.body}\n\n"
            f"## Ta mission\n{instruction}"
        )

    async def _complete(
        self, system: str, user: str, model: str, max_tokens: int
    ) -> tuple[str, object]:
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": user}],
        )
        content = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        return content, response.usage

    async def _stream(
        self,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        callback: Callable[[str], Awaitable[None]],
    ) -> tuple[str, object]:
        chunks: list[str] = []
        async with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=[
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                chunks.append(text)
                await callback(text)
            message = await stream.get_final_message()
        return "".join(chunks), message.usage


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
