"""Les tests repassent quand le rebase ramène des commits de la base — ticket-568.

Couverture :
- la base a avancé → la commande de test repasse avant le push (avant l'ouverture de la PR) ;
- la base n'a pas bougé → aucun test relancé, aucune étape ajoutée ;
- tests rouges après rebase → rien n'est poussé, `arret` renseigné, sortie dans l'arrêt ;
- un résultat qui ne prouve rien (expiré, non démarré, lanceur qui lève) est rouge ;
- sans commande à lancer, aucune trace ; sans crochet, comportement d'avant ;
- `base_a_avance` : vrai, faux, inconnu (échec fermé), cible du worktree ;
- la ligne du journal du pipeline dit que les tests ont été relancés, et leur issue.
"""
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from tessera.models.ticket import TicketStatus
from tessera.services.livraison import Livraison, LivraisonService
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import OrchestratorEvent, PipelineResult
from tessera.services.retest_apres_rebase import (
    RetestApresRebase,
    ResultatRetest,
    etape_de,
    retest_du_run,
)
from tessera.services.test_runner import TestCommandNotFound, TestResult


def _verts() -> TestResult:
    return TestResult(passed=True, total=12, failed=0, output_summary="12 passed")


def _rouges() -> TestResult:
    return TestResult(
        passed=False,
        total=12,
        failed=1,
        output_summary="1 failed, 11 passed",
        failure_details="FAILED test_longueur_des_fichiers.py - 714 lignes pour 713",
    )


class _FauxGit:
    def __init__(self, appels: list[str], ancetre: bool | None = False) -> None:
        self.appels = appels
        self.ancetre = ancetre
        self.comparaisons: list[tuple[str, str]] = []
        self.conflits: tuple[str, ...] = ()

    async def est_ancetre(self, ancetre: str, descendant: str) -> bool | None:
        self.comparaisons.append((ancetre, descendant))
        return self.ancetre

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        return None

    async def commit_bookkeeping(self) -> None:
        return None

    async def commits_hors_rangement(self, depuis: str) -> list[str]:
        return []

    async def rejouer_sur(self, base: str, resolveur: object = None) -> tuple[str, ...]:
        self.appels.append("rebase")
        return self.conflits

    async def sha_distant(self, branch: str) -> str | None:
        return "a1" * 20


class _Ouverte:
    pr_number = 7


class _FauxWorkflow:
    def __init__(self, appels: list[str]) -> None:
        self.appels = appels

    async def open_pull_request(self, **kwargs: object) -> _Ouverte:
        self.appels.append("pr")
        return _Ouverte()

    async def etat_ci(self, pr_number: int) -> str:
        return "passing"

    async def has_workflows(self) -> bool:
        return False

    async def pr_ouverte_de(self, branch: str) -> int | None:
        return None

    async def pr_state(self, pr_number: int) -> str:
        return "open"

    async def tete_pr(self, pr_number: int) -> str | None:
        return None

    async def merge_si_la_ci_est_verte(self, pr_number: int) -> bool:
        return False


class _Lanceur:
    """The test launcher: counts its calls and records them in the shared order."""

    def __init__(self, appels: list[str], resultat: TestResult | Exception) -> None:
        self.appels = appels
        self.resultat = resultat
        self.lancements = 0

    async def __call__(self) -> TestResult:
        self.lancements += 1
        self.appels.append("tests")
        if isinstance(self.resultat, Exception):
            raise self.resultat
        return self.resultat


class _Banc:
    def __init__(self, tmp_path: Path, resultat: TestResult | Exception, **git: Any) -> None:
        self.appels: list[str] = []
        self.git = _FauxGit(self.appels, **git)
        self.workflow = _FauxWorkflow(self.appels)
        self.lanceur = _Lanceur(self.appels, resultat)
        self.retest = RetestApresRebase(self.git, self.lanceur, worktree=False)
        (tmp_path / "agents.json").write_text(json.dumps({"autonomy": "pr"}), encoding="utf-8")
        self.tmp_path = tmp_path

    def service(self, avec_retest: bool = True) -> LivraisonService:
        return LivraisonService(
            git_workspace=self.git,
            workflow=self.workflow,
            project_path=self.tmp_path,
            base_branch="main",
            retest=self.retest if avec_retest else None,
        )

    async def livrer(self, avec_retest: bool = True) -> Livraison:
        return await self.service(avec_retest).livrer_phase_1(
            ticket_id="ticket-001",
            ticket_title="Du travail",
            ticket_body="",
            branch="ticket-001-slug",
            approuve=True,
        )


