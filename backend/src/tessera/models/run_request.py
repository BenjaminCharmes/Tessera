"""Corps de `POST /orchestrator/run` et sa réponse — sortis du routeur (ticket-864)."""
from pydantic import BaseModel, Field, field_validator

from tessera.utils.project_id import validate_project_id


class RunRequest(BaseModel):
    project_id: str
    #: Optionnel depuis ticket-128 : une file porte `ticket_ids`, un run
    #: autonome ne porte ni l'un ni l'autre.
    ticket_id: str | None = None
    ticket_ids: list[str] = Field(default_factory=list)
    mode: str = "single"
    max_tickets: int = 5
    depuis_github: bool = False
    #: Plafond de dépense explicite d'une file (ticket-383) : remplace le calcul
    #: `run_max_budget_usd × nombre de tickets`. Strictement positif — 0
    #: voudrait dire « sans plafond » et permettrait à tout appelant de
    #: lever la borne. None : calcul par défaut. Ignoré hors mode file.
    budget_usd: float | None = Field(default=None, gt=0)
    #: Passe outre les manques relevés avant le départ (ticket-477) : ils sont
    #: journalisés, le run démarre quand même.
    force: bool = False
    #: Mode « pressé » (ticket-578) : un rôle qui déclare un `fallback` est
    #: construit directement avec lui, sans tenter le principal. Faux par
    #: défaut : le réglage du manifeste économise le quota.
    rapide: bool = False

    @field_validator("project_id")
    @classmethod
    def _check_project_id(cls, v: str) -> str:
        if not validate_project_id(v):
            raise ValueError(f"project_id invalide : {v!r}")
        return v


class RunStarted(BaseModel):
    """What POST /run answers: the run started, here is how to watch it."""

    run_id: str
    #: Une revue de projet rend sa fiche de synthèse et ce qu'elle peut coûter,
    #: avant que le run ne parte (ticket-864, ADR-020). Vides hors revue.
    ticket_id: str | None = None
    plafond_usd: float | None = None
    cout_estime_usd: float | None = None
