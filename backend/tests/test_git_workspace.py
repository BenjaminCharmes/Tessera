import asyncio
from pathlib import Path

import pytest

from vibe_ide.services.git_workspace import (
    GitCommandError,
    GitWorkspaceService,
    InvalidSlugError,
    NotAGitRepository,
)


async def _git(cwd: Path, *args: str) -> None:
    """Runs a git command in the test fixture, failing loudly."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    """A real git repository with one commit on the default branch."""
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@vibe-ide.local")
    await _git(root, "config", "user.name", "vibe-ide test")
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(root, "add", "README.md")
    await _git(root, "commit", "-q", "-m", "init")
    return root


async def test_create_branch_bascule_dessus(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    name = await service.create_branch("ticket-001", "ajouter-la-feature-x")
    assert name == "ticket-001-ajouter-la-feature-x"

    proc = await asyncio.create_subprocess_exec(
        "git", "branch", "--show-current",
        cwd=str(repo), stdout=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    assert out.decode().strip() == name


async def test_create_branch_tronque_et_assainit_le_slug(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    name = await service.create_branch("ticket-002", "Ajouter  Des/Accents Éèà !! " + "x" * 80)
    assert name.startswith("ticket-002-")
    assert len(name) <= 60
    assert all(c.isalnum() or c == "-" for c in name)
    assert "--" not in name


async def test_create_branch_assainit_le_ticket_id(repo: Path) -> None:
    # ticket_id is interpolated into the branch name just like slug: an
    # unsanitized ticket_id containing invalid ref characters must not
    # crash `checkout -b`.
    service = GitWorkspaceService(repo)
    name = await service.create_branch("ticket/weird id!", "une-feature")
    assert name.startswith("ticket-weird-id-")
    assert all(c.isalnum() or c == "-" for c in name)

    proc = await asyncio.create_subprocess_exec(
        "git", "branch", "--show-current",
        cwd=str(repo), stdout=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    assert out.decode().strip() == name


async def test_create_branch_reutilise_une_branche_existante(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    first = await service.create_branch("ticket-003", "reprise")
    second = await service.create_branch("ticket-003", "reprise")
    assert first == second


async def test_current_diff_voit_un_fichier_modifie(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-004", "modif")
    (repo / "README.md").write_text("# projet modifie\n", encoding="utf-8")

    diff = await service.current_diff()
    assert "README.md" in diff
    assert "projet modifie" in diff


async def test_current_diff_voit_un_fichier_nouveau(repo: Path) -> None:
    # Un fichier non suivi n'apparaît pas dans un `git diff` nu : c'est
    # précisément le cas d'usage du codeur, qui crée des fichiers.
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-005", "ajout")
    (repo / "nouveau.py").write_text("def hello():\n    return 'bonjour'\n", encoding="utf-8")

    diff = await service.current_diff()
    assert "nouveau.py" in diff
    assert "bonjour" in diff


async def test_current_diff_vide_quand_rien_ne_change(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-006", "rien")
    diff = await service.current_diff()
    assert diff.strip() == ""


async def test_commit_all_renvoie_un_sha(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-007", "commit")
    (repo / "nouveau.py").write_text("x = 1\n", encoding="utf-8")

    sha = await service.commit_all("feat: ticket-007")
    assert sha is not None
    assert len(sha) >= 7
    assert (await service.current_diff()).strip() == ""


async def test_commit_all_renvoie_none_sans_changement(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-008", "vide")
    assert await service.commit_all("feat: rien") is None


async def test_current_diff_voit_un_changement_deja_stage(repo: Path) -> None:
    # A coding agent with shell access may run `git add` on its own; a bare
    # `git diff` only shows the unstaged half and would miss this entirely.
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-011", "stage")
    (repo / "README.md").write_text("# projet stage\n", encoding="utf-8")
    await _git(repo, "add", "README.md")

    diff = await service.current_diff()
    assert "README.md" in diff
    assert "projet stage" in diff


async def test_current_diff_sur_depot_sans_commit(tmp_path: Path) -> None:
    # HEAD is ambiguous on a repository with no commits yet; current_diff
    # must fall back sensibly instead of raising.
    root = tmp_path / "projet-vierge"
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@vibe-ide.local")
    await _git(root, "config", "user.name", "vibe-ide test")
    (root / "nouveau.py").write_text("x = 1\n", encoding="utf-8")

    service = GitWorkspaceService(root)
    diff = await service.current_diff()
    assert "nouveau.py" in diff
    assert "x = 1" in diff


async def test_is_clean_vrai_sans_changement(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    assert await service.is_clean() is True


async def test_is_clean_faux_avec_changement(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    (repo / "README.md").write_text("# modifie\n", encoding="utf-8")
    assert await service.is_clean() is False


async def test_repertoire_sans_depot_git_leve_not_a_git_repository(tmp_path: Path) -> None:
    service = GitWorkspaceService(tmp_path)
    with pytest.raises(NotAGitRepository):
        await service.create_branch("ticket-009", "sans-git")


async def test_slug_vide_leve_invalid_slug_error(repo: Path) -> None:
    # An empty slug is a bad input, not a failed git command: no git
    # process ever runs, so it must not be reported as a GitCommandError.
    service = GitWorkspaceService(repo)
    with pytest.raises(InvalidSlugError) as exc:
        await service.create_branch("ticket-010", "")
    assert exc.value.slug == ""
    assert not isinstance(exc.value, GitCommandError)


async def test_current_diff_exclut_les_tickets_et_le_journal_pipeline(repo: Path) -> None:
    # tickets/ and memory/pipeline-log.md are vibe-ide's own bookkeeping,
    # not code produced by the coder agent: they must never show up in the
    # diff handed to the reviewer/auditor/validator/doc-updater.
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-012", "exclusions")

    (repo / "tickets" / "todo").mkdir(parents=True)
    (repo / "tickets" / "todo" / "ticket-012.md").write_text(
        "status: in-progress\n", encoding="utf-8"
    )
    (repo / "memory").mkdir()
    (repo / "memory" / "pipeline-log.md").write_text(
        "- run started\n", encoding="utf-8"
    )
    await _git(repo, "add", "-A")
    await _git(repo, "commit", "-q", "-m", "seed bookkeeping files")

    # Simulate one pipeline run: rewrite the ticket, append to the log, and
    # make a real source change.
    (repo / "tickets" / "todo" / "ticket-012.md").write_text(
        "status: in-review\n", encoding="utf-8"
    )
    with (repo / "memory" / "pipeline-log.md").open("a", encoding="utf-8") as f:
        f.write("- run finished\n")
    (repo / "feature.py").write_text("def feature():\n    return 42\n", encoding="utf-8")

    diff = await service.current_diff()
    assert "tickets" not in diff
    assert "pipeline-log" not in diff
    assert "in-review" not in diff
    assert "run finished" not in diff
    assert "feature.py" in diff
    assert "return 42" in diff


async def test_commit_all_ne_committe_pas_les_tickets_sous_le_message_du_ticket(
    repo: Path,
) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-013", "commit-bookkeeping")

    (repo / "tickets" / "todo").mkdir(parents=True)
    (repo / "tickets" / "todo" / "ticket-013.md").write_text(
        "status: in-progress\n", encoding="utf-8"
    )
    (repo / "memory").mkdir()
    (repo / "memory" / "pipeline-log.md").write_text(
        "- run started\n", encoding="utf-8"
    )
    await _git(repo, "add", "-A")
    await _git(repo, "commit", "-q", "-m", "seed bookkeeping files")

    (repo / "tickets" / "todo" / "ticket-013.md").write_text(
        "status: done\n", encoding="utf-8"
    )
    with (repo / "memory" / "pipeline-log.md").open("a", encoding="utf-8") as f:
        f.write("- run finished\n")
    (repo / "feature.py").write_text("x = 1\n", encoding="utf-8")

    sha = await service.commit_all("feat: ticket-013 — some feature")
    assert sha is not None

    log = await service._run("log", "--format=%s")
    subjects = log.splitlines()
    # Most recent first: the bookkeeping commit lands after the ticket commit.
    assert subjects[0] == "chore: vibe-ide pipeline bookkeeping"
    assert subjects[1] == "feat: ticket-013 — some feature"

    ticket_commit_files = await service._run(
        "show", "--name-only", "--format=", "HEAD^"
    )
    assert "feature.py" in ticket_commit_files
    assert "tickets" not in ticket_commit_files
    assert "pipeline-log" not in ticket_commit_files

    # The working tree ends up clean — the next run's dirty-tree check must
    # not be tripped up by bookkeeping left uncommitted.
    assert await service.is_clean() is True


async def test_is_clean_ignore_les_fichiers_non_suivis(repo: Path) -> None:
    # A first run in any project holding a non-ignored untracked file (build
    # output, scratch notes) must not be refused before anything happens:
    # is_clean() narrows to tracked modifications only.
    service = GitWorkspaceService(repo)
    (repo / "scratch-notes.txt").write_text("just some notes\n", encoding="utf-8")
    assert await service.is_clean() is True

    # A tracked modification must still be reported.
    (repo / "README.md").write_text("# modifie\n", encoding="utf-8")
    assert await service.is_clean() is False


async def test_create_branch_les_branches_suivantes_partent_de_la_ref_de_base(
    repo: Path,
) -> None:
    # Every ticket branch must fork from the ref that was checked out the
    # first time the service is used, never from the previously created
    # ticket branch — otherwise ticket 2 carries ticket 1's commits.
    service = GitWorkspaceService(repo)

    await service.create_branch("ticket-020", "premier")
    (repo / "premier.py").write_text("x = 1\n", encoding="utf-8")
    await service.commit_all("feat: ticket-020 — premier")

    await service.create_branch("ticket-021", "second")

    log = await service._run("log", "--format=%s")
    subjects = log.splitlines()
    assert "feat: ticket-020 — premier" not in subjects

    files_at_head = await service._run("ls-tree", "-r", "--name-only", "HEAD")
    assert "premier.py" not in files_at_head


async def test_not_a_git_repository_ignore_le_texte_de_stderr(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The repo-detection mechanism must not rely on parsing stderr text.

    We cannot easily force git itself to speak French in this environment,
    so instead we prove the *mechanism*: force `_is_own_repository` to
    report "not a repo", and make git fail for an unrelated reason whose
    stderr contains no "not a git repository"-like phrase in any language
    (an unknown flag). NotAGitRepository must still be raised, showing the
    decision comes solely from the exit-code check, never from stderr text.
    """
    service = GitWorkspaceService(repo)

    async def fake_not_own_repository() -> bool:
        return False

    monkeypatch.setattr(service, "_is_own_repository", fake_not_own_repository)

    with pytest.raises(NotAGitRepository):
        await service._run("--this-flag-does-not-exist")


