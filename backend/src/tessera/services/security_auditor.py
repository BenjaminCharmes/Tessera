from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from tessera.services.providers.base import LLMProvider
from tessera.utils.json_extract import extract_json
from tessera.services.modeles_par_defaut import MODELE_JUGEMENT
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_MODEL = MODELE_JUGEMENT
_MAX_TOKENS = 2048
_PROMPT_FILE = "securite.md"
# Depuis le ticket-208, l'audit reçoit tout le diff d'une branche reprise :
# à 16 000 caractères, la fin passait sans audit (ticket-221). ~30 000 tokens,
# bien en deçà de la fenêtre des modèles servis.
_CODE_MAX_CHARS = 120_000
_RETRY_HINT = (
    "Ta réponse précédente n'était pas un JSON valide ; "
    "réponds uniquement par l'objet JSON demandé."
)

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
    # True par défaut : un champ absent vaut "introduit par ce ticket"
    # (echec fermé, ADR-039). L'auditeur pose False quand c'est du contexte.
    introduced: bool = True


@dataclass
class SecurityAuditResult:
    issues: list[SecurityIssue]
    verdict: AuditVerdict
    summary: str
    # Pourquoi l'audit bloque quand ce n'est pas le LLM qui l'a décidé :
    # provider en panne, réponse illisible, faille HIGH ignorée. Vide sur un
    # verdict rendu normalement. Part dans l'événement, donc à l'écran.
    reason: str = ""
    # Non vide quand l'audit avec outils a épuisé ses tours et que le verdict
    # vient du second appel, sur le diff seul (ticket-495). L'étape en fait un
    # événement `security_audit_fallback`.
    fallback_reason: str = ""

    @property
    def has_critical(self) -> bool:
        # Seules les failles introduites par ce ticket comptent pour le blocage.
        return any(i.severity == "CRITICAL" and i.introduced for i in self.issues)

    @property
    def has_high(self) -> bool:
        # Seules les failles introduites par ce ticket comptent pour le blocage.
        return any(i.severity == "HIGH" and i.introduced for i in self.issues)


