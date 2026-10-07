"""Remet d'aplomb les dépôts laissés en cours après un arrêt brutal — ticket-369.

`solder_les_runs_orphelins` clôt en base les runs interrompus, mais laisse
le dépôt du projet tel que le processus tué l'a laissé : arbre sale, fiche
du ticket dans un statut intermédiaire, branche courante sur la branche du
ticket. Ce module comble le gap au démarrage.

Pour chaque run soldé, si la copie de travail est sur la branche du ticket :
1. la fiche du ticket est déplacée dans tickets/todo/ et son statut forcé à todo,
   sur la branche du ticket, avant tout commit ;
2. les changements en cours (fiche incluse) sont commités avec le message des runs
   non approuvés (ADR-018 : l'arbre ne reste jamais sale) ;
3. la copie de travail revient sur la branche de base sans y écrire quoi que ce soit.

La branche de base n'est jamais modifiée : un run suivant ne trouve donc aucune
divergence locale (ticket-375).

Une erreur git est journalisée et n'empêche jamais le démarrage du backend.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
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


async def _reprendre_depot_seul(
    project_id: str,
    ticket_id: str,
    workspace_dir: Path,
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
            extra={
                "project_id": project_id,
                "ticket_id": ticket_id,
                "error": str(exc),
            },
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

    # Lit la fiche avant toute opération : le statut et le chemin sont stables
    # tant qu'on est sur la branche du ticket.
    ticket_svc = TicketService(project_path, project_id)
    ticket_avant = await ticket_svc.get_ticket(ticket_id)
    ticket_contenu: str | None = None
    ticket_nom: str | None = None
    old_ticket_path: Path | None = None
    if ticket_avant is not None and ticket_avant.status in (
        TicketStatus.in_progress,
        TicketStatus.in_review,
    ):
        try:
            old_ticket_path = Path(ticket_avant.file_path)
            ticket_contenu = old_ticket_path.read_text(encoding="utf-8")
            ticket_nom = old_ticket_path.name
        except OSError:
            pass

    try:
        # 1. Remettre la fiche du ticket en todo SUR LA BRANCHE DU TICKET,
        #    avant le commit, pour qu'elle en fasse partie (ticket-375).
        #    La branche de base n'est plus touchée du tout après le checkout.
        todo_path: Path | None = None
        if ticket_contenu is not None and ticket_nom is not None:
            todo_dir = project_path / "tickets" / "todo"
            todo_dir.mkdir(parents=True, exist_ok=True)
            todo_path = todo_dir / ticket_nom
            _ecrire_ticket_todo(todo_path, ticket_contenu)
            # Supprimer l'ancien emplacement s'il diffère du nouveau.
            if old_ticket_path is not None and old_ticket_path != todo_path:
                try:
                    old_ticket_path.unlink()
                except OSError:
                    pass
            _logger.info(
                "reprise_ticket_remis_en_todo_sur_branche_ticket",
                extra={"project_id": project_id, "ticket_id": ticket_id},
            )

        # 2. Commiter les changements en cours (ADR-018 : l'arbre ne reste jamais sale).
        # Seuls les fichiers déjà suivis, dans tout le dépôt (`:/`) : jamais
        # `add -A`. Pour un projet `git_root: ancestor` (ide-core), le dépôt est
        # celui de Tessera entier, et `add -A` y embarquerait les fichiers non
        # suivis et les autres projets de `projects/` comme sous-dépôts. Le
        # pipeline exclut les non-suivis préexistants qu'il a relevés à la
        # création de la branche ; après un arrêt, cette liste est perdue. Un
        # fichier créé par le codeur reste donc dans l'arbre, non suivi : rien
        # n'est perdu, rien d'étranger n'est commité.
        await _git(project_path, "add", "--update", "--", ":/")
        # Ajouter aussi la fiche déplacée dans todo/ : `--update` ne suit que les
        # fichiers déjà connus de l'index, pas les nouveaux emplacements.
        if todo_path is not None:
            rel = todo_path.relative_to(project_path)
            await _git(project_path, "add", "--", rel.as_posix())
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

    except Exception as exc:
        _logger.warning(
            "reprise_erreur_git",
            extra={
                "project_id": project_id,
                "ticket_id": ticket_id,
                "error": str(exc),
            },
        )


async def reprendre_depots_orphelins(
    run_ids: list[str],
    db_path: Path | str,
    workspace_dir: Path,
) -> None:
    """Pour chaque run orphelin soldé, remet d'aplomb le dépôt de son projet.

    Appelée dans le lifespan après `solder_les_runs_orphelins`. Les `run_ids`
    sont ceux retournés par le solde : leurs `project_id` et `ticket_id` sont
    lus en base pour trouver le dépôt à nettoyer.
    """
    if not run_ids:
        return

    async with aiosqlite.connect(str(db_path)) as db:
        placeholders = ",".join("?" * len(run_ids))
        async with db.execute(
            f"SELECT project_id, ticket_id FROM pipeline_runs WHERE id IN ({placeholders})",
            run_ids,
        ) as cursor:
            rows = await cursor.fetchall()

    for project_id, ticket_id in rows:
        await _reprendre_depot_seul(str(project_id), str(ticket_id), workspace_dir)
