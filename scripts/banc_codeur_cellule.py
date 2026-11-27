"""One cell of the coder bench: (entry, arm) replayed in a history-free copy.

Ticket-1055, ADR-095, design §3, §5, §7. The cell talks to its roles through
`Roles`, a bundle of async callables: no push, no PR, no `RunLock`, no SQLite
and no `Orchestrator` can be reached from here. Real roles live in
`banc_codeur_roles.py`; tests pass doubles. Nothing here imports `tessera`.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import stat
import subprocess
import tarfile
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from banc_codeur_corpus import CorpusInvalide, Entree, somme_texte, texte_ticket

MAX_TOURS = 3
PLAFOND_CELLULE_USD = 6.0


class IndisponibleErreur(RuntimeError):
    """The arm's provider cannot answer: the cell is recorded `indisponible`."""


@dataclass(frozen=True)
class Appel:
    """Cost, tokens (in, out, cache) and duration of one coder call."""

    cout_usd: float = 0.0
    jetons: tuple[int, int, int] = (0, 0, 0)
    duree_ms: int = 0


@dataclass(frozen=True)
class Controle:
    """Reviewer plus validator on the copy's diff: approval, feedback, cost."""

    approuve: bool
    retour: str = ""
    cout_usd: float = 0.0


@dataclass(frozen=True)
class Roles:
    """What a cell needs; the same reviewer, validator and tests for every arm."""

    env: Callable[[Path], Awaitable[bool]]
    coder: Callable[[Path, str, str], Awaitable[Appel]]
    tester: Callable[[Path], Awaitable[bool]]
    controler: Callable[[Path, str, bool], Awaitable[Controle]]


@dataclass
class Resultat:
    id: str
    bras: str
    gel_sha256: str
    modele: str
    etat: str
    tours: int | None = None
    approuve_t1: bool = False
    approuve_final: bool = False
    tests_verts: bool = False
    tests_reference_verts: bool | None = None
    cout_codeur_usd: float = 0.0
    cout_controles_usd: float = 0.0
    jetons: dict[str, int] = field(default_factory=lambda: {"entree": 0, "sortie": 0, "cache": 0})
    duree_ms: dict[str, int] = field(default_factory=lambda: {"codeur": 0, "total": 0})

    @property
    def cout_usd(self) -> float:
        return self.cout_codeur_usd + self.cout_controles_usd


def vers_ligne(resultat: Resultat) -> str:
    return json.dumps(asdict(resultat), ensure_ascii=False, sort_keys=True)


def lire_resultats(chemin: Path) -> list[Resultat]:
    """Lines already consigned; a missing file is an empty run."""
    if not chemin.exists():
        return []
    lignes = [x for x in chemin.read_text(encoding="utf-8").splitlines() if x.strip()]
    return [Resultat(**json.loads(x)) for x in lignes]


def _rendre_ecrivable(fonction: Callable[[str], object], chemin: str, _: object) -> None:
    """Git objects are read-only on Windows: lift that, then retry the removal."""
    os.chmod(chemin, stat.S_IWRITE)
    fonction(chemin)


