import json
import re
from typing import Any

# Barre oblique inverse non suivie d'un caractère d'échappement JSON valide.
# Valides après \ : " \ / b f n r t u (pour \uXXXX).
#
# Les barres se lisent **par paires** : `\\` est un échappement complet, et la
# barre qui le termine ne doit pas être examinée seule. Sans cela, `a\\p`
# (barre échappée puis `p`, valide) devenait `a\\\p` dès qu'une autre barre du
# texte était fautive, et l'objet restait illisible.
_ESCAPE = re.compile(r"\\(.)", re.DOTALL)
_VALID_ESCAPE_CHARS = frozenset('"\\/bfnrtu')


def _fix_backslashes(text: str) -> str:
    """Double les barres obliques inverses qui ne commencent pas un échappement JSON valide."""
    return _ESCAPE.sub(
        lambda m: m.group(0) if m.group(1) in _VALID_ESCAPE_CHARS else "\\\\" + m.group(1),
        text,
    )


def _scan_dict(decoder: json.JSONDecoder, text: str) -> "dict[str, Any] | None":
    """Scan *text* from each ``{`` and return the first valid JSON object, or None."""
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


def _scan_dict_with_key(
    decoder: json.JSONDecoder, text: str, key: str
) -> "dict[str, Any] | None":
    """Scan *text* from each ``{`` and return the first object containing *key*, or None."""
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


def _first_dict(decoder: json.JSONDecoder, text: str) -> "dict[str, Any] | None":
    """Return the first JSON object decoded from *text*, or None.

    When the initial scan fails, retries once after doubling any backslash
    that does not introduce a valid JSON escape sequence.
    """
    result = _scan_dict(decoder, text)
    if result is None:
        result = _scan_dict(decoder, _fix_backslashes(text))
    return result


def _first_dict_with_key(
    decoder: json.JSONDecoder, text: str, key: str
) -> "dict[str, Any] | None":
    """Return the first JSON object from *text* that contains *key*, or None.

    When the initial scan fails, retries once after doubling any backslash
    that does not introduce a valid JSON escape sequence.
    """
    result = _scan_dict_with_key(decoder, text, key)
    if result is None:
        result = _scan_dict_with_key(decoder, _fix_backslashes(text), key)
    return result


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

    In both cases, if a JSON object cannot be decoded because it contains
    a backslash not followed by a valid JSON escape character (e.g. ``\\x``,
    ``\\p``, ``\\.``), the scan is retried after doubling those backslashes.
    A truly malformed object (missing brace, mismatched quotes…) still
    returns None.
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
