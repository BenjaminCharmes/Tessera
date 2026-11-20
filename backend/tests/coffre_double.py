"""An in-memory ``Coffre`` for tests: no test reaches the real vault."""
from collections.abc import Callable

from tessera.coffre import NOMS_SECRETS


class CoffreDouble:
    """Dict-backed vault; ``erreur`` makes every call raise it."""

    def __init__(
        self, entrees: dict[str, str] | None = None, erreur: Exception | None = None
    ) -> None:
        self.entrees: dict[str, str] = dict(entrees or {})
        self.erreur = erreur
        self.appels = 0

    def _appel(self) -> None:
        self.appels += 1
        if self.erreur is not None:
            raise self.erreur

    def lire(self, nom: str) -> str | None:
        """Return the stored value, or None."""
        self._appel()
        return self.entrees.get(nom)

    def ecrire(self, nom: str, valeur: str) -> None:
        """Store a value."""
        self._appel()
        self.entrees[nom] = valeur

    def supprimer(self, nom: str) -> None:
        """Remove an entry, missing or not."""
        self._appel()
        self.entrees.pop(nom, None)

    def presents(self) -> frozenset[str]:
        """Return the known names the double holds."""
        self._appel()
        return frozenset(nom for nom in NOMS_SECRETS if nom in self.entrees)


def ouvrant(
    coffre: CoffreDouble | None = None, erreur: Exception | None = None
) -> Callable[[], CoffreDouble]:
    """Return a stand-in for ``coffre_du_systeme`` that hands back ``coffre``."""

    def ouvrir() -> CoffreDouble:
        if erreur is not None:
            raise erreur
        assert coffre is not None
        return coffre

    return ouvrir
