"""Arreter un run en cours — ticket-069."""
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.dialogue import DialogueChannel
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun


def _run() -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        return None

    return PipelineRun(
        project_id="p",
        ticket=Ticket(
            id="ticket-001", title="T", type=TicketType.feat,
            status=TicketStatus.in_progress, priority=TicketPriority.medium,
            agent="codeur", body="",
        ),
        on_event=_on_event,
    )


def test_un_run_ne_demande_pas_son_arret_par_defaut() -> None:
    assert _run().stop_requested is False


def test_l_arret_se_demande_par_le_canal_de_dialogue() -> None:
    # Le canal est deja le chemin par lequel l'utilisateur parle a un run en
    # cours : y ajouter l'arret evite d'inventer un second transport.
    canal = DialogueChannel(interactive=True)
    run = _run()
    run.dialogue = canal

    canal.request_stop()

    assert run.stop_requested is True


def test_l_arret_debloque_une_question_en_attente() -> None:
    # Sinon arreter un run suspendu sur une question ne ferait rien : il
    # resterait bloque jusqu'au delai d'ADR-025.
    canal = DialogueChannel(timeout_s=60.0, interactive=True)
    canal.request_stop()

    assert canal.stop_requested is True


async def test_une_question_posee_apres_un_arret_ne_bloque_pas() -> None:
    import asyncio

    canal = DialogueChannel(timeout_s=60.0, interactive=True)
    canal.request_stop()

    reponse = await asyncio.wait_for(canal.ask("On continue ?"), timeout=1.0)

    assert "arrêt" in reponse.lower()


# ------------------------------------------------------------------
# Sortie du pipeline sur arret
# ------------------------------------------------------------------


class _Git:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def commit_all(self, message: str) -> str:
        self.messages.append(message)
        return "abc1234"

    async def advance_base_ref(self) -> None:
        raise AssertionError("un run arrete ne doit pas avancer la ref de base")


class _Tickets:
    def __init__(self) -> None:
        self.statut: TicketStatus | None = None

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statut = status


class _Orch:
    def __init__(self, git: _Git) -> None:
        self._git_workspace = git
        self._ticket_svc = _Tickets()
        self._max_review_rounds = 3
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


async def test_un_run_arrete_commite_son_travail() -> None:
    # ADR-018 : chaque run laisse l'arbre propre pour le suivant. Un arret qui
    # abandonnerait le travail dans l'arbre bloquerait le ticket suivant, ce
    # qu'on vient justement de corriger ailleurs.
    from tessera.services import pipeline_outcomes as outcomes

    git = _Git()
    orch = _Orch(git)
    run = _run()
    run.branch = "ticket-001-x"
    run.round_num = 1

    resultat = await outcomes.finish_stopped(orch, run)  # type: ignore[arg-type]

    assert resultat.approved is False
    assert resultat.final_status is TicketStatus.blocked
    assert git.messages, "le travail doit etre commite"
    assert "arrêt" in git.messages[0].lower() or "stopped" in git.messages[0].lower()


async def test_un_run_arrete_annonce_la_raison() -> None:
    from tessera.services import pipeline_outcomes as outcomes

    events: list[OrchestratorEvent] = []

    async def _on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    run = _run()
    run.on_event = _on_event
    run.branch = "ticket-001-x"

    await outcomes.finish_stopped(_Orch(_Git()), run)  # type: ignore[arg-type]

    raisons = [e.data.get("reason") for e in events if e.type is EventType.ERROR]
    assert "stopped_by_user" in raisons
