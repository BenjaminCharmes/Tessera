"""The supervision journal — `memory/supervision.md`, written by the service alone (ticket-853, ADR-080).

One line per action of the supervisor: `- AAAA-MM-JJ | action | cible | sha | résumé`.
Same mechanics as `lecons.md` (ADR-074): a run never writes here (the guard sits
in `pipeline`), and a read never raises — an absent or unreadable file is an
empty journal. The module decides nothing and shows nothing.
"""
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from tessera.services.supervision.superviseur_actions import Action

FICHIER = "supervision.md"
RESUME_MAX = 200
A_TOI = "a_toi"
RESOLU = "resolu"
ACTIONS_JOURNAL = frozenset({*(action.value for action in Action), A_TOI, RESOLU})

_ENTETE = (
    "# Journal du superviseur\n\n"
    "Une ligne par action : `- date | action | cible | sha | résumé`. "
    "Le service seul écrit ici.\n\n"
)
_SEPARATEUR = "|"


@dataclass(frozen=True)
class LigneJournal:
    """One line of the journal."""

    jour: date
    action: str
    cible: str
    sha: str
    resume: str


def _champ_simple(nom: str, valeur: str) -> str:
    if "\n" in valeur or "\r" in valeur or _SEPARATEUR in valeur:
        raise ValueError(f"« {nom} » tient sur une ligne, sans « {_SEPARATEUR} »")
    return valeur.strip()


def _ligne_de(jour: date, action: str, cible: str, sha: str, resume: str) -> str:
    """The journal line for these fields; `ValueError` when one cannot be written."""
    if action not in ACTIONS_JOURNAL:
        raise ValueError(f"Action hors journal : {action!r}")
    cible_nette = _champ_simple("cible", cible)
    if not cible_nette:
        raise ValueError("« cible » est vide")
    if "\n" in resume or "\r" in resume:
        raise ValueError("a summary is a single line")
    resume_net = resume.strip()
    if len(resume_net) > RESUME_MAX:
        raise ValueError(f"a summary holds at most {RESUME_MAX} characters")
    champs = (jour.isoformat(), str(action), cible_nette, _champ_simple("sha", sha), resume_net)
    return "- " + " | ".join(champs)


def ajouter_ligne(
    memory_dir: Path, *, jour: date, action: str, cible: str, sha: str, resume: str
) -> None:
    """Append one line to the journal, creating the file with its header if absent."""
    ligne = _ligne_de(jour, action, cible, sha, resume)
    chemin = memory_dir / FICHIER
    try:
        contenu = chemin.read_text(encoding="utf-8")
    except FileNotFoundError:
        contenu = _ENTETE
    if not contenu.endswith("\n"):
        contenu += "\n"
    memory_dir.mkdir(parents=True, exist_ok=True)
    chemin.write_text(f"{contenu}{ligne}\n", encoding="utf-8", newline="\n")


def _lire_ligne(brut: str) -> LigneJournal | None:
    """The line as a `LigneJournal`, `None` for any text that is not a journal line."""
    texte = brut.strip()
    if not texte.startswith("- "):
        return None
    champs = [c.strip() for c in texte[2:].split(_SEPARATEUR, 4)]
    if len(champs) != 5 or champs[1] not in ACTIONS_JOURNAL or not champs[2]:
        return None
    try:
        jour = date.fromisoformat(champs[0])
    except ValueError:
        return None
    return LigneJournal(jour, champs[1], champs[2], champs[3], champs[4])


def lire_journal(memory_dir: Path, depuis: date | None = None) -> list[LigneJournal]:
    """The journal lines, oldest first, from `depuis` on; empty if absent or unreadable."""
    try:
        contenu = (memory_dir / FICHIER).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    lues = (_lire_ligne(brut) for brut in contenu.splitlines())
    return [
        ligne for ligne in lues
        if ligne is not None and (depuis is None or ligne.jour >= depuis)
    ]


def cas_a_toi_ouverts(lignes: list[LigneJournal]) -> list[LigneJournal]:
    """The `a_toi` cases with no `resolu` line of the same target after them."""
    ouverts: dict[str, LigneJournal] = {}
    for ligne in lignes:
        if ligne.action == A_TOI:
            ouverts[ligne.cible] = ligne
        elif ligne.action == RESOLU:
            ouverts.pop(ligne.cible, None)
    return list(ouverts.values())
