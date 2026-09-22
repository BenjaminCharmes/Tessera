"""Un commit qui echoue ne fait jamais remonter d'exception — ticket-121.

`commit_work` leve `CommitFailed` ; seul `finish_approved` l'attrapait. Sur
`security_block`, `stopped`, `rounds_exhausted`, l'exception remontait a
`_run_pipeline`, qui appelait `finish_interrupted`, qui rappelait
`commit_work`, qui relevait : 500 FastAPI, arbre sale, run jamais clos.
"""

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_outcomes as outcomes
from tessera.services.git_workspace import GitCommandError
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.pipeline_run import PipelineRun


def _ticket(tid: str = "ticket-001") -> Ticket:
    return Ticket(
        id=tid, title="Un ticket", type=TicketType.feat,
        status=TicketStatus.in_progress, priority=TicketPriority.medium,
        agent="codeur", body="",
    )


class _GitQuiEchoue:
    async def commit_all(self, message: str) -> str | None:
        raise GitCommandError(command=["git", "commit"], returncode=1, stderr="index.lock")

    async def advance_base_ref(self) -> None:
        raise AssertionError("un commit rate n'avance pas la ref de base")


class _Tickets:
    def __init__(self) -> None:
        self.statut: TicketStatus | None = None

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statut = status


class _Orch:
    def __init__(self) -> None:
        self._git_workspace = _GitQuiEchoue()
        self._ticket_svc = _Tickets()
        self._max_review_rounds = 3

    def _log(self, message: str) -> None:
        return None


def _run(events: list[OrchestratorEvent]) -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    run = PipelineRun(project_id="p", ticket=_ticket(), on_event=_on_event)
    run.branch = "ticket-001-x"
    run.round_num = 1
    return run


def _verifie_bloque(resultat: PipelineResult, events: list[OrchestratorEvent]) -> None:
    assert resultat.final_status is TicketStatus.blocked
    assert resultat.approved is False
    assert (resultat.arret or "").startswith("commit_failed")
    assert resultat.commit_sha is None
    assert [e for e in events if e.type is EventType.PIPELINE_DONE], (
        "la fin du run doit etre annoncee meme si le commit a echoue"
    )


async def test_un_commit_rate_sur_blocage_securite_rend_un_resultat() -> None:
    # Avant : `CommitFailed` remontait de `finish_security_block` jusqu'a
    # FastAPI. Le run rendait un 500 et restait ouvert en base.
    events: list[OrchestratorEvent] = []
    resultat = await outcomes.finish_security_block(_Orch(), _run(events), "secret en clair")  # type: ignore[arg-type]
    _verifie_bloque(resultat, events)


async def test_un_commit_rate_sur_arret_rend_un_resultat() -> None:
    events: list[OrchestratorEvent] = []
    resultat = await outcomes.finish_stopped(_Orch(), _run(events))  # type: ignore[arg-type]
    _verifie_bloque(resultat, events)


async def test_un_commit_rate_apres_epuisement_des_tours_rend_un_resultat() -> None:
    events: list[OrchestratorEvent] = []
    resultat = await outcomes.finish_rounds_exhausted(_Orch(), _run(events))  # type: ignore[arg-type]
    _verifie_bloque(resultat, events)


async def test_un_commit_rate_sur_interruption_ne_releve_jamais() -> None:
    # C'est le dernier filet : `_run_pipeline` appelle `finish_interrupted`
    # sur toute exception. Si lui-meme leve, plus rien n'attrape.
    events: list[OrchestratorEvent] = []
    resultat = await outcomes.finish_interrupted(  # type: ignore[arg-type]
        _Orch(), _run(events), RuntimeError("plafond atteint")
    )
    _verifie_bloque(resultat, events)
    # La cause d'origine ne doit pas disparaitre derriere l'echec du commit.
    assert "plafond atteint" in (resultat.arret or "")


async def test_un_commit_rate_sur_approbation_nomme_sa_cause() -> None:
    # `finish_approved` attrapait deja l'exception, mais rendait un `blocked`
    # muet : rien dans `arret` ne disait pourquoi le ticket n'etait pas `done`.
    events: list[OrchestratorEvent] = []
    resultat = await outcomes.finish_approved(_Orch(), _run(events))  # type: ignore[arg-type]
    _verifie_bloque(resultat, events)
    assert "index.lock" in (resultat.arret or "")
