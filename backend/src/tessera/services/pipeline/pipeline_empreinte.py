"""Empreinte des fichiers protégés, prise autour de chaque appel d'agent — ticket-933.

Les gardes d'écriture lisent des commandes (`>`, `tee`, `cp`…) : un `sed -i`, un
`dd of=` ou un heredoc donné à `python -` leur échappent (ADR-031). Ce module ne
lit pas la commande, il constate le résultat : le contenu haché des fichiers que
`chemins_proteges` désigne, avant et après l'appel. Une différence arrête le run
en `blocked`, avec son commit (ADR-037), le motif nomme les fichiers sans leur
contenu.

La liste ne copie pas `chemins_proteges.py` : on énumère des candidats bornés
(des fichiers, jamais l'arbre entier) et `motif_de_protection` décide.
"""
import asyncio
import hashlib
from collections.abc import Awaitable
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from tessera.services.git_workspace.git_runner import git
from tessera.services.noyau.pipeline_events import PipelineResult
from tessera.services.pipeline.pipeline_contraintes import bloquer
from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.providers.chemins_proteges import motif_de_protection
from tessera.services.providers.perimetre import racine_autorisee
from tessera.services.providers.script_verification import script_de_verification
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.pipeline.orchestrator import Orchestrator

_logger = get_logger(__name__)

_T = TypeVar("_T")

#: Chemin affichable → sha256 du contenu, ou None si le fichier est absent.
Empreinte = dict[str, str | None]

CODE_ARRET = "protected_file_modified"
RESUME = "protected file changed by an agent"

_FICHIERS_DU_PROJET = ("agents.json", "CLAUDE.md", "CLAUDE.local.md", ".mcp.json")
_DOSSIERS = (
    ".claude/skills", ".claude/commands", ".claude/agents", ".claude/hooks",
    ".github/workflows", "scripts/hooks",
)
_FICHIERS_DU_DEPOT = ("scripts/termes_interdits_ci.py",)


def _fichiers_sous(dossier: Path) -> list[Path]:
    """Files under `dossier`; empty when it is absent."""
    if not dossier.is_dir():
        return []
    return [p for p in dossier.rglob("*") if p.is_file() or p.is_symlink()]


def _candidats_du_projet(projet: Path, racine: Path) -> list[Path]:
    trouves: list[Path] = [projet / nom for nom in _FICHIERS_DU_PROJET]
    trouves += [racine / nom for nom in _FICHIERS_DU_DEPOT]
    for base in {projet, racine}:
        trouves += sorted((base / ".claude").glob("settings*.json"))
        for dossier in _DOSSIERS:
            trouves += _fichiers_sous(base / dossier)
    return trouves


async def _dossiers_git(racine: Path) -> list[Path]:
    """The common git dir and the worktree's own git dir; empty outside a repository."""
    resultat = await git(racine, "rev-parse", "--git-common-dir", "--git-dir")
    if resultat.code != 0:
        return []
    uniques: dict[Path, None] = {}
    for ligne in resultat.out.splitlines():
        if ligne.strip():
            uniques[(racine / ligne.strip()).resolve()] = None
    return list(uniques)


def _candidats_git(dossier: Path) -> list[Path]:
    return [dossier / "config", dossier / "config.worktree", *_fichiers_sous(dossier / "hooks")]


def _condenser(chemin: Path) -> str | None:
    try:
        return hashlib.sha256(chemin.read_bytes()).hexdigest()
    except OSError:
        return None


def _nom(chemin: Path, racine: Path, dossiers_git: list[Path]) -> str:
    """Name shown in the reason: relative to the root, `.git/…` for a git dir."""
    for dossier in dossiers_git:
        if chemin.is_relative_to(dossier):
            return f"{dossier.name}/{chemin.relative_to(dossier).as_posix()}"
    try:
        return chemin.resolve().relative_to(racine).as_posix()
    except ValueError:
        return chemin.as_posix()


def _hacher(
    candidats: list[Path], projet: Path, racine: Path, dossiers_git: list[Path],
    script: Path | None,
) -> Empreinte:
    resultat: Empreinte = {}
    for chemin in candidats:
        if motif_de_protection(str(chemin), projet, racine, script) is not None:
            resultat[_nom(chemin, racine, dossiers_git)] = _condenser(chemin)
    if script is not None:
        resultat[_nom(script, racine, dossiers_git)] = _condenser(script)
    return resultat


async def empreinte(orch: "Orchestrator") -> Empreinte:
    """Hash of every protected file the run can reach; empty without a project."""
    projet = orch._project_path
    if projet is None:
        return {}
    racine = racine_autorisee(projet).resolve()
    dossiers = await _dossiers_git(racine)
    candidats = _candidats_du_projet(projet, racine)
    for dossier in dossiers:
        candidats += _candidats_git(dossier)
    script = script_de_verification(projet, orch._test_command)
    return await asyncio.to_thread(_hacher, candidats, projet, racine, dossiers, script)


def noms_changes(avant: Empreinte, apres: Empreinte) -> list[str]:
    """Names whose hash differs, appeared or disappeared; never a content."""
    return sorted(n for n in avant.keys() | apres.keys() if avant.get(n) != apres.get(n))


async def gardee(
    orch: "Orchestrator", run: PipelineRun, appel: Awaitable[_T]
) -> "_T | PipelineResult":
    """Await `appel` between two fingerprints; a change returns the blocked result instead.

    L'empreinte est prise juste avant chaque appel, jamais une fois au départ :
    git écrit lui-même dans `.git/config` entre deux appels (upstream, worktree).
    Si l'appel lève, rien n'est comparé : l'exception suit son chemin (ADR-037).
    """
    avant = await empreinte(orch)
    resultat = await appel
    changes = noms_changes(avant, await empreinte(orch))
    if changes:
        return await arret_fichier_protege(orch, run, changes)
    return resultat


async def arret_fichier_protege(
    orch: "Orchestrator", run: PipelineRun, changes: list[str]
) -> PipelineResult:
    """Block the run, naming the protected files an agent call changed."""
    raison = "fichier protégé modifié pendant un appel d'agent : " + ", ".join(changes)
    _logger.warning("protected_file_modified", extra={"files": changes})
    return await bloquer(orch, run, CODE_ARRET, raison, RESUME)
