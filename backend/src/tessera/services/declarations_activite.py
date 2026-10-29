"""Les services d'un projet qui déclarent un fichier d'activité — ticket-671.

La déclaration est un geste humain dans `agents.json` (ADR-027, ADR-064) :
Tessera la lit, ne l'écrit jamais.
"""
import json
from pathlib import Path

from pydantic import ValidationError

from tessera.models.agent import ServiceDeclare


def services_avec_activite(racine: Path) -> list[ServiceDeclare]:
    """The services of `agents.json` that declare an activity file.

    Une entrée mal formée est ignorée, comme le fait `load_services_config` :
    un `agents.json` absent ou illisible ne déclare rien.
    """
    try:
        data = json.loads((racine / "agents.json").read_text(encoding="utf-8"))
        bruts = data.get("services") or []
    except (OSError, ValueError, AttributeError):
        return []
    if not isinstance(bruts, list):
        return []
    declares: list[ServiceDeclare] = []
    for brut in bruts:
        try:
            declare = ServiceDeclare.model_validate(brut)
        except ValidationError:
            continue
        if declare.activite:
            declares.append(declare)
    return declares
