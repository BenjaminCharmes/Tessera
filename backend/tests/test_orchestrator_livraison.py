"""La livraison suit chaque run, quel que soit le mode — ticket-084.

Ticket-307 : phase 1 dans run_pipeline, phase 2 dans CIWatcher (ADR-051).
Ticket-378 : après livraison, arbre propre et branche de base active.
"""
import asyncio
from pathlib import Path
from typing import Any

import pytest

from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_fin_de_file import nettoyer_apres_file
from tessera.services.pipeline_events import (
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.models.ticket import Ticket, TicketStatus, TicketType, TicketPriority


def _resultat(ticket_id: str, approuve: bool = True) -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.done if approuve else TicketStatus.blocked,
        rounds=1,
        approved=approuve,
        branch=f"{ticket_id}-slug",
        commit_sha="abc",
    )


class _OrchestrateurDouble(Orchestrator):
    """Orchestrateur dont seul le pipeline interne est doublé.

    Le reste — l'enchaînement de la file, et la livraison qu'on teste ici —
    est le vrai code.
    """

    def __init__(self, resultats: list[PipelineResult], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._resultats = list(resultats)

    async def _run_pipeline(self, *args: Any, **kwargs: Any) -> PipelineResult:
        return self._resultats.pop(0)


def _construire(
    tmp_path: Path, resultats: list[PipelineResult], livrer: Any
) -> _OrchestrateurDouble:
    from unittest.mock import AsyncMock, MagicMock

    tickets = AsyncMock()
    tickets.get_ticket.return_value = None
    return _OrchestrateurDouble(
        resultats,
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=livrer,
    )


async def test_la_livraison_suit_chaque_ticket_d_une_file(tmp_path: Path) -> None:
    # La livraison n'était branchée que sur le run unique : une file de dix
    # tickets n'en livrait aucun, alors que c'est le mode où l'absence de
    # clic compte le plus.
    livres: list[str] = []

    async def _livrer(resultat: PipelineResult) -> Livraison:
        livres.append(resultat.ticket_id)
        return Livraison(pr_number=7, merged=True)

    orch = _construire(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
    )

    resultats = await orch.run_queue("p", ["ticket-001", "ticket-002"])

    assert livres == ["ticket-001", "ticket-002"]
    assert all(r.livraison is not None and r.livraison.merged for r in resultats)


async def test_un_ticket_non_approuve_n_est_pas_livre(tmp_path: Path) -> None:
    livres: list[str] = []

    async def _livrer(resultat: PipelineResult) -> Livraison:
        livres.append(resultat.ticket_id)
        return Livraison()

    orch = _construire(tmp_path, [_resultat("ticket-001", approuve=False)], _livrer)

    await orch.run_pipeline("p", "ticket-001", _rien)

    assert livres == []


async def test_la_livraison_est_annoncee_sur_le_flux(tmp_path: Path) -> None:
    async def _livrer(resultat: PipelineResult) -> Livraison:
        return Livraison(etapes=("PR #7 ouverte",), pr_number=7)

    orch = _construire(tmp_path, [_resultat("ticket-001")], _livrer)
    recus: list[OrchestratorEvent] = []

    async def _capter(event: OrchestratorEvent) -> None:
        recus.append(event)

    await orch.run_pipeline("p", "ticket-001", _capter)

    livraison = [e for e in recus if e.type is EventType.LIVRAISON_DONE]
    assert len(livraison) == 1
    assert livraison[0].data["pr_number"] == 7


async def test_sans_livreur_le_run_est_rendu_tel_quel(tmp_path: Path) -> None:
    # Un orchestrateur construit sans livreur — appel programmatique, test —
    # ne doit pas changer de comportement.
    orch = _construire(tmp_path, [_resultat("ticket-001")], None)

    resultat = await orch.run_pipeline("p", "ticket-001", _rien)

    assert resultat.livraison is None


async def _rien(event: OrchestratorEvent) -> None:
    return None


# ------------------------------------------------------------------
# La documentation se met à jour une fois par lot — ticket-092
# ------------------------------------------------------------------


async def test_la_doc_se_met_a_jour_apres_chaque_ticket_approuve_de_la_file(tmp_path: Path) -> None:
    # Depuis ticket-198 : la documentation part sur la branche de chaque run
    # approuvé, pour sa PR. En fin de file, elle restait sur le disque sans
    # commit, et le run suivant refusait l'arbre sale.
    appels: list[int] = []

    async def _documenter() -> None:
        appels.append(1)

    orch = _construire(
        tmp_path,
        [_resultat(f"ticket-{n:03d}") for n in range(1, 4)],
        None,
    )
    orch._documenter = _documenter  # type: ignore[assignment]

    await orch.run_queue("p", ["ticket-001", "ticket-002", "ticket-003"])

    assert appels == [1, 1, 1]


async def test_un_run_unique_approuve_declenche_la_doc(tmp_path: Path) -> None:
    # Le mode le plus utilisé depuis l'IDE ne documentait jamais : les tickets
    # s'accumulaient derrière le marqueur jusqu'à la fin d'une file (ticket-198).
    appels: list[int] = []

    async def _documenter() -> None:
        appels.append(1)

    orch = _construire(tmp_path, [_resultat("ticket-001")], None)
    orch._documenter = _documenter  # type: ignore[assignment]

    await orch.run_pipeline("p", "ticket-001", _rien)

    assert appels == [1]


async def test_une_doc_qui_echoue_ne_casse_pas_la_file(tmp_path: Path) -> None:
    async def _documenter() -> None:
        raise RuntimeError("provider injoignable")

    orch = _construire(tmp_path, [_resultat("ticket-001")], None)
    orch._documenter = _documenter  # type: ignore[assignment]

    resultats = await orch.run_queue("p", ["ticket-001"])

    assert len(resultats) == 1


# ------------------------------------------------------------------
# ADR-051 — Phase 1 dans run_pipeline, phase 2 dans CIWatcher
# ------------------------------------------------------------------


def _construire_avec_surveiller(
    tmp_path: Path,
    resultats: list[PipelineResult],
    livrer: Any,
    surveiller: Any = None,
    ci_watcher: Any = None,
    ticket_service: Any = None,
) -> _OrchestrateurDouble:
    from unittest.mock import AsyncMock, MagicMock

    if ticket_service is None:
        tickets = AsyncMock()
        tickets.get_ticket.return_value = None
        ticket_service = tickets
    return _OrchestrateurDouble(
        resultats,
        runner=MagicMock(),
        ticket_service=ticket_service,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=livrer,
        surveiller=surveiller,
        ci_watcher=ci_watcher,
    )


async def test_run_approuve_appelle_livrer_phase_1_puis_surveiller(
    tmp_path: Path,
) -> None:
    """Critère 1 : run approuvé → livrer appelé, surveiller délégué en arrière-plan."""
    surveilles: list[tuple[str, str, int]] = []

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, arret=None)

    async def _surveiller(
        project_id: str, ticket_id: str, pr_number: int, on_event: Any
    ) -> None:
        surveilles.append((project_id, ticket_id, pr_number))

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001")],
        _livrer,
        surveiller=_surveiller,
    )

    result = await orch.run_pipeline("proj", "ticket-001", _rien)

    assert result.livraison is not None
    assert result.livraison.pr_number == 7
    # surveiller a été appelé (phase 2 confiée au CIWatcher)
    assert surveilles == [("proj", "ticket-001", 7)]


