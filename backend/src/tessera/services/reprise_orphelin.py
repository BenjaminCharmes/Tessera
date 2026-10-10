"""Remet d'aplomb les dépôts laissés en cours après un arrêt brutal — ticket-369.

`solder_les_runs_orphelins` clôt en base les runs interrompus, mais laisse
le dépôt du projet tel que le processus tué l'a laissé : arbre sale, fiche
du ticket dans un statut intermédiaire, branche courante sur la branche du
ticket. Ce module comble le gap au démarrage.

Pour chaque run soldé, si la copie de travail est sur la branche du ticket :
1. la fiche du ticket est déplacée dans tickets/todo/ et son statut forcé à todo,
   sur la branche du ticket, avant tout commit — sauf si elle est déjà « done »
   (ticket approuvé non livré) : dans ce cas elle est laissée telle quelle et
   une ligne est ajoutée dans memory/pipeline-log.md ;
2. les fichiers non suivis créés par le codeur après le démarrage du run
   (date de modification > started_at) sont ajoutés au commit de reprise,
   hors chemins ignorés par git et hors dépôts imbriqués (ticket-389) ;
3. les changements en cours (fiche incluse) sont commités avec le message des runs
   non approuvés (ADR-018 : l'arbre ne reste jamais sale) ;
4. la copie de travail revient sur la branche de base sans y écrire quoi que ce soit.

La branche de base n'est jamais modifiée : un run suivant ne trouve donc aucune
divergence locale (ticket-375).

Une erreur git est journalisée et n'empêche jamais le démarrage du backend.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import frontmatter as fm

from tessera.models.ticket import TicketStatus
from tessera.services.pipeline_text import _unapproved_commit_message
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Raison écrite dans le message de commit d'un run interrompu par un arrêt.
_RAISON_ARRET = "run interrupted by a backend stop"


async def _git(project_path: Path, *args: str) -> str:
    """Exécute une commande git dans `project_path` avec les hooks désactivés.

    Désactive les hooks comme `GitWorkspaceService._run` : un hook écrit par
    un agent pendant le run ne doit pas tourner ici sous l'identité du backend.

    Lève `RuntimeError` si git renvoie un code non nul.
    """
    hooks_dir = Path(tempfile.gettempdir()) / "tessera-sans-hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-c", f"core.hooksPath={hooks_dir}",
        "-c", "core.quotePath=false",
        *args,
        cwd=str(project_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} a échoué dans {project_path} : "
            f"{err.decode('utf-8', errors='replace')!r}"
        )
    return out.decode("utf-8", errors="replace").strip()


def _lire_base_branch(project_path: Path, fallback: str = "develop") -> str:
    """Lit `base_branch` depuis `agents.json`, ou renvoie `fallback`.

    Le fallback « develop » correspond au flux de livraison de ce dépôt
    (ticket-XXX → develop → main). Une valeur absente ou illisible ne bloque
    pas la reprise.
    """
    agents_json = project_path / "agents.json"
    if agents_json.is_file():
        try:
            data = json.loads(agents_json.read_text(encoding="utf-8"))
            valeur = data.get("base_branch")
            if isinstance(valeur, str) and valeur.strip():
                return valeur.strip()
        except Exception:
            pass
    return fallback


def _ecrire_ticket_todo(dest: Path, contenu: str) -> None:
    """Écrit le contenu du ticket dans `dest` avec le statut forcé à todo.

    Utilisé quand le checkout a supprimé le fichier (ticket existait uniquement
    sur la branche du ticket, pas sur la branche de base).
    """
    post = fm.loads(contenu)
    post["status"] = TicketStatus.todo.value
    dest.write_text(fm.dumps(post), encoding="utf-8")


def _est_dans_depot_imbrique(project_path: Path, fichier: Path) -> bool:
    """True si `fichier` se trouve dans un dépôt git imbriqué sous `project_path`.

    Parcourt les ancêtres de `fichier` jusqu'à `project_path` et renvoie True
    dès qu'un dossier intermédiaire contient un `.git`.
    """
    current = fichier.parent
    while True:
        try:
            if current == project_path or not current.is_relative_to(project_path):
                break
        except ValueError:
            break
        if (current / ".git").exists():
            return True
        current = current.parent
    return False


async def _trouver_fichiers_nouveaux(
    project_path: Path,
    started_at: datetime,
) -> list[str]:
    """List untracked, non-ignored files newer than `started_at`.

    Exclut les répertoires (y compris les dépôts imbriqués, listés avec "/"),
    les fichiers ignorés par git et les fichiers dans un dépôt imbriqué.
    Renvoie des chemins POSIX relatifs à `project_path`, prêts pour `git add`.
    """
    try:
        sortie = await _git(
            project_path, "ls-files", "--others", "--exclude-standard", "-z"
        )
    except Exception:
        return []

    if not sortie:
        return []

    fichiers: list[str] = []
    for chemin in sortie.split("\0"):
        if not chemin:
            continue
        # Les répertoires (dépôts imbriqués ou vides) se terminent par "/" :
        # seuls les fichiers entrent dans le commit.
        if chemin.endswith("/"):
            continue
        fichier = project_path / chemin
        if _est_dans_depot_imbrique(project_path, fichier):
            continue
        try:
            mtime = datetime.fromtimestamp(fichier.stat().st_mtime, tz=timezone.utc)
            if mtime > started_at:
                fichiers.append(chemin)
        except OSError:
            pass
    return fichiers


def _journaliser_approuve_non_livre(project_path: Path, ticket_id: str) -> None:
    """Appends an 'approved but undelivered' entry to memory/pipeline-log.md."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ligne = (
        f"- {ts} — [{ticket_id}] approuvé mais non livré : livraison à reprendre\n"
    )
    log_path = project_path / "memory" / "pipeline-log.md"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(ligne)
    except Exception as exc:
        _logger.warning(
            "reprise_journal_echec",
            extra={
                "project_path": str(project_path),
                "ticket_id": ticket_id,
                "error": str(exc),
            },
        )


