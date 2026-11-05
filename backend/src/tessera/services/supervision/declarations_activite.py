"""Les services d'un projet qui déclarent un fichier d'activité — ticket-671.

La déclaration est un geste humain dans `agents.json` (ADR-027, ADR-064) :
Tessera la lit, ne l'écrit jamais.
"""
from pathlib import Path

from pydantic import ValidationError

from tessera.models.agent import ServiceDeclare
from tessera.services.manifeste import lire_liste


def services_avec_activite(racine: Path) -> list[ServiceDeclare]:
    """The services of `agents.json` that declare an activity file.

    Une entrée mal formée est ignorée, comme le fait `load_services_config` :
    un `agents.json` absent ou illisible ne déclare rien.
    """
    bruts = lire_liste(racine, "services") or []
    declares: list[ServiceDeclare] = []
    for brut in bruts:
        try:
            declare = ServiceDeclare.model_validate(brut)
        except ValidationError:
            continue
        if declare.activite:
            declares.append(declare)
    return declares