async def test_pr_orpheline_est_confiee_a_la_surveillance_malgre_son_arret(
    tmp_path: Path,
) -> None:
    """Une phase 1 qui a levé après l'ouverture de la PR passe quand même en phase 2."""
    surveilles: list[tuple[str, str, int]] = []

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(
            pr_number=13,
            arret="Livraison interrompue : TimeoutError",
            pr_orpheline=True,
        )

    async def _surveiller(
        project_id: str, ticket_id: str, pr_number: int, on_event: Any
    ) -> None:
        surveilles.append((project_id, ticket_id, pr_number))

    orch = _construire_avec_surveiller(
        tmp_path, [_resultat("ticket-001")], _livrer, surveiller=_surveiller
    )

    await orch.run_pipeline("proj", "ticket-001", _rien)

    assert surveilles == [("proj", "ticket-001", 13)]


async def test_conflit_resolu_reste_sans_surveillance(tmp_path: Path) -> None:
    """ADR-033 : une PR avec arret mais sans `pr_orpheline` n'est jamais surveillée."""
    surveilles: list[int] = []

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(
            pr_number=13,
            conflits=("src/app.py",),
            arret="Conflit résolu sur src/app.py : la PR #13 est ouverte, à relire.",
        )

    async def _surveiller(
        project_id: str, ticket_id: str, pr_number: int, on_event: Any
    ) -> None:
        surveilles.append(pr_number)

    orch = _construire_avec_surveiller(
        tmp_path, [_resultat("ticket-001")], _livrer, surveiller=_surveiller
    )

    await orch.run_pipeline("proj", "ticket-001", _rien)

    assert surveilles == []


async def test_surveiller_non_appele_sans_pr(tmp_path: Path) -> None:
    """Pas de surveillance quand la phase 1 n'a pas ouvert de PR."""
    surveilles: list[str] = []

    async def _livrer(result: PipelineResult) -> Livraison:
        # Phase 1 arrêtée (rebase refusé, etc.)
        return Livraison(arret="Rebase refusé")

    async def _surveiller(
        project_id: str, ticket_id: str, pr_number: int, on_event: Any
    ) -> None:
        surveilles.append(ticket_id)

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001")],
        _livrer,
        surveiller=_surveiller,
    )

    await orch.run_pipeline("proj", "ticket-001", _rien)

    assert surveilles == []


async def test_run_closed_emis_avant_ci_merge_done(tmp_path: Path) -> None:
    """Critère 2 : run_closed précède ci_merge_done (arrière-plan)."""
    from tessera.services.ci_watcher import CIWatcher
    from tessera.services.pipeline_events import EventType

    watcher = CIWatcher()
    gate = asyncio.Event()
    events_recus: list[OrchestratorEvent] = []

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=42, arret=None)

    async def _phase2_bloquante(pr_number: int) -> Livraison:
        await gate.wait()
        return Livraison(pr_number=pr_number, merged=True)

    async def _surveiller(
        project_id: str, ticket_id: str, pr_number: int, on_event: Any
    ) -> None:
        # Démarre la tâche de fond, retourne immédiatement.
        await watcher.surveiller(project_id, ticket_id, pr_number, _phase2_bloquante, on_event)

    async def _capturer(event: OrchestratorEvent) -> None:
        events_recus.append(event)

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001")],
        _livrer,
        surveiller=_surveiller,
    )

    # run_pipeline retourne avant que la gate soit levée.
    result = await orch.run_pipeline("proj", "ticket-001", _capturer)

    # À ce stade, la phase 2 est bloquée sur la gate : ci_merge_done n'a pas
    # encore été émis.
    ci_done_avant = [e for e in events_recus if e.type is EventType.CI_MERGE_DONE]
    assert ci_done_avant == [], "ci_merge_done ne doit pas être émis avant run_closed"

    # Lever la gate : la phase 2 peut terminer.
    gate.set()
    await asyncio.sleep(0.05)

    ci_done_apres = [e for e in events_recus if e.type is EventType.CI_MERGE_DONE]
    assert len(ci_done_apres) == 1
    assert ci_done_apres[0].data["merged"] is True

    await watcher.arreter()


async def test_ticket_dependant_attend_le_merge_avant_de_demarrer(
    tmp_path: Path,
) -> None:
    """Critère 3 : ticket dépendant attend ci_merge_done avant de démarrer."""
    from unittest.mock import AsyncMock
    from tessera.models.ticket import Ticket

    gate = asyncio.Event()
    departs: list[str] = []

    class _FakeCIWatcher:
        def en_attente(self, project_id: str) -> tuple[str, ...]:
            return ("ticket-001",)

        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> bool:
            await gate.wait()
            return True  # merge succeeded

    def _make_ticket_dep(tid: str, depends_on: list[str]) -> Ticket:
        return Ticket(
            id=tid,
            title="titre",
            type=TicketType.feat,
            status=TicketStatus.todo,
            priority=TicketPriority.medium,
            agent="codeur",
            body="corps",
            depends_on=depends_on,
        )

    ticket_001 = _make_ticket_dep("ticket-001", [])
    ticket_002 = _make_ticket_dep("ticket-002", ["ticket-001"])

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: {
        "ticket-001": ticket_001,
        "ticket-002": ticket_002,
    }.get(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        departs.append(result.ticket_id)
        return Livraison(pr_number=7, arret=None)

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_FakeCIWatcher(),
        ticket_service=tickets,
    )

    # Démarrer la file en arrière-plan.
    tache = asyncio.create_task(
        orch.run_queue("proj", ["ticket-001", "ticket-002"])
    )
    await asyncio.sleep(0.05)

    # ticket-001 a démarré, ticket-002 attend.
    assert "ticket-001" in departs
    assert "ticket-002" not in departs

    # Lever la gate → ticket-002 peut démarrer.
    gate.set()
    await asyncio.sleep(0.05)

    results = await tache
    assert len(results) == 2
    assert "ticket-002" in departs


