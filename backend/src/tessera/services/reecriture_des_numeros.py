"""Rewriting of ticket and ADR numbers on the lines a run adds — ticket-659."""
import os
import re
from pathlib import Path

from tessera.services.numerotation import Genre, numeros_de_noms
from tessera.services.releve_du_diff import Releve

JOURNAL = "memory/pipeline-log.md"
PREFIXES: dict[Genre, str] = {"ticket": "ticket-", "adr": "ADR-"}


def nommer(genre: Genre, numero: int) -> str:
    """`ticket-061`, `ADR-061` : trois chiffres au moins, comme dans le dépôt."""
    return f"{PREFIXES[genre]}{numero:03d}"

_NUMERO_DE_NOM = re.compile(r"^ticket-\d+")
_MENTIONS: dict[Genre, re.Pattern[str]] = {
    "ticket": re.compile(r"(?<![\w-])ticket-(\d+)(?!\d)"),
    "adr": re.compile(r"(?<![\w-])ADR-(\d+)(?!\d)"),
}


def reecrire_les_mentions(
    depot: Path, releve: Releve, table: dict[Genre, dict[int, int]]
) -> set[str]:
    """Rewrite the mentions on added lines, in one pass; returns the files changed."""
    touches: set[str] = set()
    for chemin, numeros in releve.lignes.items():
        if chemin == JOURNAL or not (depot / chemin).is_file():
            continue
        texte = (depot / chemin).read_bytes().decode("utf-8", errors="replace").split("\n")
        avant = list(texte)
        for n in (n for n in numeros if 0 < n <= len(texte)):
            texte[n - 1] = _remplacer(texte[n - 1], table)
        if texte != avant:
            (depot / chemin).write_bytes("\n".join(texte).encode("utf-8"))
            touches.add(chemin)
    return touches


def _remplacer(ligne: str, table: dict[Genre, dict[int, int]]) -> str:
    for genre, correspondances in table.items():
        ligne = _MENTIONS[genre].sub(
            lambda m: (
                nommer(genre, correspondances[int(m.group(1))])
                if int(m.group(1)) in correspondances
                else m.group(0)
            ),
            ligne,
        )
    return ligne


def renommer_les_fiches(
    depot: Path, releve: Releve, correspondances: dict[int, int]
) -> set[str]:
    """Rename the added ticket files whose number moved; returns old and new paths."""
    touches: set[str] = set()
    for chemin in sorted(releve.ajoutes):
        dossier, _, nom = chemin.rpartition("/")
        ancien = next(iter(numeros_de_noms([nom])), None)
        if not chemin.startswith("tickets/") or ancien not in correspondances:
            continue
        nouveau_nom = _NUMERO_DE_NOM.sub(nommer("ticket", correspondances[ancien]), nom, count=1)
        os.replace(depot / chemin, depot / dossier / nouveau_nom)
        touches |= {chemin, f"{dossier}/{nouveau_nom}"}
    return touches
