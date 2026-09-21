"""Flattening of a multi-turn conversation into a single prompt."""
from collections.abc import Mapping, Sequence

_UNKNOWN_ROLE = "unknown"


def format_conversation(messages: Sequence[Mapping[str, str]]) -> str:
    """Flattens a multi-turn conversation into a single prompt string.

    Each turn is rendered as ``[ROLE] content`` on its own line, joined by a
    blank line between turns. The role and content are read defensively via
    ``.get()`` so a malformed turn (missing "role" and/or "content") degrades
    to a placeholder instead of raising.

    Limitation: role labels are not escaped or otherwise distinguished from
    turn content. If a turn's content itself contains a bracketed,
    role-like token (e.g. literal text such as ``[ASSISTANT]``), the
    rendered output can look like an extra turn boundary to a model reading
    the flattened prompt. Current callers only pass user-authored
    conversational text, so the practical risk is low, but this is not
    mitigated at the formatting layer.
    """

    # Le protocole LLMProvider n'expose qu'un `user: str` — le SDK Agent
    # (`query()`) ne prend qu'une seule invite, il n'y a donc nulle part où
    # poser une liste de messages structurée côté SDK. On aplatit donc chaque
    # tour en une ligne préfixée par son rôle. C'est un compromis de fidélité
    # assumé (le modèle ne voit plus des tours distincts mais un seul bloc de
    # texte), préféré à l'ajout d'une deuxième forme d'entrée au protocole pour
    # les deux seuls appelants qui en ont besoin (agent_creator, project_creator).
    return "\n\n".join(
        f"[{message.get('role', _UNKNOWN_ROLE).upper()}] {message.get('content', '')}"
        for message in messages
    )
