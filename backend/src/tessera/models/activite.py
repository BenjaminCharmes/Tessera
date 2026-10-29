"""L'activité des agents d'un produit — ticket-671, ADR-064.

Le produit écrit le fichier, Tessera le lit : aucun champ inconnu n'est toléré,
tout ce qui sort du contrat fait refuser le fichier entier.
"""
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

NB_AGENTS_MAX = 12


class AgentDeProduit(BaseModel):
    """One agent of a product, as the product's activity file describes it."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9-]+$", min_length=1, max_length=40)
    nom: str = Field(min_length=1, max_length=40)
    etat: Literal["actif", "repos"]
    depuis: AwareDatetime | None = None
    #: Un nom d'étape, jamais un texte d'utilisateur.
    libelle: str | None = Field(default=None, max_length=80)


class FichierActivite(BaseModel):
    """The content of an activity file, version 1."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    maj: AwareDatetime
    agents: list[AgentDeProduit] = Field(max_length=NB_AGENTS_MAX)

    @model_validator(mode="after")
    def _ids_uniques(self) -> "FichierActivite":
        ids = [a.id for a in self.agents]
        if len(ids) != len(set(ids)):
            raise ValueError("agent id declared twice")
        return self


class ActiviteDeService(BaseModel):
    """The agents of one running service of a project."""

    project_id: str
    service: str
    agents: list[AgentDeProduit]
