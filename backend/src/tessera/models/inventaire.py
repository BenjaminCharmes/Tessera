"""Ce que l'inventaire des apps rend — ticket-416 et ticket-435."""
from typing import Literal

from pydantic import BaseModel


class AppEnCours(BaseModel):
    """One running app of a project."""

    project_id: str
    project_name: str
    nom: str
    origine: Literal["tessera", "externe"]
    pid: int
    ports: list[int]
    demarre_a: str | None
    memoire_mo: float


class PortOccupe(BaseModel):
    """A port a project declares, held by a program that is not the project's.

    Volontairement sans pid : ce n'est pas une app du projet, il n'y a rien à
    arrêter, et aucun identifiant de processus n'est exposé qui pourrait l'être.
    """

    project_id: str
    project_name: str
    nom: str
    port: int
    message: str

    @classmethod
    def de(
        cls, project_id: str, project_name: str, nom: str, port: int
    ) -> "PortOccupe":
        return cls(
            project_id=project_id,
            project_name=project_name,
            nom=nom,
            port=port,
            message=(
                f"port {port} déclaré par {project_name}, "
                "occupé par un autre programme"
            ),
        )


class Inventaire(BaseModel):
    """Everything the machine shows about the projects' ports."""

    apps: list[AppEnCours]
    ports_occupes: list[PortOccupe]
