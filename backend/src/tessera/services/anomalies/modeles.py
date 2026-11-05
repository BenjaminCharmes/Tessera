"""The anomaly model — ticket-834 (ADR-078).

Une anomalie est un constat, jamais un ordre : elle dit qu'un run sort de
l'ordinaire, et c'est tout. Les six règles sont décrites dans la spec
`2026-11-05-detecteur-d-anomalies-design.md`.
"""
from typing import Literal

from pydantic import BaseModel, Field

Regle = Literal[
    "outil_repete",
    "etape_longue",
    "silence",
    "cout_anormal",
    "tours_de_revue",
    "blocages_identiques",
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
