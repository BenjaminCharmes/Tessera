"""Service Project Creator — ticket-004."""
import time
from pathlib import Path

from anthropic import AsyncAnthropic

from vibe_ide.models.project import (
    ConversationMessage,
    CreateProjectResponse,
    ProjectCreate,
)
from vibe_ide.models.ticket import TicketDraft, TicketPriority, TicketType
from vibe_ide.services.project_loader import ProjectLoader
from vibe_ide.utils.json_extract import extract_json
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 4096


class ProjectCreatorService:
    def __init__(
        self, client: AsyncAnthropic, prompts_dir: Path, workspace_dir: Path
    ) -> None:
        self._client = client
        self._prompts_dir = prompts_dir
        self._workspace_dir = workspace_dir

    async def create_project(
        self, conversation: list[ConversationMessage]
    ) -> CreateProjectResponse:
        t0 = time.monotonic()
        system_prompt = self._load_system_prompt()
        messages = [{"role": m.role, "content": m.content} for m in conversation]

        response = await self._client.messages.create(
            model=_DEFAULT_MODEL,
            max_tokens=_DEFAULT_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )

        content = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )

        _logger.info(
            "project_creator_call",
            extra={
                "input_tokens": getattr(response.usage, "input_tokens", 0),
                "output_tokens": getattr(response.usage, "output_tokens", 0),
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
        )

    def _load_system_prompt(self) -> str:
        prompt_file = self._prompts_dir / "project-creator.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        _logger.warning("prompt_file_missing", extra={"path": str(prompt_file)})
        return "Tu es le Project Creator de vibe-ide. Aide l'utilisateur à créer un projet."

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


