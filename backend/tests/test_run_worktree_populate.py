"""Populate a run worktree, unlink it before removing it — ticket-523."""
import logging
import os
from pathlib import Path
from typing import Literal

import pytest

from tessera.models.worktree_config import ConfigWorktree, EntreePopulate
from tessera.services import run_worktree_populate
from tessera.services.run_worktree import LienPersistant, RunWorktree, creer, supprimer
from tessera.services.run_worktree_populate import peupler, retirer_les_liens
from tests.depot_worktree import BRANCHE, construire, git, lier

_LOGGER = "tessera.services.run_worktree_populate"


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return construire(tmp_path, monkeypatch)


def _config(*entrees: tuple[str, Literal["copy", "link"]]) -> ConfigWorktree:
    return ConfigWorktree(populate=tuple(EntreePopulate(path=p, mode=m) for p, m in entrees))


async def _worktree(repo: Path) -> RunWorktree:
    return await creer(repo, repo, "demo", "ticket-1", BRANCHE, "develop")


def _evenements(caplog: pytest.LogCaptureFixture, nom: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage() == nom]


async def test_peupler_copies_a_file_and_a_folder_apart_from_the_checkout(
    checkout: Path,
) -> None:
    wt = await _worktree(checkout)
    absents = await peupler(wt, checkout, _config(("secret.cfg", "copy"), ("cache", "copy")))
    assert absents == []
    assert (wt.racine / "secret.cfg").read_text(encoding="utf-8") == "secret"
    assert (wt.racine / "cache" / "a.txt").read_text(encoding="utf-8") == "cache"
    (wt.racine / "secret.cfg").write_text("change", encoding="utf-8")
    (wt.racine / "cache" / "a.txt").write_text("change", encoding="utf-8")
    assert (checkout / "secret.cfg").read_text(encoding="utf-8") == "secret"
    assert (checkout / "cache" / "a.txt").read_text(encoding="utf-8") == "cache"


async def test_peupler_links_a_folder_that_shows_the_checkout_content(checkout: Path) -> None:
    wt = await _worktree(checkout)
    await peupler(wt, checkout, _config(("node_modules", "link")))
    assert (wt.racine / "node_modules" / "pkg" / "index.js").read_text(encoding="utf-8") == "temoin"


async def test_supprimer_leaves_the_linked_node_modules_of_the_checkout_intact(
    checkout: Path,
) -> None:
    wt = await _worktree(checkout)
    await peupler(wt, checkout, _config(("node_modules", "link")))
    await supprimer(wt, checkout)
    assert not wt.racine.exists()
    assert (checkout / "node_modules" / "pkg" / "index.js").read_text(encoding="utf-8") == "temoin"


@pytest.mark.parametrize(("chemin", "present_dans_le_worktree"),
                         [("suivi.txt", True), ("pas-suivi.txt", False)])
async def test_peupler_refuses_to_link_what_git_does_not_ignore(
    checkout: Path, chemin: str, present_dans_le_worktree: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    wt = await _worktree(checkout)
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        await peupler(wt, checkout, _config((chemin, "link")))
    refus = _evenements(caplog, "worktree_populate_refuse")
    assert [r.__dict__["raison"] for r in refus] == ["non_ignore_par_git"]
    cible = wt.racine / chemin
    # Un fichier suivi est déjà là, en vrai fichier ; un fichier libre n'a rien créé.
    assert os.path.lexists(cible) is present_dans_le_worktree
    assert not cible.is_symlink()
    assert git(wt.racine, "status", "--porcelain") == ""


async def test_peupler_reports_a_missing_entry_and_populates_the_others(
    checkout: Path, caplog: pytest.LogCaptureFixture
) -> None:
    wt = await _worktree(checkout)
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        absents = await peupler(
            wt, checkout, _config(("absent.bin", "copy"), ("secret.cfg", "copy"))
        )
    assert absents == ["absent.bin"]
    manquants = _evenements(caplog, "worktree_populate_manquant")
    assert [r.__dict__["chemin"] for r in manquants] == ["absent.bin"]
    assert (wt.racine / "secret.cfg").is_file()


def test_retirer_les_liens_never_enters_the_target_of_a_link(tmp_path: Path) -> None:
    autre = tmp_path / "autre"
    autre.mkdir()
    (autre / "temoin.txt").write_text("autre", encoding="utf-8")
    cible = tmp_path / "cible"
    cible.mkdir()
    (cible / "temoin.txt").write_text("cible", encoding="utf-8")
    # Un lien niché dans la cible : le parcours le retirerait s'il y descendait.
    lier(autre, cible / "interne")
    racine = tmp_path / "arbre"
    (racine / "dossier").mkdir(parents=True)
    lier(cible, racine / "dossier" / "node_modules")
    assert retirer_les_liens(racine) == []
    assert not os.path.lexists(racine / "dossier" / "node_modules")
    assert (cible / "temoin.txt").read_text(encoding="utf-8") == "cible"
    assert os.path.lexists(cible / "interne")
    assert (autre / "temoin.txt").read_text(encoding="utf-8") == "autre"


async def test_a_link_that_stays_stops_supprimer_and_the_worktree_remains(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = await _worktree(checkout)
    await peupler(wt, checkout, _config(("node_modules", "link")))
    monkeypatch.setattr(run_worktree_populate, "_delier", lambda chemin: False)
    with pytest.raises(LienPersistant) as exc:
        await supprimer(wt, checkout)
    assert exc.value.liens == [wt.racine / "node_modules"]
    assert (wt.racine / "node_modules" / "pkg" / "index.js").is_file()
    assert "ticket-1" in git(checkout, "worktree", "list", "--porcelain")
