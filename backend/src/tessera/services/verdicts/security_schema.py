"""JSON schema (draft-07) of the security audit answer (ADR-061)."""
from typing import Any

# Doit rester égal aux clés de `_SEVERITIES` dans `security_auditor` ; un test
# les confronte.
SEVERITY_KEYS: tuple[str, ...] = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")

SECURITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "BLOCK"]},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": list(SEVERITY_KEYS)},
                    "type": {"type": "string"},
                    "location": {"type": "string"},
                    "description": {"type": "string"},
                    "fix": {"type": "string"},
                    "introduced": {"type": "boolean"},
                },
                "required": ["severity", "description", "introduced"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["verdict", "issues", "summary"],
}
