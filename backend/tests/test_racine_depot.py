"""The single walk up to the repository root — ticket-676."""
import json
import re
from pathlib import Path

import pytest

from tessera.services.politique_run import PolitiqueRun
from tessera.services.providers.perimetre import racine_autorisee
from tessera.services.project_overview import find_icon
from tessera.services.racine_depot import (
    GIT_ROOT_ANCESTOR,
    declare_ancestor,
    depot_au_dessus,
    depot_le_plus_proche,
    est_ancestor,
    est_un_depot,
    racine_ecriture_projet,
)

_SRC = Path(__file__).resolve().parents[1] / "src" / "tessera"


def _worktree_lie(dossier: Path) -> None:
    """A linked worktree: `.git` is a file pointing at the real git dir."""
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / ".git").write_text("gitdir: /ailleurs/.git/worktrees/x\n", encoding="utf-8")


def _projet(racine: Path, git_root: str | None) -> Path:
    projet = racine / "projects" / "ide-core"
    projet.mkdir(parents=True)
    if git_root is not None:
        (projet / "agents.json").write_text(
            json.dumps({"git_root": git_root}), encoding="utf-8"
        )
    return projet


def test_est_un_depot_accepts_a_git_folder(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    assert est_un_depot(tmp_path)


def test_est_un_depot_accepts_a_git_file(tmp_path: Path) -> None:
    _worktree_lie(tmp_path)

    assert est_un_depot(tmp_path)


def test_est_un_depot_refuses_a_plain_folder(tmp_path: Path) -> None:
    assert not est_un_depot(tmp_path)


def test_est_ancestor_reads_only_the_exact_value() -> None:
    assert est_ancestor(GIT_ROOT_ANCESTOR)
    assert not est_ancestor("Ancestor")
    assert not est_ancestor(None)
    assert not est_ancestor(["ancestor"])


def test_declare_ancestor_reads_the_manifest(tmp_path: Path) -> None:
    assert declare_ancestor(_projet(tmp_path / "a", "ancestor"))
    assert not declare_ancestor(_projet(tmp_path / "b", "autre"))
    assert not declare_ancestor(_projet(tmp_path / "c", None))


def test_depot_au_dessus_skips_the_start_folder(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    projet = tmp_path / "projects" / "p"
    projet.mkdir(parents=True)
    (projet / ".git").mkdir()

    assert depot_au_dessus(projet) == tmp_path
    assert depot_le_plus_proche(projet) == projet


def test_depot_au_dessus_is_none_without_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Un dossier dont aucun ancêtre ne porte `.git` : `est_un_depot` est
    # forcé à faux pour ne pas dépendre de l'emplacement du dossier temporaire.
    monkeypatch.setattr("tessera.services.racine_depot.est_un_depot", lambda _d: False)

    assert depot_au_dessus(tmp_path) is None
    assert depot_le_plus_proche(tmp_path) is None


def test_a_git_file_is_a_repository_root_everywhere(tmp_path: Path) -> None:
    # Un `.git` fichier (worktree lié) est une racine de dépôt pour tous les
    # lecteurs : la fonction commune, la racine d'écriture, la politique de
    # run et l'icône de la carte.
    _worktree_lie(tmp_path)
    projet = _projet(tmp_path, "ancestor")
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")

    assert depot_au_dessus(projet) == tmp_path
    assert racine_autorisee(projet) == tmp_path.resolve()
    assert PolitiqueRun.lire(projet).racine_ecriture(projet) == tmp_path.resolve()
    trouvee = find_icon(projet)
    assert trouvee is not None and trouvee[0].name == "favicon.svg"


def test_racine_ecriture_projet_without_ancestor_is_the_project(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    projet = _projet(tmp_path, None)

    assert racine_ecriture_projet(projet, False) == projet.resolve()


def test_racine_ecriture_projet_falls_back_on_the_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tessera.services.racine_depot.est_un_depot", lambda _d: False)
    projet = _projet(tmp_path, GIT_ROOT_ANCESTOR)

    assert racine_ecriture_projet(projet, True) == projet.resolve().parent


def test_racine_ecriture_projet_climbs_to_the_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    projet = _projet(tmp_path, GIT_ROOT_ANCESTOR)

    assert racine_ecriture_projet(projet, True) == tmp_path.resolve()


def test_ancestor_is_compared_in_one_module_only() -> None:
    litteral = re.compile(r"""["']ancestor["']""")
    fautifs = [
        str(chemin.relative_to(_SRC))
        for chemin in _SRC.rglob("*.py")
        if litteral.search(chemin.read_text(encoding="utf-8"))
    ]

    assert fautifs == [str(Path("services") / "racine_depot.py")]
