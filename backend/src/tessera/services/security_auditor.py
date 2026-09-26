from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from tessera.services.providers.base import LLMProvider
from tessera.utils.json_extract import extract_json
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048
_PROMPT_FILE = "securite.md"
_CODE_MAX_CHARS = 16_000

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
_SEVERITIES: dict[str, Severity] = {
    "CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW", "INFO": "INFO",
}
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
    # Pourquoi l'audit bloque quand ce n'est pas le LLM qui l'a décidé :
    # provider en panne, réponse illisible, faille HIGH ignorée. Vide sur un
    # verdict rendu normalement. Part dans l'événement, donc à l'écran.
    reason: str = ""

    @property
    def has_critical(self) -> bool:
        return any(i.severity == "CRITICAL" for i in self.issues)

    @property
    def has_high(self) -> bool:
        return any(i.severity == "HIGH" for i in self.issues)


class SecurityAuditorService:
    def __init__(
        self, provider: LLMProvider, prompts_dir: Path, model: str | None = None
    ) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        # Le modèle vient du manifeste du projet quand il déclare ce rôle
        # (ticket-188) ; sinon le défaut d'avant, rien ne change.
        self._model = model or _MODEL

    async def audit(
        self,
        code_diff: str,
        project_path: Path,
    ) -> SecurityAuditResult:
        system_prompt = self._load_system_prompt()
        user_message = f"## Code à auditer\n{code_diff[:_CODE_MAX_CHARS]}"

        try:
            result = await self._provider.complete(
                system=system_prompt,
                user=user_message,
                model=self._model,
                max_tokens=_MAX_TOKENS,
            )
        except Exception as exc:
            # Échoue fermé : un audit qui n'a pas eu lieu n'a rien approuvé.
            # Le run se bloque quand le provider tombe, c'est voulu ; le
            # `reason` doit le dire à l'écran (ticket-122).
            _logger.warning("security_auditor_llm_failed", extra={"error": str(exc)})
            return _blocked(f"Audit sécurité indisponible : {exc}")

        return self._parse_response(result.content)

    def _load_system_prompt(self) -> str:
        prompt_path = self._prompts_dir / _PROMPT_FILE
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "Audit code for security vulnerabilities. Respond with JSON."

    def _parse_response(self, raw: str) -> SecurityAuditResult:
        parsed = extract_json(raw)
        if not parsed:
            _logger.warning("security_auditor_invalid_json", extra={"raw": raw[:200]})
            return _blocked("Réponse de l'auditeur sécurité illisible (JSON attendu).")

        raw_verdict = parsed.get("verdict", "PASS")
        verdict: AuditVerdict = "BLOCK" if raw_verdict == "BLOCK" else "PASS"

        issues: list[SecurityIssue] = []
        for entry in parsed.get("issues", []):
            if not isinstance(entry, dict):
                continue
            severity = _SEVERITIES.get(str(entry.get("severity", "INFO")), "INFO")
            issues.append(
                SecurityIssue(
                    severity=severity,
                    type=str(entry.get("type", "")),
                    location=str(entry.get("location", "")),
                    description=str(entry.get("description", "")),
                    fix=str(entry.get("fix", "")),
                )
            )

        result = SecurityAuditResult(
            issues=issues,
            verdict=verdict,
            summary=str(parsed.get("summary", "")),
        )
        # La docstring du prompt promet qu'une faille CRITICAL ou HIGH bloque ;
        # seul le verdict du LLM était lu, et il pouvait lister la faille puis
        # conclure PASS (ticket-122).
        if verdict == "PASS" and (result.has_critical or result.has_high):
            worst = "CRITICAL" if result.has_critical else "HIGH"
            result.verdict = "BLOCK"
            result.reason = f"Faille {worst} relevée malgré un verdict PASS."
            result.summary = f"{result.reason} {result.summary}".strip()
        return result


def _blocked(reason: str) -> SecurityAuditResult:
    return SecurityAuditResult(issues=[], verdict="BLOCK", summary=reason, reason=reason)