async def _gerer_fiche_ticket(
    project_path: Path,
    project_id: str,
    ticket_id: str,
    ticket_svc: TicketService,
) -> tuple[Path | None, bool]:
    """Handle the ticket file during recovery.

    Returns ``(todo_path, ticket_was_approved)`` :
    - ``todo_path`` : chemin de la fiche déplacée en todo/ à stager dans git,
      ou ``None`` si aucun déplacement n'a eu lieu.
    - ``ticket_was_approved`` : ``True`` si le ticket était déjà ``done`` ;
      l'appelant écrira le journal **après** le checkout pour que le fichier
      ne soit pas commité puis supprimé par le retour sur la branche de base.

    Cas traités :
    - Ticket ``done`` : ne touche pas à la fiche, signale l'état à l'appelant.
    - Ticket ``in_progress`` ou ``in_review`` : déplace la fiche en todo/ et
      renvoie son nouveau chemin.
    - Tout autre statut ou ticket introuvable : ne fait rien.
    """
    ticket = await ticket_svc.get_ticket(ticket_id)
    if ticket is None:
        return None, False

    if ticket.status == TicketStatus.done:
        _logger.info(
            "reprise_ticket_approuve_non_livre",
            extra={"project_id": project_id, "ticket_id": ticket_id},
        )
        return None, True

    if ticket.status not in (TicketStatus.in_progress, TicketStatus.in_review):
        return None, False

    try:
        old_path = Path(ticket.file_path)
        contenu = old_path.read_text(encoding="utf-8")
        nom = old_path.name
    except OSError:
        return None, False

    todo_dir = project_path / "tickets" / "todo"
    todo_dir.mkdir(parents=True, exist_ok=True)
    todo_path = todo_dir / nom
    _ecrire_ticket_todo(todo_path, contenu)
    if old_path != todo_path:
        try:
            old_path.unlink()
        except OSError:
            pass
    _logger.info(
        "reprise_ticket_remis_en_todo_sur_branche_ticket",
        extra={"project_id": project_id, "ticket_id": ticket_id},
    )
    return todo_path, False


