"""Lit le fichier d'activité qu'un produit écrit — ticket-671, ADR-064.

Échec fermé : à la moindre anomalie, aucun agent. Tessera n'écrit jamais ce
fichier et n'interroge aucune route du produit.
"""
from datetime import datetime
from pathlib import Path

from tessera.models.activite import AgentDeProduit, FichierActivite
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

TAILLE_MAX_OCTETS = 16 * 1024
PEREMPTION_S = 30
AVANCE_MAX_S = 5


class ActiviteRefusee(Exception):
    """Le fichier d'activité ne respecte pas le contrat."""


def _resoudre(racine: Path, chemin: str) -> Path:
    """Le fichier désigné, refusé s'il sort du projet une fois les liens suivis."""
    racine_r = racine.resolve()
    cible = (racine_r / chemin).resolve()
    if not cible.is_relative_to(racine_r):
        raise ActiviteRefusee("path leaves the project")
    if not cible.is_file():
        raise ActiviteRefusee("not a regular file")
    return cible


def _lire_borne(cible: Path) -> bytes:
    """Le contenu, lu au plus `TAILLE_MAX_OCTETS` : jamais un fichier entier."""
    with cible.open("rb") as f:
        brut = f.read(TAILLE_MAX_OCTETS + 1)
    if len(brut) > TAILLE_MAX_OCTETS:
        raise ActiviteRefusee("file too large")
    return brut


def _verifier_la_date(fichier: FichierActivite, maintenant: datetime) -> None:
    age_s = (maintenant - fichier.maj).total_seconds()
    if age_s > PEREMPTION_S:
        raise ActiviteRefusee("file is stale")
    if age_s < -AVANCE_MAX_S:
        raise ActiviteRefusee("file is dated in the future")


def lire_activite(
    racine: Path, chemin: str, maintenant: datetime
) -> list[AgentDeProduit]:
    """The agents of an activity file, or `[]` on any failure. Never raises.

    `chemin` est relatif à `racine` ; `maintenant` est aware (UTC). Le journal
    ne reçoit que la cause, jamais le contenu du fichier.
    """
    try:
        brut = _lire_borne(_resoudre(racine, chemin))
        # Strict : une date n'est qu'une chaîne ISO, jamais un nombre de secondes.
        fichier = FichierActivite.model_validate_json(brut, strict=True)
        _verifier_la_date(fichier, maintenant)
    except Exception as exc:  # noqa: BLE001 — le contrat : jamais de levée
        _logger.debug("activite_refusee", extra={"cause": type(exc).__name__})
        return []
    return fichier.agents
