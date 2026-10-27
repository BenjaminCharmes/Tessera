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
