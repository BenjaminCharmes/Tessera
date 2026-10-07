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


def _first_dict_with_key(
    decoder: json.JSONDecoder, text: str, key: str
) -> "dict[str, Any] | None":
    """Return the first JSON object from *text* that contains *key*, or None."""
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and key in obj:
            return obj
    return None


def extract_json(
    text: str, required_key: str | None = None
) -> "dict[str, Any] | None":
    """Extracts a valid JSON object from a Claude response.

    Tries the ```json … ``` block first, then scans the full text from each
    ``{`` using ``json.JSONDecoder.raw_decode``.  The decoder understands
    string boundaries, so a ``}`` or ``{`` inside a quoted value does not
    confuse the extraction.

    When *required_key* is given, all ```json blocks are searched first,
    then the full text — returning the first object that **contains** that
    key.  Without *required_key*, the existing behaviour is unchanged: the
    very first valid object is returned.
    """
    decoder = json.JSONDecoder()

    if required_key is not None:
        # Cherche dans chaque bloc ```json``` dans l'ordre d'apparition
        for block_match in re.finditer(r"```json\s*(.*?)\s*```", text, re.DOTALL):
            result = _first_dict_with_key(decoder, block_match.group(1), required_key)
            if result is not None:
                return result
        # Repli : tout le texte
        return _first_dict_with_key(decoder, text, required_key)

    # Comportement actuel inchangé : premier objet JSON trouvé
    first_block = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if first_block:
        result = _first_dict(decoder, first_block.group(1))
        if result is not None:
            return result

    # Repli : raw_decode à partir de chaque `{` du texte entier
    return _first_dict(decoder, text)
