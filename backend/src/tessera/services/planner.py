"""Service PlannerService — ticket-028."""
import time
from pathlib import Path
from typing import Any

from tessera.models.project import PlanResult
from tessera.models.ticket import TicketDraftPlan
from tessera.services.cost_calculator import DEFAULT_MODEL
from tessera.services.providers.base import LLMProvider
from tessera.utils.json_extract import extract_json
from tessera.services.prompt_loader import load_system_prompt
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_MODEL = DEFAULT_MODEL
_DEFAULT_MAX_TOKENS = 4096


class PlannerService:
    def __init__(
        self,
        provider: LLMProvider,
        prompts_dir: Path,
        workspace_dir: Path,
        model: str | None = None,
    ) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        self._workspace_dir = workspace_dir
        # Le modèle vient du manifeste du projet quand il déclare ce rôle
        # (ticket-188) ; sinon le défaut d'avant, rien ne change.
        self._model = model or _DEFAULT_MODEL

    async def plan(self, project_id: str, description: str) -> PlanResult:
        claude_md = self._load_claude_md(project_id)
        system_prompt = self._load_system_prompt()
        user_message = self._build_user_message(description, claude_md)

        t0 = time.monotonic()
        result = await self._provider.complete(
            system=system_prompt,
            user=user_message,
            model=self._model,
            max_tokens=_DEFAULT_MAX_TOKENS,
        )

        raw = result.content

        _logger.info(
            "planner_call",
            extra={
                "project": project_id,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "duration_ms": int((time.monotonic() - t0) * 1000),
            },
        )

        data = extract_json(raw)
        if data is None or "tickets" not in data:
            raise ValueError(
                f"Le planificateur n'a pas retourné un JSON valide. Réponse : {raw[:200]}"
            )

        drafts = self._parse_drafts(data["tickets"])
        self._validate_dependencies(drafts)

        return PlanResult(drafts=drafts, summary=data.get("summary", ""))

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_drafts(
        self, raw_tickets: list[dict[str, Any]]
    ) -> list[TicketDraftPlan]:
        return [
            TicketDraftPlan(
                title=item.get("title", ""),
                type=item.get("type", "feat"),
                priority=item.get("priority", "medium"),
                agent=item.get("agent", "codeur"),
                description=item.get("description", ""),
                acceptance_criteria=item.get("acceptance_criteria", []),
                depends_on_index=item.get("depends_on_index", []),
            )
            for item in raw_tickets
        ]

    # ------------------------------------------------------------------
    # Dependency validation
    # ------------------------------------------------------------------

    def _validate_dependencies(self, drafts: list[TicketDraftPlan]) -> None:
        n = len(drafts)
        for i, draft in enumerate(drafts):
            for dep in draft.depends_on_index:
                if dep == i:
                    raise ValueError(
                        f"Le ticket {i} ('{draft.title}') se référence lui-même."
                    )
                if dep < 0 or dep >= n:
                    raise ValueError(
                        f"Le ticket {i} ('{draft.title}') référence un index inexistant : {dep}."
                    )
        if self._has_cycle(drafts):
            raise ValueError("Les dépendances entre tickets contiennent un cycle.")

    def _has_cycle(self, drafts: list[TicketDraftPlan]) -> bool:
        n = len(drafts)
        # 0=white (unvisited), 1=gray (in stack), 2=black (done)
        color = [0] * n

        def dfs(v: int) -> bool:
            color[v] = 1
            for w in drafts[v].depends_on_index:
                if color[w] == 1:
                    return True
                if color[w] == 0 and dfs(w):
                    return True
            color[v] = 2
            return False

        return any(color[v] == 0 and dfs(v) for v in range(n))

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------

    def _load_claude_md(self, project_id: str) -> str:
        path = self._workspace_dir / project_id / "CLAUDE.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _load_system_prompt(self) -> str:
        return load_system_prompt(self._prompts_dir, "planificateur.md")

    def _build_user_message(self, description: str, claude_md: str) -> str:
        parts = [f"## Description de l'évolution\n\n{description}\n"]
        if claude_md:
            parts.append(f"\n## CLAUDE.md du projet\n\n{claude_md}\n")
        return "".join(parts)