async def test_advance_base_ref_chaine_les_tickets_approuves(repo: Path) -> None:
    # Isolation must not mean amnesia: once a ticket's work is approved and
    # committed, the next ticket has to build *on top of it*, otherwise a
    # plan of sequential tickets runs each step against a stale base.
    service = GitWorkspaceService(repo)

    await service.create_branch("ticket-030", "premier")
    (repo / "premier.py").write_text("x = 1\n", encoding="utf-8")
    await service.commit_all("feat: ticket-030 — premier")
    await service.advance_base_ref()

    await service.create_branch("ticket-031", "second")

    files_at_head = await service._run("ls-tree", "-r", "--name-only", "HEAD")
    assert "premier.py" in files_at_head


async def test_commit_all_ignore_les_fichiers_non_suivis_preexistants(
    repo: Path,
) -> None:
    # An untracked file that was already sitting in the tree before the run
    # started was not produced by the coder: `git add -A` must not sweep it
    # into the ticket's commit. Files the coder creates during the run must
    # still be committed.
    (repo / "scratch-notes.txt").write_text("notes perso\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-040", "feature")

    (repo / "nouveau.py").write_text("y = 2\n", encoding="utf-8")
    sha = await service.commit_all("feat: ticket-040 — feature")
    assert sha is not None

    files_at_head = await service._run("ls-tree", "-r", "--name-only", "HEAD")
    assert "nouveau.py" in files_at_head
    assert "scratch-notes.txt" not in files_at_head


