"""Direct anomaly rules — ticket-835 (ADR-078).

Pures : ni I/O ni horloge, le « maintenant » est un paramètre. Les seuils
viennent de `settings`, lus par l'appelant.
"""
from collections.abc import Sequence
from datetime import datetime

from tessera.services.anomalies.modeles import Anomalie, AppelOutil


def _serie_finale(appels: Sequence[AppelOutil], seuil: int) -> list[AppelOutil]:
    """The latest run of consecutive identical calls that reaches `seuil`, else empty."""
    meilleure: list[AppelOutil] = []
    courante: list[AppelOutil] = []
    for appel in appels:
        if courante and (
            (appel.agent, appel.tool, appel.input_hash)
            == (courante[0].agent, courante[0].tool, courante[0].input_hash)
        ):
            courante.append(appel)
        else:
            courante = [appel]
        if len(courante) >= seuil:
            meilleure = list(courante)
    return meilleure


def outil_repete(appels: Sequence[AppelOutil], seuil: int = 4) -> Anomalie | None:
    """A series of identical tool calls by the same agent, `seuil` long at least."""
    serie = _serie_finale(appels, seuil)
    if not serie:
        return None
    premier = serie[0]
    qui = premier.agent or "L'agent"
    # Le message nomme l'outil, jamais son `input` : un chemin ou un jeton peut s'y trouver.
    return Anomalie(
        regle="outil_repete",
        cle=f"outil_repete:{premier.id}",
        ticket_id=premier.ticket_id,
        message=(
            f"{qui} a appelé {premier.tool} "
            f"{len(serie)} fois de suite avec les mêmes arguments."
        )[:200],
        mesure=float(len(serie)),
        seuil=float(seuil),
        unite="appels",
        agent=premier.agent,
    )


def silence(
    dernier: datetime | None,
    maintenant: datetime,
    *,
    ticket_id: str,
    seuil_s: float = 900.0,
    exempte: bool = False,
) -> Anomalie | None:
    """No event, tokens included, for `seuil_s` seconds."""
    if dernier is None or exempte:
        return None
    ecart = (maintenant - dernier).total_seconds()
    if ecart < seuil_s:
        return None
    return Anomalie(
        regle="silence",
        cle=f"silence:{dernier.isoformat()}",
        ticket_id=ticket_id,
        message=f"Aucun événement depuis {int(ecart // 60)} min sur ce run.",
        mesure=ecart,
        seuil=seuil_s,
        unite="s",
    )


def tours_de_revue(tour: int, ticket_id: str, seuil: int = 3) -> Anomalie | None:
    """The review round reached `seuil`: the last attempt after two refusals."""
    if tour < seuil:
        return None
    return Anomalie(
        regle="tours_de_revue",
        cle=f"tours:{ticket_id}",
        ticket_id=ticket_id,
        message=f"Le tour de revue {tour} est atteint : c'est la dernière tentative.",
        mesure=float(tour),
        seuil=float(seuil),
        unite="tours",
    )
