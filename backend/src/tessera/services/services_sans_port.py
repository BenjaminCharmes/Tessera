"""Les services déclarés qui n'écoutent aucun port — ticket-438.

Une app `externe` se trouve d'ordinaire par le port qu'elle écoute. Un worker
n'en a pas : on le cherche par sa ligne de commande, et on ne l'accepte que si
le processus appartient au projet (`appartient_au_projet`). Les deux critères
sont cumulés : `python -m app.worker` existe dans plusieurs projets, et la
signature seule prendrait celui de l'un pour celui de l'autre.
"""
from pathlib import Path

from tessera.services.attribution_processus import appartient_au_projet
from tessera.services.project_loader import load_services_config
from tessera.services.signature_commande import commande_porte, signature
from tessera.services.sonde_systeme import InfoProcessus


def _signatures(racine: Path) -> list[tuple[str, str]]:
    """(nom du service, signature) pour chaque service déclaré reconnaissable."""
    trouvees: list[tuple[str, str]] = []
    for declare in load_services_config(racine):
        sig = signature(declare["commande"])
        if sig is not None:
            trouvees.append((declare["nom"], sig))
    return trouvees


def _nom_du_service(
    info: InfoProcessus, signatures: list[tuple[str, str]]
) -> str | None:
    return next((nom for nom, sig in signatures if commande_porte(sig, info)), None)


def processus_sans_port(
    racine: Path, procs: dict[int, InfoProcessus], exclus: set[int]
) -> list[tuple[str, int]]:
    """(service, pid) of the project's declared services found by command line.

    Seule la racine de chaque arbre est rendue : un lanceur et son enfant
    portent la même commande, et ne sont qu'une app. `exclus` écarte ce qui
    est déjà compté ailleurs.
    """
    signatures = _signatures(racine)
    if not signatures:
        return []
    candidats: dict[int, str] = {}
    for pid, info in procs.items():
        nom = _nom_du_service(info, signatures)
        if pid not in exclus and nom is not None and appartient_au_projet(pid, racine, procs):
            candidats[pid] = nom
    return sorted(
        ((nom, pid) for pid, nom in candidats.items() if procs[pid].ppid not in candidats),
        key=lambda t: t[1],
    )