async def test_rebase_bringing_a_commit_reruns_the_tests_before_the_push(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _verts(), ancetre=False)

    livraison = await banc.livrer()

    assert banc.lanceur.lancements == 1
    assert banc.appels == ["rebase", "tests", "pr"]
    assert banc.git.comparaisons == [("main", "HEAD")]
    assert livraison.pr_number == 7
    assert livraison.arret is None
    assert "tests relancés après rebase : verts (12 passed)" in livraison.etapes
    assert len(livraison.etapes) == len(livraison.durees_ms)


async def test_rebase_without_new_base_commit_does_not_rerun_the_tests(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _verts(), ancetre=True)

    livraison = await banc.livrer()

    assert banc.lanceur.lancements == 0
    assert banc.appels == ["rebase", "pr"]
    assert livraison.pr_number == 7
    assert not any("tests relancés" in etape for etape in livraison.etapes)


async def test_red_tests_after_rebase_block_the_push(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _rouges(), ancetre=False)

    livraison = await banc.livrer()

    assert "pr" not in banc.appels
    assert livraison.pr_number is None
    assert livraison.arret is not None
    assert livraison.arret.startswith("Tests rouges après rebase sur main : rien n'est poussé.")
    assert "714 lignes pour 713" in livraison.arret
    assert any(e.startswith("tests relancés après rebase : rouges") for e in livraison.etapes)
    assert len(livraison.etapes) == len(livraison.durees_ms)


async def test_unknown_ancestry_reruns_the_tests(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _verts(), ancetre=None)

    await banc.livrer()

    assert banc.lanceur.lancements == 1


async def test_delivery_without_hook_never_compares_nor_tests(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _rouges(), ancetre=False)

    livraison = await banc.livrer(avec_retest=False)

    assert banc.git.comparaisons == []
    assert banc.lanceur.lancements == 0
    assert livraison.pr_number == 7


async def test_unresolved_conflict_does_not_rerun_the_tests(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _verts(), ancetre=False)
    banc.git.conflits = ("services/a.py",)

    livraison = await banc.livrer()

    assert banc.lanceur.lancements == 0
    assert livraison.conflits == ("services/a.py",)


async def test_launcher_that_raises_counts_as_red(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, RuntimeError("boom"), ancetre=False)

    livraison = await banc.livrer()

    assert "pr" not in banc.appels
    assert livraison.arret is not None
    assert "n'ont pas pu tourner : RuntimeError" in livraison.arret


async def test_expired_or_unstarted_run_counts_as_red(tmp_path: Path) -> None:
    for incomplet in (
        TestResult(passed=True, total=0, failed=0, output_summary="délai", expiree=True),
        TestResult(passed=True, total=0, failed=0, output_summary="nope", demarree=False),
    ):
        banc = _Banc(tmp_path, incomplet, ancetre=False)

        livraison = await banc.livrer()

        assert livraison.pr_number is None
        assert livraison.arret is not None


async def test_project_without_test_command_leaves_no_trace(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, TestCommandNotFound("rien"), ancetre=False)

    livraison = await banc.livrer()

    assert livraison.pr_number == 7
    assert not any("tests relancés" in etape for etape in livraison.etapes)


class _LanceurEnSerie:
    """A launcher that returns its results in order and counts its calls."""

    def __init__(self, *resultats: TestResult | Exception) -> None:
        self._restants = list(resultats)
        self.lancements = 0

    async def __call__(self) -> TestResult:
        self.lancements += 1
        suivant = self._restants.pop(0)
        if isinstance(suivant, Exception):
            raise suivant
        return suivant


async def test_red_then_green_retest_continues_and_says_so() -> None:
    lanceur = _LanceurEnSerie(_rouges(), _verts())
    retest = RetestApresRebase(_FauxGit([]), lanceur, worktree=False)

    jugement = await retest.juger("main")

    assert jugement is not None
    assert jugement.arret is None
    assert "2e essai" in jugement.etape
    assert "FAILED test_longueur_des_fichiers.py" in jugement.etape
    assert "\n" not in jugement.etape
    assert lanceur.lancements == 2


async def test_red_twice_retest_stops() -> None:
    lanceur = _LanceurEnSerie(_rouges(), _rouges())
    retest = RetestApresRebase(_FauxGit([]), lanceur, worktree=False)

    jugement = await retest.juger("main")

    assert jugement is not None
    assert jugement.arret is not None
    assert jugement.arret.startswith("Tests rouges après rebase sur main")
    assert lanceur.lancements == 2


