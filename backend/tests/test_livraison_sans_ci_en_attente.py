"""merge_without_ci waits for a pending CI verdict — ticket-1004."""
import json
from pathlib import Path

from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.livraison.livraison import LivraisonService
from tessera.services.livraison.livraison_merge import arret_de_merge, tenter_le_merge


class _FauxGit:
    async def rejouer_sur(self, base, resolveur=None):  # type: ignore[no-untyped-def]
        return ()

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        return None

    async def commit_bookkeeping(self) -> None:
        pass


class _FauxWorkflow:
    def __init__(self, etats: list[str]) -> None:
        self._etats = list(etats)
        self.code_http_ci: int | None = None
        self.refus_ci: str | None = None
        self.merges: list[int] = []

    async def has_workflows(self) -> bool:
        return True

    async def pr_state(self, pr_number: int) -> str:
        return "open"

    async def etat_ci(self, pr_number: int) -> str:
        return self._etats.pop(0) if len(self._etats) > 1 else self._etats[0]

    async def merge_si_la_ci_est_verte(self, pr_number: int) -> bool:
        self.merges.append(pr_number)
        return True


async def _pas_de_sommeil(secondes: float) -> None:
    return None


def _service(tmp_path: Path, workflow: _FauxWorkflow) -> LivraisonService:
    (tmp_path / "agents.json").write_text(
        json.dumps({"autonomy": "merge", "merge_without_ci": True}), encoding="utf-8"
    )
    return LivraisonService(
        git_workspace=_FauxGit(),
        workflow=workflow,
        project_path=tmp_path,
        base_branch="develop",
        attente_ci_max_s=100,
        intervalle_ci_s=10,
        grace_ci_s=0,
        dormir=_pas_de_sommeil,
        politique=PolitiqueRun.lire(tmp_path),
    )


async def test_pending_then_passing_merges(tmp_path: Path) -> None:
    workflow = _FauxWorkflow(["pending", "pending", "passing"])

    livraison = await _service(tmp_path, workflow).livrer_phase_2(7, ticket_id="t")

    assert workflow.merges == [7]
    assert livraison.merged is True
    assert livraison.arret is None


async def test_pending_then_failing_does_not_merge(tmp_path: Path) -> None:
    workflow = _FauxWorkflow(["pending", "failing"])

    livraison = await _service(tmp_path, workflow).livrer_phase_2(7, ticket_id="t")

    assert workflow.merges == []
    assert livraison.merged is False
    assert "failing" in (livraison.arret or "")


async def test_none_merges_at_once(tmp_path: Path) -> None:
    workflow = _FauxWorkflow(["none"])

    livraison = await _service(tmp_path, workflow).livrer_phase_2(7, ticket_id="t")

    assert workflow.merges == [7]
    assert livraison.merged is True


async def test_pending_past_the_bound_stops_without_merging(tmp_path: Path) -> None:
    workflow = _FauxWorkflow(["pending"])

    livraison = await _service(tmp_path, workflow).livrer_phase_2(7, ticket_id="t")

    assert workflow.merges == []
    assert "verdict" in (livraison.arret or "")


async def test_a_ci_refusal_is_not_written_as_a_github_refusal() -> None:
    workflow = _FauxWorkflow(["pending"])

    async def _refuse(pr_number: int) -> bool:
        workflow.refus_ci = "pending"
        return False

    workflow.merge_si_la_ci_est_verte = _refuse  # type: ignore[method-assign]
    issue = await tenter_le_merge(workflow, 7, None)  # type: ignore[arg-type]

    arret = arret_de_merge(7, issue)
    assert issue.merged is False
    assert "GitHub a refusé" not in arret
    assert "pending" in arret
