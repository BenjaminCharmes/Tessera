"""JSON schema (draft-07) of the validator answer (ADR-061)."""
from typing import Any

# Pas de champ `verdict` : il se recalcule depuis les critères. `criterion`
# reste optionnel, pour la réconciliation par texte quand l'index manque.
VALIDATOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "criterion": {"type": "string"},
                    "passed": {"type": "boolean"},
                    "note": {"type": "string"},
                },
                "required": ["index", "passed"],
            },
        },
        "feedback": {"type": "string"},
    },
    "required": ["criteria", "feedback"],
}
