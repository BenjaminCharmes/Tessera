"""One pipeline at a time per project — ticket-055, ticket-121, ticket-127.

Born in `chat_suggestion.py` for `/chat/run` alone. Two `POST
/orchestrator/run` on the same project both passed `ensure_clean_tree`, then
the second `create_branch` switched the tree under the first coder. The lock
now guards every entry point, so it lives in its own module with a single
process-wide instance that the routers share.

Depuis ticket-127 il ne tient plus son propre dictionnaire : il est une
**façade** sur `RunRegistry`, qui sait déjà ce qui tourne et depuis quand.
Deux structures décrivant « ce projet est-il occupé ? » divergeraient, et
c'est la supervision qui afficherait le faux (ADR-034).
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from tessera.services.run_registry import (
    RUN_REGISTRY,
    RunAlreadyInProgress,
    RunRegistry,
)

#: Ré-exportée : l'exception est levée par le registre, mais tout le code
#: appelant l'importe d'ici depuis ticket-055.
__all__ = ["RUN_LOCK", "RunAlreadyInProgress", "RunLock"]


class RunLock:
    """One pipeline at a time per project.

    Deliberately not a real mutex: a second attempt must *fail loudly* rather
    than queue silently. Someone who clicks twice wants to know the first is
    still running, not to have a second run start ten minutes later.

    En mémoire du process : suffisant pour un backend local, sans effet
    entre deux backends qui partageraient un dépôt (ticket-121, hors
    périmètre).
    """

    def __init__(self, registry: RunRegistry | None = None) -> None:
        # Un registre **propre** par défaut, et non `RUN_REGISTRY` : avant
        # ticket-127, un `RunLock()` construit à la main avait son propre
        # dictionnaire. Le faire retomber sur le registre partagé donnait à
        # deux verrous censés être indépendants le même état — invisible en
        # production, et en test un run laissé par le voisin fait échouer le
        # suivant. Le partage se déclare, il ne s'hérite pas.
        self._registry = registry if registry is not None else RunRegistry()

    def is_running(self, project_id: str) -> bool:
        return self._registry.projet_occupe(project_id)

    def ticket_en_cours(self, project_id: str) -> str | None:
        """The ticket running on `project_id`, or None when the project is free."""
        return self._registry.ticket_du_projet(project_id)

    @asynccontextmanager
    async def acquire(
        self, project_id: str, ticket_id: str | None = None
    ) -> AsyncIterator[None]:
        async with self._registry.acquire(project_id, ticket_id):
            yield


#: L'instance que tous les routeurs partagent. Deux instances seraient deux
#: verrous, et le chat ne verrait pas le run lancé depuis le tableau.
RUN_LOCK = RunLock(RUN_REGISTRY)
