"""La livraison d'une intervention du superviseur — ticket-854, ADR-080."""
import json
from pathlib import Path

from tessera.services.livraison.livraison import LivraisonService
from tessera.services.supervision.intervention_controle import controle_de
from tessera.services.supervision.superviseur_actions import Action

_BRANCHE = "supervision-20261106-101500"
_SHA = "a" * 40


class _FauxGit:
    def __init__(self, fichiers: list[str], branche: str = _BRANCHE, tete: str = _SHA) -> None:
        self.fichiers = fichiers
        self.branche = branche
        self.tete = tete
        self.rejoue: list[str] = []

    async def rejouer_sur(self, base: str, resolveur: object = None) -> tuple[str, ...]:
        self.rejoue.append(base)
        return ()

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        return None

    async def commit_bookkeeping(self) -> None:
        return None

    async def commits_hors_rangement(self, depuis: str) -> list[str]:
        return []

    async def sha_distant(self, branch: str) -> str | None:
        return self.tete

    async def head_sha(self) -> str:
        return self.tete

    async def remettre_sur(self, sha: str) -> None:
        return None

    async def branche_courante(self) -> str:
        return self.branche

    async def fichiers_de_branche(self, base: str, branch: str) -> list[str]:
        return list(self.fichiers)


class _Pr:
    pr_number = 12
    pr_url = "https://github.com/o/r/pull/12"
    branch = _BRANCHE


class _FauxWorkflow:
    def __init__(self) -> None:
        self.ouvertures: list[dict[str, object]] = []
        self.appels_ci_ou_merge: list[str] = []

    async def open_pull_request(self, **kwargs: object) -> object:
        self.ouvertures.append(kwargs)
        return _Pr()

    async def etat_ci(self, pr_number: int) -> str:
        self.appels_ci_ou_merge.append("etat_ci")
        return "passing"

    async def has_workflows(self) -> bool:
        self.appels_ci_ou_merge.append("has_workflows")
        return True

    async def pr_ouverte_de(self, branch: str) -> int | None:
        return 12

    async def pr_state(self, pr_number: int) -> str:
        return "open"

    async def tete_pr(self, pr_number: int) -> str | None:
        return _SHA

    async def merge_si_la_ci_est_verte(self, pr_number: int, sha_attendu: str | None = None) -> bool:
        self.appels_ci_ou_merge.append("merge")
        return True


def _service(tmp_path: Path, niveau: str, git: _FauxGit) -> tuple[LivraisonService, _FauxWorkflow]:
    (tmp_path / "agents.json").write_text(json.dumps({"autonomy": niveau}), encoding="utf-8")
    workflow = _FauxWorkflow()
    service = LivraisonService(
        git_workspace=git, workflow=workflow, project_path=tmp_path, base_branch="develop",
    )
    return service, workflow


async def test_delivery_rereads_the_diff_and_refuses_a_forbidden_path(tmp_path: Path) -> None:
    git = _FauxGit(["memory/supervision.md", "backend/src/tessera/config.py"])
    service, workflow = _service(tmp_path, "pr", git)

    livraison = await service.livrer_intervention(_BRANCHE, _SHA, controle=controle_de(Action.TRIER))

    assert livraison.pr_number is None
    assert livraison.arret is not None and "config.py" in livraison.arret
    assert workflow.ouvertures == []
    assert git.rejoue == []


async def test_delivery_refuses_a_branch_that_is_not_an_intervention(tmp_path: Path) -> None:
    git = _FauxGit(["memory/supervision.md"], branche="ticket-001-x")
    service, workflow = _service(tmp_path, "pr", git)

    livraison = await service.livrer_intervention("ticket-001-x", _SHA, controle=controle_de(Action.TRIER))

    assert livraison.pr_number is None and workflow.ouvertures == []


async def test_delivery_refuses_a_head_that_is_not_the_commit(tmp_path: Path) -> None:
    git = _FauxGit(["memory/supervision.md"], tete="b" * 40)
    service, workflow = _service(tmp_path, "pr", git)

    livraison = await service.livrer_intervention(_BRANCHE, _SHA, controle=controle_de(Action.TRIER))

    assert livraison.pr_number is None and livraison.branche_modifiee
    assert workflow.ouvertures == []


async def test_delivery_opens_a_pr_and_never_merges_even_in_merge_autonomy(tmp_path: Path) -> None:
    git = _FauxGit(["memory/supervision.md"])
    service, workflow = _service(tmp_path, "merge", git)

    livraison = await service.livrer_intervention(_BRANCHE, _SHA, controle=controle_de(Action.TRIER))

    assert livraison.pr_number == 12
    assert livraison.merged is False
    assert livraison.pushed_sha == _SHA
    assert len(workflow.ouvertures) == 1
    assert workflow.ouvertures[0]["branch"] == _BRANCHE
    assert workflow.appels_ci_ou_merge == []
    assert git.rejoue == ["develop"]


async def test_delivery_stays_local_at_the_commit_level(tmp_path: Path) -> None:
    git = _FauxGit(["memory/supervision.md"])
    service, workflow = _service(tmp_path, "commit", git)

    livraison = await service.livrer_intervention(_BRANCHE, _SHA, controle=controle_de(Action.TRIER))

    assert livraison.pr_number is None and livraison.arret_voulu
    assert workflow.ouvertures == []