async def test_green_first_retest_runs_once() -> None:
    lanceur = _LanceurEnSerie(_verts())
    retest = RetestApresRebase(_FauxGit([]), lanceur, worktree=False)

    jugement = await retest.juger("main")

    assert jugement is not None
    assert jugement.arret is None
    assert "2e essai" not in jugement.etape
    assert lanceur.lancements == 1


async def test_expired_first_try_is_rerun_like_a_red_one() -> None:
    expire = TestResult(passed=True, total=0, failed=0, output_summary="délai", expiree=True)
    lanceur = _LanceurEnSerie(expire, _verts())
    retest = RetestApresRebase(_FauxGit([]), lanceur, worktree=False)

    jugement = await retest.juger("main")

    assert jugement is not None and jugement.arret is None
    assert "2e essai" in jugement.etape
    assert lanceur.lancements == 2


async def test_no_test_command_still_records_nothing() -> None:
    lanceur = _LanceurEnSerie(TestCommandNotFound("rien"))
    retest = RetestApresRebase(_FauxGit([]), lanceur, worktree=False)

    assert await retest.juger("main") is None
    assert lanceur.lancements == 1


async def test_base_a_avance_reads_the_ancestry() -> None:
    git = _FauxGit([], ancetre=True)
    retest = RetestApresRebase(git, _Lanceur([], _verts()), worktree=False)
    assert await retest.base_a_avance("main") is False
    git.ancetre = False
    assert await retest.base_a_avance("main") is True
    git.ancetre = None
    assert await retest.base_a_avance("main") is True


async def test_base_a_avance_compares_with_the_remote_in_a_worktree() -> None:
    git = _FauxGit([], ancetre=True)
    retest = RetestApresRebase(git, _Lanceur([], _verts()), worktree=True)

    await retest.base_a_avance("develop")

    assert git.comparaisons == [("origin/develop", "HEAD")]


async def test_base_a_avance_fails_closed_when_git_raises() -> None:
    git = MagicMock()
    git.est_ancetre = AsyncMock(side_effect=OSError("git absent"))
    retest = RetestApresRebase(git, _Lanceur([], _verts()), worktree=False)

    assert await retest.base_a_avance("main") is True


async def test_retest_du_run_uses_the_run_test_runner_and_command(tmp_path: Path) -> None:
    runner = MagicMock()
    runner.run_tests = AsyncMock(return_value=_verts())
    retest = retest_du_run(_FauxGit([]), False, runner, tmp_path, "python scripts/verifier.py")
    assert retest is not None

    resultat = await retest.relancer()

    runner.run_tests.assert_awaited_once_with(tmp_path, test_command="python scripts/verifier.py")
    assert resultat is not None and resultat.vert is True


def test_retest_du_run_is_absent_without_tester_or_git(tmp_path: Path) -> None:
    assert retest_du_run(_FauxGit([]), False, None, tmp_path, "cmd") is None
    assert retest_du_run(None, False, MagicMock(), tmp_path, "cmd") is None


def test_etape_de_stays_on_one_line_and_is_truncated() -> None:
    longue = "FAILED a\n" + "x" * 1000
    etape = etape_de(ResultatRetest(vert=False, resume="1 failed", details=longue))

    assert "\n" not in etape
    assert etape.startswith("tests relancés après rebase : rouges (FAILED a xxx")
    assert len(etape) < 400


async def test_pipeline_log_records_the_retest_and_its_outcome(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _rouges(), ancetre=False)
    livraison = await banc.livrer()
    journal = tmp_path / "memory" / "pipeline-log.md"

    async def livrer(_: PipelineResult) -> Livraison:
        return livraison

    tickets = AsyncMock()
    tickets.get_ticket.return_value = None
    orch = _OrchestrateurDouble(
        PipelineResult(
            ticket_id="ticket-001",
            final_status=TicketStatus.done,
            rounds=1,
            approved=True,
            branch="ticket-001-slug",
            commit_sha="abc",
        ),
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=journal,
        livrer=livrer,
    )

    async def rien(event: OrchestratorEvent) -> None:
        return None

    await orch.run_pipeline("p", "ticket-001", rien)

    lignes = journal.read_text(encoding="utf-8")
    assert "livraison: tests relancés après rebase : rouges" in lignes
    assert "livraison: arrêt — Tests rouges après rebase sur main" in lignes


class _OrchestrateurDouble(Orchestrator):
    """Orchestrator whose inner pipeline is replaced; the delivery logging is real."""

    def __init__(self, resultat: PipelineResult, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._resultat = resultat

    async def _run_pipeline(self, *args: Any, **kwargs: Any) -> PipelineResult:
        return self._resultat
