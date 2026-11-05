"""The standalone steps of delivery phase one (ticket-700)."""
from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.livraison_apres import (
    branche_modifiee,
    ouvrir_avec_recours,
    pr_a_relire,
    pr_ouverte_malgre,
    sha_pousse,
)
from tessera.services.livraison_arrets import ARRET_NON_APPROUVE, arret_niveau_commit


class _Git:
    def __init__(self, intrus: list[str] | Exception, sha: str | Exception | None) -> None:
        self._intrus = intrus
        self._sha = sha

    async def commits_hors_rangement(self, depuis: str) -> list[str]:
        if isinstance(self._intrus, Exception):
            raise self._intrus
        return self._intrus

    async def sha_distant(self, branch: str) -> str | None:
        if isinstance(self._sha, Exception):
            raise self._sha
        return self._sha


class _Workflow:
    def __init__(self, pr: int | Exception | None) -> None:
        self._pr = pr

    async def pr_ouverte_de(self, branch: str) -> int | None:
        if isinstance(self._pr, Exception):
            raise self._pr
        return self._pr


async def test_branch_unchanged_since_approval_gives_no_stop() -> None:
    assert await branche_modifiee(_Git([], None), "a" * 40) is None


async def test_extra_commit_since_approval_stops_with_its_short_sha() -> None:
    stop = await branche_modifiee(_Git(["b" * 40], None), "a" * 40)
    assert stop is not None
    assert stop.branche_modifiee is True
    assert stop.arret == "la branche a changé depuis l'approbation : bbbbbbb"


async def test_branch_that_cannot_be_compared_fails_closed() -> None:
    stop = await branche_modifiee(_Git(GitWorkspaceError("boom"), None), "a" * 40)
    assert stop is not None
    assert stop.branche_modifiee is True
    assert stop.arret is not None and "aaaaaaa" in stop.arret


async def test_pushed_sha_is_read_or_none() -> None:
    assert await sha_pousse(_Git([], "c" * 40), "ticket-1") == "c" * 40
    assert await sha_pousse(_Git([], None), "ticket-1") is None
    assert await sha_pousse(_Git([], RuntimeError("x")), "ticket-1") is None


async def test_lost_pr_search_never_raises() -> None:
    assert await pr_ouverte_malgre(_Workflow(7), "ticket-1") == 7
    assert await pr_ouverte_malgre(_Workflow(None), "ticket-1") is None
    assert await pr_ouverte_malgre(_Workflow(RuntimeError("x")), "ticket-1") is None


def test_resolved_conflict_keeps_the_pr_open_and_names_the_files() -> None:
    livraison = pr_a_relire(9, ("rebase",), (1.0,), ["a.py", "b.py"])
    assert livraison.pr_number == 9
    assert livraison.conflits == ("a.py", "b.py")
    assert livraison.merged is False
    assert livraison.arret is not None and "a.py, b.py" in livraison.arret


def test_entry_stop_messages() -> None:
    assert "reviewer a refusé" in ARRET_NON_APPROUVE
    assert "commité sur ticket-1" in arret_niveau_commit("ticket-1")
    assert '"autonomy": "pr"' in arret_niveau_commit("ticket-1")


async def test_opening_that_succeeds_is_not_retried_nor_searched() -> None:
    appels: list[int] = []

    async def ouvrir() -> object:
        appels.append(1)

        class _R:
            pr_number = 9

        return _R()

    async def dormir(_s: float) -> None:
        raise AssertionError("no wait expected")

    etapes: list[str] = []
    resultat = await ouvrir_avec_recours(ouvrir, _Workflow(RuntimeError("x")), "b", etapes, dormir)

    assert resultat == (9, None)
    assert appels == [1]
    assert etapes == []
