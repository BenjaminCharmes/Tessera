"""Conversational agent with tools — ticket-048.

Tessera could only converse through three closed, single-purpose modals.
This service opens a free discussion about a project: the agent has the
project's context, reads and writes its files, and streams its answer.

Two constraints shape it, and both come from elsewhere in the system:

- **ADR-019** — a chat that writes into the working tree breaks the clean-tree
  guarantee `ADR-018` relies on, and the next ticket would go straight to
  `blocked` without any agent running. So the chat commits its work on a
  `chat-<timestamp>` branch, exactly as a pipeline run does on the ticket's.
- **Cost** — `llm_max_budget_usd` bounds a single call, not a conversation. A
  long discussion would burn the subscription quota with nothing surfacing it,
  so the conversation carries its own ceiling.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol

from pydantic import BaseModel

from tessera.services.chat_suggestion import (
    parse_pipeline_suggestion,
    strip_suggestion_marker,
)
from tessera.services.database import ChatMessageRow
from tessera.services.git_workspace import GitWorkspaceError, GitWorkspaceService
from tessera.services.cost_calculator import DEFAULT_MODEL
from tessera.services.prompt_loader import load_system_prompt
from tessera.services.providers.base import LLMProvider
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_PROMPT_FILE = "chat.md"
_DEFAULT_MODEL = DEFAULT_MODEL
_DEFAULT_MAX_TOKENS = 8192

# Les tours les plus anciens sont élagués au-delà de cette limite : le contexte
# projet est déjà volumineux, et une conversation longue le multiplierait à
# chaque tour.
_MAX_HISTORY_TURNS = 20


class ChatBudgetExceeded(Exception):
    """The conversation has reached its spending ceiling."""

    def __init__(self, spent_usd: float, max_usd: float) -> None:
        self.spent_usd = spent_usd
        self.max_usd = max_usd
        super().__init__(
            f"Cette conversation a atteint son plafond de dépense : "
            f"{spent_usd:.2f} USD sur {max_usd:.2f} autorisés. "
            "Ouvre une nouvelle conversation, ou relève "
            "CHAT_MAX_CONVERSATION_USD."
        )


class ChatReply(BaseModel):
    """What one chat turn produced."""

    content: str
    cost_usd: float = 0.0
    branch: str | None = None
    commit_sha: str | None = None
    # Lancement proposé par l'agent (ticket-055). L'agent suggère, il ne
    # déclenche jamais : c'est l'utilisateur qui accepte, depuis l'UI.
    suggested_ticket_id: str | None = None


class _TokenCallback(Protocol):
    async def __call__(self, token: str) -> None: ...


class _ToolCallback(Protocol):
    async def __call__(self, name: str, payload: dict[str, object]) -> None: ...


class ChatService:
    def __init__(
        self,
        provider: LLMProvider,
        prompts_dir: Path,
        project_path: Path,
        project_context: str,
        git_workspace: GitWorkspaceService | None = None,
        max_conversation_usd: float = 1.0,
    ) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        self._project_path = project_path
        self._project_context = project_context
        self._git_workspace = git_workspace
        self._max_conversation_usd = max_conversation_usd

    async def send(
        self,
        history: list[ChatMessageRow],
        message: str,
        spent_usd: float = 0.0,
        on_token: Optional[_TokenCallback] = None,
        on_tool_use: Optional[_ToolCallback] = None,
    ) -> ChatReply:
        """Run one conversational turn, then commit whatever it wrote."""
        if spent_usd >= self._max_conversation_usd:
            raise ChatBudgetExceeded(spent_usd, self._max_conversation_usd)

        system = load_system_prompt(self._prompts_dir, _PROMPT_FILE)
        user = self._build_user_message(history, message)

        result = await self._provider.stream(
            system=system,
            user=user,
            model=_DEFAULT_MODEL,
            max_tokens=_DEFAULT_MAX_TOKENS,
            cwd=self._project_path,
            on_token=on_token,
            on_tool_use=on_tool_use,
        )

        branch, commit_sha = await self._commit_if_written(message)

        # Le marqueur est un protocole entre l'agent et l'UI : il est retiré du
        # texte affiché, et seul son contenu validé ressort.
        suggestion = parse_pipeline_suggestion(result.content)
        content = strip_suggestion_marker(result.content).strip()

        return ChatReply(
            content=content,
            cost_usd=result.cost_usd or 0.0,
            branch=branch,
            commit_sha=commit_sha,
            suggested_ticket_id=suggestion.ticket_id if suggestion else None,
        )

    def _build_user_message(self, history: list[ChatMessageRow], message: str) -> str:
        """Rebuild the conversation in the prompt — the provider is stateless.

        Without this, every turn would start from scratch. Older turns beyond
        `_MAX_HISTORY_TURNS` are dropped: the project context is already large
        and would otherwise be multiplied by the length of the discussion.
        """
        parts = [f"## Contexte projet\n{self._project_context}"]

        recent = history[-_MAX_HISTORY_TURNS:]
        if len(history) > len(recent):
            parts.append(
                f"_({len(history) - len(recent)} tours plus anciens omis)_"
            )
        if recent:
            turns = "\n\n".join(
                f"**{'Utilisateur' if m.role == 'user' else 'Toi'}** : {m.content}"
                for m in recent
            )
            parts.append(f"## Conversation jusqu'ici\n{turns}")

        parts.append(f"## Message de l'utilisateur\n{message}")
        return "\n\n".join(parts)

    async def _commit_if_written(self, message: str) -> tuple[str | None, str | None]:
        """Commit on a `chat-…` branch, but only if the agent actually wrote.

        A purely conversational turn must not create a branch, or every
        question would leave a dead one behind. When the agent *did* write,
        committing is what keeps the tree clean for the next pipeline run
        (ADR-018, ADR-019).
        """
        if self._git_workspace is None:
            return None, None

        try:
            if await self._git_workspace.is_clean():
                return None, None

            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            branch = await self._git_workspace.create_branch("chat", stamp)
            summary = " ".join(message.split())[:60]
            commit_sha = await self._git_workspace.commit_all(
                f"chore: chat — {summary}"
            )
            return branch, commit_sha
        except GitWorkspaceError as exc:
            # Un projet sans dépôt git reste utilisable : le chat répond, il
            # ne commite simplement pas.
            _logger.warning("chat_commit_failed", extra={"error": str(exc)})
            return None, None
