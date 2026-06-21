"""Service ProjectAnalyzer — ticket-026."""
import fnmatch
import time
from pathlib import Path

from anthropic import AsyncAnthropic

from vibe_ide.models.project import AnalysisResult
from vibe_ide.utils.json_extract import extract_json
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 4096

_BINARY_PROBE_BYTES = 512


class ProjectAnalyzerService:
    MAX_FILES = 50
    MAX_FILE_BYTES = 8_000
    EXCLUDED: frozenset[str] = frozenset(
        {".git", "node_modules", ".venv", "__pycache__", ".DS_Store", "dist", "build", ".next", "target"}
    )
    SENSITIVE_GLOBS: tuple[str, ...] = (".env*", "*.key", "*.pem", "secrets*")
    KEY_FILES: frozenset[str] = frozenset(
        {
            "README.md",
            "CLAUDE.md",
            "package.json",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "requirements.txt",
            "Makefile",
            "tsconfig.json",
            "vite.config.ts",
            "vite.config.js",
            "setup.py",
            "setup.cfg",
            "composer.json",
            "Gemfile",
            "pom.xml",
            "build.gradle",
        }
    )

    def __init__(self, client: AsyncAnthropic, prompts_dir: Path) -> None:
        self._client = client
        self._prompts_dir = prompts_dir

    async def analyze(self, project_path: Path, overwrite: bool = False) -> AnalysisResult:
        file_tree = self._build_file_tree(project_path)
        file_contents = self._collect_file_contents(project_path)

        system_prompt = self._load_system_prompt()
        user_message = self._build_user_message(file_tree, file_contents)

        t0 = time.monotonic()
        response = await self._client.messages.create(
            model=_DEFAULT_MODEL,
            max_tokens=_DEFAULT_MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = "".join(block.text for block in response.content if hasattr(block, "text"))

        _logger.info(
            "project_analyzer_call",
            extra={
                "project": project_path.name,
                "input_tokens": getattr(response.usage, "input_tokens", 0),
                "output_tokens": getattr(response.usage, "output_tokens", 0),
                "duration_ms": int((time.monotonic() - t0) * 1000),
            },
        )

        data = extract_json(raw)
        if data is None or "claude_md" not in data:
            raise ValueError(f"L'agent project-analyzer n'a pas retourné un JSON valide. Réponse : {raw[:200]}")

        claude_md: str = data["claude_md"]
        detected_stack: list[str] = data.get("detected_stack", [])
        suggested_agents: list[str] = data.get("suggested_agents", [])

        claude_md_path = project_path / "CLAUDE.md"
        written = False
        if not claude_md_path.exists() or overwrite:
            claude_md_path.write_text(claude_md, encoding="utf-8")
            written = True

        return AnalysisResult(
            claude_md=claude_md,
            detected_stack=detected_stack,
            suggested_agents=suggested_agents,
            claude_md_written=written,
        )

    # ------------------------------------------------------------------
    # File filtering helpers
    # ------------------------------------------------------------------

    def _is_sensitive(self, path: Path) -> bool:
        name = path.name
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.SENSITIVE_GLOBS)

    def _is_binary(self, path: Path) -> bool:
        try:
            return b"\x00" in path.read_bytes()[:_BINARY_PROBE_BYTES]
        except OSError:
            return True

    def _read_truncated(self, path: Path) -> str | None:
        if self._is_binary(path):
            return None
        try:
            raw = path.read_bytes()[: self.MAX_FILE_BYTES]
            return raw.decode("utf-8", errors="replace")
        except OSError:
            return None

    # ------------------------------------------------------------------
    # File tree (display only)
    # ------------------------------------------------------------------

    def _build_file_tree(self, root: Path) -> str:
        return self._walk_tree(root, prefix="", depth=0)

    def _walk_tree(self, root: Path, prefix: str, depth: int) -> str:
        if depth > 2:
            return ""
        lines: list[str] = []
        try:
            entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return ""
        for entry in entries:
            if entry.name in self.EXCLUDED or self._is_sensitive(entry):
                continue
            lines.append(f"{prefix}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                sub = self._walk_tree(entry, prefix + "  ", depth + 1)
                if sub:
                    lines.append(sub)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # File content collection
    # ------------------------------------------------------------------

    def _walk_files(self, root: Path, depth: int = 0) -> list[Path]:
        if depth > 2:
            return []
        files: list[Path] = []
        try:
            entries = sorted(root.iterdir())
        except PermissionError:
            return []
        for entry in entries:
            if entry.name in self.EXCLUDED or self._is_sensitive(entry):
                continue
            if entry.is_dir():
                files.extend(self._walk_files(entry, depth + 1))
            elif entry.is_file():
                files.append(entry)
        return files

    def _collect_file_contents(self, root: Path) -> list[tuple[str, str]]:
        all_files = self._walk_files(root)

        key: list[tuple[str, str]] = []
        other: list[tuple[str, str]] = []

        for path in all_files:
            content = self._read_truncated(path)
            if content is None:
                continue
            rel = str(path.relative_to(root))
            if path.name in self.KEY_FILES:
                key.append((rel, content))
            else:
                other.append((rel, content))

        return (key + other)[: self.MAX_FILES]

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_user_message(self, file_tree: str, file_contents: list[tuple[str, str]]) -> str:
        parts = ["## Arbre de fichiers\n\n", file_tree, "\n\n## Contenu des fichiers\n"]
        for rel_path, content in file_contents:
            parts.append(f"\n### {rel_path}\n```\n{content}\n```\n")
        return "".join(parts)

    def _load_system_prompt(self) -> str:
        prompt_file = self._prompts_dir / "project-analyzer.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        _logger.warning("prompt_file_missing", extra={"path": str(prompt_file)})
        return (
            "Tu es un expert en analyse de projets logiciels. "
            "Génère un CLAUDE.md à partir de l'arbre de fichiers et du code. "
            'Réponds uniquement avec ce JSON : {"claude_md": "...", "detected_stack": [], "suggested_agents": []}'
        )
