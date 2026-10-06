"""Tests unitaires des étapes du pipeline — ticket-046.

Les tests de `test_orchestrator.py` exercent l'enchaînement complet. Ceux-ci
exercent chaque étape isolément : c'est ce que la décomposition rend possible,
et ce qui permet de couvrir un cas limite sans monter tout un pipeline.
"""
import asyncio
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_stages as stages
from tessera.services.git_workspace import GitCommandError, GitWorkspaceService, NotAGitRepository
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun


async def _git(cwd: Path, *args: str) -> None:
    """Helper: run a git command in a test fixture repo."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()


async def _git_out(cwd: Path, *args: str) -> str:
    """Helper: run a git command and return its stdout."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()
    return stdout.decode().strip()


def _ticket(**kwargs: object) -> Ticket:
    base = dict(
        id="ticket-001",
        title="Test feature",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body="## Critères d'acceptation\n- [ ] ça marche\n",
    )
    base.update(kwargs)
    return Ticket(**base)  # type: ignore[arg-type]


class _Orch:
    """Orchestrateur minimal : seuls les attributs que l'étape testée lit."""

    def __init__(self, **attrs: object) -> None:
        self._git_workspace = None
        self._project_context = "contexte projet"
        self._test_runner = None
        self._project_path = None
        self._test_command = None
        self._security_auditor = None
        self._validator = None
        self.logs: list[str] = []
        for k, v in attrs.items():
            setattr(self, k, v)

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run(events: list[OrchestratorEvent] | None = None) -> PipelineRun:
    collected = events if events is not None else []

    async def _on_event(event: OrchestratorEvent) -> None:
        collected.append(event)

    return PipelineRun(project_id="projet", ticket=_ticket(), on_event=_on_event)


# ------------------------------------------------------------------
# build_context
# ------------------------------------------------------------------


def test_build_context_sans_retour_rend_le_contexte_projet_tel_quel() -> None:
    assert stages.build_context(_Orch(), _run()) == "contexte projet"


def test_build_context_accumule_les_retours_du_reviewer() -> None:
    run = _run()
    run.review_feedback = ["manque des tests", "nommage à revoir"]

    context = stages.build_context(_Orch(), run)

    assert context.startswith("contexte projet")
    assert "Tour 1: manque des tests" in context
    assert "Tour 2: nommage à revoir" in context


# ------------------------------------------------------------------
# ensure_clean_tree
# ------------------------------------------------------------------


async def test_ensure_clean_tree_laisse_passer_sans_git() -> None:
    assert await stages.ensure_clean_tree(_Orch(), _run()) is None


async def test_ensure_clean_tree_bloque_le_ticket_sur_un_arbre_sale() -> None:
    # Le ticket ne doit surtout pas rester en `todo` : `pick_next_ticket` le
    # resservirait à chaque slot restant d'un run autonome.
    class _DirtyGit:
        async def is_clean(self) -> bool:
            return False

        async def dirty_files(self) -> list[str]:
            return []

    class _TicketSvc:
        def __init__(self) -> None:
            self.statuses: list[TicketStatus] = []

        async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
            self.statuses.append(status)

    svc = _TicketSvc()
    events: list[OrchestratorEvent] = []
    orch = _Orch(_git_workspace=_DirtyGit(), _ticket_svc=svc)

    result = await stages.ensure_clean_tree(orch, _run(events))

    assert result is not None
    assert result.final_status == TicketStatus.blocked
    assert result.rounds == 0
    assert svc.statuses == [TicketStatus.blocked]
    assert any(e.type == EventType.ERROR for e in events)


async def test_ensure_clean_tree_porte_la_liste_des_fichiers_dans_l_evenement_error() -> None:
    """The error event carries the list of blocking files (ticket-323)."""
    class _DirtyGit:
        async def is_clean(self) -> bool:
            return False

        async def dirty_files(self) -> list[str]:
            return ["src/feature.py", "README.md"]

    class _TicketSvc:
        async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
            pass

    events: list[OrchestratorEvent] = []
    orch = _Orch(_git_workspace=_DirtyGit(), _ticket_svc=_TicketSvc())

    result = await stages.ensure_clean_tree(orch, _run(events))

    assert result is not None
    error_events = [e for e in events if e.type == EventType.ERROR]
    assert len(error_events) == 1
    fichiers = error_events[0].data.get("fichiers")
    assert isinstance(fichiers, list)
    assert "src/feature.py" in fichiers
    assert "README.md" in fichiers


