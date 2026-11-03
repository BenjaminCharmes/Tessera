"""What the validator is told of the run's dialogue — ticket-537."""
from collections.abc import Sequence
from typing import Any

from tessera.services.dialogue import DialogueChannel, DialogueExchange

Exchanges = Sequence[DialogueExchange]

# Section title shared with the validator prompt, which refers to it by name.
DECISIONS_SECTION_TITLE = "Décisions prises au dialogue pendant le run"


def build_decisions_section(exchanges: Exchanges) -> str:
    """Section listing the human answers given during the run, or nothing."""
    if not exchanges:
        return ""
    lines = "\n".join(
        f"{i}. Question : {e.question}\n   Réponse : {e.answer}"
        for i, e in enumerate(exchanges, start=1)
    )
    return f"## {DECISIONS_SECTION_TITLE}\n{lines}\n\n"


def validator_extras(refus: str, dialogue: DialogueChannel) -> dict[str, Any]:
    """Optional `validate` arguments: only those that carry something.

    A validator that does not know a parameter is called as it was before
    that parameter existed (ticket-476 for `refus`, ticket-537 for `exchanges`).
    """
    extra: dict[str, Any] = {"refus": refus} if refus else {}
    if dialogue.exchanges:
        extra["exchanges"] = dialogue.exchanges
    return extra
