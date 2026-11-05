"""Replay input and reading of one review result (ticket-843, ADR-079).

Pure functions, no provider. The verdict is read by `lire_verdict`, the very
function the pipeline uses, so a candidate is judged like the reviewer.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

from tessera.services.verdicts.verdict_reviewer import lire_verdict

Etat = Literal["ok", "indisponible", "hors_fenetre", "hors_schema"]

_DOSSIERS_DE_TICKETS = ("done", "in-review", "in-progress", "todo", "blocked")
_TITRE_DU_DIFF = "## Code produit par le codeur"


def corps_du_ticket(ticket: str, racine_tickets: Path) -> str:
    """The text of `ticket-NNN-*.md` under `racine_tickets`; `ValueError` if absent."""
    for dossier in _DOSSIERS_DE_TICKETS:
        # Le tiret final évite que `ticket-900` ne lise `ticket-9000-…`.
        for fichier in sorted((racine_tickets / dossier).glob(f"{ticket}-*.md")):
            return fichier.read_text(encoding="utf-8")
    raise ValueError(f"ticket introuvable : {ticket}")


def composer_entree(corps_ticket: str, diff: str) -> str:
    """What both arms receive: the ticket, then the diff. No test, no audit."""
    return f"{corps_ticket.rstrip()}\n\n{_TITRE_DU_DIFF}\n{diff}"


def leve(structured: dict[str, Any] | None, seuil: int) -> bool:
    """True when `lire_verdict` refuses: a remark at the threshold, or an unreadable answer."""
    approuve, _ = lire_verdict(structured, seuil)
    return not approuve


def remarques_au_seuil(
    structured: dict[str, Any] | None, seuil: int
) -> tuple[dict[str, Any], ...]:
    """The remarks that make the review refuse, empty when it approves."""
    approuve, _ = lire_verdict(structured, seuil)
    if approuve or structured is None:
        return ()
    blocage = structured.get("blocking")
    if not isinstance(blocage, list):
        return ()
    return tuple(
        r for r in blocage
        if isinstance(r, dict) and isinstance(r.get("confidence"), int)
        and not isinstance(r["confidence"], bool) and r["confidence"] >= seuil
    )


def _normaliser(texte: str) -> str:
    return texte.replace("\\", "/").lower()


def designe_le_defaut(remarque: dict[str, Any], fichiers_defaut: Sequence[str]) -> bool:
    """Proposes a match: a defect file shows in `location` or `text`. A human decides."""
    lu = _normaliser(f"{remarque.get('location', '')}\n{remarque.get('text', '')}")
    for fichier in fichiers_defaut:
        chemin = _normaliser(fichier)
        if chemin and (chemin in lu or chemin.rsplit("/", 1)[-1] in lu):
            return True
    return False


@dataclass(frozen=True)
class Resultat:
    """One line of `resultats.jsonl`: one call of one arm on one entry."""

    id: str
    bras: Literal["B", "C"]
    modele: str
    gel_sha256: str
    etat: Etat
    leve: bool | None
    remarques: tuple[dict[str, Any], ...]
    cout_usd: float
    duree_ms: int


def vers_ligne(r: Resultat) -> str:
    """One JSON line, without a line break."""
    return json.dumps(asdict(r), ensure_ascii=False)


def _depuis_ligne(ligne: str) -> Resultat:
    brut = json.loads(ligne)
    return Resultat(
        id=brut["id"], bras=cast(Literal["B", "C"], brut["bras"]), modele=brut["modele"],
        gel_sha256=brut["gel_sha256"], etat=cast(Etat, brut["etat"]), leve=brut["leve"],
        remarques=tuple(brut["remarques"]), cout_usd=float(brut["cout_usd"]),
        duree_ms=int(brut["duree_ms"]),
    )


def lire_resultats(chemin: Path) -> list[Resultat]:
    """Reads the results file; a missing file reads as no result."""
    if not chemin.is_file():
        return []
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    return [_depuis_ligne(ligne) for ligne in lignes if ligne.strip()]
