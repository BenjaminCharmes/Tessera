"""Run again, once and alone, the test files that only timed out (ticket-971).

Un test instable sous charge coûtait trois tours à un ticket qui n'y touchait
pas. Seule une expiration est relancée, et seulement hors du diff du run : un
échec d'assertion, ou un fichier que le run a modifié, reste rouge.
"""
import posixpath
import re
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from tessera.services.verification.resultat_de_test import TestResult
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_VITEST_FAIL = re.compile(r"^\s*FAIL\s+(?:\|[^|]*\|\s+)?(\S+\.(?:test|spec)\.\w+)")
_PYTEST_FAIL = re.compile(r"^\s*(?:FAILED|ERROR)\s+([^\s:]+)(?:::\S*)?(?:\s+-\s+(.*))?$")
_EXPIRATION = re.compile(
    r"Test timed out in|Hook timed out in|Unable to find an element|Timed out in waitFor"
    r"|Failed: Timeout\s*>|Timeout\s*>\s*[\d.]+\s*s",
)

#: Lance une étape et rend (code, sortie), ou un `TestResult` si elle n'a pu finir.
Executeur = Callable[[list[str], Path], Awaitable["tuple[int, str] | TestResult"]]


@dataclass
class Echec:
    """One failing test file read from a step output."""

    genre: str  # "vitest" ou "pytest"
    fichier: str
    expiration: bool


@dataclass
class Relance:
    """What the lone second run of the timed-out files gave."""

    fichiers: list[str]
    duree_ms: int
    vert: bool
    sortie: str


def _echecs_vitest(lignes: list[str]) -> list[Echec]:
    blocs: list[tuple[str, list[str]]] = []
    for ligne in lignes:
        trouve = _VITEST_FAIL.match(ligne)
        if trouve:
            blocs.append((trouve.group(1), [ligne]))
        elif blocs:
            blocs[-1][1].append(ligne)
    return [Echec("vitest", f, bool(_EXPIRATION.search("\n".join(b)))) for f, b in blocs]


def _echecs_pytest(lignes: list[str]) -> list[Echec]:
    echecs: list[Echec] = []
    for ligne in lignes:
        trouve = _PYTEST_FAIL.match(ligne)
        if trouve:
            message = trouve.group(2) or ""
            echecs.append(Echec("pytest", trouve.group(1), bool(_EXPIRATION.search(message))))
    return echecs


def lire_les_echecs(sortie: str) -> list[Echec]:
    """Return the failing test files named in a pytest or vitest output."""
    lignes = _ANSI.sub("", sortie).splitlines()
    return _echecs_vitest(lignes) + _echecs_pytest(lignes)


def _dossier_et_nom(chemin: str) -> tuple[str, str]:
    dossier, nom = posixpath.split(chemin.replace("\\", "/"))
    return dossier, re.sub(r"(?:\.test|\.spec)?\.\w+$", "", nom).removeprefix("test_")


def _meme_dossier(du_diff: str, fichier: str) -> bool:
    d1, f1 = posixpath.dirname(du_diff.replace("\\", "/")), posixpath.dirname(fichier)
    return d1 == f1 or d1.endswith("/" + f1)


def touche_le_diff(fichier: str, diff: Sequence[str]) -> bool:
    """True when the run changed the test file or the code it tests beside it."""
    _, racine = _dossier_et_nom(fichier)
    for chemin in diff:
        chemin = chemin.replace("\\", "/")
        if chemin == fichier or chemin.endswith("/" + fichier):
            return True
        if _meme_dossier(chemin, fichier) and _dossier_et_nom(chemin)[1] == racine:
            return True
    return False


def fichiers_a_relancer(sortie: str, diff: Sequence[str]) -> dict[str, list[str]]:
    """Files to run again by kind; empty unless every failure is a timeout outside the diff."""
    echecs = lire_les_echecs(sortie)
    if not echecs or "unhandled" in sortie.lower():
        return {}
    if any(not e.expiration or touche_le_diff(e.fichier, diff) for e in echecs):
        return {}
    par_genre: dict[str, list[str]] = {}
    for echec in echecs:
        if echec.fichier not in par_genre.setdefault(echec.genre, []):
            par_genre[echec.genre].append(echec.fichier)
    return par_genre


def _racine_des_fichiers(fichiers: list[str], candidats: list[Path]) -> Path | None:
    for base in candidats:
        for dossier in (base, base / "frontend", base / "backend"):
            if all((dossier / f).is_file() for f in fichiers):
                return dossier
    return None


def _commande(genre: str, fichiers: list[str]) -> list[str]:
    if genre == "vitest":
        return ["npx", "vitest", "run", *fichiers]
    return ["uv", "run", "python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *fichiers]


async def relancer_les_instables(
    sortie: str,
    diff: Sequence[str],
    dossier: Path,
    racine: Path,
    executer: Executeur,
) -> Relance | None:
    """Run the timed-out files again once; None when the failure is not eligible."""
    par_genre = fichiers_a_relancer(sortie, diff)
    if not par_genre:
        return None
    debut = time.monotonic()
    vert = True
    sorties: list[str] = []
    tous: list[str] = []
    for genre, fichiers in par_genre.items():
        cwd = _racine_des_fichiers(fichiers, [dossier, dossier.parent, racine])
        if cwd is None:
            return None
        issue = await executer(_commande(genre, fichiers), cwd)
        tous += fichiers
        if isinstance(issue, TestResult):
            vert = False
            sorties.append(issue.output_summary)
            continue
        vert = vert and issue[0] == 0
        sorties.append(issue[1])
    relance = Relance(tous, int((time.monotonic() - debut) * 1000), vert, "\n".join(sorties))
    _logger.warning(
        "tests_instables_relances",
        extra={"fichiers": tous, "duree_ms": relance.duree_ms, "vert": vert},
    )
    return relance


def noter_les_relances(result: TestResult, relances: list[Relance]) -> None:
    """Record green retries on ``result``; a red retry adds its output to the details."""
    for relance in relances:
        if relance.vert:
            result.instables_relances += relance.fichiers
            result.instables_relances_ms += relance.duree_ms
        elif not result.passed:
            titre = "--- relance seule des fichiers expirés ---"
            result.failure_details = "\n\n".join([result.failure_details, titre, relance.sortie])


def issue_apres_relance(code: int, sortie: str, relance: Relance) -> tuple[int, str]:
    """Green after a green retry; else keep the failure with both outputs."""
    if relance.vert:
        note = f"[relance seule, verte : {', '.join(relance.fichiers)} en {relance.duree_ms} ms]"
        return 0, "\n".join([note, relance.sortie])
    separateur = "--- relance seule des fichiers expirés ---"
    return code, "\n\n".join([sortie, "\n".join([separateur, relance.sortie])])


async def reprendre_l_etape(
    code: int,
    sortie: str,
    diff: Sequence[str],
    dossier: Path,
    racine: Path,
    executer: Executeur,
) -> tuple[int, str, Relance | None]:
    """Run the timed-out files of a red step again; rend the step's new code and output."""
    relance = await relancer_les_instables(sortie, diff, dossier, racine, executer)
    if relance is None:
        return code, sortie, None
    nouveau, texte = issue_apres_relance(code, sortie, relance)
    return nouveau, texte, relance