async def test_ensure_clean_tree_laisse_passer_si_le_controle_git_echoue() -> None:
    # Un dépôt cassé ne doit pas empêcher de travailler : le garde-fou est un
    # filet de sécurité, pas une condition de démarrage.
    class _BrokenGit:
        async def is_clean(self) -> bool:
            raise GitCommandError(command=["git", "status"], returncode=128, stderr="boom")

    assert await stages.ensure_clean_tree(_Orch(_git_workspace=_BrokenGit()), _run()) is None


async def test_ensure_clean_tree_laisse_passer_quand_seul_le_journal_est_modifie(
    tmp_path: Path,
) -> None:
    """A queue that skips done tickets must not block the next real ticket (ticket-278).

    `run_queue` calls `_log` for each skipped ticket, which appends to
    `memory/pipeline-log.md`.  When `ensure_clean_tree` runs for the next
    ticket, only the pipeline log is dirty — a modification the orchestrator
    made itself.  It must be treated as clean.
    """
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")

    # Track README and pipeline log so both appear in the index.
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    (root / "memory").mkdir()
    (root / "memory" / "pipeline-log.md").write_text("# log\n", encoding="utf-8")
    await _git(root, "add", "README.md", "memory/pipeline-log.md")
    await _git(root, "commit", "-q", "-m", "init")

    # Simulate what _log writes when run_queue skips already-done tickets.
    (root / "memory" / "pipeline-log.md").write_text(
        "# log\n- ticket-006 saute : deja termine\n", encoding="utf-8"
    )

    workspace = GitWorkspaceService(root)
    result = await stages.ensure_clean_tree(_Orch(_git_workspace=workspace), _run())

    assert result is None, "Le journal modifie par _log ne doit pas bloquer le ticket suivant"


# ------------------------------------------------------------------
# create_branch
# ------------------------------------------------------------------


async def test_create_branch_degrade_sans_depot_git() -> None:
    # Un projet sans dépôt git reste utilisable : on continue sans branche.
    # NotAGitRepository est la seule erreur qui autorise ce repli (ticket-314).
    class _NoRepoGit:
        async def commit_bookkeeping(self) -> None:
            pass

        async def initialiser_base_ref(
            self, base_branch: str | None = None, *, exiger_distant: bool = False
        ) -> str | None:
            return None

        async def create_branch(self, ticket_id: str, slug: str) -> str:
            raise NotAGitRepository(
                command=["git", "checkout"], returncode=128, stderr="not a git repository"
            )

    run = _run()
    result = await stages.create_branch(_Orch(_git_workspace=_NoRepoGit()), run)

    assert result is None
    assert run.branch is None


async def test_create_branch_renseigne_la_branche_et_emet_l_evenement() -> None:
    class _Git:
        async def commit_bookkeeping(self) -> None:
            pass

        async def initialiser_base_ref(
            self, base_branch: str | None = None, *, exiger_distant: bool = False
        ) -> str | None:
            return None

        async def create_branch(self, ticket_id: str, slug: str) -> str:
            return f"{ticket_id}-slug"

    events: list[OrchestratorEvent] = []
    run = _run(events)
    await stages.create_branch(_Orch(_git_workspace=_Git()), run)

    assert run.branch == "ticket-001-slug"
    assert [e.type for e in events] == [EventType.BRANCH_CREATED]


