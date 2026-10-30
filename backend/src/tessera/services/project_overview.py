"""Vue d'ensemble des projets — ticket-398.

Une seule lecture pour tout ce qu'affiche une carte de projet. Le calcul git
et le comptage des tickets sont mis en cache par projet, invalidés quand le
dépôt ou les dossiers de tickets bougent : deux appels de suite ne relancent
aucune commande git.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from tessera.models.project import Project
from tessera.models.ticket import TicketStatus
from tessera.services.manifeste import lire_valeur
from tessera.services.online_declaration import StripeMode, read_online_declaration
from tessera.services.politique_run import PolitiqueRun
from tessera.services.ticket_service import _STATUS_DIRS
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Icônes d'app cherchées, dans cet ordre. Des chemins fixes, jamais reçus de
#: la requête : servir un chemin venu du client ouvrirait tout le disque.
#: `.tessera/icon.svg` passe en premier : c'est l'icône que Tessera affiche pour
#: un projet sans interface web (profil, script, bibliothèque), hors de l'app.
ICON_CANDIDATES: tuple[tuple[str, str], ...] = (
    (".tessera/icon.svg", "image/svg+xml"),
    ("frontend/public/favicon.svg", "image/svg+xml"),
    ("frontend/public/favicon.png", "image/png"),
    ("frontend/public/icon.svg", "image/svg+xml"),
    ("frontend/public/logo.svg", "image/svg+xml"),
    ("frontend/public/icons/icon-192.png", "image/png"),
    ("public/favicon.svg", "image/svg+xml"),
    ("public/favicon.png", "image/png"),
    ("public/icon.svg", "image/svg+xml"),
    # Convention Next.js (app router) : l'icône vit à côté des pages.
    ("src/app/icon.svg", "image/svg+xml"),
    ("src/app/icon.png", "image/png"),
    # Jeux et pages statiques : un index.html et son favicon à la racine.
    ("favicon.svg", "image/svg+xml"),
    ("favicon.png", "image/png"),
)

_COUNTED = (
    TicketStatus.todo,
    TicketStatus.in_progress,
    TicketStatus.in_review,
    TicketStatus.blocked,
    TicketStatus.done,
)


class TicketCounts(BaseModel):
    todo: int = 0
    in_progress: int = 0
    in_review: int = 0
    blocked: int = 0
    done: int = 0


class ProjectOverview(BaseModel):
    id: str
    name: str
    category: str | None = None
    description: str = ""
    github_remote: str | None = None
    created_at: str
    last_activity: str | None = None
    tickets: TicketCounts
    run_actif: bool = False
    icon: bool = False
    services_declares: bool = False
    services_en_cours: bool = False
    #: `agents.json` déclare un bloc `online` (ticket-472) : la carte offre « Mettre en ligne ».
    online_declared: bool = False
    online_domain: str | None = None
    online_stripe_mode: StripeMode | None = None
    #: Le projet fait tourner chaque run dans un worktree (ADR-056) : il ne se lance
    #: qu'un ticket à la fois, la carte n'offre donc pas de file (ticket-633).
    worktree: bool = False
    avertissements: list[str] = []


class _Calcul(BaseModel):
    created_at: str
    last_activity: str | None
    tickets: TicketCounts


_Signature = tuple[int, ...]
_cache: dict[str, tuple[_Signature, _Calcul]] = {}


def clear_overview_cache() -> None:
    """Vide le cache — utile aux tests."""
    _cache.clear()


def _chercher(racine: Path) -> tuple[Path, str] | None:
    for relatif, media_type in ICON_CANDIDATES:
        fichier = (racine / relatif).resolve()
        if fichier.is_file() and fichier.is_relative_to(racine):
            return fichier, media_type
    return None


def _racine_ancestrale(project_path: Path) -> Path | None:
    """Le dépôt qui contient le projet, s'il déclare `git_root: ancestor`.

    Le projet bootstrap (ide-core) vit dans `projects/ide-core/` : son app est
    l'IDE lui-même, dont l'icône est à la racine du dépôt (ADR-028).
    """
    if lire_valeur(project_path, "git_root") != "ancestor":
        return None
    git = _git_dir(project_path)
    return git.parent.resolve() if git is not None and git.name == ".git" else None


def find_icon(project_path: Path) -> tuple[Path, str] | None:
    """La première icône trouvée, avec son type de contenu, ou `None`.

    Cherchée dans le projet, puis, pour un projet `git_root: ancestor`, à la
    racine du dépôt qui le contient. Un lien symbolique qui sortirait du
    dossier fouillé est ignoré.
    """
    trouvee = _chercher(project_path.resolve())
    if trouvee is not None:
        return trouvee
    ancetre = _racine_ancestrale(project_path)
    return _chercher(ancetre) if ancetre is not None else None


def _mtime(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _git_dir(project_path: Path) -> Path | None:
    """Le `.git` qui régit ce dossier : le sien, ou celui d'un ancêtre
    (`git_root: ancestor`, ADR-028). Un `.git` fichier (worktree) est suivi."""
    for dossier in (project_path, *project_path.parents):
        candidat = dossier / ".git"
        if candidat.is_dir():
            return candidat
        if candidat.is_file():
            try:
                contenu = candidat.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            if contenu.startswith("gitdir:"):
                return (dossier / contenu.removeprefix("gitdir:").strip()).resolve()
            return None
    return None


def _signature(project_path: Path) -> _Signature:
    """Les dates de modification qui disent que le calcul est périmé.

    Au-delà de `.git/HEAD`, `.git/refs/heads/` et `tickets/`, on suit les
    sous-dossiers : un commit sur `refs/heads/a/b` ou un ticket déplacé vers
    `done/` ne touche que le dossier fils.
    """
    valeurs: list[int] = []
    git = _git_dir(project_path)
    if git is not None:
        valeurs += [_mtime(git / "HEAD"), _mtime(git / "packed-refs")]
        for dossier, _, _ in os.walk(git / "refs" / "heads"):
            valeurs.append(_mtime(Path(dossier)))
    tickets = project_path / "tickets"
    valeurs.append(_mtime(tickets))
    valeurs += [_mtime(tickets / nom) for nom in sorted(_STATUS_DIRS.values())]
    return tuple(valeurs)


async def _git_dates(project_path: Path, *args: str) -> list[str]:
    """Les lignes de `git log` pour ce dossier ; liste vide sans dépôt."""
    proc = await asyncio.create_subprocess_exec(
        "git", "log", *args, "--format=%cI", "--", ".",
        cwd=str(project_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    sortie, _ = await proc.communicate()
    if proc.returncode:
        return []
    return [ligne for ligne in sortie.decode("utf-8", errors="replace").split("\n") if ligne]


def _plus_ancienne(dates: list[str]) -> str | None:
    valides: list[tuple[datetime, str]] = []
    for brute in dates:
        try:
            valides.append((datetime.fromisoformat(brute), brute))
        except ValueError:
            _logger.warning("overview_bad_git_date", extra={"value": brute})
    return min(valides)[1] if valides else None


def _creation_du_dossier(project_path: Path) -> str:
    stat = project_path.stat()
    secondes = getattr(stat, "st_birthtime", stat.st_ctime)
    return datetime.fromtimestamp(secondes, tz=timezone.utc).isoformat()


def count_tickets(project_path: Path) -> TicketCounts:
    """Le nombre de fiches par statut, lu depuis les dossiers de tickets."""
    comptes: dict[str, int] = {}
    for statut in _COUNTED:
        dossier = project_path / "tickets" / _STATUS_DIRS[statut]
        nombre = len(list(dossier.glob("*.md"))) if dossier.is_dir() else 0
        comptes[statut.name] = nombre
    return TicketCounts(**comptes)


async def _calculer(project_path: Path) -> _Calcul:
    ajouts, derniers = await asyncio.gather(
        _git_dates(project_path, "--diff-filter=A"),
        _git_dates(project_path, "-1"),
    )
    return _Calcul(
        created_at=_plus_ancienne(ajouts) or _creation_du_dossier(project_path),
        last_activity=derniers[0] if derniers else None,
        tickets=count_tickets(project_path),
    )


async def _calcul_en_cache(project_path: Path) -> _Calcul:
    cle = str(project_path.resolve())
    signature = _signature(project_path)
    en_cache = _cache.get(cle)
    if en_cache is not None and en_cache[0] == signature:
        return en_cache[1]
    calcul = await _calculer(project_path)
    _cache[cle] = (signature, calcul)
    return calcul


def _en_worktree(project_path: Path) -> bool:
    """Vrai quand les runs du projet tournent dans un worktree ; faux s'il est illisible."""
    try:
        return PolitiqueRun.lire(project_path).worktree is not None
    except Exception:  # noqa: BLE001 — une carte ne tombe pas pour un manifeste illisible
        return False


async def build_overview(
    project: Project,
    *,
    run_actif: bool,
    services_declares: bool = False,
    services_en_cours: bool = False,
) -> ProjectOverview:
    """La carte d'un projet. `run_actif`, `icon` et l'état des services se
    lisent à chaque appel : ils bougent sans toucher ni le dépôt ni les
    tickets, le cache ne doit donc pas les figer."""
    calcul = await _calcul_en_cache(project.path)
    online = read_online_declaration(project.path)
    return ProjectOverview(
        id=project.id,
        name=project.name,
        category=project.category,
        description=project.description,
        github_remote=project.github_remote,
        created_at=calcul.created_at,
        last_activity=calcul.last_activity,
        tickets=calcul.tickets,
        run_actif=run_actif,
        icon=find_icon(project.path) is not None,
        services_declares=services_declares,
        services_en_cours=services_en_cours,
        online_declared=online.declared,
        online_domain=online.domain,
        online_stripe_mode=online.stripe_mode,
        worktree=_en_worktree(project.path),
        avertissements=list(project.avertissements),
    )
