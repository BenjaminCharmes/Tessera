"""What a supervisor decision writes in the run's worktree — ticket-856, ADR-080.

`appliquer_decision` is the callback handed to `intervenir`: it moves a block to
its section or drops it, checks the diff (`deplacement_pur`, `retrait_pur`)
before writing, and writes nothing on the first doubt. The block is found again
in the worktree's own file by its id: the checkout may have moved on since.
"""
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal

from tessera.services.supervision.intervention import Application
from tessera.services.supervision.superviseur_actions import deplacement_pur
from tessera.services.supervision.superviseur_decision_blocs import BlocPropose, Genre, deplacer_bloc, retirer_bloc, retrait_pur
from tessera.services.supervision.superviseur_journal import RESUME_MAX

Issue = Literal["accepter", "ecarter"]

FICHIERS: dict[Genre, str] = {"lecon": "lecons.md", "regle": "contraintes.md"}


class RefusDecision(ValueError):
    """A move the code refuses to write: the intervention ends `blocked`, with nothing changed."""


def resume_de(issue: Issue, vers: str, raison: str) -> str:
    """The journal summary of a decision: one line, no separator, within the journal's limit."""
    debut = f"acceptée vers {vers} : " if issue == "accepter" else "écartée : "
    ligne = re.sub(r"\s+", " ", f"{debut}{raison}".replace("|", "/")).strip()
    return ligne[:RESUME_MAX]


def _lire(chemin: Path) -> str:
    # Les octets, pas le texte : read_text() réécrirait un fichier CRLF en LF.
    return chemin.read_bytes().decode("utf-8")


def _calculer(avant: str, bloc: BlocPropose, issue: Issue, vers: str) -> str:
    if issue == "accepter":
        apres = deplacer_bloc(avant, bloc.genre, bloc.cible, vers)
        pur = deplacement_pur(avant, apres, bloc.texte, vers)
    else:
        apres = retirer_bloc(avant, bloc.genre, bloc.cible)
        pur = retrait_pur(avant, apres, bloc.texte)
    if not pur:
        raise RefusDecision(f"{bloc.cible} : le diff n'est pas un simple mouvement du bloc")
    return apres


def appliquer_decision(
    bloc: BlocPropose, issue: Issue, vers: str, resume: str
) -> Callable[[Path], Awaitable[Application]]:
    """The writer of one decision, for `intervenir`; `vers` is the section a block joins."""

    async def appliquer(projet: Path) -> Application:
        chemin = projet / "memory" / FICHIERS[bloc.genre]
        try:
            avant = _lire(chemin)
            apres = _calculer(avant, bloc, issue, vers)
        except RefusDecision:
            raise
        except (OSError, UnicodeDecodeError, ValueError):
            return Application(bloc.cible, "bloc ou section introuvable dans le worktree : rien n'est écrit")
        chemin.write_bytes(apres.encode("utf-8"))
        return Application(bloc.cible, resume)

    return appliquer