async def test_create_branch_git_command_error_bloque_le_run() -> None:
    """A GitCommandError from create_branch blocks the run — ticket-314, criterion 1.

    Only ``NotAGitRepository`` allows continuing without a branch.  Any other
    git failure on a real repository must stop the pipeline so that the coder
    agent never runs on the wrong branch.
    """
    class _GitAvecErreur:
        async def commit_bookkeeping(self) -> None:
            pass

        async def initialiser_base_ref(
            self, base_branch: str | None = None, *, exiger_distant: bool = False
        ) -> str | None:
            return None

        async def create_branch(self, ticket_id: str, slug: str) -> str:
            raise GitCommandError(
                command=["git", "checkout", "-b"],
                returncode=1,
                stderr=(
                    "error: Your local changes to the following files would be "
                    "overwritten by checkout:\n        code.py\nAborting"
                ),
            )

    svc = _Tickets()
    events: list[OrchestratorEvent] = []
    run = _run(events)
    result = await stages.create_branch(
        _Orch(_git_workspace=_GitAvecErreur(), _ticket_svc=svc), run
    )

    assert result is not None
    assert result.final_status is TicketStatus.blocked
    assert result.approved is False
    assert result.arret is not None
    assert "overwritten" in result.arret
    assert run.branch is None
    assert TicketStatus.blocked in svc.statuts
    assert any(e.type == EventType.ERROR for e in events)


