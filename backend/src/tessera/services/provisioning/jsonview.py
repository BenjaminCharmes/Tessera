"""Narrowing helpers for decoded JSON — ticket-466.

An API body is untyped; these keep the clients free of ``Any`` by turning an
unexpected shape into an empty value instead of an exception.
"""


def as_dict(value: object) -> dict[str, object]:
    """Return ``value`` when it is an object, an empty dict otherwise."""
    return value if isinstance(value, dict) else {}


def as_list(value: object) -> list[object]:
    """Return ``value`` when it is an array, an empty list otherwise."""
    return value if isinstance(value, list) else []


def as_str(value: object) -> str:
    """Return ``value`` when it is a string, an empty string otherwise."""
    return value if isinstance(value, str) else ""
