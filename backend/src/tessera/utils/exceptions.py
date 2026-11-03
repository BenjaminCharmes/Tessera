"""Décrire une exception de façon lisible, même quand elle n'a pas de message."""


def decrire_exception(exc: BaseException) -> str:
    """Return a readable, never-empty description of an exception.

    `str(exc)` is empty for `TimeoutError()` and several network errors; the
    type name is then the only information left. A message that already
    contains the type name is kept as is, to avoid ``Foo: Foo: ...``.
    """
    nom = type(exc).__name__
    message = str(exc).strip()
    if not message:
        return nom
    if nom in message:
        return message
    return f"{nom}: {message}"
