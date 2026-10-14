"""À qui est ce processus ? — ticket-435.

Un port déclaré par un projet ne prouve rien : une autre application de la
machine peut l'occuper. Un processus n'est attribué à un projet que si sa
ligne de commande (ou celle de son parent direct) désigne un chemin situé sous
le dossier du projet. Dans le doute, il n'est à personne : l'inventaire ne
propose jamais « Arrêter » sur un processus dont il n'est pas sûr.
"""
import os
import re
from pathlib import Path

from tessera.services.sonde_systeme import InfoProcessus

#: Un chemin ne se prolonge pas par ces caractères : `projets/ide` ne doit pas
#: reconnaître `projets/ide-core`.
_FIN_DE_CHEMIN = r"(?![\w.\-])"
_DEBUT_DE_CHEMIN = r"(?<![\w.\-/])"


def _normaliser(texte: str) -> str:
    """Slashes avant, casse ignorée sous Windows."""
    unifie = texte.replace("\\", "/")
    return unifie.lower() if os.name == "nt" else unifie


def _racines(racine: Path) -> set[str]:
    """Le dossier tel que déclaré et tel que résolu (liens, jonctions)."""
    candidats = {racine, racine.resolve()}
    return {_normaliser(str(c)).rstrip("/") for c in candidats}


def _commande_sous(commande: str, racines: set[str]) -> bool:
    texte = _normaliser(commande)
    return any(
        re.search(_DEBUT_DE_CHEMIN + re.escape(r) + _FIN_DE_CHEMIN, texte)
        for r in racines
    )


def appartient_au_projet(
    pid: int, racine: Path, procs: dict[int, InfoProcessus]
) -> bool:
    """Whether the process, or its direct parent, runs from under `racine`."""
    info = procs.get(pid)
    if info is None:
        return False
    racines = _racines(racine)
    if _commande_sous(info.commande, racines):
        return True
    parent = procs.get(info.ppid)
    return parent is not None and _commande_sous(parent.commande, racines)
