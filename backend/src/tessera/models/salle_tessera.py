"""What the Tessera server room shows — ticket-726."""
from pydantic import BaseModel


class ProcessusDeTessera(BaseModel):
    """One of Tessera's own servers: the backend, or the Vite that serves the frontend."""

    nom: str
    port: int
    #: `None` when nothing listens on the port.
    pid: int | None
    memoire_mo: float
    demarre_a: str | None


class EtatOllama(BaseModel):
    """The local model server, as the circuit breaker of ticket-380 sees it."""

    url: str
    #: Seconds left before Ollama takes calls again ; `None` when it does now.
    refroidissement_s: float | None


class RunVivant(BaseModel):
    """A run the registry holds open, with its queue position when it is a queue."""

    project_id: str
    ticket_id: str | None
    agent: str | None
    etape: str | None
    file_index: int
    file_total: int
    #: The tickets left in the queue, in order.
    suivants: list[str]


class LigneDeJournal(BaseModel):
    """A line of `tessera.log`, reduced to its event: no path, no payload."""

    ts: str | None
    niveau: str
    evenement: str
    ticket_id: str | None
    role: str | None


class SalleTessera(BaseModel):
    """Everything the room draws ; each field is a fact read at request time (ADR-058)."""

    processus: list[ProcessusDeTessera]
    ollama: EtatOllama
    runs: list[RunVivant]
    #: Project id -> ticket ids whose PR waits for CI or merge in the CIWatcher.
    ci_en_attente: dict[str, list[str]]
    journal: list[LigneDeJournal]
    base_mo: float
    worktrees: int