class SecurityAuditorService:
    def __init__(
        self,
        provider: LLMProvider,
        prompts_dir: Path,
        model: str | None = None,
        max_turns: int | None = None,
        diff_only_provider: LLMProvider | None = None,
    ) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        # Le modèle vient du manifeste du projet quand il déclare ce rôle
        # (ticket-188) ; sinon le défaut d'avant, rien ne change.
        self._model = model or _MODEL
        # Le budget de tours annoncé à l'auditeur (ticket-495), et le provider
        # sans outil du second essai si ce budget s'épuise. Sans lui, pas de
        # repli : la limite de tours bloque comme toute indisponibilité.
        self._max_turns = max_turns
        self._diff_only_provider = diff_only_provider

    async def audit(
        self,
        code_diff: str,
        project_path: Path,
    ) -> SecurityAuditResult:
        base_prompt = self._load_system_prompt()
        user_message = f"## Code à auditer\n{code_diff[:_CODE_MAX_CHARS]}"
        system_prompt = base_prompt
        if self._max_turns is not None:
            system_prompt = f"{base_prompt}\n\n{_budget_note(self._max_turns)}"
        try:
            return await self._ask(self._provider, system_prompt, user_message, project_path)
        except Exception as exc:
            # Échoue fermé : un audit qui n'a pas eu lieu n'a rien approuvé.
            # Le run se bloque quand le provider tombe, c'est voulu ; le
            # `reason` doit le dire à l'écran (ticket-122). Seule la limite de
            # tours a un second essai ; le repli d'ADR-046 couvre le reste.
            _logger.warning("security_auditor_llm_failed", extra={"error": str(exc)})
            if self._diff_only_provider is None or not _is_turn_limit(exc):
                return _blocked(f"Audit sécurité indisponible : {exc}")
            return await self._audit_diff_only(
                self._diff_only_provider, base_prompt, user_message, project_path, exc
            )

    async def _audit_diff_only(
        self,
        provider: LLMProvider,
        system_prompt: str,
        user_message: str,
        project_path: Path,
        cause: Exception,
    ) -> SecurityAuditResult:
        """Second and last try: no tool, the diff alone, as before ticket-485."""
        fallback_reason = f"Limite de tours atteinte ({cause}) ; audit refait sur le diff seul."
        try:
            result = await self._ask(provider, system_prompt, user_message, project_path)
        except Exception as exc:
            _logger.warning("security_auditor_fallback_failed", extra={"error": str(exc)})
            result = _blocked(f"Audit sécurité indisponible : {exc}")
        result.fallback_reason = fallback_reason
        return result

    async def _ask(
        self, provider: LLMProvider, system_prompt: str, user_message: str, project_path: Path
    ) -> SecurityAuditResult:
        """Calls ``provider`` and parses the verdict; provider errors propagate."""
        for attempt in (1, 2):
            # Ticket-436 : une réponse illisible est redemandée une seule fois,
            # avec une consigne de plus ; la seconde illisible bloque.
            message = user_message if attempt == 1 else f"{user_message}\n\n{_RETRY_HINT}"
            result = await provider.complete(
                system=system_prompt,
                user=message,
                model=self._model,
                max_tokens=_MAX_TOKENS,
                # Ticket-485 : l'audit lit le code hors diff avant de
                # bloquer ; `cwd` le place dans le projet.
                cwd=project_path.resolve(),
            )
            parsed = self._parse_response(result.content, attempt)
            if parsed is not None:
                return parsed

        return _blocked(
            "Réponse de l'auditeur sécurité illisible (JSON attendu) "
            "après deux tentatives."
        )

    def _load_system_prompt(self) -> str:
        prompt_path = self._prompts_dir / _PROMPT_FILE
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "Audit code for security vulnerabilities. Respond with JSON."

    def _parse_response(self, raw: str, attempt: int = 1) -> SecurityAuditResult | None:
        """Parse the auditor answer; return None when it holds no readable JSON."""
        parsed = extract_json(raw, required_key="verdict")
        if not parsed:
            _logger.warning(
                "security_auditor_invalid_json",
                extra={"raw": raw[:200], "attempt": attempt},
            )
            return None

        # Seul "PASS" explicite est accepté ; toute autre valeur ferme l'audit
        # (ADR-039 : l'audit échoue fermé si la réponse est ambiguë).
        raw_verdict = str(parsed.get("verdict", ""))
        verdict: AuditVerdict = "PASS" if raw_verdict == "PASS" else "BLOCK"

        issues: list[SecurityIssue] = []
        for entry in parsed.get("issues", []):
            if not isinstance(entry, dict):
                continue
            severity = _SEVERITIES.get(str(entry.get("severity", "INFO")), "INFO")
            # Echec fermé (ADR-039) : seul un booléen False explicite marque la
            # faille comme préexistante. Absent, null, 0, "" ou "false" (chaîne)
            # valent True — bool() ferait passer null, 0 et "" pour False.
            introduced = entry.get("introduced", True) is not False
            issues.append(
                SecurityIssue(
                    severity=severity,
                    type=str(entry.get("type", "")),
                    location=str(entry.get("location", "")),
                    description=str(entry.get("description", "")),
                    fix=str(entry.get("fix", "")),
                    introduced=introduced,
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


def _budget_note(max_turns: int) -> str:
    """The turn budget told to the auditor, taken from the setting (ticket-495)."""
    return (
        f"Tu disposes d'au plus {max_turns} lectures. Lis d'abord ce qui peut "
        "changer un BLOCK en PASS ; garde le dernier tour pour ton verdict. "
        "Un point que tu n'as pas pu vérifier se signale dans `summary`, "
        "il ne bloque pas."
    )


def _is_turn_limit(exc: Exception) -> bool:
    """True when the SDK stopped the call on its turn limit."""
    return "maximum number of turns" in str(exc).lower()


def _blocked(reason: str) -> SecurityAuditResult:
    return SecurityAuditResult(issues=[], verdict="BLOCK", summary=reason, reason=reason)
