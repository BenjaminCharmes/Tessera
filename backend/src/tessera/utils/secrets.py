"""Registry of the secrets the backend must never print — ADR-053.

Two sources feed it: the online-service tokens of ``Settings`` (registered when
the logger module loads) and any secret an API hands back while a run executes
(``register``). The logger replaces every registered value by ``***``, and the
push gate treats them as forbidden terms.
"""
import json
import threading
from collections.abc import Iterable

#: What replaces a secret in a log line.
MASQUE = "***"


class SecretRegistry:
    """Thread-safe set of secret values, with masking of free text."""

    def __init__(self) -> None:
        self._valeurs: set[str] = set()
        self._verrou = threading.Lock()

    def register(self, valeur: str) -> None:
        """Add one secret; an empty or blank value is ignored."""
        if not valeur.strip():
            return
        with self._verrou:
            self._valeurs.add(valeur)

    def register_all(self, valeurs: Iterable[str]) -> None:
        """Add several secrets."""
        for valeur in valeurs:
            self.register(valeur)

    def valeurs(self) -> frozenset[str]:
        """Return a snapshot of the registered values."""
        with self._verrou:
            return frozenset(self._valeurs)

    def clear(self) -> None:
        """Forget every secret (tests only)."""
        with self._verrou:
            self._valeurs.clear()

    def mask(self, texte: str) -> str:
        """Replace each registered value in ``texte`` by ``***``.

        The JSON-escaped form is masked too: the log formatter serialises its
        payload, and a value holding a quote or a backslash would otherwise
        survive in its escaped shape. Longest values go first, so a secret that
        contains another one is masked whole.
        """
        formes: set[str] = set()
        for valeur in self.valeurs():
            formes.add(valeur)
            formes.add(json.dumps(valeur)[1:-1])
        for forme in sorted(formes, key=len, reverse=True):
            if forme:
                texte = texte.replace(forme, MASQUE)
        return texte


#: The process-wide registry.
SECRETS = SecretRegistry()
