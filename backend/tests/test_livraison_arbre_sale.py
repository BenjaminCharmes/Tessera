"""La livraison bute sur l'arbre que le pipeline vient de salir — ticket-159.

Premier run approuve du projet demineur : tout au vert, commit `feat:` ecrit,
puis la livraison rend `git rebase --abort : fatal: no rebase in progress`.
Deux defauts enchaines, corriges separement ici.
"""

import asyncio
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_outcomes as outcomes
from tessera.services.git_workspace import GitCommandError, GitWorkspaceService
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun


async def _git(cwd: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@Tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(root, "add", "README.md")
    await _git(root, "commit", "-q", "-m", "init")
    return root


# --- Defaut 1 : l'arbre est sale quand la livraison commence ----------------


def _ticket() -> Ticket:
    return Ticket(
        id="ticket-001", title="Le modele de grille", type=TicketType.feat,
        status=TicketStatus.in_review, priority=TicketPriority.medium,
        agent="codeur", body="",
    )


class _Tickets:
    """Note l'ordre reel : le deplacement du fichier, puis les commits."""

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self._journal.append(f"statut:{status.value}")


class _Git:
    def __init__(self, journal: list[str]) -> None:
        self._journal = journal

    async def commit_all(self, message: str) -> str | None:
        self._journal.append("commit")
        return "abc1234"

    async def advance_base_ref(self) -> None:
        self._journal.append("advance")


class _Orch:
    def __init__(self, journal: list[str]) -> None:
        self._git_workspace = _Git(journal)
        self._ticket_svc = _Tickets(journal)
        self._max_review_rounds = 3

    def _log(self, message: str) -> None:
        return None


async def test_le_ticket_est_deplace_avant_le_commit_de_fin_de_run() -> None:
    """Sinon le deplacement reste non commite et `git rebase` refuse de demarrer.

    ADR-018 veut un arbre propre a la sortie du run. `finish_approved` etait le
    seul `finish_*` a committer avant de bouger le fichier du ticket : le
    deplacement de `in-review/` vers `done/` restait dans l'arbre, et la
    livraison qui suit immediatement trouvait `D tickets/in-review/...` plus un
    `tickets/done/` non suivi.
    """
    journal: list[str] = []
    events: list[OrchestratorEvent] = []

    async def _on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    run = PipelineRun(project_id="p", ticket=_ticket(), on_event=_on_event)
    run.branch = "ticket-001-x"
    run.round_num = 1

    resultat = await outcomes.finish_approved(_Orch(journal), run)

    assert resultat.approved is True
    assert journal.index("statut:done") < journal.index("commit"), (
        f"le deplacement du ticket doit entrer dans le commit de fin de run : {journal}"
    )


# --- Defaut 2 : `rebase --abort` sans rebase en cours -----------------------


async def test_un_rebase_refuse_sur_arbre_sale_remonte_sa_propre_erreur(
    repo: Path,
) -> None:
    """`--abort` ne doit pas masquer la cause reelle.

    Un rebase refuse **sans conflit** n'a rien laisse en cours : l'annuler leve
    a son tour, et c'est cette seconde erreur qui remontait. Le message final
    parlait donc de `no rebase in progress`, jamais de l'arbre sale.
    """
    await _git(repo, "checkout", "-q", "-b", "ticket-001-x")
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(repo, "add", "code.py")
    await _git(repo, "commit", "-q", "-m", "feat: du travail")

    # Ce que le pipeline laissait derriere lui : une modification non commitee.
    (repo / "README.md").write_text("# projet modifie\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    with pytest.raises(GitCommandError) as leve:
        await service.rejouer_sur("main")

    message = str(leve.value).lower()
    assert "no rebase in progress" not in message, (
        f"l'erreur de `--abort` masque la cause reelle : {message}"
    )
    assert "rebase" in " ".join(leve.value.command)


async def test_un_rebase_sans_conflit_ni_echec_ne_remonte_rien(repo: Path) -> None:
    """Le cas nominal reste silencieux : rien a annuler, rien a lever."""
    await _git(repo, "checkout", "-q", "-b", "ticket-001-x")
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(repo, "add", "code.py")
    await _git(repo, "commit", "-q", "-m", "feat: du travail")

    service = GitWorkspaceService(repo)
    assert await service.rejouer_sur("main") == ()


# --- Le critere d'acceptation, de bout en bout -----------------------------


async def test_un_run_approuve_laisse_l_arbre_propre(repo: Path) -> None:
    """Deplacement du ticket compris — la prémisse d'ADR-018, verifiee pour de vrai.

    Vrai depot, vrai `TicketService`, vrai `GitWorkspaceService` : seuls les
    agents manquent. C'est la forme exacte de la panne du premier run approuve
    du projet demineur, ou l'arbre portait `D tickets/in-review/...` et un
    `tickets/done/` non suivi au moment ou la livraison demarrait.
    """
    from tessera.services.ticket_service import TicketService

    tickets = repo / "tickets" / "in-review"
    tickets.mkdir(parents=True)
    (tickets / "ticket-001-modele-de-grille.md").write_text(
        "---\n"
        "id: ticket-001\n"
        'title: "Le modele de grille"\n'
        "type: feat\n"
        "status: in-review\n"
        "priority: medium\n"
        "agent: codeur\n"
        "---\n\n# ticket-001\n",
        encoding="utf-8",
    )
    await _git(repo, "add", "tickets")
    await _git(repo, "commit", "-q", "-m", "chore: le ticket")
    await _git(repo, "checkout", "-q", "-b", "ticket-001-x")

    git = GitWorkspaceService(repo)
    await git.create_branch("ticket-001", "modele-de-grille")
    (repo / "grille.py").write_text("GRILLE = []\n", encoding="utf-8")

    class _OrchReel:
        def __init__(self) -> None:
            self._git_workspace = git
            self._ticket_svc = TicketService(repo, "demineur")
            self._max_review_rounds = 3

        def _log(self, message: str) -> None:
            return None

    events: list[OrchestratorEvent] = []

    async def _on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    run = PipelineRun(project_id="demineur", ticket=_ticket(), on_event=_on_event)
    run.branch = "ticket-001-modele-de-grille"
    run.round_num = 1

    resultat = await outcomes.finish_approved(_OrchReel(), run)

    assert resultat.approved is True
    assert (repo / "tickets" / "done" / "ticket-001-modele-de-grille.md").exists()
    assert await git.is_clean(), (
        "l'arbre doit etre propre a la sortie : la livraison enchaine tout de suite"
    )
