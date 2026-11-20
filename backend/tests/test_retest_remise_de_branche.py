"""A red retest after a rebase puts the branch back on its pre-rebase head — ticket-740."""
from pathlib import Path

from tessera.services.git_workspace import GitCommandError
from tessera.services.livraison.livraison_rebase import remettre_la_branche
from tests.test_retest_apres_rebase import _Banc, _rouges, _verts

_AVANT = "b2" * 20


async def test_red_retest_puts_the_branch_back_on_the_head_noted_before_the_rebase(
    tmp_path: Path,
) -> None:
    banc = _Banc(tmp_path, _rouges(), ancetre=False)

    livraison = await banc.livrer()

    assert banc.git.remises == [_AVANT]
    assert banc.appels == ["rebase", "tests", "tests", "remise"]
    assert livraison.pr_number is None
    assert livraison.arret is not None
    assert livraison.arret.startswith("Tests rouges après rebase sur main : rien n'est poussé.")
    assert f"Branche remise sur {_AVANT[:7]}." in livraison.arret


async def test_green_retest_puts_nothing_back(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _verts(), ancetre=False)

    livraison = await banc.livrer()

    assert banc.git.remises == []
    assert "remise" not in banc.appels
    assert livraison.pr_number == 7
    assert not any("branche remise" in etape for etape in livraison.etapes)


async def test_base_without_advance_puts_nothing_back(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _rouges(), ancetre=True)

    await banc.livrer()

    assert banc.git.remises == []


async def test_journal_step_names_the_short_sha_before_the_rebase(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _rouges(), ancetre=False)

    livraison = await banc.livrer()

    assert f"branche remise sur {_AVANT[:7]}" in livraison.etapes
    assert len(livraison.etapes) == len(livraison.durees_ms)


async def test_journal_step_says_the_conflict_resolution_was_dropped(tmp_path: Path) -> None:
    etapes: list[str] = []
    durees: list[float] = []
    banc = _Banc(tmp_path, _rouges(), ancetre=False)

    arret = await remettre_la_branche(
        banc.git, _AVANT, ["services/a.py"], etapes, durees, "Tests rouges"
    )

    assert etapes == [f"branche remise sur {_AVANT[:7]} ; résolution de conflit abandonnée"]
    assert "résolution de conflit abandonnée" in arret
    assert len(etapes) == len(durees)


async def test_restoration_that_raises_leaves_a_stop_that_says_so_and_pushes_nothing(
    tmp_path: Path,
) -> None:
    banc = _Banc(tmp_path, _rouges(), ancetre=False)
    banc.git.remise_echoue = GitCommandError(["reset"], 1, "unable to write")

    livraison = await banc.livrer()

    assert livraison.pr_number is None
    assert "pr" not in banc.appels
    assert livraison.arret is not None
    assert f"n'a pas pu être remise sur {_AVANT[:7]}" in livraison.arret
    assert "elle reste rebasée" in livraison.arret
    assert f"branche non remise sur {_AVANT[:7]} : GitCommandError" in livraison.etapes


async def test_unreadable_head_before_the_rebase_is_said_in_the_stop(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, _rouges(), ancetre=False)

    async def illisible() -> str:
        raise GitCommandError(["rev-parse"], 1, "boom")

    banc.git.head_sha = illisible  # type: ignore[method-assign]

    livraison = await banc.livrer()

    assert banc.git.remises == []
    assert livraison.pr_number is None
    assert livraison.arret is not None
    assert "sa tête d'avant le rebase est inconnue" in livraison.arret