def copier_sans_historique(depot: Path, base_sha: str, cible: Path) -> None:
    """`git archive base_sha` extracted into `cible`, then `git init` and one commit.

    The future is not in the copy: the agent reads git, the real diff must not be there.
    """
    if cible.exists():
        shutil.rmtree(cible, onerror=_rendre_ecrivable)
    cible.mkdir(parents=True)
    archive = subprocess.run(
        ["git", "-C", str(depot), "archive", "--format=tar", base_sha],
        capture_output=True, check=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(cible, filter="data")
    env = ["-c", "user.name=banc", "-c", "user.email=banc@example.com", "-c", "commit.gpgsign=false"]
    # `origin/develop` sur le commit de base, sans remote : `verifier.py --impact base`
    # y trouve son point de départ et ne teste que le diff, frontend compris (ticket-1057).
    for args in (["init", "-q"], ["add", "-A"], [*env, "commit", "-q", "-m", "base"],
                 ["update-ref", "refs/remotes/origin/develop", "HEAD"]):
        subprocess.run(["git", "-C", str(cible), *args], capture_output=True, check=True)


def diff_de_la_copie(cwd: Path) -> str:
    """What the coder changed since the single base commit."""
    subprocess.run(["git", "-C", str(cwd), "add", "-A"], capture_output=True, check=True)
    sortie = subprocess.run(
        ["git", "-C", str(cwd), "diff", "--cached", "HEAD"], capture_output=True, check=True
    )
    return sortie.stdout.decode("utf-8", "replace")


def poser_solution(depot: Path, entree: Entree, cwd: Path) -> None:
    """Applies the real diff `base_sha..sha` to a base copy: the reference to check."""
    diff = subprocess.run(
        ["git", "-C", str(depot), "diff", "--binary", "--no-renames", entree.base_sha, entree.sha],
        capture_output=True, check=True,
    )
    subprocess.run(["git", "-C", str(cwd), "apply", "--whitespace=nowarn", "-"],
                   input=diff.stdout, capture_output=True, check=True)


def poser_tests_reference(depot: Path, entree: Entree, cwd: Path) -> None:
    """Writes the test files of the real diff into the copy, after the fact."""
    for chemin in entree.fichiers:
        if "test" not in Path(chemin).name:
            continue
        lu = subprocess.run(
            ["git", "-C", str(depot), "show", f"{entree.sha}:{chemin}"], capture_output=True
        )
        if lu.returncode == 0:
            (cwd / chemin).parent.mkdir(parents=True, exist_ok=True)
            (cwd / chemin).write_bytes(lu.stdout)


def lire_ticket(depot: Path, entree: Entree) -> str:
    """The ticket at `base_sha`, refused when its sum differs from the manifest."""
    texte = texte_ticket(depot, entree.base_sha, entree.ticket_chemin)
    if somme_texte(texte) != entree.ticket_sha256:
        raise CorpusInvalide(f"{entree.id} : le texte du ticket ne correspond plus à ticket_sha256")
    return texte


async def _tours(roles: Roles, cwd: Path, ticket: str, res: Resultat) -> None:
    retour, tests_verts = "", False
    for tour in range(1, MAX_TOURS + 1):
        appel = await roles.coder(cwd, ticket, retour)
        res.cout_codeur_usd += appel.cout_usd
        res.duree_ms["codeur"] += appel.duree_ms
        for cle, valeur in zip(("entree", "sortie", "cache"), appel.jetons, strict=True):
            res.jetons[cle] += valeur
        res.tours = tour
        if res.cout_usd > PLAFOND_CELLULE_USD:
            res.etat = "plafond_cellule"
            return
        tests_verts = await roles.tester(cwd)
        controle = await roles.controler(cwd, ticket, tests_verts)
        res.cout_controles_usd += controle.cout_usd
        res.tests_verts = tests_verts
        res.approuve_final = tests_verts and controle.approuve
        if tour == 1:
            res.approuve_t1 = res.approuve_final
        if res.approuve_final or res.cout_usd > PLAFOND_CELLULE_USD:
            break
        retour = controle.retour
    if res.cout_usd > PLAFOND_CELLULE_USD:
        res.etat = "plafond_cellule"


async def rejouer_cellule(
    entree: Entree, bras_id: str, modele: str, gel: str, roles: Roles, *,
    depot: Path, racine_copies: Path,
) -> Resultat:
    """Replays one (entry, arm) cell: coder, tests, controls, three rounds at most."""
    res = Resultat(id=entree.id, bras=bras_id, gel_sha256=gel, modele=modele, etat="ok")
    ticket = lire_ticket(depot, entree)
    cwd = racine_copies / f"{entree.id}-{bras_id}"
    copier_sans_historique(depot, entree.base_sha, cwd)
    debut = time.monotonic()
    if not await roles.env(cwd):
        res.etat = "echec_env"
        return res
    try:
        await _tours(roles, cwd, ticket, res)
    except IndisponibleErreur:
        res.etat = "indisponible"
    if res.etat == "ok":
        poser_tests_reference(depot, entree, cwd)
        res.tests_reference_verts = await roles.tester(cwd)
    res.duree_ms["total"] = round((time.monotonic() - debut) * 1000)
    return res