async def _reprendre_depot_seul(
    project_id: str,
    ticket_id: str,
    workspace_dir: Path,
    started_at: datetime,
) -> None:
    """Remet d'aplomb le dépôt d'un seul run orphelin.

    Ne fait rien si la copie de travail n'est pas sur la branche du ticket.
    Toute erreur git est journalisée sans remonter.
    """
    project_path = workspace_dir / project_id
    if not project_path.is_dir():
        _logger.warning(
            "reprise_projet_introuvable",
            extra={"project_id": project_id, "ticket_id": ticket_id},
        )
        return

    try:
        current_branch = await _git(
            project_path, "rev-parse", "--abbrev-ref", "HEAD"
        )
    except Exception as exc:
        _logger.warning(
            "reprise_erreur_git",
            extra={"project_id": project_id, "ticket_id": ticket_id, "error": str(exc)},
        )
        return

    # N'agit que si la copie de travail est sur la branche du ticket.
    expected_prefix = ticket_id + "-"
    if current_branch != ticket_id and not current_branch.startswith(expected_prefix):
        _logger.info(
            "reprise_branche_differente_ignoree",
            extra={
                "project_id": project_id,
                "ticket_id": ticket_id,
                "current_branch": current_branch,
            },
        )
        return

    try:
        ticket_svc = TicketService(project_path, project_id)

        # 1. Gérer la fiche du ticket SUR LA BRANCHE DU TICKET, avant le commit.
        #    - in_progress / in_review → déplacement en todo/ (ticket-375)
        #    - done → signalé par ticket_approuve pour journalisation après checkout
        todo_path, ticket_approuve = await _gerer_fiche_ticket(
            project_path, project_id, ticket_id, ticket_svc
        )

        # 2. Commiter les changements en cours (ADR-018 : l'arbre ne reste jamais sale).
        # Seuls les fichiers déjà suivis d'abord (`--update`), pour ne jamais
        # embarquer un projet voisin ou un brouillon étranger.
        await _git(project_path, "add", "--update", "--", ":/")

        # Ajouter aussi la fiche déplacée dans todo/ : `--update` ne suit que les
        # fichiers déjà connus de l'index, pas les nouveaux emplacements.
        if todo_path is not None:
            rel = todo_path.relative_to(project_path)
            await _git(project_path, "add", "--", rel.as_posix())

        # Ajouter les fichiers non suivis créés par le codeur après started_at
        # (ticket-389) : nouveaux fichiers source, tests, etc. créés pendant le run.
        nouveaux = await _trouver_fichiers_nouveaux(project_path, started_at)
        for chemin in nouveaux:
            await _git(project_path, "add", "--", chemin)

        staged = await _git(project_path, "diff", "--cached", "--name-only")
        if staged:
            commit_msg = _unapproved_commit_message(ticket_id, _RAISON_ARRET)
            await _git(project_path, "commit", "-m", commit_msg)
            _logger.info(
                "reprise_commit_effectue",
                extra={"project_id": project_id, "ticket_id": ticket_id},
            )

        # 3. Revenir sur la branche de base sans y écrire quoi que ce soit.
        base_branch = _lire_base_branch(project_path)
        await _git(project_path, "checkout", base_branch)
        _logger.info(
            "reprise_retour_branche_base",
            extra={"project_id": project_id, "base_branch": base_branch},
        )

        # 4. Journaliser « approuvé mais non livré » APRÈS le checkout pour que
        #    le fichier reste sur le disque sans jamais être commité ni supprimé
        #    par le retour sur la branche de base.
        if ticket_approuve:
            _journaliser_approuve_non_livre(project_path, ticket_id)

    except Exception as exc:
        _logger.warning(
            "reprise_erreur_git",
            extra={"project_id": project_id, "ticket_id": ticket_id, "error": str(exc)},
        )


async def reprendre_depots_orphelins(
    run_ids: list[str],
    db_path: Path | str,
    workspace_dir: Path,
) -> None:
    """Pour chaque run orphelin soldé, remet d'aplomb le dépôt de son projet.

    Appelée dans le lifespan après `solder_les_runs_orphelins`. Les `run_ids`
    sont ceux retournés par le solde : leurs `project_id`, `ticket_id` et
    `started_at` sont lus en base pour trouver le dépôt à nettoyer.
    """
    if not run_ids:
        return

    async with aiosqlite.connect(str(db_path)) as db:
        placeholders = ",".join("?" * len(run_ids))
        async with db.execute(
            f"SELECT project_id, ticket_id, started_at"
            f" FROM pipeline_runs WHERE id IN ({placeholders})",
            run_ids,
        ) as cursor:
            rows = await cursor.fetchall()

    for project_id, ticket_id, started_at_str in rows:
        try:
            started_at = datetime.fromisoformat(str(started_at_str))
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            started_at = datetime.now(timezone.utc)
        await _reprendre_depot_seul(
            str(project_id), str(ticket_id), workspace_dir, started_at
        )
