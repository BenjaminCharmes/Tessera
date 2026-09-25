"""Retirer un projet de l'IDE — ticket-063."""
import asyncio
import shutil
import stat
from pathlib import Path

import pytest

from tessera.services.project_removal import (
    RemovalError,
    RemovalPlan,
    delete_project,
    describe_removal,
    detach_project,
)


async def _git(cwd: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def _make_copy(ws: Path, name: str = "copie") -> Path:
    p = ws / name
    p.mkdir()
    (p / "main.py").write_text("x = 1\n", encoding="utf-8")
    return p


def _make_symlink(ws: Path, tmp_path: Path, name: str = "lie") -> tuple[Path, Path]:
    source = tmp_path / f"source-{name}"
    source.mkdir()
    (source / "important.py").write_text("ne pas perdre\n", encoding="utf-8")
    link = ws / name
    try:
        link.symlink_to(source, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks indisponibles sur cette machine")
    return link, source


# ------------------------------------------------------------------
# Décrire avant d'agir
# ------------------------------------------------------------------


async def test_decrit_un_projet_lie_comme_tel(workspace: Path, tmp_path: Path) -> None:
    link, source = _make_symlink(workspace, tmp_path)

    plan = await describe_removal(link)

    assert isinstance(plan, RemovalPlan)
    assert plan.is_symlink is True
    assert plan.real_path == str(source.resolve())


async def test_decrit_une_copie_avec_son_chemin_reel(workspace: Path) -> None:
    project = _make_copy(workspace)

    plan = await describe_removal(project)

    assert plan.is_symlink is False
    assert plan.real_path == str(project.resolve())


async def test_compte_les_commits_non_pousses(workspace: Path) -> None:
    # Ce que l'utilisateur perdrait vraiment : la confirmation doit le nommer.
    project = _make_copy(workspace)
    await _git(project, "init", "-q")
    await _git(project, "config", "user.email", "t@t.local")
    await _git(project, "config", "user.name", "t")
    await _git(project, "add", "main.py")
    await _git(project, "commit", "-q", "-m", "travail non poussé")

    plan = await describe_removal(project)

    assert plan.unpushed_commits == 1


async def test_un_projet_sans_git_n_a_pas_de_commits_a_perdre(workspace: Path) -> None:
    plan = await describe_removal(_make_copy(workspace))
    assert plan.unpushed_commits == 0


# ------------------------------------------------------------------
# Retirer — les fichiers restent
# ------------------------------------------------------------------


async def test_retirer_un_lien_supprime_le_lien_pas_la_cible(
    workspace: Path, tmp_path: Path
) -> None:
    # Le point critique : `projects/fluentdb` EST `Desktop/fluentdb`. Retirer
    # le projet ne doit jamais toucher au dossier de travail réel.
    link, source = _make_symlink(workspace, tmp_path)

    await detach_project(link)

    assert not link.exists()
    assert source.is_dir()
    assert (source / "important.py").read_text(encoding="utf-8") == "ne pas perdre\n"


async def test_retirer_une_copie_la_deplace_hors_du_workspace(
    workspace: Path,
) -> None:
    project = _make_copy(workspace)

    moved_to = await detach_project(project)

    assert not project.exists()
    assert Path(moved_to).is_dir()
    assert (Path(moved_to) / "main.py").read_text(encoding="utf-8") == "x = 1\n"
    # Hors du workspace : l'IDE ne doit plus le voir.
    assert workspace not in Path(moved_to).parents


# ------------------------------------------------------------------
# Supprimer — action distincte
# ------------------------------------------------------------------


async def test_supprimer_un_lien_ne_touche_jamais_la_cible(
    workspace: Path, tmp_path: Path
) -> None:
    # Proposer d'effacer `Desktop/fluentdb` depuis un IDE serait dangereux :
    # la suppression d'un lien s'arrête au lien.
    link, source = _make_symlink(workspace, tmp_path)

    await delete_project(link, confirmed=True)

    assert not link.exists()
    assert source.is_dir()
    assert (source / "important.py").exists()


async def test_supprimer_une_copie_l_efface(workspace: Path) -> None:
    project = _make_copy(workspace)

    await delete_project(project, confirmed=True)

    assert not project.exists()


async def test_supprimer_sans_confirmation_est_refuse(workspace: Path) -> None:
    project = _make_copy(workspace)

    with pytest.raises(RemovalError) as exc:
        await delete_project(project, confirmed=False)

    assert project.is_dir()
    assert "confirm" in str(exc.value).lower()


async def test_supprimer_hors_du_workspace_est_refuse(
    workspace: Path, tmp_path: Path
) -> None:
    # Garde-fou : la suppression ne doit pouvoir viser qu'une entrée du
    # workspace, jamais un chemin arbitraire.
    outside = tmp_path / "ailleurs"
    outside.mkdir()

    with pytest.raises(RemovalError):
        await delete_project(outside, confirmed=True, workspace=workspace)

    assert outside.is_dir()


def test_un_projet_detache_atterrit_hors_du_depot_de_l_ide(tmp_path: Path) -> None:
    # Panne latente : `projects/../..` designe la racine du depot de Tessera.
    # Le projet detache y restait, non suivi — et depuis qu'un projet peut
    # travailler dans le depot parent (ADR-028), un `git add -A` depuis la
    # racine pouvait l'y committer en entier (ticket-078).
    from tessera.services.project_removal import _detached_destination

    depot = tmp_path / "Tessera"
    (depot / ".git").mkdir(parents=True)
    projet = depot / "projects" / "mon-projet"
    projet.mkdir(parents=True)

    destination = _detached_destination(projet)

    assert depot not in destination.parents, destination
    assert destination.parent.name == "tessera-detaches"


def test_sans_depot_au_dessus_le_comportement_ne_change_pas(tmp_path: Path) -> None:
    from tessera.services.project_removal import _detached_destination

    projet = tmp_path / "workspace" / "projects" / "mon-projet"
    projet.mkdir(parents=True)

    destination = _detached_destination(projet)

    assert destination.parent.name == "tessera-detaches"


async def test_supprimer_un_projet_qui_porte_un_depot_git(workspace: Path) -> None:
    """Deleting a project whose .git holds read-only objects must succeed.

    Reproduces the failure found on a real project: git marks its objects
    read-only, and on Windows `shutil.rmtree` refuses to unlink a file
    carrying that attribute — POSIX only checks the parent directory. The
    endpoint answered 500 on `.git/objects/00/07d9…`.

    It is a direct consequence of ticket-104: before it, a created project had
    no `.git` at all, so deletion worked. Giving every project a repository
    broke the opposite operation.
    """
    project = _make_copy(workspace)
    objets = project / ".git" / "objects" / "00"
    objets.mkdir(parents=True)
    objet = objets / "07d9e3246b0bdfb0a9dcebd8056df271077a65"
    objet.write_bytes(b"contenu d'un objet git")
    objet.chmod(stat.S_IREAD)

    await delete_project(project, confirmed=True)

    assert not project.exists()


async def test_une_erreur_qui_n_est_pas_un_droit_remonte(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The read-only retry must not swallow other failures.

    A deletion that reports success while leaving files behind is worse than
    one that fails: the project disappears from the UI and stays on disk.
    """
    project = _make_copy(workspace)

    def _verrouille(*_args: object, **_kwargs: object) -> None:
        raise OSError("fichier verrouillé par un autre processus")

    monkeypatch.setattr(shutil, "rmtree", _verrouille)

    with pytest.raises(OSError):
        await delete_project(project, confirmed=True)
