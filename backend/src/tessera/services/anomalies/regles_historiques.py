"""Rules judged against the history of the project — tickets 836 to 838 (ADR-078).

Pures : l'historique (médianes, derniers runs) est lu par l'appelant.
"""
from collections.abc import Sequence
from datetime import datetime
from statistics import median

from tessera.services.anomalies.modeles import Anomalie, Etape


def mediane_si_assez(echantillon: Sequence[float], minimum: int = 10) -> float | None:
    """Median of the sample, or None below `minimum` values: too few to judge."""
    if len(echantillon) < minimum:
        return None
    return float(median(echantillon))


def etape_longue(
    etape: Etape,
    maintenant: datetime,
    passees_s: Sequence[float],
    *,
    ticket_id: str,
    plancher_s: float = 300.0,
    facteur: float = 3.0,
    minimum: int = 10,
) -> Anomalie | None:
    """An open stage lasting more than `max(facteur x median, plancher_s)`.

    Le plancher évite qu'un audit médian à 20 s n'alerte à 60 s.
    """
    if etape.fin is not None or etape.abandonnee:
        return None
    mediane = mediane_si_assez(passees_s, minimum)
    if mediane is None:
        return None
    seuil = max(facteur * mediane, plancher_s)
    duree = (maintenant - etape.debut).total_seconds()
    if duree <= seuil:
        return None
    return Anomalie(
        regle="etape_longue",
        cle=f"etape_longue:{etape.nom}:{etape.debut.isoformat()}",
        ticket_id=ticket_id,
        message=(
            f"L'étape {etape.nom} dure depuis {int(duree // 60)} min, "
            f"pour une médiane de {int(mediane // 60)} min."
        ),
        mesure=duree,
        seuil=seuil,
        unite="s",
        etape=etape.nom,
        agent=etape.agent,
    )
