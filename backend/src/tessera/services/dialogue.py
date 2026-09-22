"""Dialogue between the user and a pipeline run in progress — ticket-066.

Until now a run was a closed pipe: once started it went from the coder to the
last stage without ever handing back control. An agent that hit an ambiguity
decided alone, and its assumption only surfaced at commit time — usually after
it had written the wrong code.

Two directions, deliberately kept apart:

- **the agent asks** (`ask`) — the run suspends until the user answers;
- **the user interjects** (`interject`) — the message waits in a queue that a
  stage drains *between two agent turns*.

They must not be confused. A « by the way, remember the tests » sent while the
agent is asking « do we break the API? » would otherwise become the answer to
that question.

## Why a run never waits forever

ADR-018 makes the whole ticket queue depend on a clean tree at the start of
each run, and ADR-020 already forbids stopping in the middle of a ticket: a
suspended run is holding uncommitted work. So a question that goes unanswered
past `timeout_s` resolves on its own, and the agent is told to carry on *while
stating its assumption* — the assumption then travels in the run's report,
where it can be reviewed, instead of being invisible.

In autonomous mode nobody is watching, so a question does not even start the
clock: it resolves at once. Waiting an hour per question would otherwise burn a
whole overnight run on questions no one could ever answer.
"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Optional

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Ce que l'agent reçoit quand aucun humain n'a répondu — délai dépassé, ou
#: run autonome. Le texte est une consigne, pas un constat : il doit conduire
#: l'agent à décider *et à le dire*, pas à réessayer ni à abandonner.
STOP_ANSWER = (
    "Arrêt demandé par l'utilisateur. N'écris plus rien et termine ton tour "
    "immédiatement, en résumant en une phrase où tu en étais."
)

NO_HUMAN_ANSWER = (
    "Aucune réponse humaine n'est disponible. Poursuis sans attendre : "
    "choisis l'option la plus raisonnable, et énonce explicitement "
    "l'hypothèse que tu retiens dans ta réponse, afin qu'elle puisse être "
    "relue."
)


class DialogueChannel:
    """Les deux sens du dialogue pour un run, sans rien savoir du transport.

    Ni WebSocket, ni SDK, ni LLM ici : c'est ce qui rend la suspension, la
    reprise sur délai et le mode autonome testables sans lancer un run.
    """

    def __init__(
        self,
        timeout_s: float = 300.0,
        interactive: bool = True,
        on_question: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> None:
        self._timeout_s = timeout_s
        self._interactive = interactive
        # Le canal ignore tout du transport, mais quelqu'un doit prévenir
        # l'extérieur : une question posée sans événement ressemble, côté
        # utilisateur, à un run qui s'est figé de lui-même.
        self._on_question = on_question
        self._pending_question: str | None = None
        self._answer: asyncio.Future[str] | None = None
        # Signalé dès qu'une question est posée : l'UI (et les tests) doivent
        # pouvoir attendre la question plutôt que de scruter l'attribut.
        self._question_posed = asyncio.Event()
        self._mailbox: list[str] = []
        # L'arrêt passe par ce canal, qui est déjà le chemin par lequel
        # l'utilisateur parle à un run en cours : inventer un second transport
        # pour un seul booléen n'apporterait rien (ticket-069).
        self._stop_requested = False

    # -- côté agent ------------------------------------------------

    async def ask(self, question: str) -> str:
        """Pose une question et attend la réponse, sans jamais bloquer pour de bon."""
        if self._stop_requested:
            # Attendre ici retiendrait le run jusqu'au délai d'ADR-025 alors
            # qu'on vient justement de demander qu'il s'arrête.
            return STOP_ANSWER
        if not self._interactive:
            return NO_HUMAN_ANSWER

        loop = asyncio.get_running_loop()
        self._answer = loop.create_future()
        self._pending_question = question
        self._question_posed.set()
        if self._on_question is not None:
            await self._on_question(question)
        try:
            return await asyncio.wait_for(self._answer, timeout=self._timeout_s)
        except asyncio.TimeoutError:
            _logger.info("question_sans_reponse", extra={"question": question})
            return NO_HUMAN_ANSWER
        finally:
            self._pending_question = None
            self._answer = None
            self._question_posed.clear()

    def drain(self) -> list[str]:
        """Vide la boîte aux lettres — appelé entre deux tours d'agent."""
        messages, self._mailbox = self._mailbox, []
        return messages

    # -- côté utilisateur ------------------------------------------

    def answer(self, text: str) -> None:
        """Répond à la question en cours. Sans question en cours, ne fait rien."""
        if self._answer is None or self._answer.done():
            _logger.info("reponse_sans_question")
            return
        self._answer.set_result(text)

    def request_stop(self) -> None:
        """Demande l'arrêt du run. Débloque aussi une question en attente."""
        self._stop_requested = True
        if self._answer is not None and not self._answer.done():
            self._answer.set_result(STOP_ANSWER)

    def interject(self, text: str) -> None:
        """Dépose un message spontané, lu au prochain tour d'agent."""
        self._mailbox.append(text)

    # -- lecture ---------------------------------------------------

    @property
    def pending_question(self) -> str | None:
        return self._pending_question

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    @property
    def interactive(self) -> bool:
        return self._interactive

    async def wait_for_question(self) -> str:
        """Attend qu'une question soit posée, et la renvoie."""
        await self._question_posed.wait()
        return self._pending_question or ""