async def test_create_branch_commit_bookkeeping_avant_le_checkout(
    tmp_path: Path,
) -> None:
    """Pending bookkeeping is committed before the branch switch — ticket-314, criterion 3.

    Reproduces the real failure: pipeline-log.md is modified in the working
    tree, and the base (develop) has a different version of it.  Without the
    fix, ``git checkout -b`` refuses the switch.  With it, the log is committed
    first and the new branch is created successfully.

    The orchestrator here has no project path, so the pending log lines are
    not carried to the new branch (ticket-331): this is the fallback, where
    the bookkeeping commit takes them as before.
    """
    root = tmp_path / "repo"
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")

    # Initial commit: pipeline-log at version A (represents develop state)
    (root / "memory").mkdir()
    (root / "memory" / "pipeline-log.md").write_text("# log\n", encoding="utf-8")
    (root / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "init")
    initial_sha = await _git_out(root, "rev-parse", "HEAD")

    # Ticket-016 branch: pipeline-log at version B (differs from A on develop)
    await _git(root, "checkout", "-q", "-b", "ticket-016-old-feat")
    (root / "memory" / "pipeline-log.md").write_text(
        "# log\n- ticket 016\n", encoding="utf-8"
    )
    await _git(root, "add", "memory/pipeline-log.md")
    await _git(root, "commit", "-q", "-m", "ticket 016 work")

    # Interrupted delivery left pipeline-log uncommitted at version C
    (root / "memory" / "pipeline-log.md").write_text(
        "# log\n- ticket 016\n- delivery note\n", encoding="utf-8"
    )

    # Workspace on ticket-016, base_ref forced to the initial commit (like develop)
    workspace = GitWorkspaceService(root)
    workspace._base_ref = initial_sha  # type: ignore[assignment]

    class _Svc:
        async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
            pass

    events: list[OrchestratorEvent] = []
    run = _run(events)
    result = await stages.create_branch(
        _Orch(_git_workspace=workspace, _ticket_svc=_Svc()), run
    )

    # Branch was created: bookkeeping commit cleared the obstacle
    assert result is None, "Branch creation should succeed after committing bookkeeping"
    assert run.branch is not None

    # The pipeline-log modification was committed on the previous branch
    await _git(root, "checkout", "-q", "ticket-016-old-feat")
    log_content = (root / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert "delivery note" in log_content, (
        "Bookkeeping should have been committed on the previous branch"
    )


async def test_create_branch_fichier_code_modifie_bloque(tmp_path: Path) -> None:
    """A modified code file still blocks branch creation — ticket-314, criterion 4.

    ``commit_bookkeeping`` only stages Tessera's own artifact paths.  A code
    file left dirty in the working tree causes the checkout to fail, and the
    resulting ``GitCommandError`` produces a blocked result.  The code file
    itself is never swept into a bookkeeping commit.
    """
    root = tmp_path / "repo"
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")

    # Initial commit: code.py at version A (represents develop state)
    (root / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "init")
    initial_sha = await _git_out(root, "rev-parse", "HEAD")

    # Ticket-016 branch: code.py at version B
    await _git(root, "checkout", "-q", "-b", "ticket-016-with-code")
    (root / "code.py").write_text("x = 2\n", encoding="utf-8")
    await _git(root, "add", "code.py")
    await _git(root, "commit", "-q", "-m", "ticket 016 code change")

    # Uncommitted modification to code.py (version C — differs from A on develop)
    (root / "code.py").write_text("x = 3\n", encoding="utf-8")

    # Workspace on ticket-016, base_ref forced to the initial commit
    workspace = GitWorkspaceService(root)
    workspace._base_ref = initial_sha  # type: ignore[assignment]

    svc = _Tickets()
    events: list[OrchestratorEvent] = []
    run = _run(events)
    result = await stages.create_branch(
        _Orch(_git_workspace=workspace, _ticket_svc=svc), run
    )

    # Branch creation must be blocked: checkout would overwrite code.py
    assert result is not None
    assert result.final_status is TicketStatus.blocked
    assert result.arret is not None
    assert run.branch is None
    assert TicketStatus.blocked in svc.statuts

    # code.py was NOT committed by commit_bookkeeping: it is still dirty
    status_out = await _git_out(root, "status", "--porcelain", "--untracked-files=no")
    assert any("code.py" in line for line in status_out.splitlines()), (
        "code.py should still be modified (not committed by commit_bookkeeping)"
    )


# ------------------------------------------------------------------
# PipelineRun.start_round
# ------------------------------------------------------------------


def test_start_round_remet_a_zero_l_etat_du_tour() -> None:
    # Sans ce reset, un second tour relirait le diff du premier.
    run = _run()
    run.reviewed_code = "diff du tour 1"
    run.test_context = "tests du tour 1"
    run.security_context = "audit du tour 1"
    run.review_feedback = ["à garder entre les tours"]

    run.start_round(2)

    assert run.round_num == 2
    assert run.reviewed_code == ""
    assert run.test_context == ""
    assert run.security_context == ""
    assert run.review_feedback == ["à garder entre les tours"]


# ------------------------------------------------------------------
# Messages spontanes de l'utilisateur — ticket-066
# ------------------------------------------------------------------


def test_build_context_injecte_les_messages_spontanes() -> None:
    # Le pipeline etait un tuyau ferme : une consigne donnee pendant un run
    # n'arrivait jamais a l'agent. Elle est desormais lue au tour suivant.
    run = _run()
    run.dialogue.interject("utilise pathlib, pas os.path")

    contexte = stages.build_context(_Orch(), run)

    assert "utilise pathlib, pas os.path" in contexte
    assert "contexte projet" in contexte


def test_un_message_spontane_n_est_injecte_qu_une_fois() -> None:
    # Sinon la consigne se repeterait a chaque tour, en gonflant le contexte
    # a chaque fois un peu plus.
    run = _run()
    run.dialogue.interject("pense aux tests")

    premier = stages.build_context(_Orch(), run)
    second = stages.build_context(_Orch(), run)

    assert "pense aux tests" in premier
    assert "pense aux tests" not in second


def test_build_context_sans_message_spontane_est_inchange() -> None:
    assert stages.build_context(_Orch(), _run()) == "contexte projet"


def test_l_outil_ask_user_n_est_offert_qu_en_mode_interactif() -> None:
    # Offrir `ask_user` a un run non interactif promettrait a l'agent une
    # réponse que personne ne peut donner : il attendrait le delai complet a
    # chaque question, pour rien (ADR-025).
    from tessera.services.dialogue import DialogueChannel

    run = _run()
    assert stages.asker_for(run) is None

    run.dialogue = DialogueChannel(interactive=True)
    assert stages.asker_for(run) == run.dialogue.ask


# ------------------------------------------------------------------
# Sécurité et validation échouent fermé — ticket-122
# ------------------------------------------------------------------


class _Tickets:
    def __init__(self) -> None:
        self.statuts: list[TicketStatus] = []

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statuts.append(status)


class _AuditeurEnPanne:
    async def audit(self, code_diff: str, project_path: Path) -> object:
        raise RuntimeError("provider down")


class _ValidateurEnPanne:
    async def validate(self, **kwargs: object) -> object:
        raise RuntimeError("provider down")


async def test_une_panne_de_l_auditeur_bloque_le_run() -> None:
    # L'exception était avalée et l'audit sauté : un diff non audité arrivait
    # au reviewer comme s'il était propre. Une panne n'est pas un PASS.
    events: list[OrchestratorEvent] = []
    run = _run(events)
    run.reviewed_code = "diff"
    orch = _Orch(
        _security_auditor=_AuditeurEnPanne(),
        _project_path=Path("."),
        _ticket_svc=_Tickets(),
    )

    result = await stages.run_security_audit(orch, run)

    assert result is not None
    assert result.final_status is TicketStatus.blocked
    done = [e for e in events if e.type == EventType.SECURITY_AUDIT_DONE]
    assert done and done[0].data["verdict"] == "BLOCK"
    assert "provider down" in done[0].data["reason"]
    assert [e.type for e in events][-1] is EventType.PIPELINE_DONE


async def test_une_panne_du_validateur_demande_des_changements() -> None:
    # Même raisonnement : l'exception valait approbation.
    events: list[OrchestratorEvent] = []
    run = _run(events)
    orch = _Orch(_validator=_ValidateurEnPanne())

    approved, reason = await stages.run_validation(orch, run)

    assert approved is False
    assert "provider down" in reason


async def test_run_validation_sans_validateur_approuve_avec_raison_vide() -> None:
    # run_validation est maintenant indépendante : sans validateur elle rend
    # (True, "") et non plus (True, reason_du_reviewer) (ticket-289).
    run = _run()
    orch = _Orch()

    approved, reason = await stages.run_validation(orch, run)

    assert approved is True
    assert reason == ""


# ------------------------------------------------------------------
# RunActif.en_dict — etapes_en_cours (ticket-289)
# ------------------------------------------------------------------


def test_en_dict_contient_etapes_en_cours_vide_par_defaut() -> None:
    from tessera.services.run_registry import RunActif

    run = RunActif(run_id="r1", project_id="p1")
    d = run.en_dict()

    assert "etapes_en_cours" in d
    assert d["etapes_en_cours"] == []


def test_en_dict_expose_les_etapes_en_cours() -> None:
    from tessera.services.run_registry import RunActif

    run = RunActif(run_id="r1", project_id="p1")
    run.etapes_en_cours = ["revue", "validation"]
    d = run.en_dict()

    assert d["etapes_en_cours"] == ["revue", "validation"]


def test_suivre_ajoute_revue_et_validation_dans_etapes_en_cours() -> None:
    """_suivre tracks both stages when reviewer and validator run concurrently."""
    from tessera.models.agent import AgentRole
    from tessera.services.pipeline_events import EventType, OrchestratorEvent
    from tessera.services.run_executor import _suivre
    from tessera.services.run_registry import RunActif

    run_actif = RunActif(run_id="r1", project_id="p1")

    _suivre(
        run_actif,
        OrchestratorEvent(
            type=EventType.AGENT_STARTED,
            agent=AgentRole.reviewer,
            ticket_id="ticket-001",
            data={"round": 1},
        ),
    )
    _suivre(
        run_actif,
        OrchestratorEvent(
            type=EventType.VALIDATION_STARTED,
            ticket_id="ticket-001",
            data={},
        ),
    )

    assert "revue" in run_actif.etapes_en_cours
    assert "validation" in run_actif.etapes_en_cours
    assert run_actif.en_dict()["etapes_en_cours"] == ["revue", "validation"]

    # Les étapes disparaissent quand les événements DONE arrivent.
    _suivre(
        run_actif,
        OrchestratorEvent(
            type=EventType.VALIDATION_DONE,
            ticket_id="ticket-001",
            data={"verdict": "APPROVED"},
        ),
    )
    _suivre(
        run_actif,
        OrchestratorEvent(
            type=EventType.AGENT_DONE,
            agent=AgentRole.reviewer,
            ticket_id="ticket-001",
            data={"cost_usd": 0.0, "duration_ms": 100},
        ),
    )

    assert run_actif.etapes_en_cours == []


# ------------------------------------------------------------------
# run_tests — gestion des timeouts (ticket-349)
# ------------------------------------------------------------------


class _TestRunnerResult:
    """Fake TestRunnerService that returns a sequence of results."""

    def __init__(self, results: list) -> None:
        self._results = iter(results)

    async def run_tests(
        self, project_path: object, test_command: object = None, **_kwargs: object
    ) -> object:
        return next(self._results)


def _expired_result() -> object:
    from tessera.services.test_runner import TestResult
    return TestResult(passed=False, expiree=True, total=0, failed=0, output_summary="Timeout après 60s — cmd")


def _green_result() -> object:
    from tessera.services.test_runner import TestResult
    return TestResult(passed=True, expiree=False, total=5, failed=0, output_summary="5 passed in 0.5s")


def _red_result() -> object:
    from tessera.services.test_runner import TestResult
    return TestResult(passed=False, expiree=False, total=5, failed=1, output_summary="1 failed, 4 passed in 0.5s")


async def test_run_tests_sans_runner_rend_true() -> None:
    """Without a test runner configured, run_tests returns True."""
    result = await stages.run_tests(_Orch(), _run())
    assert result is True


async def test_run_tests_premier_expire_second_vert_passe_a_la_securite() -> None:
    """First timeout + second green: continues without invoking the coder again (ticket-349)."""
    from tessera.services.pipeline_events import PipelineResult

    runner = _TestRunnerResult([_expired_result(), _green_result()])
    orch = _Orch(
        _test_runner=runner,
        _project_path=Path("/fake"),
        _test_command="uv run pytest",
    )
    result = await stages.run_tests(orch, _run())

    assert result is True, "After expired+green, run_tests must return True (not a bool‑like PipelineResult)"
    assert "délai dépassé, suite relancée" in "\n".join(orch.logs)


async def test_run_tests_deux_expirements_bloquent_le_run() -> None:
    """Two consecutive timeouts terminate the run as blocked (ticket-349)."""
    from tessera.services.pipeline_events import PipelineResult
    from tessera.models.ticket import TicketStatus

    class _TicketSvcMock:
        def __init__(self) -> None:
            self.statuts: list[TicketStatus] = []

        async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
            self.statuts.append(status)

    svc = _TicketSvcMock()
    events: list[OrchestratorEvent] = []
    runner = _TestRunnerResult([_expired_result(), _expired_result()])
    orch = _Orch(
        _test_runner=runner,
        _project_path=Path("/fake"),
        _test_command="uv run pytest",
        _ticket_svc=svc,
    )
    result = await stages.run_tests(orch, _run(events))

    assert isinstance(result, PipelineResult)
    assert result.final_status is TicketStatus.blocked
    assert result.approved is False
    assert result.arret is not None
    assert "délai dépassé deux fois" in result.arret


async def test_run_tests_rouge_non_expire_renvoie_false() -> None:
    """A regular (non-expired) test failure returns False as before (ticket-349)."""
    runner = _TestRunnerResult([_red_result()])
    orch = _Orch(
        _test_runner=runner,
        _project_path=Path("/fake"),
        _test_command="uv run pytest",
    )
    result = await stages.run_tests(orch, _run())

    assert result is False


async def test_run_tests_log_mentionne_relance_sur_timeout() -> None:
    """The pipeline-log records the retry when a timeout triggers a replay (ticket-349)."""
    runner = _TestRunnerResult([_expired_result(), _green_result()])
    orch = _Orch(
        _test_runner=runner,
        _project_path=Path("/fake"),
        _test_command="uv run pytest",
    )
    await stages.run_tests(orch, _run())

    relance_logs = [l for l in orch.logs if "délai dépassé, suite relancée" in l]
    assert relance_logs, "Expected a log line mentioning 'délai dépassé, suite relancée'"
