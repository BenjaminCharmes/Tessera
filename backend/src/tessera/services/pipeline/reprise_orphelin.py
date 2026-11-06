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

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import frontmatter as fm

from tessera.models.ticket import TicketStatus
from tessera.services.git_workspace.git_runner import git
from tessera.services.livraison.reprise_marqueur import lire_runs, marquer_depots_repris, runs_interrompus_a_reprendre
from tessera.services.pipeline.pipeline_text import _unapproved_commit_message
from tessera.services.pipeline.reprise_journal import journaliser_approuve_non_livre
from tessera.services.projets.manifeste import lire_chaine
from tessera.services.projets.racine_depot import depot_le_plus_proche
from tessera.services.projets.ticket_service import TicketService
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
    resultat = await git(project_path, *args)
    if not resultat.ok:
        raise RuntimeError(
            f"git {' '.join(args)} a échoué dans {project_path} : {resultat.err!r}"
        )
    return resultat.out.strip()


def _lire_base_branch(project_path: Path, fallback: str = "develop") -> str:
    """Lit `base_branch` depuis `agents.json`, ou renvoie `fallback`.

    Le fallback « develop » correspond au flux de livraison de ce dépôt
    (ticket-XXX → develop → main). Une valeur absente ou illisible ne bloque
    pas la reprise.
    """
    valeur = lire_chaine(project_path, "base_branch")
    if valeur is not None and valeur.strip():
        return valeur.strip()
    return fallback


def _ecrire_ticket_todo(dest: Path, contenu: str) -> None:
    """Écrit le contenu du ticket dans `dest` avec le statut forcé à todo.

    Utilisé quand le checkout a supprimé le fichier (ticket existait uniquement
    sur la branche du ticket, pas sur la branche de base).
    """
    post = fm.loads(contenu)
    post["status"] = TicketStatus.todo.value
    dest.write_text(fm.dumps(post), encoding="utf-8")


def _est_dans_depot_imbrique(racine_depot: Path, fichier: Path) -> bool:
    """True si `fichier` se trouve dans un dépôt git imbriqué sous `racine_depot`.

    Parcourt les ancêtres **résolus** de `fichier` jusqu'à la racine du dépôt
    (exclue) et renvoie True dès qu'un dossier intermédiaire contient un
    `.git`. Résoudre est nécessaire : un chemin en `../..` (projet
    `git_root: ancestor`) remonterait sinon jusqu'au `.git` du dépôt lui-même.
    """
    racine = racine_depot.resolve()
    proche = depot_le_plus_proche(fichier.resolve().parent)
    return proche is not None and proche != racine and proche.is_relative_to(racine)


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
        # `:/` : tout le dépôt. Pour un projet `git_root: ancestor` (ide-core),
        # le codeur écrit dans `backend/` et `frontend/`, hors du dossier du
        # projet ; les chemins restent rendus relatifs au cwd (`../../…`).
        # Les autres projets imbriqués apparaissent comme des dossiers (« / »).
        sortie = await _git(
            project_path, "ls-files", "--others", "--exclude-standard", "-z", "--", ":/"
        )
    except Exception:
        return []

    if not sortie:
        return []

    try:
        racine_depot = Path(await _git(project_path, "rev-parse", "--show-toplevel"))
    except Exception:
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
        if _est_dans_depot_imbrique(racine_depot, fichier):
            continue
        try:
            mtime = datetime.fromtimestamp(fichier.stat().st_mtime, tz=UTC)
            if mtime > started_at:
                fichiers.append(chemin)
        except OSError:
            pass
    return fichiers


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
) -> bool:
    """Remet d'aplomb le dépôt d'un seul run orphelin.

    Rend True quand il n'y a plus rien à reprendre : dépôt remis d'aplomb,
    copie de travail hors de la branche du ticket, ou projet introuvable
    (aucune reprise possible, inutile de retenter). Rend False sur une erreur
    git : elle est journalisée sans remonter, et le run reste à reprendre.
    """
    project_path = workspace_dir / project_id
    if not project_path.is_dir():
        _logger.warning(
            "reprise_projet_introuvable",
            extra={"project_id": project_id, "ticket_id": ticket_id},
        )
        return True

    try:
        current_branch = await _git(
            project_path, "rev-parse", "--abbrev-ref", "HEAD"
        )
    except Exception as exc:
        _logger.warning(
            "reprise_erreur_git",
            extra={"project_id": project_id, "ticket_id": ticket_id, "error": str(exc)},
        )
        return False

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
        return True

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
            journaliser_approuve_non_livre(project_path, ticket_id)

    except Exception as exc:
        _logger.warning(
            "reprise_erreur_git",
            extra={"project_id": project_id, "ticket_id": ticket_id, "error": str(exc)},
        )
        return False
    return True


async def reprendre_depots_orphelins(
    run_ids: list[str],
    db_path: Path | str,
    workspace_dir: Path,
) -> None:
    """Pour chaque run orphelin, remet d'aplomb le dépôt de son projet.

    Appelée dans le lifespan après `solder_les_runs_orphelins`. Les `run_ids`
    sont ceux du solde (processus tué net) ; s'y ajoutent les runs `interrupted`
    (arrêt propre) au dépôt pas encore repris. Un run interrompu n'est marqué
    repris qu'une fois sa reprise réussie : un échec le laisse à reprendre au
    démarrage suivant (ticket-665, ticket-875). `project_id`, `ticket_id` et
    `started_at` sont lus en base.
    """
    async with aiosqlite.connect(str(db_path)) as db:
        interrompus = await runs_interrompus_a_reprendre(db)
        rows = await lire_runs(db, [*run_ids, *interrompus])

        reussis: list[str] = []
        for run_id, project_id, ticket_id, started_at_str in rows:
            started_at = _lire_started_at(started_at_str)
            if await _reprendre_depot_seul(project_id, ticket_id, workspace_dir, started_at):
                reussis.append(run_id)
        await marquer_depots_repris(db, [r for r in reussis if r in interrompus])


def _lire_started_at(valeur: str) -> datetime:
    """Parse `started_at` as an aware datetime; now when it is unreadable."""
    try:
        started_at = datetime.fromisoformat(valeur)
    except (ValueError, TypeError):
        return datetime.now(UTC)
    return started_at if started_at.tzinfo is not None else started_at.replace(tzinfo=UTC)
