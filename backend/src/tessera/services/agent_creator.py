"""Service Agent Creator — ticket-023."""
import time
from pathlib import Path

from tessera.models.agent import AgentCreatedInfo, CreateAgentConversationResponse
from tessera.models.project import ConversationMessage
from tessera.services.agent_registry import AgentRegistryService
from tessera.services.providers.base import LLMProvider
from tessera.utils.conversation import format_conversation
from tessera.utils.json_extract import extract_json
from tessera.services.prompt_loader import load_system_prompt
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 2048


class AgentCreatorService:
    def __init__(self, provider: LLMProvider, prompts_dir: Path) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        self._registry = AgentRegistryService(prompts_dir)

    async def create_agent(
        self,
        conversation: list[ConversationMessage],
    ) -> CreateAgentConversationResponse:
        t0 = time.monotonic()
        system_prompt = self._load_system_prompt()
        messages = [{"role": m.role, "content": m.content} for m in conversation]

        result = await self._provider.complete(
            system=system_prompt,
            user=format_conversation(messages),
            model=_DEFAULT_MODEL,
            max_tokens=_DEFAULT_MAX_TOKENS,
        )

        content = result.content

        _logger.info(
            "agent_creator_call",
            extra={
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "duration_ms": int((time.monotonic() - t0) * 1000),
            },
        )

        agent_data = extract_json(content)
        if (
            agent_data is None
            or "role" not in agent_data
            or "system_prompt" not in agent_data
        ):
            return CreateAgentConversationResponse(message=content, created=False)

        role = agent_data["role"]
        self._registry.create_agent(role, agent_data["system_prompt"])

        return CreateAgentConversationResponse(
            agent=AgentCreatedInfo(
                role=role,
                description=agent_data.get("description"),
            ),
            created=True,
        )

    def _load_system_prompt(self) -> str:
        return load_system_prompt(self._prompts_dir, "agent-creator.md")
