"""Les phrases qui ne sont pas celles du projet — ticket-936.

La description d'un projet ne reprend ni celle d'un autre projet de l'espace de
travail, ni la première phrase du `CLAUDE.md` racine de Tessera (sauf pour le
projet ide-core, qui est Tessera). Le contrôle de preuve (ADR-057) juge la forme,
pas le sujet : ceci ferme le second trou.
"""
import json
import re
from pathlib import Path

#: Une phrase se termine à un point suivi d'un blanc, ou à la fin du texte.
_FIN_DE_PHRASE = re.compile(r"(?<=[.!?])\s")
_BLANCS = re.compile(r"\s+")


def premiere_phrase(texte: str) -> str:
    """The first sentence of a text, lower-cased with collapsed whitespace."""
    phrase = _FIN_DE_PHRASE.split(texte.strip(), maxsplit=1)[0]
    return _BLANCS.sub(" ", phrase).strip().casefold()


def _lire(chemin: Path) -> str:
    try:
        return chemin.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return ""


def _premiere_phrase_du_claude_md(chemin: Path) -> str:
    """First sentence of the first prose paragraph, titles and lists skipped."""
    for bloc in _lire(chemin).split("\n\n"):
        bloc = bloc.strip()
        if bloc and not bloc.startswith(("#", "-", "`", "@", "|", ">")):
            return premiere_phrase(bloc)
    return ""


def _description_du_manifeste(manifeste: Path) -> str:
    try:
        donnees = json.loads(_lire(manifeste).lstrip("﻿"))
    except ValueError:
        return ""
    texte = donnees.get("description") if isinstance(donnees, dict) else None
    return premiere_phrase(texte) if isinstance(texte, str) else ""


def phrases_interdites(
    project_path: Path, workspace: Path, racine_tessera: Path
) -> list[str]:
    """First sentences a description of ``project_path`` must not start with.

    Les descriptions des `agents.json` des projets voisins, et le `CLAUDE.md` de
    `racine_tessera` sauf si le projet vit dans ce dépôt. Un fichier absent ou
    illisible est ignoré.
    """
    interdites: list[str] = []
    if workspace.is_dir():
        for voisin in sorted(workspace.iterdir()):
            if voisin.resolve() != project_path.resolve():
                interdites.append(_description_du_manifeste(voisin / "agents.json"))
    racine = racine_tessera.resolve()
    projet = project_path.resolve()
    if racine != projet and racine not in projet.parents:
        interdites.append(_premiere_phrase_du_claude_md(racine / "CLAUDE.md"))
    return [p for p in interdites if p]
