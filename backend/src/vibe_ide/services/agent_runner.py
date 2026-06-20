import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from anthropic import AsyncAnthropic

from vibe_ide.models.agent import AgentConfig, AgentResult, AgentRole
from vibe_ide.models.ticket import Ticket, TicketStatus
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 8192

_INSTRUCTIONS: dict[AgentRole, str] = {
    AgentRole.codeur: (
        "Implémente le ticket selon les critères d'acceptation. "
        "Fournis le code complet et les tests."
    ),
    AgentRole.reviewer: (
        "Relis le code produit. Indique CHANGES_REQUESTED ou APPROVED avec justification."
    ),
    AgentRole.orchestrateur: (
        "Décompose ce ticket en sous-tickets si nécessaire. Assigne les rôles appropriés."
    ),
    AgentRole.architect: (
        "Analyse les implications architecturales et propose une solution détaillée."
    ),
    AgentRole.project_creator: (
        "Crée la structure complète du projet demandé avec ses fichiers de base."
    ),
}


class AgentRunner:
    def __init__(self, client: AsyncAnthropic, prompts_dir: Path) -> None:
        self._client = client
        self._prompts_dir = prompts_dir

    async def run(
        self,
        role: AgentRole,
        ticket: Ticket,
        project_context: str,
        agent_config: AgentConfig | None = None,
        stream_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> AgentResult:
        t0 = time.monotonic()
        system_prompt = self._load_system_prompt(role)
        user_prompt = self._build_user_prompt(ticket, role, project_context)

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

        _logger.info(
            "agent_call",
            extra={
                "role": role.value,
                "ticket_id": ticket.id,
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
                "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
                "duration_ms": duration_ms,
            },
        )

        return AgentResult(
            role=role,
            ticket_id=ticket.id,
            content=content,
            suggested_status=_parse_suggested_status(content),
            duration_ms=duration_ms,
        )

    def _load_system_prompt(self, role: AgentRole) -> str:
        prompt_file = self._prompts_dir / f"{role.value}.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        _logger.warning("prompt_file_missing", extra={"path": str(prompt_file)})
        return f"Tu es un agent {role.value} de vibe-ide. Aide à implémenter le ticket assigné."

    def _build_user_prompt(
        self, ticket: Ticket, role: AgentRole, project_context: str
    ) -> str:
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
    """Extrait le statut suggéré depuis la section dédiée de la réponse agent."""
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
    return TicketStatus.in_review  # défaut : passer en review
