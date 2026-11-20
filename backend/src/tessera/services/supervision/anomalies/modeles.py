"""The anomaly model — ticket-834 (ADR-078).

Une anomalie est un constat, jamais un ordre : elle dit qu'un run sort de
l'ordinaire, et c'est tout. Les six règles sont décrites dans la spec
`2026-11-05-detecteur-d-anomalies-design.md`.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Regle = Literal[
    "outil_repete",
    "etape_longue",
    "silence",
    "cout_anormal",
    "tours_de_revue",
    "blocages_identiques",
    "documentation_refusee_en_serie",
]

Unite = Literal["appels", "s", "usd", "pourcent", "tours", "runs"]

#: Longueur maximale du message d'une anomalie.
MESSAGE_MAX = 200


class Anomalie(BaseModel):
    """One anomaly found on the current ticket of a live run."""

    regle: Regle
    #: Clé de dédoublonnage : un épisode, pas une règle.
    cle: str
    ticket_id: str
    #: Français, sans jamais l'`input` d'un outil (ADR-053).
    message: str = Field(max_length=MESSAGE_MAX)
    mesure: float
    seuil: float
    unite: Unite
    etape: str | None = None
    agent: str | None = None


@dataclass(frozen=True)
class AppelOutil:
    """One tool call of an agent, reduced to what compares: never its input."""

    id: int
    agent: str | None
    tool: str
    #: Hachage du JSON canonique de l'`input` : deux appels identiques ont le
    #: même, et le contenu (chemin, jeton) ne quitte jamais la lecture (ADR-053).
    input_hash: str
    ticket_id: str


@dataclass(frozen=True)
class EvenementLu:
    """A persisted event, reduced to what the stage reading needs."""

    type: str
    agent: str | None
    ts: datetime


@dataclass(frozen=True)
class Etape:
    """A stage of a run, read from its start and end events."""

    nom: str
    debut: datetime
    fin: datetime | None
    agent: str | None
    #: Rouverte par un nouveau début sans fin entre les deux : ni mesure, ni
    #: échantillon. Le testeur figé n'entre donc pas dans la médiane qui le juge.
    abandonnee: bool = False


@dataclass(frozen=True)
class LigneOuverte:
    """The unfinished `single` row of a ticket in `pipeline_runs`."""

    id: str
    ticket_id: str
    started_at: str


@dataclass(frozen=True)
class RunFini:
    """A finished `single` row of `pipeline_runs`, reduced to what the blocks rule compares."""

    id: str
    ticket_id: str
    final_status: str | None
    arret: str | None


@dataclass(frozen=True)
class LotDoc:
    """One `doc_updated` event, reduced to counts: never the text of a refusal."""

    id: int
    fichiers: int
    refus: int