async def test_create_branch_part_de_la_branche_courante_pas_de_main(
    repo: Path,
) -> None:
    # Le flux du dépôt est ticket -> develop -> main (ticket-049) : une branche
    # de ticket doit partir de la branche effectivement sortie (develop), pas
    # de main. La ref de base est capturée au premier usage du service, donc
    # elle suit naturellement develop — ce test le verrouille plutôt que de le
    # supposer.
    await _git(repo, "checkout", "-q", "-b", "develop")
    (repo / "sur-develop.py").write_text("x = 1\n", encoding="utf-8")
    await _git(repo, "add", "sur-develop.py")
    await _git(repo, "commit", "-q", "-m", "chore: travail integre sur develop")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-050", "nouvelle-feature")

    # Le commit de develop doit être dans l'ancêtre de la branche de ticket.
    files_at_head = await service._run("ls-tree", "-r", "--name-only", "HEAD")
    assert "sur-develop.py" in files_at_head

    log = await service._run("log", "--format=%s")
    assert "chore: travail integre sur develop" in log


async def test_un_projet_sans_depot_propre_ne_touche_pas_au_depot_parent(
    tmp_path: Path,
) -> None:
    # Panne vecue : les projets clients poses dans `projects/` sont des
    # dossiers de documents contenant N depots en sous-dossiers, sans depot a
    # leur racine. `git` remontait alors l'arborescence et trouvait le depot
    # de vibe-ide lui-meme : un run sur le projet du client creait sa branche
    # et son commit dans le depot de l'IDE.
    parent = tmp_path / "vibe-ide"
    parent.mkdir()
    await _git(parent, "init", "-q")
    await _git(parent, "config", "user.email", "t@t.local")
    await _git(parent, "config", "user.name", "t")
    (parent / "README.md").write_text("# ide", encoding="utf-8")
    await _git(parent, "add", "README.md")
    await _git(parent, "commit", "-qm", "init")

    projet = parent / "projects" / "client"
    projet.mkdir(parents=True)
    (projet / "notes.md").write_text("# notes", encoding="utf-8")

    svc = GitWorkspaceService(projet)

    with pytest.raises(NotAGitRepository):
        await svc.create_branch("ticket-001", "essai")
