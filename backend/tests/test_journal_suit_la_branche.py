"""Pending pipeline-log lines follow the next run onto its branch — ticket-331.

Les lignes écrites après le push d'une livraison (rebase, PR ouverte, confiée
au CIWatcher) restaient non commitées ; le run suivant les commitait sur la
branche du ticket précédent, déjà poussée, où elles mouraient. Elles doivent
désormais être réécrites dans le journal de la nouvelle branche.
"""
import asyncio
from pathlib import Path

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import journal_en_attente
from tessera.services import pipeline_stages as stages
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun

_LOG = Path("memory") / "pipeline-log.md"
_LIGNE_LIVRAISON = "- 2026-10-03 07:07:27 UTC — [ticket-016] livraison: PR #16 ouverte (4469ms)"


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()
    return stdout.decode().strip()


class _Tickets:
    def __init__(self) -> None:
        self.statuts: list[TicketStatus] = []

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statuts.append(status)


class _Orch:
    def __init__(self, workspace: GitWorkspaceService, racine: Path) -> None:
        self._git_workspace = workspace
        self._project_path = racine
        self._ticket_svc = _Tickets()
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run() -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        pass

    ticket = Ticket(
        id="ticket-017",
        title="Next feature",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body="",
    )
    return PipelineRun(project_id="projet", ticket=ticket, on_event=_on_event)


async def _depot_avec_ticket_livre(root: Path) -> tuple[GitWorkspaceService, str]:
    """develop, then a delivered ticket-016 branch with one pending log line."""
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "memory").mkdir()
    (root / _LOG).write_text("# log\n", encoding="utf-8")
    (root / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "init")
    base = await _git(root, "rev-parse", "HEAD")

    await _git(root, "checkout", "-q", "-b", "ticket-016-old-feat")
    (root / _LOG).write_text("# log\n- ticket 016\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "ticket 016 work")
    # Écrite après le push de la livraison : jamais commitée.
    with (root / _LOG).open("a", encoding="utf-8") as f:
        f.write(_LIGNE_LIVRAISON + "\n")

    workspace = GitWorkspaceService(root)
    workspace._base_ref = base  # type: ignore[assignment]
    return workspace, base


async def test_pending_log_lines_follow_the_new_branch(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    workspace, _ = await _depot_avec_ticket_livre(root)
    tete_precedente = await _git(root, "rev-parse", "ticket-016-old-feat")

    run = _run()
    result = await stages.create_branch(_Orch(workspace, root), run)

    assert result is None
    assert run.branch is not None
    assert await _git(root, "branch", "--show-current") == run.branch
    assert _LIGNE_LIVRAISON in (root / _LOG).read_text(encoding="utf-8")
    # La branche livrée ne reçoit aucun commit portant la ligne.
    assert await _git(root, "rev-parse", "ticket-016-old-feat") == tete_precedente


async def test_a_line_already_in_the_new_branch_log_is_not_duplicated(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    workspace, base = await _depot_avec_ticket_livre(root)
    # La base connaît déjà la ligne (rattrapée à la main, comme la #243).
    await _git(root, "stash", "-q")
    await _git(root, "checkout", "-q", base)
    with (root / _LOG).open("a", encoding="utf-8") as f:
        f.write(_LIGNE_LIVRAISON + "\n")
    await _git(root, "commit", "-q", "-am", "log already caught up")
    nouvelle_base = await _git(root, "rev-parse", "HEAD")
    await _git(root, "checkout", "-q", "ticket-016-old-feat")
    await _git(root, "stash", "pop", "-q")
    workspace._base_ref = nouvelle_base  # type: ignore[assignment]

    run = _run()
    assert await stages.create_branch(_Orch(workspace, root), run) is None

    contenu = (root / _LOG).read_text(encoding="utf-8")
    assert contenu.count(_LIGNE_LIVRAISON) == 1


async def test_log_lines_are_written_back_when_branch_creation_fails(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    workspace, _ = await _depot_avec_ticket_livre(root)
    # Un fichier de code modifié, différent sur la base : le checkout refuse.
    (root / "code.py").write_text("x = 2\n", encoding="utf-8")
    await _git(root, "commit", "-q", "-m", "code on 016", "--", "code.py")
    (root / "code.py").write_text("x = 3\n", encoding="utf-8")

    run = _run()
    result = await stages.create_branch(_Orch(workspace, root), run)

    assert result is not None
    assert result.final_status is TicketStatus.blocked
    assert _LIGNE_LIVRAISON in (root / _LOG).read_text(encoding="utf-8")


async def test_pending_ticket_file_is_still_committed_before_the_switch(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    workspace, base = await _depot_avec_ticket_livre(root)
    tickets = root / "tickets"
    await _git(root, "stash", "-q")
    await _git(root, "checkout", "-q", base)
    tickets.mkdir()
    (tickets / "ticket-016.md").write_text("status: todo\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "ticket file on base")
    nouvelle_base = await _git(root, "rev-parse", "HEAD")
    await _git(root, "checkout", "-q", "ticket-016-old-feat")
    await _git(root, "stash", "pop", "-q")
    # Le retour sur la branche du 016 a retiré le dossier, inconnu d'elle.
    tickets.mkdir(exist_ok=True)
    (tickets / "ticket-016.md").write_text("status: done\n", encoding="utf-8")
    workspace._base_ref = nouvelle_base  # type: ignore[assignment]

    run = _run()
    assert await stages.create_branch(_Orch(workspace, root), run) is None

    fichier = await _git(root, "show", "ticket-016-old-feat:tickets/ticket-016.md")
    assert fichier == "status: done"


async def test_mettre_de_cote_ignores_an_untracked_log(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    await _git(root, "init", "-q")
    (root / "memory").mkdir()
    (root / _LOG).write_text("# log\n- local\n", encoding="utf-8")

    assert await journal_en_attente.mettre_de_cote(root) == []
    assert (root / _LOG).read_text(encoding="utf-8") == "# log\n- local\n"


def test_reecrire_appends_missing_lines_after_an_unterminated_last_line(
    tmp_path: Path,
) -> None:
    (tmp_path / "memory").mkdir()
    (tmp_path / _LOG).write_text("# log\n- a", encoding="utf-8")

    journal_en_attente.reecrire(tmp_path, ["- a", "- b"])

    assert (tmp_path / _LOG).read_text(encoding="utf-8") == "# log\n- a\n- b\n"
