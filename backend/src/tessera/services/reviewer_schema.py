"""JSON schema (draft-07) of the reviewer answer (ADR-061).

No `minimum` or `maximum`: the providers refuse them in a structured-output
schema, so the 0-100 range of `confidence` is checked on reading instead.
"""
from typing import Any

VERDICTS: tuple[str, ...] = ("APPROVED", "CHANGES_REQUESTED")

REVIEWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "summary": {"type": "string"},
        "blocking": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "location": {"type": "string"},
                    "confidence": {"type": "integer"},
                },
                "required": ["text", "confidence"],
            },
        },
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "summary", "blocking"],
}
