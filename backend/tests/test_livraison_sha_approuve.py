"""La livraison ne pousse que ce que le reviewer a lu — ticket-492.

Couverture :
- un commit de code ajouté après l'approbation → `branche_modifiee`, ni rebase
  ni PR (donc pas de push), arret « la branche a changé depuis l'approbation » ;
- une branche qui ne peut pas être comparée → refus (échec fermé, ADR-039) ;
- que du rangement après l'approbation → la PR s'ouvre, `pushed_sha` est noté ;
- un rebase du pipeline qui change la tête → `pushed_sha` est la tête rebasée ;
- sans `approved_sha`, aucune comparaison (comportement d'avant).
"""
import json
from pathlib import Path

from tessera.services.git_workspace import GitCommandError
from tessera.services.livraison import Livraison, LivraisonService

_APPROUVE = "a1" * 20
_INTRUS = "bad0" * 10
_REBASE = "5e" * 20


class _FauxGit:
    def __init__(
        self,
        intrus: list[str] | None = None,
        erreur: Exception | None = None,
        tete_apres_rebase: str = _APPROUVE,
    ) -> None:
        self.intrus = intrus or []
        self.erreur = erreur
        self.tete_distante = tete_apres_rebase
        self.nouvelle_tete = tete_apres_rebase
        self.appels: list[str] = []

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        self.appels.append("sync")
        return None

    async def commit_bookkeeping(self) -> None:
        self.appels.append("bookkeeping")

    async def commits_hors_rangement(self, depuis: str) -> list[str]:
        self.appels.append("comparaison")
        if self.erreur is not None:
            raise self.erreur
        return self.intrus

    async def rejouer_sur(self, base: str, resolveur: object = None) -> tuple[str, ...]:
        self.appels.append("rebase")
        self.tete_distante = self.nouvelle_tete
        return ()

    async def sha_distant(self, branch: str) -> str | None:
        return self.tete_distante


class _Ouverte:
    pr_number = 7


class _FauxWorkflow:
    def __init__(self) -> None:
        self.ouvertes = 0

    async def open_pull_request(self, **kwargs: object) -> _Ouverte:
        self.ouvertes += 1
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


def _service(tmp_path: Path, git: _FauxGit, wf: _FauxWorkflow) -> LivraisonService:
    (tmp_path / "agents.json").write_text(json.dumps({"autonomy": "pr"}), encoding="utf-8")
    return LivraisonService(
        git_workspace=git, workflow=wf, project_path=tmp_path, base_branch="main"
    )


async def _livrer(service: LivraisonService, approved_sha: str | None) -> Livraison:
    return await service.livrer_phase_1(
        ticket_id="ticket-001",
        ticket_title="Du travail",
        ticket_body="",
        branch="ticket-001-slug",
        approuve=True,
        approved_sha=approved_sha,
    )


async def test_code_commit_after_approval_blocks_without_push(tmp_path: Path) -> None:
    git, wf = _FauxGit(intrus=[_INTRUS]), _FauxWorkflow()

    livraison = await _livrer(_service(tmp_path, git, wf), _APPROUVE)

    assert livraison.branche_modifiee is True
    assert livraison.arret == (
        f"la branche a changé depuis l'approbation : {_INTRUS[:7]}"
    )
    assert livraison.pr_number is None
    assert "rebase" not in git.appels
    assert wf.ouvertes == 0


async def test_unreadable_comparison_blocks_without_push(tmp_path: Path) -> None:
    git = _FauxGit(erreur=GitCommandError(["git", "log"], 128, "boom"))
    wf = _FauxWorkflow()

    livraison = await _livrer(_service(tmp_path, git, wf), _APPROUVE)

    assert livraison.branche_modifiee is True
    assert wf.ouvertes == 0
    assert "rebase" not in git.appels


async def test_bookkeeping_commits_do_not_block(tmp_path: Path) -> None:
    git, wf = _FauxGit(intrus=[]), _FauxWorkflow()

    livraison = await _livrer(_service(tmp_path, git, wf), _APPROUVE)

    assert livraison.branche_modifiee is False
    assert livraison.arret is None
    assert livraison.pr_number == 7
    assert livraison.pushed_sha == _APPROUVE
    assert git.appels.index("comparaison") < git.appels.index("rebase")


async def test_pipeline_rebase_updates_pushed_sha(tmp_path: Path) -> None:
    git = _FauxGit(intrus=[], tete_apres_rebase=_APPROUVE)
    git.nouvelle_tete = _REBASE
    wf = _FauxWorkflow()

    livraison = await _livrer(_service(tmp_path, git, wf), _APPROUVE)

    assert livraison.pushed_sha == _REBASE
    assert livraison.pushed_sha != _APPROUVE


async def test_without_approved_sha_nothing_is_compared(tmp_path: Path) -> None:
    git, wf = _FauxGit(intrus=[_INTRUS]), _FauxWorkflow()

    livraison = await _livrer(_service(tmp_path, git, wf), None)

    assert "comparaison" not in git.appels
    assert livraison.pr_number == 7
