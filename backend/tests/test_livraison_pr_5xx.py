"""Opening the PR is retried once on a GitHub server error — ticket-781."""
import json
from pathlib import Path

import httpx
import pytest

from tessera.services.livraison.livraison import Livraison, LivraisonService


class _FauxGit:
    async def rejouer_sur(self, base, resolveur=None):  # type: ignore[no-untyped-def]
        return ()

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        return None

    async def commit_bookkeeping(self) -> None:
        pass

    async def commits_hors_rangement(self, depuis: str) -> list[str]:
        return []

    async def sha_distant(self, branch: str) -> str | None:
        return None


def _erreur(statut: int) -> httpx.HTTPStatusError:
    requete = httpx.Request("POST", "https://api.github.com/repos/o/r/pulls")
    return httpx.HTTPStatusError(
        f"HTTP {statut}", request=requete, response=httpx.Response(statut, request=requete)
    )


class _Workflow:
    """Opening the PR answers from a script of errors, then succeeds."""

    def __init__(self, erreurs: list[Exception], existante: int | None = None) -> None:
        self._erreurs = list(erreurs)
        self._existante = existante
        self.ouvertures = 0
        self.recherches = 0
        self.recherche_en_echec = False

    async def open_pull_request(self, **kwargs: object) -> object:
        self.ouvertures += 1
        if self._erreurs:
            raise self._erreurs.pop(0)

        class _R:
            pr_number = 7

        return _R()

    async def pr_ouverte_de(self, branch: str) -> int | None:
        self.recherches += 1
        if self.recherche_en_echec:
            raise httpx.ConnectError("recherche impossible")
        return self._existante


async def _sans_dormir(_s: float) -> None:
    return None


async def _livrer(tmp_path: Path, workflow: _Workflow) -> Livraison:
    (tmp_path / "agents.json").write_text(json.dumps({"autonomy": "pr"}), encoding="utf-8")
    svc = LivraisonService(
        git_workspace=_FauxGit(),  # type: ignore[arg-type]
        workflow=workflow,  # type: ignore[arg-type]
        project_path=tmp_path,
        base_branch="develop",
        dormir=_sans_dormir,
    )
    return await svc.livrer_phase_1(
        ticket_id="ticket-001", ticket_title="T", ticket_body="",
        branch="ticket-001-x", approuve=True,
        approved_sha="a1" * 20,
    )


async def test_a_500_then_a_success_opens_the_pr_and_logs_the_retry(tmp_path: Path) -> None:
    workflow = _Workflow([_erreur(500)])

    livraison = await _livrer(tmp_path, workflow)

    assert livraison.pr_number == 7
    assert workflow.ouvertures == 2
    assert any("nouvelle tentative" in e for e in livraison.etapes)


async def test_two_500s_in_a_row_stop_after_two_calls(tmp_path: Path) -> None:
    workflow = _Workflow([_erreur(500), _erreur(502)])

    with pytest.raises(httpx.HTTPStatusError):
        await _livrer(tmp_path, workflow)

    assert workflow.ouvertures == 2


async def test_a_422_is_not_retried(tmp_path: Path) -> None:
    workflow = _Workflow([_erreur(422)])

    with pytest.raises(httpx.HTTPStatusError):
        await _livrer(tmp_path, workflow)

    assert workflow.ouvertures == 1
    assert workflow.recherches == 0


async def test_a_500_when_the_pr_exists_resumes_it_without_opening_another(
    tmp_path: Path,
) -> None:
    workflow = _Workflow([_erreur(500)], existante=42)

    livraison = await _livrer(tmp_path, workflow)

    assert livraison.pr_number == 42
    assert workflow.ouvertures == 1


async def test_a_500_with_a_search_that_never_answers_opens_no_second_pr(
    tmp_path: Path,
) -> None:
    workflow = _Workflow([_erreur(500)])
    workflow.recherche_en_echec = True

    with pytest.raises(httpx.HTTPStatusError):
        await _livrer(tmp_path, workflow)

    assert workflow.ouvertures == 1
    assert workflow.recherches == 3
