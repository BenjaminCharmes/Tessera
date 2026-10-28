from typing import Any


def _extract_stream_delta(event: dict[str, Any]) -> str | None:
    """Extracts incremental text from a raw Anthropic ``stream_event`` payload.

    ``StreamEvent.event`` is the raw Anthropic Messages API streaming event
    (``message_start``, ``content_block_start``, ``content_block_delta``,
    ``content_block_stop``, ``message_delta``, ``message_stop``, ...). Only a
    ``content_block_delta`` carrying a ``text_delta`` produces visible text
    for live display; every other shape — including a malformed/unexpected
    one — yields ``None`` rather than raising, since a live-token feed must
    never crash the run.
    """
    try:
        if event.get("type") != "content_block_delta":
            return None
        delta = event.get("delta") or {}
        if delta.get("type") != "text_delta":
            return None
        text = delta.get("text")
        return text if isinstance(text, str) and text else None
    except AttributeError:
        return None


def _usage_from(result: Any) -> tuple[int, int, int, int]:
    """Extracts (input, output, cache_read, cache_creation) from a ResultMessage."""
    usage = getattr(result, "usage", None) or {}
    return (
        int(usage.get("input_tokens", 0) or 0),
        int(usage.get("output_tokens", 0) or 0),
        int(usage.get("cache_read_input_tokens", 0) or 0),
        int(usage.get("cache_creation_input_tokens", 0) or 0),
    )


#: Le nom de l'outil interne par lequel le CLI rend la sortie structurée : il
#: n'est pas un outil de l'agent et ne part pas dans `on_tool_use`.
OUTIL_SORTIE_STRUCTUREE = "StructuredOutput"


def _structured_from(result: Any) -> dict[str, Any] | None:
    """Extracts the validated structured output of a ResultMessage, or ``None``.

    Un ``success`` sans sortie, le sous-type d'échec des relances du SDK
    (``error_max_structured_output_retries``) et une valeur qui n'est pas un
    objet rendent tous ``None`` : c'est au service de refuser.
    """
    if getattr(result, "subtype", None) != "success":
        return None
    sortie = getattr(result, "structured_output", None)
    return sortie if isinstance(sortie, dict) else None


def _format_de_sortie(schema: dict[str, Any] | None) -> dict[str, Any] | None:
    """The SDK's ``output_format`` asking for ``schema``, or ``None`` without one."""
    return None if schema is None else {"type": "json_schema", "schema": schema}
