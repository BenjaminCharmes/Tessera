"""Duplicate ledger of agent reports — ticket-862, ADR-080.

A duplicate is the same (``categorie``, ``composant``, normalised title) seen in
the last seven days, whatever the project: a defect of Tessera is the same one
everywhere. The ledger lives in ``ide_state_dir/signaux_agents.json``, outside
every repository. A duplicate is refused and counts a view (``vu``), which the
backlog sort reads.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tessera.config import settings
from tessera.services.providers.signal_agent import Refus, SignalValide, normaliser_titre
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

NOM_FICHIER = "signaux_agents.json"
FENETRE_DOUBLON = timedelta(days=7)
FENETRE_JOUR = timedelta(days=1)

#: What the agent reads on a duplicate.
DEJA_SIGNALE = "Signalement refusé : déjà signalé. Le compteur de vues a été incrémenté."


@dataclass
class EntreeSignal:
    """One report seen: when it was first emitted, for which project, how often."""

    cle: str
    projet: str
    premier: str
    vu: int


def chemin_registre() -> Path:
    """Where the ledger lives: the state folder, never inside a repository."""
    return settings.ide_state_dir / NOM_FICHIER


def cle_doublon(signal: SignalValide) -> str:
    """Duplicate key: category, component and normalised title."""
    return "|".join((signal.categorie, signal.composant, normaliser_titre(signal.titre)))


def lire_registre() -> list[EntreeSignal]:
    """Read the ledger; an unreadable file is set aside, not overwritten."""
    chemin = chemin_registre()
    if not chemin.is_file():
        return []
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
        return [
            EntreeSignal(
                cle=str(e["cle"]), projet=str(e["projet"]),
                premier=str(e["premier"]), vu=int(e["vu"]),
            )
            for e in brut
        ]
    except (ValueError, KeyError, TypeError):
        _logger.warning("signaux_agents_illisibles", extra={"chemin": str(chemin)})
        chemin.replace(chemin.with_suffix(".corrompu"))
        return []


def _ecrire(entrees: list[EntreeSignal]) -> None:
    chemin = chemin_registre()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(".tmp")
    contenu = json.dumps([asdict(e) for e in entrees], ensure_ascii=False, indent=2)
    temporaire.write_text(contenu, encoding="utf-8")
    temporaire.replace(chemin)


def _depuis(entree: EntreeSignal, maintenant: datetime, fenetre: timedelta) -> bool:
    return maintenant - datetime.fromisoformat(entree.premier) < fenetre


def emis_du_jour(projet: str, *, maintenant: datetime | None = None) -> int:
    """How many reports the project emitted in the last 24 hours."""
    instant = maintenant or datetime.now(UTC)
    return sum(
        1 for e in lire_registre()
        if e.projet == projet and _depuis(e, instant, FENETRE_JOUR)
    )


def enregistrer_signal(
    signal: SignalValide, *, projet: str, maintenant: datetime | None = None
) -> Refus | None:
    """Record a valid report, or refuse it as a duplicate and count a view.

    ``projet`` is the run's real project, kept for the daily bound; the report
    itself may hide it (``professional``). Returns ``None`` when the report is new.
    """
    instant = maintenant or datetime.now(UTC)
    vivantes = [e for e in lire_registre() if _depuis(e, instant, FENETRE_DOUBLON)]
    cle = cle_doublon(signal)
    for entree in vivantes:
        if entree.cle == cle:
            entree.vu += 1
            _ecrire(vivantes)
            return Refus(DEJA_SIGNALE)
    vivantes.append(EntreeSignal(cle=cle, projet=projet, premier=instant.isoformat(), vu=1))
    _ecrire(vivantes)
    return None
