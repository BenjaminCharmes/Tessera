"""Un run ne peut pas se dire approuve sans avoir commite — ticket-068."""
from pathlib import Path

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_outcomes as outcomes
from tessera.services.git_workspace import GitCommandError
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun


def _ticket() -> Ticket:
    return Ticket(
        id="ticket-001", title="Un ticket", type=TicketType.feat,
        status=TicketStatus.in_progress, priority=TicketPriority.medium,
        agent="codeur", body="",
    )


class _Git:
    def __init__(self, sha: str | None = "abc1234", erreur: bool = False) -> None:
        self._sha, self._erreur = sha, erreur
        self.base_avancee = False

    async def commit_all(self, message: str) -> str | None:
        if self._erreur:
            raise GitCommandError(command=["git", "commit"], returncode=1, stderr="boom")
        return self._sha

    async def advance_base_ref(self) -> None:
        self.base_avancee = True


class _Orch:
    def __init__(self, git: _Git) -> None:
        self._git_workspace = git
        self._ticket_svc = _Tickets()
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


class _Tickets:
    def __init__(self) -> None:
        self.statut: TicketStatus | None = None

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statut = status


def _run(events: list[OrchestratorEvent]) -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    run = PipelineRun(project_id="p", ticket=_ticket(), on_event=_on_event)
    run.branch = "ticket-001-x"
    run.round_num = 2
    return run


async def test_un_commit_qui_echoue_empeche_l_approbation() -> None:
    # Panne vecue le 2026-09-17 : `commit_failed` partait en warning cote
    # serveur, le run annoncait APPROVED, le ticket passait `done`, et le
    # travail restait dans l'arbre — ce qui bloquait le ticket suivant sans
    # que rien a l'ecran ne dise pourquoi.
    events: list[OrchestratorEvent] = []
    orch = _Orch(_Git(erreur=True))

    resultat = await outcomes.finish_approved(orch, _run(events))  # type: ignore[arg-type]

    assert resultat.approved is False
    assert resultat.final_status is TicketStatus.blocked
    erreurs = [e for e in events if e.type is EventType.ERROR]
    assert erreurs, "l'echec doit etre emis, pas seulement journalise"
    assert erreurs[0].data["reason"] == "commit_failed"


async def test_un_commit_qui_echoue_n_avance_pas_la_ref_de_base() -> None:
    # Sinon le ticket suivant partirait d'une base qui ne contient pas le
    # travail qu'on croit avoir commite.
    git = _Git(erreur=True)
    await outcomes.finish_approved(_Orch(git), _run([]))  # type: ignore[arg-type]

    assert git.base_avancee is False


async def test_rien_a_committer_reste_un_succes() -> None:
    # Un ticket dont le travail existait deja n'a rien a committer : ce n'est
    # pas un echec, et ca doit se distinguer d'un commit rate.
    events: list[OrchestratorEvent] = []
    resultat = await outcomes.finish_approved(_Orch(_Git(sha=None)), _run(events))  # type: ignore[arg-type]

    assert resultat.approved is True
    assert resultat.final_status is TicketStatus.done
    assert not [e for e in events if e.type is EventType.ERROR]


async def test_un_commit_reussi_avance_la_ref_de_base() -> None:
    git = _Git(sha="abc1234")
    resultat = await outcomes.finish_approved(_Orch(git), _run([]))  # type: ignore[arg-type]

    assert resultat.approved is True
    assert resultat.commit_sha == "abc1234"
    assert git.base_avancee is True


async def test_un_titre_sur_deux_lignes_donne_un_sujet_sur_une_ligne() -> None:
    # Un `title: >` YAML replié rend un titre avec un saut de ligne. Interpolé
    # tel quel dans le sujet du commit, il coupait le message en sujet + corps
    # et `git log --oneline` montrait un sujet tronqué (ticket-122).
    git = _Git()
    orch = _Orch(git)
    messages: list[str] = []

    async def _commit_all(message: str) -> str | None:
        messages.append(message)
        return "abc1234"

    git.commit_all = _commit_all  # type: ignore[method-assign]
    run = _run([])
    run.ticket.title = "Première ligne\ndeuxième ligne"

    await outcomes.finish_approved(orch, run)  # type: ignore[arg-type]

    assert len(messages) == 1
    assert "\n" not in messages[0]
    assert messages[0] == "feat: ticket-001 — Première ligne deuxième ligne"
