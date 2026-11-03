"""Les chaînes de vérification du dépôt — ticket-584.

`scripts/verifier.py` découpe le dépôt en chaînes : `backend/` et `scripts/`
passent par pytest et mypy, `frontend/` par tsc, eslint et vitest, le reste par
rien. Les préfixes qui les définissent ne vivent qu'ici côté backend ; un test
les confronte à `scripts/verifier.py`, qui reste protégé (ADR-027) et que l'on
lit sans le modifier.
"""
from collections.abc import Iterable

#: Chaîne pytest + mypy. `scripts/` y compte : la commande de test y vit.
PREFIXES_BACKEND: tuple[str, ...] = ("backend/", "scripts/")
#: Chaîne tsc + eslint + vitest.
PREFIXES_FRONTEND: tuple[str, ...] = ("frontend/",)

CHAINES: dict[str, tuple[str, ...]] = {
    "backend": PREFIXES_BACKEND,
    "frontend": PREFIXES_FRONTEND,
}


def chaines_touchees(chemins: Iterable[str]) -> frozenset[str]:
    """Names of the verifier chains that at least one of the paths falls in."""
    return frozenset(
        nom
        for nom, prefixes in CHAINES.items()
        if any(chemin.startswith(prefixes) for chemin in chemins)
    )


def chaine_commune(base: Iterable[str], branche: Iterable[str]) -> bool:
    """True when the base and the branch both touch a chain of the verifier."""
    return bool(chaines_touchees(base) & chaines_touchees(branche))
