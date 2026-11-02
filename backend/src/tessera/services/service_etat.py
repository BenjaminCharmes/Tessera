"""Response models for the project services routes — ticket-679.

`ServiceEtat` is the one description of a service's state: `Service.en_dict()`
derives from it and the routes declare it as their `response_model`. The front
mirrors it as `ServiceActif` in `types/api.ts`; a test compares both key sets.
"""
from pydantic import BaseModel


class ServiceEtat(BaseModel):
    """State of one declared or launched service (field order is the JSON order)."""

    nom: str
    project_id: str
    pid: int | None
    demarre_a: str
    en_cours: bool
    code_de_sortie: int | None
    sortie: list[str]
    arrete_a_la_main: bool


class ServicesDemarres(BaseModel):
    """Body of `POST /services/start`."""

    services: list[ServiceEtat]


class ServicesArretes(BaseModel):
    """Body of `POST /services/stop`."""

    arretes: int
