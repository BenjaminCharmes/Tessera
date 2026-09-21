"""Passer de la conversation au pipeline — ticket-055.

Trois pièces, chacune répondant à une contrainte posée par le ticket :

- **La suggestion.** L'agent du chat n'a aucun outil qui lance un pipeline : il
  émet un marqueur que l'UI rend sous forme de bouton. Un agent
  conversationnel qui déclencherait seul l'écriture de plusieurs fichiers dans
  un dépôt est exactement ce que ticket-048 a refusé.
- **Le résumé.** Sans lui, le codeur reçoit le ticket nu et tout le
  raisonnement de la discussion est perdu. Il est borné : le contexte projet
  est déjà volumineux.
- **Le verrou.** Deux pipelines concurrents sur le même dépôt se marcheraient
  dessus dans le même arbre de travail, ce qui violerait l'isolation par
  branche d'ADR-018.
"""
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from tessera.services.database import ChatMessageRow

# Le marqueur que le prompt du chat demande à l'agent d'émettre. C'est un
# protocole entre l'agent et l'UI, jamais du contenu destiné à l'utilisateur.
_MARKER = re.compile(r"^SUGGESTION_PIPELINE:\s*(\S+)\s*$", re.MULTILINE)

# Un id de ticket et rien d'autre. Le marqueur vient d'un agent : il ne doit
# pas pouvoir injecter un chemin relatif ni un argument de commande.
_TICKET_ID = re.compile(r"^ticket-[a-z0-9-]{1,40}$")

_DEFAULT_SUMMARY_CHARS = 4000


@dataclass(frozen=True)
class PipelineSuggestion:
    """Un lancement proposé par l'agent, que l'utilisateur seul peut accepter."""

    ticket_id: str


def parse_pipeline_suggestion(content: str) -> PipelineSuggestion | None:
    """Extract the last suggestion from an agent reply, if it carries a valid one."""
    matches = _MARKER.findall(content or "")
    if not matches:
        return None
    # La dernière l'emporte : si l'agent s'est repris, c'est son dernier mot.
    candidate = matches[-1].strip()
    if not _TICKET_ID.match(candidate):
        return None
    return PipelineSuggestion(ticket_id=candidate)


def strip_suggestion_marker(content: str) -> str:
    """Remove the marker lines — the user sees a button, not a protocol line."""
    return _MARKER.sub("", content or "")


def summarize_conversation(
    history: list[ChatMessageRow], max_chars: int = _DEFAULT_SUMMARY_CHARS
) -> str:
    """Render the discussion for the coder's prompt, most recent turns kept.

    Truncating from the *start* rather than the end is deliberate: the
    decisions that matter are the ones the conversation arrived at, not the
    ones it opened with.
    """
    if not history:
        return ""

    lines = [
        f"**{'Utilisateur' if m.role == 'user' else 'Assistant'}** : {m.content}"
        for m in history
    ]
    summary = "\n\n".join(lines)
    if len(summary) <= max_chars:
        return summary

    truncated = summary[-max_chars:]
    notice = "_(début de la conversation omis)_\n\n"
    return notice + truncated[len(notice):]


class RunAlreadyInProgress(Exception):
    """A pipeline is already running on this project."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        super().__init__(
            f"Un pipeline tourne déjà sur le projet '{project_id}'. "
            "Deux exécutions simultanées se marcheraient dessus dans le même "
            "arbre de travail : attends la fin de celle en cours."
        )


class RunLock:
    """One pipeline at a time per project.

    Deliberately not a real mutex: a second attempt must *fail loudly* rather
    than queue silently. Someone who clicks twice wants to know the first is
    still running, not to have a second run start ten minutes later.
    """

    def __init__(self) -> None:
        self._running: set[str] = set()

    def is_running(self, project_id: str) -> bool:
        return project_id in self._running

    @asynccontextmanager
    async def acquire(self, project_id: str) -> AsyncIterator[None]:
        if project_id in self._running:
            raise RunAlreadyInProgress(project_id)
        self._running.add(project_id)
        try:
            yield
        finally:
            # `finally` et non le chemin nominal : un pipeline qui échoue doit
            # laisser le projet utilisable, pas verrouillé jusqu'au
            # redémarrage du backend.
            self._running.discard(project_id)
