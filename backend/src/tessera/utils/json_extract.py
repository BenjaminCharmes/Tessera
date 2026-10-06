import json
import re
from typing import Any


def _first_dict(decoder: json.JSONDecoder, text: str) -> "dict[str, Any] | None":
    """Return the first JSON object decoded from *text*, or None."""
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def extract_json(text: str) -> "dict[str, Any] | None":
    """Extracts the first valid JSON object from a Claude response.

    Tries the ```json … ``` block first, then scans the full text from each
    ``{`` using ``json.JSONDecoder.raw_decode``.  The decoder understands
    string boundaries, so a ``}`` or ``{`` inside a quoted value does not
    confuse the extraction.
    """
    decoder = json.JSONDecoder()

    # Essai prioritaire : bloc ```json ... ```
    block_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if block_match:
        result = _first_dict(decoder, block_match.group(1))
        if result is not None:
            return result

    # Repli : raw_decode à partir de chaque `{` du texte entier
    return _first_dict(decoder, text)
