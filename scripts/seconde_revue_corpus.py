"""Corpus of the second-review trial: format and checks (ticket-841, ADR-079).

Pure functions plus two read-only git calls. Outside `backend/src`: the product
never imports this module, and it imports nothing from `tessera`.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Literal, cast

# Diffs sensibles (spec §2). Un motif sans « / » se compare au nom du fichier,
# un motif avec « / » au chemin entier ; « * » traverse les dossiers.
CHEMINS_SENSIBLES: tuple[str, ...] = (
    "*/services/providers/*guard*",
    "garde_*",
    "chemins_proteges.py",
    "redirections_bash.py",
    "refus_*.py",
    "secrets_diff.py",
    "*coffre*",
    "*livraison*",
    "scripts/hooks/*",
    ".github/workflows/*",
)

MIN_DEFAUTS = 10
MIN_SAINS = 10
MIN_DEFAUTS_SENSIBLES = 4

_CHAMPS_TEXTE = ("id", "ticket", "sha", "classe", "preuve", "defaut")


class CorpusInvalide(ValueError):
    """The corpus file is malformed or inconsistent."""


@dataclass(frozen=True)
class Entree:
    """One past run, approved and merged; its diff is `sha^..sha`."""

    id: str
    ticket: str
    sha: str
    classe: Literal["defaut", "sain"]
    preuve: str
    fichiers_defaut: tuple[str, ...]
    defaut: str
    sensible: bool


@dataclass(frozen=True)
class Corpus:
    entrees: tuple[Entree, ...]
    gel_sha256: str


def _correspond(chemin: str, motif: str) -> bool:
    cible = chemin if "/" in motif else chemin.rsplit("/", 1)[-1]
    return fnmatchcase(cible, motif)


def est_sensible(fichiers: Iterable[str]) -> bool:
    """True when one file touches a guard of the product (spec §2)."""
    for fichier in fichiers:
        chemin = fichier.replace("\\", "/")
        if any(_correspond(chemin, motif) for motif in CHEMINS_SENSIBLES):
            return True
    return False


def somme_gel(entrees: Iterable[Entree]) -> str:
    """SHA-256 of the entries, whatever their order."""
    triees = sorted(entrees, key=lambda e: e.id)
    contenu = json.dumps([asdict(e) for e in triees], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()


def _champ(brut: dict[str, Any], nom: str, genre: type, position: str) -> Any:
    if nom not in brut:
        raise CorpusInvalide(f"{position} : champ absent : {nom}")
    valeur = brut[nom]
    if not isinstance(valeur, genre):
        raise CorpusInvalide(f"{position} : champ `{nom}` de mauvais type")
    return valeur


def _entree(brut: Any, rang: int) -> Entree:
    position = f"entrees[{rang}]"
    if not isinstance(brut, dict):
        raise CorpusInvalide(f"{position} n'est pas un objet")
    texte = {nom: _champ(brut, nom, str, position) for nom in _CHAMPS_TEXTE}
    fichiers = _champ(brut, "fichiers_defaut", list, position)
    if not all(isinstance(f, str) for f in fichiers):
        raise CorpusInvalide(f"{position} : `fichiers_defaut` doit être une liste de chaînes")
    sensible = _champ(brut, "sensible", bool, position)
    if texte["classe"] not in ("defaut", "sain"):
        raise CorpusInvalide(f"{position} : `classe` hors énumération : {texte['classe']!r}")
    if texte["classe"] == "defaut":
        exigences = (
            ("preuve", bool(texte["preuve"])),
            ("fichiers_defaut", bool(fichiers)),
            ("defaut", bool(texte["defaut"])),
        )
        for nom, present in exigences:
            if not present:
                raise CorpusInvalide(f"{position} : un `defaut` exige `{nom}`")
    elif texte["preuve"] or fichiers or texte["defaut"]:
        raise CorpusInvalide(f"{position} : un `sain` ne porte ni preuve, ni fichiers, ni défaut")
    return Entree(
        id=texte["id"], ticket=texte["ticket"], sha=texte["sha"],
        classe=cast(Literal["defaut", "sain"], texte["classe"]),
        preuve=texte["preuve"], fichiers_defaut=tuple(fichiers),
        defaut=texte["defaut"], sensible=sensible,
    )


def charger_corpus(chemin: Path) -> Corpus:
    """Reads and checks the manifest; raises `CorpusInvalide` when malformed."""
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
    if somme_gel(entrees) != gel:
        raise CorpusInvalide("gel_sha256 ne correspond pas aux entrées")
    return Corpus(entrees=entrees, gel_sha256=gel)


def verifier_taille(corpus: Corpus) -> list[str]:
    """One reason per missed size threshold; empty when the corpus conforms."""
    defauts = [e for e in corpus.entrees if e.classe == "defaut"]
    sains = [e for e in corpus.entrees if e.classe == "sain"]
    sensibles = [e for e in defauts if e.sensible]
    raisons: list[str] = []
    if len(defauts) < MIN_DEFAUTS:
        raisons.append(f"{len(defauts)} défaut(s), il en faut {MIN_DEFAUTS} au moins")
    if len(sains) < MIN_SAINS:
        raisons.append(f"{len(sains)} sain(s), il en faut {MIN_SAINS} au moins")
    if len(sensibles) < MIN_DEFAUTS_SENSIBLES:
        raisons.append(
            f"{len(sensibles)} défaut(s) sensible(s), il en faut {MIN_DEFAUTS_SENSIBLES} au moins"
        )
    return raisons


def _git(depot: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # Lecture seule : `cat-file` et `diff` uniquement.
    return subprocess.run(
        ["git", "-C", str(depot), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def shas_manquants(corpus: Corpus, depot: Path) -> list[str]:
    """The SHAs the repository does not hold (`git cat-file`, read only)."""
    return [
        e.sha for e in corpus.entrees
        if _git(depot, "cat-file", "-e", f"{e.sha}^{{commit}}").returncode != 0
    ]


def diff_de(entree: Entree, depot: Path) -> str:
    """`git diff sha^..sha`, read only; raises `CorpusInvalide` if git refuses."""
    sortie = _git(depot, "diff", f"{entree.sha}^..{entree.sha}")
    if sortie.returncode != 0:
        raise CorpusInvalide(f"diff impossible pour {entree.id} : {sortie.stderr.strip()}")
    return sortie.stdout