async def test_ticket_sans_dependance_demarre_sans_attendre(
    tmp_path: Path,
) -> None:
    """Critère 4 : ticket sans dépendance démarre pendant que la PR attend la CI."""
    from unittest.mock import AsyncMock
    from tessera.models.ticket import Ticket

    gate = asyncio.Event()
    departs: list[str] = []

    class _FakeCIWatcher:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> None:
            # Ne doit jamais être appelé pour un ticket sans dépendance.
            raise AssertionError(f"attendre_merge appelé pour {ticket_id}")

    def _make_ticket(tid: str) -> Ticket:
        return Ticket(
            id=tid,
            title="titre",
            type=TicketType.feat,
            status=TicketStatus.todo,
            priority=TicketPriority.medium,
            agent="codeur",
            body="corps",
            depends_on=[],  # pas de dépendance
        )

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: _make_ticket(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        departs.append(result.ticket_id)
        return Livraison(pr_number=7, arret=None)

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_FakeCIWatcher(),
        ticket_service=tickets,
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    # Les deux tickets ont démarré sans attente.
    assert departs == ["ticket-001", "ticket-002"]
    assert len(results) == 2


async def test_livraison_sans_pr_ne_bloque_pas_le_ticket_suivant(
    tmp_path: Path,
) -> None:
    """Critère 5 : livraison échouée sans PR → file continue normalement."""
    from unittest.mock import AsyncMock
    from tessera.models.ticket import Ticket

    departs: list[str] = []

    class _FakeCIWatcher:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> None:
            raise AssertionError("attendre_merge ne doit pas être appelé")

    def _make_ticket(tid: str) -> Ticket:
        return Ticket(
            id=tid, title="t", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="b", depends_on=[],
        )

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: _make_ticket(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        departs.append(result.ticket_id)
        # Phase 1 échouée : exception capturée → pas de PR, arret set
        return Livraison(arret="Livraison interrompue : réseau injoignable")

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_FakeCIWatcher(),
        ticket_service=tickets,
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    # La file n'est pas arrêtée par la livraison échouée.
    assert departs == ["ticket-001", "ticket-002"]
    assert len(results) == 2


# ------------------------------------------------------------------
# ticket-361 — la file s'arrête quand une dépendance n'a pas été livrée
# ------------------------------------------------------------------


async def test_queue_stops_when_approved_no_pr_and_dependent_follows(
    tmp_path: Path,
) -> None:
    """Criteria 1-3: approved ticket with no PR opened, dependent ticket B → queue
    stops before B, livraison.arret names both tickets, log records the
    interruption."""
    from unittest.mock import AsyncMock, MagicMock
    from tessera.models.ticket import Ticket, TicketType, TicketPriority, TicketStatus

    def _make_dep_ticket(tid: str, depends_on: list[str]) -> Ticket:
        return Ticket(
            id=tid, title="t", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="b", depends_on=depends_on,
        )

    ticket_a = _make_dep_ticket("ticket-001", [])
    ticket_b = _make_dep_ticket("ticket-002", ["ticket-001"])

    ticket_svc = AsyncMock()
    ticket_svc.get_ticket.side_effect = lambda tid: {
        "ticket-001": ticket_a,
        "ticket-002": ticket_b,
    }.get(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(arret="404 Not Found : jeton sans accès au dépôt")

    log_path = tmp_path / "memory" / "log.md"
    orch = _OrchestrateurDouble(
        [_resultat("ticket-001"), _resultat("ticket-002")],
        runner=MagicMock(),
        ticket_service=ticket_svc,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log_path,
        livrer=_livrer,
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    # Criterion 1: ticket-002 did not run
    assert len(results) == 1
    assert results[0].ticket_id == "ticket-001"

    # Criterion 2: livraison.arret names ticket-002 and ticket-001
    livraison = results[0].livraison
    assert livraison is not None
    assert livraison.arret is not None
    assert "ticket-002" in livraison.arret
    assert "ticket-001" in livraison.arret

    # Criterion 3: log records the interruption and names the undelivered ticket
    log_content = log_path.read_text(encoding="utf-8")
    assert "file interrompue" in log_content
    assert "ticket-001" in log_content


async def test_queue_continues_when_approved_no_pr_and_no_dependent(
    tmp_path: Path,
) -> None:
    """Criterion 4: approved ticket with no PR opened, next ticket has no
    dependency on it → queue continues normally."""
    from unittest.mock import AsyncMock, MagicMock
    from tessera.models.ticket import Ticket, TicketType, TicketPriority, TicketStatus

    def _make_nodep_ticket(tid: str) -> Ticket:
        return Ticket(
            id=tid, title="t", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="b", depends_on=[],
        )

    ticket_svc = AsyncMock()
    ticket_svc.get_ticket.side_effect = lambda tid: _make_nodep_ticket(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(arret="404 Not Found : jeton sans accès au dépôt")

    orch = _OrchestrateurDouble(
        [_resultat("ticket-001"), _resultat("ticket-002")],
        runner=MagicMock(),
        ticket_service=ticket_svc,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=_livrer,
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    # Both tickets ran
    assert len(results) == 2
    assert results[0].ticket_id == "ticket-001"
    assert results[1].ticket_id == "ticket-002"


# ------------------------------------------------------------------
# ticket-378 — arbre propre et branche de base après livraison
# ------------------------------------------------------------------


async def _git(cwd: Path, *args: str) -> None:
    """Run a git command, assert success."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, f"git {' '.join(args)} failed: {stderr.decode()}"


async def _git_out(cwd: Path, *args: str) -> str:
    """Run a git command and return stdout."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


@pytest.fixture
async def depot_avec_distant(tmp_path: Path) -> tuple[Path, Path]:
    """Bare remote + cloned local repo with a ticket branch ready for delivery.

    Returns (local_path, remote_path). The local repo is on
    ``ticket-001-slug`` with one commit on top of ``main``.
    ``memory/pipeline-log.md`` is tracked on the ticket branch.
    """
    distant = tmp_path / "distant.git"
    distant.mkdir()
    await _git(distant, "init", "--bare", "-q", "-b", "main")

    local = tmp_path / "local"
    proc = await asyncio.create_subprocess_exec(
        "git", "clone", str(distant), str(local),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()

    await _git(local, "config", "user.email", "test@tessera.local")
    await _git(local, "config", "user.name", "Tessera test")

    # Initial commit on main
    (local / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(local, "add", "README.md")
    await _git(local, "commit", "-m", "init")
    await _git(local, "push", "origin", "main")

    # Ticket branch
    await _git(local, "checkout", "-b", "ticket-001-slug")
    (local / "code.py").write_text("x = 1\n", encoding="utf-8")
    (local / "memory").mkdir()
    (local / "memory" / "pipeline-log.md").write_text(
        "- run started\n", encoding="utf-8"
    )
    await _git(local, "add", "code.py", "memory/pipeline-log.md")
    await _git(local, "commit", "-m", "feat: du travail")
    await _git(local, "push", "origin", "ticket-001-slug")

    return local, distant


def _construire_avec_git(
    repo: Path,
    base_branch: str,
    git_ws: GitWorkspaceService,
    resultat: PipelineResult,
) -> "_OrchestrateurDouble":
    """Orchestrator double backed by a real git workspace and base_branch."""
    from unittest.mock import AsyncMock, MagicMock

    tickets = AsyncMock()
    tickets.get_ticket.return_value = None

    log_path = repo / "memory" / "pipeline-log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    async def _livrer_simule(result: PipelineResult) -> Livraison:
        """Simulate phase-1 delivery: commit bookkeeping, return Livraison."""
        await git_ws.commit_bookkeeping()
        return Livraison(
            etapes=("rebase sur main", "PR #7 ouverte"),
            durees_ms=(100.0, 200.0),
            pr_number=7,
        )

    return _OrchestrateurDouble(
        [resultat],
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log_path,
        git_workspace=git_ws,
        base_branch=base_branch,
        livrer=_livrer_simule,
    )


async def test_arbre_propre_apres_livraison(
    depot_avec_distant: tuple[Path, Path],
) -> None:
    """Criterion 1: working tree is clean after a delivered run (ticket-378).

    Tracked files only (--untracked-files=no): the test verifies that
    pipeline-log.md is committed and no tracked file is left modified.
    """
    local, _ = depot_avec_distant
    git_ws = GitWorkspaceService(local)
    res = _resultat("ticket-001")
    res = res.model_copy(update={"branch": "ticket-001-slug"})

    orch = _construire_avec_git(local, "main", git_ws, res)
    await orch.run_pipeline("p", "ticket-001", _rien)

    status = await _git_out(local, "status", "--porcelain", "--untracked-files=no")
    assert status == "", (
        f"working tree must be clean after delivery, got: {status!r}"
    )


async def test_log_livraison_dans_dernier_commit(
    depot_avec_distant: tuple[Path, Path],
) -> None:
    """Criterion 2: the PR line appears in pipeline-log.md of the last
    commit on the ticket branch (ticket-378)."""
    local, _ = depot_avec_distant
    git_ws = GitWorkspaceService(local)
    res = _resultat("ticket-001")
    res = res.model_copy(update={"branch": "ticket-001-slug"})

    orch = _construire_avec_git(local, "main", git_ws, res)
    await orch.run_pipeline("p", "ticket-001", _rien)

    # Read pipeline-log.md from the last commit of the ticket branch
    log_content = await _git_out(
        local, "show", "ticket-001-slug:memory/pipeline-log.md"
    )
    assert "PR #7 ouverte" in log_content, (
        f"'PR #7 ouverte' must appear in the last commit of the ticket branch; "
        f"got:\n{log_content}"
    )


async def test_copie_de_travail_sur_branche_de_base(
    depot_avec_distant: tuple[Path, Path],
) -> None:
    """Criterion 3: after delivery, the working tree is on the base branch
    (ticket-378)."""
    local, _ = depot_avec_distant
    git_ws = GitWorkspaceService(local)
    res = _resultat("ticket-001")
    res = res.model_copy(update={"branch": "ticket-001-slug"})

    orch = _construire_avec_git(local, "main", git_ws, res)
    await orch.run_pipeline("p", "ticket-001", _rien)

    current_branch = await _git_out(local, "rev-parse", "--abbrev-ref", "HEAD")
    assert current_branch == "main", (
        f"working tree must be on 'main' after delivery, got: {current_branch!r}"
    )


async def test_base_sans_nouveau_commit_apres_livraison(
    depot_avec_distant: tuple[Path, Path],
) -> None:
    """Criterion 4: the local base branch receives no new commits during
    delivery (ticket-378)."""
    local, _ = depot_avec_distant
    git_ws = GitWorkspaceService(local)

    # Record the tip of main before delivery
    main_sha_avant = await _git_out(local, "rev-parse", "main")

    res = _resultat("ticket-001")
    res = res.model_copy(update={"branch": "ticket-001-slug"})

    orch = _construire_avec_git(local, "main", git_ws, res)
    await orch.run_pipeline("p", "ticket-001", _rien)

    main_sha_apres = await _git_out(local, "rev-parse", "main")
    assert main_sha_avant == main_sha_apres, (
        "delivery must not add commits to the base branch"
    )


# ------------------------------------------------------------------
# ticket-384 — la file s'arrête quand le merge d'une dépendance échoue
# ------------------------------------------------------------------


async def test_file_s_arrete_quand_dependance_non_mergee(
    tmp_path: Path,
) -> None:
    """A queue stops and logs 'file interrompue : ticket-… non mergé' when
    the merge of a dependency fails."""
    from unittest.mock import AsyncMock
    from tessera.models.ticket import Ticket, TicketType, TicketPriority, TicketStatus

    class _FakeCIWatcherFail:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> bool:
            return False  # merge failed

    def _make_ticket(tid: str, depends_on: list[str]) -> Ticket:
        return Ticket(
            id=tid, title="titre", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="corps", depends_on=depends_on,
        )

    ticket_a = _make_ticket("ticket-001", [])
    ticket_b = _make_ticket("ticket-002", ["ticket-001"])

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: {
        "ticket-001": ticket_a,
        "ticket-002": ticket_b,
    }.get(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, arret=None)

    log_path = tmp_path / "memory" / "log.md"
    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_FakeCIWatcherFail(),
        ticket_service=tickets,
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    # ticket-002 ne doit pas avoir démarré.
    assert len(results) == 1
    assert results[0].ticket_id == "ticket-001"

    # Le log doit enregistrer l'interruption.
    assert log_path.exists(), "pipeline-log.md doit avoir été créé"
    log_content = log_path.read_text(encoding="utf-8")
    assert "file interrompue" in log_content
    assert "ticket-001" in log_content
    assert "non mergé" in log_content


async def test_ticket_independant_continue_quand_dependance_non_mergee(
    tmp_path: Path,
) -> None:
    """A ticket with no dependency on A continues normally even when A's merge
    fails — it is not blocked by A's outcome."""
    from unittest.mock import AsyncMock
    from tessera.models.ticket import Ticket, TicketType, TicketPriority, TicketStatus

    class _FakeCIWatcherFail:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> bool:
            return False  # merge failed — but caller should never reach this

    def _make_ticket(tid: str) -> Ticket:
        return Ticket(
            id=tid, title="titre", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="corps", depends_on=[],  # no dependency
        )

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: _make_ticket(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, arret=None)

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-003")],
        _livrer,
        ci_watcher=_FakeCIWatcherFail(),
        ticket_service=tickets,
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-003"])

    # Les deux tickets doivent avoir tourné : ticket-003 ne dépend pas de ticket-001.
    assert len(results) == 2
    assert results[0].ticket_id == "ticket-001"
    assert results[1].ticket_id == "ticket-003"


# ------------------------------------------------------------------
# ticket-569 — un ticket non mergé n'arrête que ceux qui en dépendent
# ------------------------------------------------------------------


async def _file_avec_dependances(
    tmp_path: Path, deps: dict[str, list[str]], lances: list[str]
) -> tuple[list[PipelineResult], str]:
    """Run a queue of ``deps`` keys whose first ticket never merges.

    ``lances`` are the ids expected to start, in order: the double hands out
    one result per start, whatever ticket is actually run.

    Returns the results and the content of the pipeline log.
    """
    from unittest.mock import AsyncMock
    from tessera.models.ticket import Ticket, TicketType, TicketPriority, TicketStatus

    class _FakeCIWatcherFail:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> bool:
            return False

    par_id = {
        tid: Ticket(
            id=tid, title="titre", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="corps", depends_on=dependances,
        )
        for tid, dependances in deps.items()
    }
    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: par_id.get(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, arret=None)

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat(tid) for tid in lances],
        _livrer,
        ci_watcher=_FakeCIWatcherFail(),
        ticket_service=tickets,
    )
    results = await orch.run_queue("proj", list(deps))
    log_path = tmp_path / "memory" / "log.md"
    return results, log_path.read_text(encoding="utf-8") if log_path.exists() else ""


async def test_dependant_saute_et_la_file_continue_avec_un_independant(
    tmp_path: Path,
) -> None:
    results, _ = await _file_avec_dependances(
        tmp_path,
        {"ticket-001": [], "ticket-002": ["ticket-001"], "ticket-003": []},
        ["ticket-001", "ticket-003"],
    )

    assert [r.ticket_id for r in results] == ["ticket-001", "ticket-003"]


async def test_dependant_transitif_saute_aussi(tmp_path: Path) -> None:
    results, log = await _file_avec_dependances(
        tmp_path,
        {
            "ticket-001": [],
            "ticket-002": ["ticket-001"],
            "ticket-003": ["ticket-002"],
            "ticket-004": [],
        },
        ["ticket-001", "ticket-004"],
    )

    assert [r.ticket_id for r in results] == ["ticket-001", "ticket-004"]
    assert "ticket-003 sauté : dépend de ticket-002, sauté" in log


async def test_ticket_saute_ecrit_sa_dependance_au_journal(tmp_path: Path) -> None:
    _, log = await _file_avec_dependances(
        tmp_path,
        {"ticket-001": [], "ticket-002": ["ticket-001"], "ticket-003": []},
        ["ticket-001", "ticket-003"],
    )

    assert "ticket-002 sauté : dépend de ticket-001, non mergé" in log
    assert "file interrompue" not in log


async def test_file_s_arrete_quand_tous_les_restants_dependent_du_non_merge(
    tmp_path: Path,
) -> None:
    results, log = await _file_avec_dependances(
        tmp_path,
        {
            "ticket-001": [],
            "ticket-002": ["ticket-001"],
            "ticket-003": ["ticket-002"],
        },
        ["ticket-001"],
    )

    assert [r.ticket_id for r in results] == ["ticket-001"]
    assert "file interrompue : ticket-001 non mergé" in log


# ------------------------------------------------------------------
# ticket-382 — merge_without_ci : attendre le merge avant le suivant
# ------------------------------------------------------------------


def _construire_merge_without_ci(
    tmp_path: Path,
    resultats: list[PipelineResult],
    livrer: Any,
    ci_watcher: Any = None,
    ticket_service: Any = None,
    attente_merge_max_s: float = 600.0,
    git_workspace: Any = None,
    base_branch: str | None = None,
) -> _OrchestrateurDouble:
    """Orchestrator double with merge_without_ci=True and a short timeout."""
    from unittest.mock import AsyncMock, MagicMock

    if ticket_service is None:
        tickets = AsyncMock()
        tickets.get_ticket.return_value = None
        ticket_service = tickets
    return _OrchestrateurDouble(
        resultats,
        runner=MagicMock(),
        ticket_service=ticket_service,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=livrer,
        ci_watcher=ci_watcher,
        merge_without_ci=True,
        attente_merge_max_s=attente_merge_max_s,
        git_workspace=git_workspace,
        base_branch=base_branch,
    )


async def test_merge_without_ci_attend_le_merge_avant_ticket_suivant(
    tmp_path: Path,
) -> None:
    """Criterion 1: two independent tickets on merge_without_ci=True — ticket-002
    does not start until ticket-001's merge is signalled."""
    from unittest.mock import AsyncMock

    gate = asyncio.Event()
    departs: list[str] = []

    class _FakeCIWatcher:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> bool:
            await gate.wait()
            return True

    def _make_ticket(tid: str) -> Ticket:
        return Ticket(
            id=tid, title="t", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="b", depends_on=[],
        )

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: _make_ticket(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        departs.append(result.ticket_id)
        return Livraison(pr_number=7, arret=None)

    orch = _construire_merge_without_ci(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_FakeCIWatcher(),
        ticket_service=tickets,
    )

    # Démarrer la file en arrière-plan.
    tache = asyncio.create_task(
        orch.run_queue("proj", ["ticket-001", "ticket-002"])
    )
    await asyncio.sleep(0.05)

    # ticket-001 livré, ticket-002 attend le merge du premier.
    assert "ticket-001" in departs
    assert "ticket-002" not in departs

    # Lever la gate → le merge est signalé, ticket-002 peut démarrer.
    gate.set()
    results = await tache

    assert len(results) == 2
    assert "ticket-002" in departs


async def test_sans_merge_without_ci_ticket_independant_demarre_sans_attendre(
    tmp_path: Path,
) -> None:
    """Criterion 2: without merge_without_ci, independent tickets start without
    waiting for any merge — attendre_merge is never called."""
    from unittest.mock import AsyncMock

    class _FakeCIWatcherNeverResolves:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> bool:
            raise AssertionError("attendre_merge ne doit pas être appelé")

    def _make_ticket(tid: str) -> Ticket:
        return Ticket(
            id=tid, title="t", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="b", depends_on=[],
        )

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: _make_ticket(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, arret=None)

    # Sans merge_without_ci=True (utilise _construire_avec_surveiller standard).
    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_FakeCIWatcherNeverResolves(),
        ticket_service=tickets,
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    assert len(results) == 2
    assert results[0].ticket_id == "ticket-001"
    assert results[1].ticket_id == "ticket-002"


async def test_merge_without_ci_sync_base_depuis_distant_appele(
    tmp_path: Path,
) -> None:
    """Criterion 3: after the merge, sync_base_depuis_distant is called on
    git_workspace with the configured base branch."""
    from unittest.mock import AsyncMock

    class _FakeCIWatcher:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> bool:
            return True  # merge immédiat

    def _make_ticket(tid: str) -> Ticket:
        return Ticket(
            id=tid, title="t", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="b", depends_on=[],
        )

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: _make_ticket(tid)

    sync_appels: list[str] = []
    git_ws = AsyncMock()
    # sync_base_depuis_distant retourne None = succès.
    git_ws.sync_base_depuis_distant.side_effect = lambda branch: (
        sync_appels.append(branch) or None
    )

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, arret=None)

    orch = _construire_merge_without_ci(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_FakeCIWatcher(),
        ticket_service=tickets,
        git_workspace=git_ws,
        base_branch="main",
    )

    await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    # sync appelé une fois, après le merge du premier ticket.
    assert sync_appels == ["main"]


# ------------------------------------------------------------------
# ticket-390 — arbre propre après tout run, livré ou non
# ------------------------------------------------------------------


async def test_queue_unapproved_retourne_sur_base_apres_file_interrompue(
    tmp_path: Path,
) -> None:
    """Criterion 1 (ticket-390): after a queue stopped by an unapproved ticket,
    retourner_sur_base is called with the base branch after the 'file
    interrompue' line has been written to the pipeline log."""
    from unittest.mock import AsyncMock, MagicMock

    log_path = tmp_path / "memory" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    checkout_calls: list[str] = []

    git_ws = AsyncMock()

    async def _retourner(branch: str) -> None:
        # Pipeline-log must already contain 'file interrompue' at this point.
        log_content = log_path.read_text(encoding="utf-8")
        assert "file interrompue" in log_content, (
            f"'file interrompue' not yet logged when retourner_sur_base was called:\n"
            f"{log_content}"
        )
        checkout_calls.append(branch)

    git_ws.retourner_sur_base.side_effect = _retourner

    tickets = AsyncMock()
    tickets.get_ticket.return_value = None

    orch = _OrchestrateurDouble(
        [_resultat("ticket-001", approuve=False)],
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log_path,
        git_workspace=git_ws,
        base_branch="main",
    )

    await orch.run_queue("proj", ["ticket-001"])

    assert checkout_calls == ["main"], (
        f"retourner_sur_base must be called once with 'main', got: {checkout_calls}"
    )


async def test_livraison_sans_pr_appelle_commit_bookkeeping_puis_retour_base(
    tmp_path: Path,
) -> None:
    """Criterion 2 (ticket-390): a delivery stopped without a PR (conflict)
    calls commit_bookkeeping then retourner_sur_base."""
    from unittest.mock import AsyncMock, MagicMock

    calls: list[str] = []
    git_ws = AsyncMock()
    git_ws.commit_bookkeeping.side_effect = lambda: calls.append("commit")
    git_ws.retourner_sur_base.side_effect = (
        lambda branch: calls.append(f"checkout:{branch}")
    )

    async def _livrer(result: PipelineResult) -> Livraison:
        # Delivery stopped on conflict — no PR opened.
        return Livraison(arret="Conflit sur rebase — aucune PR ouverte")

    orch = _OrchestrateurDouble(
        [_resultat("ticket-001")],
        runner=MagicMock(),
        ticket_service=AsyncMock(**{"get_ticket.return_value": None}),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        git_workspace=git_ws,
        base_branch="main",
        livrer=_livrer,
    )

    await orch.run_pipeline("proj", "ticket-001", _rien)

    assert "commit" in calls, "commit_bookkeeping was not called"
    assert "checkout:main" in calls, "retourner_sur_base was not called with 'main'"
    assert calls.index("commit") < calls.index("checkout:main"), (
        "commit_bookkeeping must be called before retourner_sur_base"
    )


async def test_exception_retourner_sur_base_ne_fait_pas_echouer_le_run(
    tmp_path: Path,
) -> None:
    """Criterion 3 (ticket-390): an exception from retourner_sur_base does not
    cause run_pipeline to raise."""
    from unittest.mock import AsyncMock, MagicMock

    git_ws = AsyncMock()
    git_ws.retourner_sur_base.side_effect = RuntimeError("git checkout failed")

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(arret="Conflit sur rebase")

    orch = _OrchestrateurDouble(
        [_resultat("ticket-001")],
        runner=MagicMock(),
        ticket_service=AsyncMock(**{"get_ticket.return_value": None}),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        git_workspace=git_ws,
        base_branch="main",
        livrer=_livrer,
    )

    # Must not raise — the run itself was approved.
    result = await orch.run_pipeline("proj", "ticket-001", _rien)
    assert result.approved


async def test_file_interrompue_est_commitee_dans_bookkeeping(
    depot_avec_distant: tuple[Path, Path],
) -> None:
    """Criterion 4 (ticket-390): the 'file interrompue' line is committed in
    the last bookkeeping commit on the ticket branch; no modification of
    memory/pipeline-log.md remains uncommitted after the queue ends."""
    from unittest.mock import AsyncMock, MagicMock

    local, _ = depot_avec_distant
    git_ws = GitWorkspaceService(local)

    log_path = local / "memory" / "pipeline-log.md"

    tickets = AsyncMock()
    tickets.get_ticket.return_value = None

    orch = _OrchestrateurDouble(
        [_resultat("ticket-001", approuve=False)],
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log_path,
        git_workspace=git_ws,
        base_branch="main",
    )

    await orch.run_queue("proj", ["ticket-001"])

    # After cleanup, the working tree must be on the base branch.
    current_branch = await _git_out(local, "rev-parse", "--abbrev-ref", "HEAD")
    assert current_branch == "main", (
        f"Expected branch 'main' after queue, got: {current_branch!r}"
    )

    # The 'file interrompue' line must be committed on the ticket branch.
    committed_log = await _git_out(
        local, "show", "ticket-001-slug:memory/pipeline-log.md"
    )
    assert "file interrompue" in committed_log, (
        f"'file interrompue' not found in last commit of ticket-001-slug:\n"
        f"{committed_log}"
    )

    # No uncommitted tracked changes anywhere.
    status = await _git_out(local, "status", "--porcelain", "--untracked-files=no")
    assert status == "", f"Working tree must be clean after queue, got: {status!r}"


async def test_merge_without_ci_timeout_continue_et_log(
    tmp_path: Path,
) -> None:
    """Criterion 4: when attente_merge_max_s is exceeded, the queue continues
    to the next ticket and logs the timeout."""
    from unittest.mock import AsyncMock

    class _FakeCIWatcherBlocking:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> bool:
            # Ne se résout jamais — simule un merge qui tarde.
            await asyncio.Event().wait()
            return True  # jamais atteint

    def _make_ticket(tid: str) -> Ticket:
        return Ticket(
            id=tid, title="t", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="b", depends_on=[],
        )

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: _make_ticket(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, arret=None)

    log_path = tmp_path / "memory" / "log.md"
    orch = _construire_merge_without_ci(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_FakeCIWatcherBlocking(),
        ticket_service=tickets,
        attente_merge_max_s=0.01,  # délai très court pour le test
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    # La file continue malgré le timeout.
    assert len(results) == 2

    # Le journal mentionne le délai dépassé.
    log_content = log_path.read_text(encoding="utf-8")
    assert "délai" in log_content


async def test_aucun_commit_de_journal_sur_la_branche_de_base(tmp_path: Path) -> None:
    """Ticket-390 review: when the tree is already on the base branch, the
    bookkeeping is never committed there — a local commit on develop would
    diverge it from the remote."""
    from unittest.mock import AsyncMock, MagicMock

    git_ws = AsyncMock()
    git_ws.branche_courante.return_value = "main"

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(arret="Conflit sur rebase — aucune PR ouverte")

    orch = _OrchestrateurDouble(
        [_resultat("ticket-001")],
        runner=MagicMock(),
        ticket_service=AsyncMock(**{"get_ticket.return_value": None}),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        git_workspace=git_ws,
        base_branch="main",
        livrer=_livrer,
    )

    await orch.run_pipeline("proj", "ticket-001", _rien)
    await nettoyer_apres_file(orch)

    git_ws.commit_bookkeeping.assert_not_called()
    git_ws.retourner_sur_base.assert_called_with("main")


async def test_le_ticket_dependant_part_de_la_base_realignee_apres_le_merge(
    tmp_path: Path,
) -> None:
    """Ticket-403: on a project that waits for its CI, a dependent ticket
    starts only after the base was realigned onto the merge — not from the
    stale local base (ticket-400 had started without ticket-399)."""
    from unittest.mock import AsyncMock, MagicMock
    from tessera.models.ticket import Ticket

    ordre: list[str] = []

    class _FakeCIWatcher:
        async def attendre_merge(
            self, project_id: str, ticket_id: str, **_: Any
        ) -> bool:
            ordre.append(f"merge:{ticket_id}")
            return True

    def _t(tid: str, depends_on: list[str]) -> Ticket:
        return Ticket(
            id=tid, title="titre", type=TicketType.feat, status=TicketStatus.todo,
            priority=TicketPriority.medium, agent="codeur", body="corps",
            depends_on=depends_on,
        )

    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: {
        "ticket-001": _t("ticket-001", []),
        "ticket-002": _t("ticket-002", ["ticket-001"]),
        "ticket-003": _t("ticket-003", []),
    }.get(tid)

    git_ws = AsyncMock()
    git_ws.sync_base_depuis_distant.side_effect = lambda base: ordre.append(
        f"sync:{base}"
    )

    async def _livrer(result: PipelineResult) -> Livraison:
        ordre.append(f"depart:{result.ticket_id}")
        return Livraison(pr_number=7, arret=None)

    orch = _OrchestrateurDouble(
        [_resultat("ticket-001"), _resultat("ticket-002"), _resultat("ticket-003")],
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=_livrer,
        ci_watcher=_FakeCIWatcher(),
        git_workspace=git_ws,
        base_branch="develop",
    )

    await orch.run_queue("proj", ["ticket-001", "ticket-002", "ticket-003"])

    # 001 → attente de son merge → réalignement → 002. Personne ne dépend de 002 :
    # pas d'attente ni de réalignement avant 003.
    assert ordre == [
        "depart:ticket-001",
        "merge:ticket-001",
        "sync:develop",
        "depart:ticket-002",
        "depart:ticket-003",
    ]


# ------------------------------------------------------------------
# ticket-406 — réalignement de la base au départ d'un run
# ------------------------------------------------------------------


def _orchestrateur_de_depart(
    tmp_path: Path, git_ws: Any, base_branch: str | None
) -> Orchestrator:
    from unittest.mock import AsyncMock, MagicMock

    return Orchestrator(
        runner=MagicMock(),
        ticket_service=AsyncMock(),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        git_workspace=git_ws,
        base_branch=base_branch,
    )


def _espace_git_double(ordre: list[str], branche_courante: str = "develop") -> Any:
    from unittest.mock import AsyncMock

    git_ws = AsyncMock()
    git_ws.branche_courante.return_value = branche_courante
    git_ws.initialiser_base_ref.return_value = None

    async def _sync(base: str) -> None:
        ordre.append(f"sync:{base}")

    async def _creer(ticket_id: str, slug: str) -> str:
        ordre.append("create_branch")
        return f"{ticket_id}-slug"

    async def _retour(base: str) -> None:
        ordre.append(f"checkout:{base}")

    git_ws.sync_base_depuis_distant.side_effect = _sync
    git_ws.create_branch.side_effect = _creer
    git_ws.retourner_sur_base.side_effect = _retour
    return git_ws


def _run_de_depart() -> Any:
    from tessera.services.pipeline_run import PipelineRun

    async def _on_event(event: OrchestratorEvent) -> None:
        pass

    ticket = Ticket(
        id="ticket-001", title="t", type=TicketType.feat,
        status=TicketStatus.todo, priority=TicketPriority.medium,
        agent="codeur", body="b",
    )
    return PipelineRun(project_id="proj", ticket=ticket, on_event=_on_event)


async def test_la_base_est_realignee_avant_la_creation_de_la_branche(
    tmp_path: Path,
) -> None:
    from tessera.services import pipeline_branche

    ordre: list[str] = []
    git_ws = _espace_git_double(ordre)
    orch = _orchestrateur_de_depart(tmp_path, git_ws, "develop")

    refused = await pipeline_branche.create_branch(orch, _run_de_depart())

    assert refused is None
    assert ordre == ["sync:develop", "create_branch"]


async def test_un_realignement_refuse_n_empeche_pas_le_run_et_est_journalise(
    tmp_path: Path,
) -> None:
    from tessera.services import pipeline_branche

    ordre: list[str] = []
    git_ws = _espace_git_double(ordre)
    git_ws.sync_base_depuis_distant.side_effect = None
    git_ws.sync_base_depuis_distant.return_value = "fetch origin develop échoué"
    orch = _orchestrateur_de_depart(tmp_path, git_ws, "develop")
    run = _run_de_depart()

    refused = await pipeline_branche.create_branch(orch, run)

    assert refused is None
    assert run.branch == "ticket-001-slug"
    journal = (tmp_path / "memory" / "log.md").read_text(encoding="utf-8")
    assert "base non réalignée — fetch origin develop échoué" in journal


async def test_aucun_realignement_sans_espace_git_ni_branche_de_base(
    tmp_path: Path,
) -> None:
    from tessera.services import pipeline_branche

    ordre: list[str] = []
    git_ws = _espace_git_double(ordre)
    sans_base = _orchestrateur_de_depart(tmp_path, git_ws, None)

    assert await pipeline_branche.create_branch(sans_base, _run_de_depart()) is None
    git_ws.sync_base_depuis_distant.assert_not_called()

    sans_espace = _orchestrateur_de_depart(tmp_path, None, "develop")
    assert await pipeline_branche.create_branch(sans_espace, _run_de_depart()) is None


async def test_l_arbre_reste_sur_une_branche_de_ticket_revient_sur_la_base_avant_le_realignement(
    tmp_path: Path,
) -> None:
    from tessera.services import pipeline_branche

    ordre: list[str] = []
    git_ws = _espace_git_double(ordre, branche_courante="ticket-000-ancien")
    orch = _orchestrateur_de_depart(tmp_path, git_ws, "develop")

    assert await pipeline_branche.create_branch(orch, _run_de_depart()) is None

    assert ordre == ["checkout:develop", "sync:develop", "create_branch"]


async def test_un_retour_sur_la_base_refuse_est_journalise_et_le_run_demarre(
    tmp_path: Path,
) -> None:
    from tessera.services import pipeline_branche
    from tessera.services.git_workspace import GitCommandError

    ordre: list[str] = []
    git_ws = _espace_git_double(ordre, branche_courante="ticket-000-ancien")
    git_ws.retourner_sur_base.side_effect = GitCommandError(
        command=["git", "checkout", "develop"], returncode=1, stderr="refused"
    )
    orch = _orchestrateur_de_depart(tmp_path, git_ws, "develop")
    run = _run_de_depart()

    assert await pipeline_branche.create_branch(orch, run) is None

    git_ws.sync_base_depuis_distant.assert_not_called()
    assert run.branch == "ticket-001-slug"
    journal = (tmp_path / "memory" / "log.md").read_text(encoding="utf-8")
    assert "base non réalignée" in journal


async def test_le_depart_sur_la_base_ne_commite_pas_la_tenue_de_livres(
    tmp_path: Path,
) -> None:
    from tessera.services import pipeline_branche

    git_ws = _espace_git_double([], branche_courante="develop")
    orch = _orchestrateur_de_depart(tmp_path, git_ws, "develop")

    assert await pipeline_branche.create_branch(orch, _run_de_depart()) is None

    git_ws.commit_bookkeeping.assert_not_called()


async def test_merge_without_ci_une_pr_non_mergee_fait_sauter_ses_dependants(
    tmp_path: Path,
) -> None:
    """ticket-666: with merge_without_ci, an unmerged PR skips its dependents
    (ADR-060) instead of letting them start without its code."""
    from unittest.mock import AsyncMock

    class _CIWatcherNonMerge:
        async def attendre_merge(self, project_id: str, ticket_id: str, **_: Any) -> bool:
            return False

    deps = {"ticket-001": [], "ticket-002": ["ticket-001"], "ticket-003": []}
    par_id = {
        tid: Ticket(
            id=tid, title="t", type=TicketType.feat,
            status=TicketStatus.todo, priority=TicketPriority.medium,
            agent="codeur", body="b", depends_on=d,
        )
        for tid, d in deps.items()
    }
    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: par_id.get(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=39, arret=None)

    orch = _construire_merge_without_ci(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-003")],
        _livrer,
        ci_watcher=_CIWatcherNonMerge(),
        ticket_service=tickets,
    )
    results = await orch.run_queue("proj", list(deps))

    assert [r.ticket_id for r in results] == ["ticket-001", "ticket-003"]
    log = (tmp_path / "memory" / "log.md").read_text(encoding="utf-8")
    assert "ticket-002 sauté : dépend de ticket-001, non mergé" in log

