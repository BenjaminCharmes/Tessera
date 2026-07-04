from dataclasses import dataclass, field
from pathlib import Path

from anthropic import AsyncAnthropic

from vibe_ide.utils.json_extract import extract_json
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 2048
_DOC_MAX_CHARS = 8_000
_PROMPT_FILE = "doc-updater.md"


@dataclass
class DocUpdateResult:
    no_changes: bool
    files_updated: list[str] = field(default_factory=list)


class DocUpdaterService:
    def __init__(self, client: AsyncAnthropic, prompts_dir: Path) -> None:
        self._client = client
        self._prompts_dir = prompts_dir

    async def update_docs(
        self,
        project_path: Path,
        diff: str,
        ticket_title: str,
    ) -> DocUpdateResult:
        system_prompt = self._load_system_prompt()
        doc_context = self._read_docs(project_path)

        user_message = (
            f"## Ticket\n{ticket_title}\n\n"
            f"## Code produit (diff/résumé)\n{diff or '(vide)'}\n\n"
            f"## Documentation existante\n{doc_context}"
        )

        try:
            response = await self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as exc:
            _logger.warning("doc_updater_llm_failed", extra={"error": str(exc)})
            return DocUpdateResult(no_changes=True)

        raw = response.content[0].text
        parsed = extract_json(raw)

        if not parsed or parsed.get("no_changes"):
            return DocUpdateResult(no_changes=True)

        return self._write_files(project_path, parsed.get("files", []))

    def _load_system_prompt(self) -> str:
        prompt_path = self._prompts_dir / _PROMPT_FILE
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "Update documentation based on code changes. Respond with JSON."

    def _read_docs(self, project_path: Path) -> str:
        parts: list[str] = []
        candidates = [
            project_path / "README.md",
            project_path / "CLAUDE.md",
            project_path / "docs" / "architecture.md",
        ]
        for doc_path in candidates:
            if doc_path.exists():
                content = doc_path.read_text(encoding="utf-8")[:_DOC_MAX_CHARS]
                parts.append(f"### {doc_path.name}\n{content}")
        return "\n\n".join(parts) or "(aucune documentation trouvée)"

    def _write_files(self, project_path: Path, files: list[object]) -> DocUpdateResult:
        updated: list[str] = []
        for entry in files:
            if not isinstance(entry, dict):
                continue
            rel_path = str(entry.get("path", ""))
            content = entry.get("content", "")
            if not rel_path or not isinstance(content, str):
                continue

            target = (project_path / rel_path).resolve()
            if not str(target).startswith(str(project_path.resolve())):
                _logger.warning("doc_updater_path_traversal", extra={"path": rel_path})
                continue

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                updated.append(rel_path)
            except Exception as exc:
                _logger.warning(
                    "doc_updater_write_failed",
                    extra={"path": rel_path, "error": str(exc)},
                )

        return DocUpdateResult(no_changes=len(updated) == 0, files_updated=updated)
