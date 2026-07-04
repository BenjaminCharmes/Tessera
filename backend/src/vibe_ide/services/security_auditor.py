from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from anthropic import AsyncAnthropic

from vibe_ide.utils.json_extract import extract_json
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048
_PROMPT_FILE = "securite.md"
_CODE_MAX_CHARS = 16_000

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
AuditVerdict = Literal["PASS", "BLOCK"]


@dataclass
class SecurityIssue:
    severity: Severity
    type: str
    location: str
    description: str
    fix: str


@dataclass
class SecurityAuditResult:
    issues: list[SecurityIssue]
    verdict: AuditVerdict
    summary: str

    @property
    def has_critical(self) -> bool:
        return any(i.severity == "CRITICAL" for i in self.issues)

    @property
    def has_high(self) -> bool:
        return any(i.severity == "HIGH" for i in self.issues)


class SecurityAuditorService:
    def __init__(self, client: AsyncAnthropic, prompts_dir: Path) -> None:
        self._client = client
        self._prompts_dir = prompts_dir

    async def audit(
        self,
        code_diff: str,
        project_path: Path,
    ) -> SecurityAuditResult:
        system_prompt = self._load_system_prompt()
        user_message = f"## Code à auditer\n{code_diff[:_CODE_MAX_CHARS]}"

        try:
            response = await self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as exc:
            _logger.warning("security_auditor_llm_failed", extra={"error": str(exc)})
            return SecurityAuditResult(
                issues=[],
                verdict="PASS",
                summary="Audit LLM indisponible — PASS par défaut.",
            )

        raw = response.content[0].text
        return self._parse_response(raw)

    def _load_system_prompt(self) -> str:
        prompt_path = self._prompts_dir / _PROMPT_FILE
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "Audit code for security vulnerabilities. Respond with JSON."

    def _parse_response(self, raw: str) -> SecurityAuditResult:
        parsed = extract_json(raw)
        if not parsed:
            _logger.warning("security_auditor_invalid_json", extra={"raw": raw[:200]})
            return SecurityAuditResult(issues=[], verdict="PASS", summary="")

        raw_verdict = parsed.get("verdict", "PASS")
        verdict: AuditVerdict = "BLOCK" if raw_verdict == "BLOCK" else "PASS"

        issues: list[SecurityIssue] = []
        for entry in parsed.get("issues", []):
            if not isinstance(entry, dict):
                continue
            severity = str(entry.get("severity", "INFO"))
            if severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
                severity = "INFO"
            issues.append(
                SecurityIssue(
                    severity=severity,  # type: ignore[arg-type]
                    type=str(entry.get("type", "")),
                    location=str(entry.get("location", "")),
                    description=str(entry.get("description", "")),
                    fix=str(entry.get("fix", "")),
                )
            )

        return SecurityAuditResult(
            issues=issues,
            verdict=verdict,
            summary=str(parsed.get("summary", "")),
        )
