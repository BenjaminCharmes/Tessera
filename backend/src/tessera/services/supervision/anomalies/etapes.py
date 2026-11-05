"""Stages of a run, read from events already persisted — ticket-836 (ADR-078).

Pure : aucune I/O, aucun événement de plus à émettre.
"""
from collections.abc import Sequence

from tessera.services.supervision.anomalies.modeles import Etape, EvenementLu

#: Étape → (type de début, types de fin). Les étapes d'agent (`codeur`,
#: `reviewer`, …) n'y figurent pas : elles s'écrivent `agent_started` /
#: `agent_done`, et l'étape porte le nom de l'agent.
ETAPES_NOMMEES: dict[str, tuple[str, tuple[str, ...]]] = {
    "tests": ("test_started", ("test_result",)),
    "securite": ("security_audit_started", ("security_audit_done",)),
    "validation": ("validation_started", ("validation_done",)),
    "documentation": ("documentation_started", ("doc_updated", "documentation_failed")),
    "livraison": ("livraison_started", ("livraison_done",)),
}

#: Les étapes qui n'émettent rien pendant qu'elles travaillent (ticket-587).
ETAPES_SILENCIEUSES: frozenset[str] = frozenset(ETAPES_NOMMEES)

_DEBUTS = {debut: nom for nom, (debut, _) in ETAPES_NOMMEES.items()}
_FINS = {fin: nom for nom, (_, fins) in ETAPES_NOMMEES.items() for fin in fins}

#: Tous les types d'événement qui bornent une étape.
TYPES_D_ETAPE: tuple[str, ...] = ("agent_started", "agent_done", *_DEBUTS, *_FINS)


def types_de_l_etape(nom: str) -> tuple[str, tuple[str, ...], str | None]:
    """Return (start type, end types, agent filter) of a stage name."""
    if nom in ETAPES_NOMMEES:
        debut, fins = ETAPES_NOMMEES[nom]
        return debut, fins, None
    return "agent_started", ("agent_done",), nom


def _classer(evenement: EvenementLu) -> tuple[str, bool, str | None] | None:
    """Return (stage name, is_start, agent) of an event, or None if it bounds no stage."""
    if evenement.type in ("agent_started", "agent_done"):
        if not evenement.agent:
            return None
        return evenement.agent, evenement.type == "agent_started", evenement.agent
    if evenement.type in _DEBUTS:
        return _DEBUTS[evenement.type], True, None
    if evenement.type in _FINS:
        return _FINS[evenement.type], False, None
    return None


def _abandonnee(etape: Etape) -> Etape:
    return Etape(nom=etape.nom, debut=etape.debut, fin=None, agent=etape.agent, abandonnee=True)


def etapes_depuis(evenements: Sequence[EvenementLu]) -> list[Etape]:
    """Pair start and end events into stages, open ones and abandoned ones included.

    Les événements sont dans l'ordre où ils ont été écrits. Deux étapes de nom
    différent se chevauchent sans se gêner (la revue et la validation).
    """
    etapes: list[Etape] = []
    ouvertes: dict[str, Etape] = {}
    for evenement in evenements:
        classe = _classer(evenement)
        if classe is None:
            continue
        nom, est_debut, agent = classe
        if est_debut:
            precedente = ouvertes.pop(nom, None)
            if precedente is not None:
                etapes.append(_abandonnee(precedente))
            ouvertes[nom] = Etape(nom=nom, debut=evenement.ts, fin=None, agent=agent)
        else:
            commencee = ouvertes.pop(nom, None)
            if commencee is not None:
                etapes.append(
                    Etape(nom=nom, debut=commencee.debut, fin=evenement.ts, agent=commencee.agent)
                )
    etapes.extend(ouvertes.values())
    return sorted(etapes, key=lambda e: e.debut)
