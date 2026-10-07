"""Tests for extract_json — ticket-345."""
import json

from tessera.utils.json_extract import extract_json


# ------------------------------------------------------------------
# Cas passants — objets avec chaînes contenant des accolades spéciales
# ------------------------------------------------------------------


def test_extract_dict_with_closing_brace_and_backticks_in_string() -> None:
    """An object whose string value ends with ``}``` `` `` `` does not fool the extractor."""
    obj = {"key": "value}```", "count": 42}
    result = extract_json(json.dumps(obj))
    assert result == obj


def test_extract_dict_with_lone_opening_brace_in_string() -> None:
    """An object whose string value contains a lone ``{`` is decoded correctly."""
    obj = {"message": "open { brace", "status": "ok"}
    result = extract_json(json.dumps(obj))
    assert result == obj


def test_extract_dict_preceded_by_non_json_brace() -> None:
    """When the text starts with a non-JSON ``{``, the real object is found anyway."""
    obj = {"tickets": [{"title": "A"}], "summary": "test"}
    text = "{ invalid prefix\n\n" + json.dumps(obj)
    result = extract_json(text)
    assert result == obj


def test_extract_truncated_object_returns_none() -> None:
    """A truncated JSON object returns None — not a partial decode."""
    text = '{"key": "value", "nested": {"a": 1'  # missing closing braces
    result = extract_json(text)
    assert result is None


# ------------------------------------------------------------------
# Cas passants — blocs markdown et texte mêlé
# ------------------------------------------------------------------


def test_extract_from_json_code_block() -> None:
    obj = {"tickets": [], "summary": "ok"}
    text = f"Here is the plan:\n\n```json\n{json.dumps(obj)}\n```"
    result = extract_json(text)
    assert result == obj


def test_extract_bare_json_without_code_block() -> None:
    obj = {"x": 1, "y": 2}
    result = extract_json(json.dumps(obj))
    assert result == obj


def test_extract_json_surrounded_by_prose() -> None:
    obj = {"answer": "yes"}
    text = f"Here is my answer: {json.dumps(obj)} — hope that helps."
    result = extract_json(text)
    assert result == obj


# ------------------------------------------------------------------
# Cas négatifs
# ------------------------------------------------------------------


def test_no_json_returns_none() -> None:
    result = extract_json("There is no JSON here at all.")
    assert result is None


def test_array_at_root_returns_none() -> None:
    """A JSON array (not an object) is not returned."""
    result = extract_json("[1, 2, 3]")
    assert result is None


# ------------------------------------------------------------------
# required_key — ticket-371
# ------------------------------------------------------------------


def test_required_key_skips_first_object_without_key() -> None:
    """With required_key, a leading JSON object that lacks the key is skipped."""
    first = {"project_id": "abc"}
    verdict_obj = {"criteria": [{"criterion": "x", "passed": True}], "feedback": "ok"}
    text = json.dumps(first) + "\n\nSome prose.\n\n" + json.dumps(verdict_obj)

    result = extract_json(text, required_key="criteria")

    assert result == verdict_obj


def test_required_key_skips_json_block_without_key() -> None:
    """With required_key, a ```json block without the key is skipped, the next block wins."""
    first = {"project_id": "abc"}
    verdict_obj = {"criteria": [{"criterion": "y", "passed": False}], "feedback": "bad"}
    text = (
        f"```json\n{json.dumps(first)}\n```\n\n"
        "Some prose.\n\n"
        f"```json\n{json.dumps(verdict_obj)}\n```"
    )

    result = extract_json(text, required_key="criteria")

    assert result == verdict_obj


def test_without_required_key_returns_first_object() -> None:
    """Without required_key, the first JSON object is always returned even if a later
    one would contain a desired key."""
    first = {"project_id": "abc"}
    second = {"criteria": [{"criterion": "x", "passed": True}]}
    text = json.dumps(first) + "\n\n" + json.dumps(second)

    result = extract_json(text)

    assert result == first


def test_required_key_returns_none_when_no_object_has_key() -> None:
    """With required_key, None is returned when no object contains that key."""
    text = json.dumps({"project_id": "abc"}) + " " + json.dumps({"issues": []})

    result = extract_json(text, required_key="verdict")

    assert result is None


# ------------------------------------------------------------------
# Barres obliques inverses non échappées — ticket-376
# ------------------------------------------------------------------


def test_unescaped_backslash_in_string_is_fixed() -> None:
    """A JSON object whose string contains an invalid escape (\\x) is still decoded.

    Mirrors the exact criterion from ticket-376.
    """
    # \x n'est pas un échappement JSON valide : le décodeur doit doubler le \
    # puis retenter, et rendre quand même le verdict.
    text = '{"verdict": "PASS", "summary": "refuse ..\\x"}'
    result = extract_json(text, required_key="verdict")
    assert result is not None
    assert result["verdict"] == "PASS"


def test_valid_json_escapes_not_doubled() -> None:
    """A valid JSON object containing \\n and \\uXXXX is decoded as-is, without doubling."""
    # Ces séquences sont valides ; elles ne doivent pas être touchées par le
    # correcteur, et les valeurs décodées doivent être les caractères réels.
    text = '{"message": "line1\\nline2", "char": "\\u0041"}'
    result = extract_json(text)
    assert result is not None
    assert result["message"] == "line1\nline2"
    assert result["char"] == "A"


def test_broken_json_missing_brace_still_returns_none() -> None:
    """A JSON object broken by a missing brace is still None after the backslash retry."""
    result = extract_json('{"key": "value", "nested": {"a": 1')
    assert result is None


def test_valid_escaped_backslash_survives_the_fix_of_an_invalid_one() -> None:
    r"""An escaped backslash before a letter is kept when another backslash is fixed.

    Le texte JSON contient `a\\p` (barre échappée puis `p`, valide) et `..\x`
    (invalide). Doubler chaque barre isolément cassait la première séquence.
    """
    texte = r'{"verdict": "PASS", "ok": "a\\p", "bad": "..\x"}'
    result = extract_json(texte, required_key="verdict")
    assert result is not None
    assert result["verdict"] == "PASS"
    assert result["ok"] == r"a\p"
    assert result["bad"] == r"..\x"
