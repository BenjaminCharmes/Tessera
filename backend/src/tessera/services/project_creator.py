"""Service Project Creator — ticket-004."""
import time
from pathlib import Path

from tessera.models.project import (
    ConversationMessage,
    CreateProjectResponse,
    ProjectCreate,
)
from tessera.models.ticket import TicketDraft, TicketPriority, TicketType
from tessera.services.agent_registry import AgentRegistryService
from tessera.services.cost_calculator import DEFAULT_MODEL
from tessera.services.project_loader import ProjectLoader
from tessera.services.providers.base import LLMProvider
from tessera.utils.conversation import format_conversation
from tessera.utils.json_extract import extract_json
from tessera.services.prompt_loader import load_system_prompt
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_MODEL = DEFAULT_MODEL
_BOOTSTRAP_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_MAX_TOKENS = 4096
_BOOTSTRAP_MAX_TOKENS = 1024


class ProjectCreatorService:
    def __init__(
        self, provider: LLMProvider, prompts_dir: Path, workspace_dir: Path
    ) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        self._workspace_dir = workspace_dir
        self._registry = AgentRegistryService(prompts_dir)

    async def create_project(
        self, conversation: list[ConversationMessage]
    ) -> CreateProjectResponse:
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
            "project_creator_call",
            extra={
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "duration_ms": int((time.monotonic() - t0) * 1000),
            },
        )

        project_data = extract_json(content)
        if project_data is None:
            return CreateProjectResponse(agent_message=content, done=False)

        loader = ProjectLoader(self._workspace_dir)
        project = await loader.create_project(
            ProjectCreate(
                project_id=project_data["project_id"],
                name=project_data["name"],
                active_agents=project_data.get("active_agents", []),
                claude_md_content=project_data.get("claude_md", ""),
            )
        )

        await self._save_conversation_log(project_data["project_id"], conversation, content)

        agents_created = await self._auto_create_missing_agents(
            roles=project_data.get("active_agents", []),
            project_name=project_data["name"],
            project_description=project_data.get("description", ""),
        )

        suggested_tickets = [
            TicketDraft(
                title=t["title"],
                type=TicketType(t["type"]),
                priority=TicketPriority(t["priority"]),
                agent=t["agent"],
                description=t["description"],
            )
            for t in project_data.get("suggested_tickets", [])
        ]

        return CreateProjectResponse(
            project=project,
            suggested_tickets=suggested_tickets,
            claude_md_generated=project_data.get("claude_md", ""),
            done=True,
            agents_created=agents_created,
        )

    async def _auto_create_missing_agents(
        self, roles: list[str], project_name: str, project_description: str
    ) -> list[str]:
        created: list[str] = []
        # Les rôles déclarés natifs comptent comme existants même si leur
        # prompt n'est pas encore sur le disque : ils sont livrés avec le
        # dépôt, et en fabriquer un à la volée écraserait celui du produit.
        existing = {a.role for a in self._registry.list_agents()}
        for role in roles:
            if role in existing:
                continue
            try:
                prompt = await self._bootstrap_agent(role, project_name, project_description)
                self._registry.create_agent(role, prompt)
                created.append(role)
                _logger.info("agent_auto_created", extra={"role": role})
            except Exception as exc:
                _logger.warning(
                    "agent_auto_create_failed",
                    extra={"role": role, "error": str(exc)},
                )
        return created

    async def _bootstrap_agent(
        self, role: str, project_name: str, project_description: str
    ) -> str:
        prompt = (
            f'Génère le system prompt d\'un agent nommé "{role}" pour le projet "{project_name}".\n'
            f"Description du projet : {project_description}\n"
            "Réponds uniquement avec le system prompt (minimum 50 mots), sans JSON ni balises."
        )
        result = await self._provider.complete(
            system="",
            user=prompt,
            model=_BOOTSTRAP_MODEL,
            max_tokens=_BOOTSTRAP_MAX_TOKENS,
        )
        return result.content

    def _load_system_prompt(self) -> str:
        return load_system_prompt(self._prompts_dir, "project-creator.md")

    async def _save_conversation_log(
        self, project_id: str, conversation: list[ConversationMessage], final_response: str
    ) -> None:
        log_path = self._workspace_dir / project_id / "memory" / "project-creation-log.md"
        lines = ["# Log de création du projet\n"]
        for msg in conversation:
            prefix = "**User**" if msg.role == "user" else "**Assistant**"
            lines.append(f"{prefix}: {msg.content}\n")
        lines.append(f"\n**Assistant (réponse finale)**: {final_response}\n")
        log_path.write_text("\n".join(lines), encoding="utf-8")
