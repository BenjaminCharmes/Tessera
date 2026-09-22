"""One pipeline at a time per project — ticket-055, extended by ticket-121.

Born in `chat_suggestion.py` for `/chat/run` alone. Two `POST
/orchestrator/run` on the same project both passed `ensure_clean_tree`, then
the second `create_branch` switched the tree under the first coder. The lock
now guards every entry point, so it lives in its own module with a single
process-wide instance that the routers share.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class RunAlreadyInProgress(Exception):
    """A pipeline is already running on this project."""

    def __init__(self, project_id: str, ticket_id: str | None = None) -> None:
        self.project_id = project_id
        self.ticket_id = ticket_id
        en_cours = f" ({ticket_id})" if ticket_id else ""
        super().__init__(
            f"Un pipeline tourne déjà sur le projet '{project_id}'{en_cours}. "
            "Deux exécutions simultanées se marcheraient dessus dans le même "
            "arbre de travail : attends la fin de celle en cours."
        )


class RunLock:
    """One pipeline at a time per project.

    Deliberately not a real mutex: a second attempt must *fail loudly* rather
    than queue silently. Someone who clicks twice wants to know the first is
    still running, not to have a second run start ten minutes later.

    En mémoire du process : suffisant pour un backend local, sans effet
    entre deux backends qui partageraient un dépôt (ticket-121, hors
    périmètre).
    """

    def __init__(self) -> None:
        self._running: dict[str, str | None] = {}

    def is_running(self, project_id: str) -> bool:
        return project_id in self._running

    def ticket_en_cours(self, project_id: str) -> str | None:
        """The ticket running on `project_id`, or None when the project is free."""
        return self._running.get(project_id)

    @asynccontextmanager
    async def acquire(
        self, project_id: str, ticket_id: str | None = None
    ) -> AsyncIterator[None]:
        if project_id in self._running:
            raise RunAlreadyInProgress(project_id, self._running[project_id])
        self._running[project_id] = ticket_id
        try:
            yield
        finally:
            # `finally` et non le chemin nominal : un pipeline qui échoue doit
            # laisser le projet utilisable, pas verrouillé jusqu'au
            # redémarrage du backend.
            self._running.pop(project_id, None)


#: L'instance que tous les routeurs partagent. Deux instances seraient deux
#: verrous, et le chat ne verrait pas le run lancé depuis le tableau.
RUN_LOCK = RunLock()
