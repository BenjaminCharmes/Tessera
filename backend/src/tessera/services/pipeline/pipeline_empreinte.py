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
import re
import subprocess
from collections.abc import Awaitable
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from tessera.services.git_workspace.git_runner import git
from tessera.services.noyau.git_commande import build_command
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


#: Clés de branche que git, l'IDE ou une session humaine réécrivent sans cesse
#: (`push -u`, `vscode-merge-base`) et qui n'exécutent rien (ticket-937).
_CLE_DE_BRANCHE = re.compile(r"^branch\..+\.(remote|merge|rebase|vscode-merge-base)$")


def _est_cle_de_branche(entree: bytes) -> bool:
    cle = entree.split(b"\n", 1)[0].decode("utf-8", "replace")
    return _CLE_DE_BRANCHE.match(cle) is not None


def entrees_de_config(chemin: Path) -> bytes | None:
    """Sorted `git config --list --includes` entries, branch keys left out; None if git fails.

    Git lit lui-même le fichier : `[branch "x"] [core]` sur une ligne, ou un
    `[include]`, ne trompent pas l'empreinte comme ils trompaient un filtre de
    texte (ticket-941). Les fichiers inclus entrent dans la liste.
    """
    commande = build_command(("config", "--file", str(chemin), "--list", "--includes", "-z"))
    try:
        res = subprocess.run(commande, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    entrees = [e for e in res.stdout.split(b"\0") if e and not _est_cle_de_branche(e)]
    return b"\0".join(sorted(entrees))


def _condenser(chemin: Path) -> str | None:
    try:
        contenu = chemin.read_bytes()
    except OSError:
        return None
    if chemin.name in ("config", "config.worktree"):
        # Si git ne peut pas lire le fichier, le contenu brut est haché : la porte
        # échoue fermée.
        contenu = entrees_de_config(chemin) or contenu
    return hashlib.sha256(contenu).hexdigest()


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
    commiter = not config_git_changee(changes)
    if not commiter:
        # Un `filter.*` de la config nouvelle s'exécuterait au `git add` : l'arbre
        # reste tel quel (ticket-965).
        _logger.warning("commit_de_blocage_saute", extra={"files": changes})
    return await bloquer(orch, run, CODE_ARRET, raison, RESUME, commiter=commiter)


def config_git_changee(changes: list[str]) -> bool:
    """True when a changed name is a git `config` or `config.worktree` file."""
    return any(n.rsplit("/", 1)[-1] in ("config", "config.worktree") and "/" in n
               and not n.startswith((".claude/", ".github/", "scripts/")) for n in changes)
