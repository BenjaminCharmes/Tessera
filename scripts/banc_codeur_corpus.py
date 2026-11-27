"""Corpus of the coder bench: format, freeze sum and checks (ticket-1053, ADR-095).

Pure functions plus read-only git calls (`ls-tree`, `show`). Outside
`backend/src`: the product never imports this module, and it imports nothing
from `tessera`. Selection from the history lives in `banc_codeur_proposer.py`.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MIN_HORS_PILOTE = 9

_CHAMPS_TEXTE = ("id", "ticket", "sha", "base_sha", "ticket_chemin", "ticket_sha256")
_FRONTMATTER = re.compile(r"---\n.*?\n---\n?", re.DOTALL)


class CorpusInvalide(ValueError):
    """The corpus file is malformed, inconsistent or not frozen."""


@dataclass(frozen=True)
class Entree:
    """One merged ticket; its base is the first parent of the squash `sha`."""

    id: str
    ticket: str
    sha: str
    base_sha: str
    ticket_chemin: str
    ticket_sha256: str
    fichiers: tuple[str, ...]
    lignes_ajoutees: int
    pilote: bool


@dataclass(frozen=True)
class Corpus:
    entrees: tuple[Entree, ...]
    gel_sha256: str


def git(depot: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Read-only git call; the caller checks `returncode`."""
    return subprocess.run(["git", "-C", str(depot), *args], capture_output=True)


def sans_frontmatter(texte: str) -> str:
    """Ticket text without its YAML frontmatter, line endings normalised."""
    texte = texte.replace("\r\n", "\n")
    trouve = _FRONTMATTER.match(texte)
    return texte[trouve.end():] if trouve else texte


def somme_texte(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


def texte_ticket(depot: Path, base_sha: str, ticket_chemin: str) -> str:
    """The ticket as it stood at `base_sha`, frontmatter removed (`git show`)."""
    sortie = git(depot, "show", f"{base_sha}:{ticket_chemin}")
    if sortie.returncode != 0:
        raise CorpusInvalide(
            f"ticket illisible à {base_sha[:12]} : {ticket_chemin} "
            f"({sortie.stderr.decode('utf-8', 'replace').strip()})"
        )
    return sans_frontmatter(sortie.stdout.decode("utf-8", "replace"))


def chemin_du_ticket(depot: Path, base_sha: str, numero: str) -> str | None:
    """Path of `ticket-<numero>-*.md` under a `tickets/` folder at `base_sha`."""
    sortie = git(depot, "ls-tree", "-r", "--name-only", base_sha)
    if sortie.returncode != 0:
        return None
    motif = re.compile(rf"(^|/)tickets/[^/]+/ticket-{re.escape(numero)}-[^/]*\.md$")
    trouves = sorted(
        c for c in sortie.stdout.decode("utf-8", "replace").splitlines() if motif.search(c)
    )
    return trouves[0] if trouves else None


def somme_gel(entrees: Iterable[Entree]) -> str:
    """SHA-256 of the non-pilot entries, whatever their order."""
    gelees = sorted((e for e in entrees if not e.pilote), key=lambda e: e.id)
    contenu = json.dumps([asdict(e) for e in gelees], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()


def _champ(brut: dict[str, Any], nom: str, genre: type, position: str) -> Any:
    if nom not in brut:
        raise CorpusInvalide(f"{position} : champ absent : {nom}")
    valeur = brut[nom]
    if not isinstance(valeur, genre) or (genre is int and isinstance(valeur, bool)):
        raise CorpusInvalide(f"{position} : champ `{nom}` de mauvais type")
    return valeur


def _entree(brut: Any, rang: int) -> Entree:
    position = f"entrees[{rang}]"
    if not isinstance(brut, dict):
        raise CorpusInvalide(f"{position} n'est pas un objet")
    texte = {nom: _champ(brut, nom, str, position) for nom in _CHAMPS_TEXTE}
    fichiers = _champ(brut, "fichiers", list, position)
    if not all(isinstance(f, str) for f in fichiers):
        raise CorpusInvalide(f"{position} : `fichiers` doit être une liste de chaînes")
    return Entree(
        **texte, fichiers=tuple(fichiers),
        lignes_ajoutees=_champ(brut, "lignes_ajoutees", int, position),
        pilote=_champ(brut, "pilote", bool, position),
    )


def charger(chemin: Path) -> Corpus:
    """Reads the manifest; raises `CorpusInvalide` when malformed. Does not check the sum."""
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CorpusInvalide(f"corpus illisible : {exc}") from exc
    if not isinstance(brut, dict) or not isinstance(brut.get("entrees"), list):
        raise CorpusInvalide("le corpus doit être un objet portant une liste `entrees`")
    gel = brut.get("gel_sha256")
    if not isinstance(gel, str):
        raise CorpusInvalide("champ absent ou de mauvais type : gel_sha256")
    entrees = tuple(_entree(e, i) for i, e in enumerate(brut["entrees"]))
    for nom in ("id", "sha"):
        valeurs = [getattr(e, nom) for e in entrees]
        if len(set(valeurs)) != len(valeurs):
            raise CorpusInvalide(f"`{nom}` en double dans le corpus")
    return Corpus(entrees=entrees, gel_sha256=gel)


def verifier(corpus: Corpus) -> None:
    """Refuses a corpus whose sum does not match or with too few non-pilot entries."""
    hors_pilote = [e for e in corpus.entrees if not e.pilote]
    if len(hors_pilote) < MIN_HORS_PILOTE:
        raise CorpusInvalide(
            f"{len(hors_pilote)} entrée(s) hors pilote, il en faut {MIN_HORS_PILOTE} au moins"
        )
    if somme_gel(corpus.entrees) != corpus.gel_sha256:
        raise CorpusInvalide("gel_sha256 ne correspond pas aux entrées")


def textes_divergents(corpus: Corpus, depot: Path) -> list[str]:
    """Ids whose ticket text read at `base_sha` no longer matches `ticket_sha256`."""
    divergents: list[str] = []
    for e in corpus.entrees:
        try:
            lu = somme_texte(texte_ticket(depot, e.base_sha, e.ticket_chemin))
        except CorpusInvalide:
            lu = ""
        if lu != e.ticket_sha256:
            divergents.append(e.id)
    return divergents
