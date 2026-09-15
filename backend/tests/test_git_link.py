"""Liaison d'un projet à un dépôt GitHub — ticket-061."""
import asyncio
from pathlib import Path

import pytest

from vibe_ide.services.git_link import (
    GitLinkError,
    RemoteNotEmpty,
    git_status,
    init_repository,
    link_remote,
)


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    p = tmp_path / "mon-projet"
    p.mkdir()
    (p / "main.py").write_text("print('hello')\n", encoding="utf-8")
    return p


# ------------------------------------------------------------------
# État
# ------------------------------------------------------------------


async def test_un_projet_sans_git_est_signale_comme_tel(project: Path) -> None:
    # Le cas d'un projet créé de zéro ou importé en `copy` : `.git` est exclu
    # de la copie, donc le pipeline ne peut ni brancher ni committer.
    status = await git_status(project)

    assert status.is_repository is False
    assert status.remote_url is None


async def test_un_projet_avec_git_et_remote_est_decrit(project: Path) -> None:
    await _git(project, "init", "-q")
    await _git(project, "remote", "add", "origin", "https://github.com/moi/repo.git")

    status = await git_status(project)

    assert status.is_repository is True
    assert status.remote_url == "https://github.com/moi/repo.git"


# ------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------


async def test_init_cree_un_depot_avec_un_premier_commit(project: Path) -> None:
    await init_repository(project)

    status = await git_status(project)
    assert status.is_repository is True
    assert status.has_commits is True
    # Le contenu existant doit être dans ce premier commit, sinon le pipeline
    # le verrait comme des modifications non suivies.
    assert "main.py" in await _git(project, "ls-tree", "-r", "--name-only", "HEAD")


async def test_init_sur_un_depot_existant_ne_le_touche_pas(project: Path) -> None:
    await _git(project, "init", "-q")
    await _git(project, "config", "user.email", "t@t.local")
    await _git(project, "config", "user.name", "t")
    await _git(project, "add", "main.py")
    await _git(project, "commit", "-q", "-m", "commit initial de l'utilisateur")

    await init_repository(project)

    log = await _git(project, "log", "--format=%s")
    assert "commit initial de l'utilisateur" in log
    assert len(log.strip().splitlines()) == 1


# ------------------------------------------------------------------
# Liaison d'un remote
# ------------------------------------------------------------------


async def test_link_attache_le_remote_et_le_consigne(project: Path) -> None:
    await init_repository(project)

    await link_remote(project, "https://github.com/moi/repo.git", remote_is_empty=True)

    assert "https://github.com/moi/repo.git" in await _git(project, "remote", "-v")
    # `agents.json` porte déjà `github_remote`, lu par les endpoints PR et sync.
    import json

    data = json.loads((project / "agents.json").read_text(encoding="utf-8"))
    assert data["github_remote"] == "https://github.com/moi/repo.git"


async def test_link_refuse_une_url_qui_n_est_pas_un_depot(project: Path) -> None:
    await init_repository(project)

    with pytest.raises(GitLinkError) as exc:
        await link_remote(project, "pas-une-url", remote_is_empty=True)

    assert "URL" in str(exc.value)


async def test_link_exige_une_confirmation_si_le_remote_n_est_pas_vide(
    project: Path,
) -> None:
    # Attacher un remote qui a déjà un historique à un projet local est une
    # source de conflits : ça se décide, ça ne se subit pas.
    await init_repository(project)

    with pytest.raises(RemoteNotEmpty):
        await link_remote(project, "https://github.com/moi/repo.git", remote_is_empty=False)

    await link_remote(
        project, "https://github.com/moi/repo.git", remote_is_empty=False, confirmed=True
    )
    assert "github.com/moi/repo.git" in await _git(project, "remote", "-v")


async def test_link_sur_un_projet_sans_depot_est_refuse(project: Path) -> None:
    with pytest.raises(GitLinkError) as exc:
        await link_remote(project, "https://github.com/moi/repo.git", remote_is_empty=True)

    assert "dépôt" in str(exc.value).lower()


async def test_link_remplace_un_remote_existant_seulement_si_confirme(
    project: Path,
) -> None:
    await init_repository(project)
    await link_remote(project, "https://github.com/moi/premier.git", remote_is_empty=True)

    with pytest.raises(GitLinkError) as exc:
        await link_remote(project, "https://github.com/moi/second.git", remote_is_empty=True)
    assert "origin" in str(exc.value)

    await link_remote(
        project, "https://github.com/moi/second.git", remote_is_empty=True, confirmed=True
    )
    assert "second.git" in await _git(project, "remote", "get-url", "origin")


# ------------------------------------------------------------------
# Projet imbriqué dans un autre dépôt
# ------------------------------------------------------------------


async def test_un_projet_imbrique_dans_un_autre_depot_est_signale(
    tmp_path: Path,
) -> None:
    # Cas réel : `projects/ide-core` est à l'intérieur du dépôt vibe-ide. Git
    # remonte au parent, et `git_status` répondait « dépôt = oui » avec le
    # remote du parent. Trompeur : `init` serait sans effet, et le pipeline
    # commiterait dans le dépôt englobant, pas dans le projet.
    outer = tmp_path / "depot-englobant"
    outer.mkdir()
    await _git(outer, "init", "-q")
    await _git(outer, "remote", "add", "origin", "https://github.com/moi/englobant.git")

    nested = outer / "projects" / "mon-projet"
    nested.mkdir(parents=True)
    (nested / "main.py").write_text("x = 1\n", encoding="utf-8")

    status = await git_status(nested)

    assert status.is_own_repository is False
    assert status.is_nested_in is not None
    assert status.remote_url is None


async def test_un_depot_propre_n_est_pas_imbrique(project: Path) -> None:
    await init_repository(project)

    status = await git_status(project)

    assert status.is_own_repository is True
    assert status.is_nested_in is None


async def test_init_sur_un_projet_imbrique_cree_bien_son_propre_depot(
    tmp_path: Path,
) -> None:
    outer = tmp_path / "depot-englobant"
    outer.mkdir()
    await _git(outer, "init", "-q")
    nested = outer / "projects" / "mon-projet"
    nested.mkdir(parents=True)
    (nested / "main.py").write_text("x = 1\n", encoding="utf-8")

    await init_repository(nested)

    status = await git_status(nested)
    assert status.is_own_repository is True
    assert (nested / ".git").exists()
