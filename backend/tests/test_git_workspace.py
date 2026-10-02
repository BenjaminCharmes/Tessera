import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import (
    GitCommandError,
    GitWorkspaceService,
    InvalidSlugError,
    NotAGitRepository,
    _resumer_lockfiles,
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
    await _git(root, "config", "user.email", "test@Tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
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


async def test_diff_from_base_covers_earlier_commits_of_a_resumed_branch(repo: Path) -> None:
    # ticket-208 : un premier run a commité `a.py` (travail non approuvé), un
    # second run reprend la branche et n'écrit que `b.md`. La branche date
    # d'avant le correctif : aucune ref ne retient son point de départ.
    await _git(repo, "checkout", "-q", "-b", "ticket-020-reprise")
    (repo / "a.py").write_text("print('premier run')\n", encoding="utf-8")
    await _git(repo, "add", "a.py")
    await _git(repo, "commit", "-q", "-m", "chore: unapproved work")
    await _git(repo, "checkout", "-q", "-")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-020", "reprise")
    (repo / "b.md").write_text("second run\n", encoding="utf-8")

    diff = await service.diff_depuis_base()
    assert "a.py" in diff
    assert "b.md" in diff


async def test_diff_from_base_equals_current_diff_on_a_fresh_branch(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-021", "neuve")
    (repo / "README.md").write_text("# projet modifie\n", encoding="utf-8")
    (repo / "nouveau.py").write_text("x = 1\n", encoding="utf-8")

    assert await service.diff_depuis_base() == await service.current_diff()


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
    await _git(root, "config", "user.email", "test@Tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
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


async def test_is_clean_vrai_si_seul_le_journal_pipeline_est_modifie(repo: Path) -> None:
    """A modified pipeline log must not block the next ticket (ticket-278).

    `_log` writes to `memory/pipeline-log.md` when a queue skips done
    tickets.  The dirty-tree check must ignore that write so it does not
    mistake the orchestrator's own bookkeeping for an external modification.
    """
    (repo / "memory").mkdir()
    log = repo / "memory" / "pipeline-log.md"
    log.write_text("# log\n", encoding="utf-8")
    await _git(repo, "add", "memory/pipeline-log.md")
    await _git(repo, "commit", "-q", "-m", "track log")

    log.write_text("# log\n- ticket-006 saute : deja termine\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    assert await service.is_clean() is True


async def test_is_clean_vrai_si_seul_un_fichier_tickets_est_modifie(repo: Path) -> None:
    """A modified ticket file must not block the next ticket (ticket-278).

    `TicketService.update_status` rewrites ticket files when a queue skips
    done tickets.  The dirty-tree check must ignore those rewrites.
    """
    tickets_dir = repo / "tickets" / "todo"
    tickets_dir.mkdir(parents=True)
    ticket_file = tickets_dir / "ticket-001-feature.md"
    ticket_file.write_text("# ticket-001\nstatus: todo\n", encoding="utf-8")
    await _git(repo, "add", "tickets/")
    await _git(repo, "commit", "-q", "-m", "track tickets")

    ticket_file.write_text("# ticket-001\nstatus: done\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    assert await service.is_clean() is True


async def test_is_clean_faux_si_un_fichier_non_bookkeeping_est_modifie(repo: Path) -> None:
    """A modification outside bookkeeping paths must still be refused (ticket-278)."""
    (repo / "README.md").write_text("# modifie par quelqu un d autre\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    assert await service.is_clean() is False


async def test_dirty_files_contient_le_fichier_code_modifie(repo: Path) -> None:
    """A modified code file appears in dirty_files (ticket-323)."""
    (repo / "README.md").write_text("# modifie\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    fichiers = await service.dirty_files()

    assert "README.md" in fichiers


async def test_dirty_files_exclut_le_journal_pipeline(repo: Path) -> None:
    """The pipeline log does not appear in dirty_files (ticket-323).

    ``_log`` appends to ``memory/pipeline-log.md`` between tickets. That
    modification belongs to Tessera's own bookkeeping and must not be
    reported as a blocking dirty file — otherwise the next ticket in a queue
    would be refused.
    """
    (repo / "memory").mkdir()
    log = repo / "memory" / "pipeline-log.md"
    log.write_text("# log\n", encoding="utf-8")
    await _git(repo, "add", "memory/pipeline-log.md")
    await _git(repo, "commit", "-q", "-m", "track log")

    log.write_text("# log\n- ticket-006 saute\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    fichiers = await service.dirty_files()

    assert fichiers == []


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
    # tickets/ and memory/pipeline-log.md are Tessera's own bookkeeping,
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
    assert subjects[0] == "chore: tessera pipeline bookkeeping"
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
    # de Tessera lui-meme : un run sur le projet du client creait sa branche
    # et son commit dans le depot de l'IDE.
    parent = tmp_path / "Tessera"
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


# ------------------------------------------------------------------
# Rejouer la branche sur une base qui a bougé — ticket-083
# ------------------------------------------------------------------


async def test_le_rebase_rejoue_la_branche_sur_la_base(repo: Path) -> None:
    # Sans cela, la PR part sur une base périmée : GitHub la déclare non
    # mergeable, et l'attente de CI tourne pour rien.
    service = GitWorkspaceService(repo)
    base = (await service._run("rev-parse", "--abbrev-ref", "HEAD")).strip()

    branche = await service.create_branch("ticket-001", "ma-feature")
    (repo / "feature.py").write_text("x = 1\n", encoding="utf-8")
    await service.commit_all("feat: ticket-001 — feature")

    await _git(repo, "checkout", "-q", base)
    (repo / "autre.py").write_text("y = 2\n", encoding="utf-8")
    await _git(repo, "add", "autre.py")
    await _git(repo, "commit", "-q", "-m", "chore: autre")
    await _git(repo, "checkout", "-q", branche)

    conflits = await service.rejouer_sur(base)

    assert conflits == ()
    assert (repo / "autre.py").exists()
    assert (repo / "feature.py").exists()


async def test_un_conflit_est_nomme_et_la_branche_reste_intacte(repo: Path) -> None:
    # Un rebase laissé à mi-chemin bloque tout ce qui suit : le ticket suivant
    # démarre sur un arbre en conflit, et l'utilisateur hérite d'un dépôt dans
    # un état qu'il n'a pas choisi.
    service = GitWorkspaceService(repo)
    base = (await service._run("rev-parse", "--abbrev-ref", "HEAD")).strip()

    branche = await service.create_branch("ticket-001", "ma-feature")
    (repo / "partage.py").write_text("version = 'branche'\n", encoding="utf-8")
    await service.commit_all("feat: ticket-001 — feature")

    await _git(repo, "checkout", "-q", base)
    (repo / "partage.py").write_text("version = 'base'\n", encoding="utf-8")
    await _git(repo, "add", "partage.py")
    await _git(repo, "commit", "-q", "-m", "chore: base")
    await _git(repo, "checkout", "-q", branche)

    conflits = await service.rejouer_sur(base)

    assert "partage.py" in conflits
    assert await service.is_clean()
    contenu = (repo / "partage.py").read_text(encoding="utf-8")
    assert "<<<<<<<" not in contenu
    assert contenu == "version = 'branche'\n"


# ------------------------------------------------------------------
# Faire résoudre un conflit, sans jamais laisser l'arbre à mi-chemin — t.090
# ------------------------------------------------------------------


async def _branche_en_conflit(repo: Path, service: GitWorkspaceService) -> str:
    """Prépare une branche dont le rebase sur la base entre en conflit."""
    base = (await service._run("rev-parse", "--abbrev-ref", "HEAD")).strip()
    branche = await service.create_branch("ticket-001", "ma-feature")
    (repo / "partage.py").write_text("version = 'branche'\n", encoding="utf-8")
    await service.commit_all("feat: ticket-001 — feature")
    await _git(repo, "checkout", "-q", base)
    (repo / "partage.py").write_text("version = 'base'\n", encoding="utf-8")
    await _git(repo, "add", "partage.py")
    await _git(repo, "commit", "-q", "-m", "chore: base")
    await _git(repo, "checkout", "-q", branche)
    return base


async def test_un_resolveur_qui_reussit_termine_le_rebase(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    base = await _branche_en_conflit(repo, service)

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        assert fichiers == ("partage.py",)
        (repo / "partage.py").write_text("version = 'les deux'\n", encoding="utf-8")

    conflits = await service.rejouer_sur(base, resolveur=resoudre)

    assert conflits == ()
    assert await service.is_clean()
    assert (repo / "partage.py").read_text(encoding="utf-8") == "version = 'les deux'\n"
    journal = await service._run("log", "--oneline")
    assert "base" in journal and "feature" in journal


async def test_un_resolveur_qui_laisse_des_marqueurs_fait_tout_annuler(
    repo: Path,
) -> None:
    # Un fichier qui garde ses `<<<<<<<` compile rarement et se relit encore
    # moins. Le committer serait pire que ne rien faire.
    service = GitWorkspaceService(repo)
    base = await _branche_en_conflit(repo, service)

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        (repo / "partage.py").write_text(
            "<<<<<<< HEAD\nversion = 'base'\n=======\nversion = 'branche'\n>>>>>>>\n",
            encoding="utf-8",
        )

    conflits = await service.rejouer_sur(base, resolveur=resoudre)

    assert conflits == ("partage.py",)
    assert await service.is_clean()
    assert (repo / "partage.py").read_text(encoding="utf-8") == "version = 'branche'\n"


async def test_un_resolveur_qui_leve_fait_tout_annuler(repo: Path) -> None:
    # L'arbre ne doit jamais rester à mi-rebase : le ticket suivant démarrerait
    # dessus, et l'utilisateur hériterait d'un dépôt qu'il n'a pas choisi.
    service = GitWorkspaceService(repo)
    base = await _branche_en_conflit(repo, service)

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        raise RuntimeError("l'agent a abandonné")

    conflits = await service.rejouer_sur(base, resolveur=resoudre)

    assert conflits == ("partage.py",)
    assert await service.is_clean()
    assert (repo / "partage.py").read_text(encoding="utf-8") == "version = 'branche'\n"


async def test_sans_resolveur_le_comportement_ne_change_pas(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    base = await _branche_en_conflit(repo, service)

    conflits = await service.rejouer_sur(base)

    assert conflits == ("partage.py",)
    assert await service.is_clean()


# ------------------------------------------------------------------
# Un hook déposé par l'agent ne s'exécute pas — ticket-119
# ------------------------------------------------------------------


async def test_un_pre_commit_depose_dans_le_depot_n_est_pas_execute(repo: Path) -> None:
    # `commit_all` lance `git commit` dans le process de l'orchestrateur, sous
    # l'identité de l'utilisateur. Un `pre-commit` écrit par un agent pendant
    # le run s'exécutait donc à la fin du run, sans qu'une seule commande git
    # ait transité par `Bash` : ADR-027 contourné par un fichier.
    marqueur = repo.parent / "le-hook-a-tourne"
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    chemin_marqueur = marqueur.as_posix()
    (hooks / "pre-commit").write_text(
        f"#!/bin/sh\necho pwned > '{chemin_marqueur}'\nexit 0\n", encoding="utf-8"
    )
    (hooks / "pre-commit").chmod(0o755)

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-119", "hooks")
    # Écrit après `create_branch` : un fichier déjà là au départ compte comme
    # non-suivi préexistant, donc pas comme le travail du run.
    (repo / "travail.py").write_text("x = 1\n", encoding="utf-8")
    sha = await service.commit_all("feat: travail")

    assert sha is not None
    assert not marqueur.exists(), "le hook du dépôt a été exécuté par l'orchestrateur"


async def test_what_a_push_publishes_is_read_from_the_commits(repo: Path) -> None:
    # ticket-206 : au push, l'arbre est propre ; le contrôle des termes lit le
    # contenu commité, le corps des messages et le committer.
    await _git(repo, "branch", "-M", "develop")
    service = GitWorkspaceService(repo)
    branche = await service.create_branch("ticket-030", "publication")
    (repo / "note.md").write_text("contenu commite\n", encoding="utf-8")
    await _git(repo, "add", "note.md")
    await _git(repo, "-c", "user.name=Committer Test", "-c", "user.email=c@example.com",
               "commit", "-q", "-m", "feat: sujet", "-m", "un corps de message")

    assert await service.current_diff() == "" or "note.md" not in await service.current_diff()
    diff = await service.diff_de_branche("develop", branche)
    assert "+contenu commite" in diff

    (commit,) = await service.commits_depuis_base("develop", branche)
    assert "un corps de message" in commit.message
    assert "c@example.com" in commit.auteur


# ---------------------------------------------------------------------------
# Lockfile summarization — ticket-272
# ---------------------------------------------------------------------------


def test_lockfile_summary_replaces_content_and_keeps_other_files() -> None:
    """uv.lock content is replaced by a summary; package.json content is kept."""
    diff = (
        "diff --git a/uv.lock b/uv.lock\n"
        "index abc..def 100644\n"
        "--- a/uv.lock\n"
        "+++ b/uv.lock\n"
        "@@ -1,3 +1,3 @@\n"
        " context\n"
        "-old-dep==1.0.0\n"
        "+old-dep==2.0.0\n"
        "diff --git a/package.json b/package.json\n"
        "index ghi..jkl 100644\n"
        "--- a/package.json\n"
        "+++ b/package.json\n"
        '@@ -1,2 +1,2 @@\n'
        '-  "version": "1.0"\n'
        '+  "version": "1.1"\n'
    )
    result = _resumer_lockfiles(diff)
    assert "uv.lock: lockfile modified" in result
    assert "old-dep==1.0.0" not in result
    assert "old-dep==2.0.0" not in result
    assert "package.json" in result
    assert '"version": "1.1"' in result


def test_lockfile_summary_counts_added_and_removed_lines() -> None:
    """The summary line reports the exact count of added and removed lines."""
    diff = (
        "diff --git a/yarn.lock b/yarn.lock\n"
        "index abc..def 100644\n"
        "--- a/yarn.lock\n"
        "+++ b/yarn.lock\n"
        "@@ -1,5 +1,6 @@\n"
        " context\n"
        "-removed1\n"
        "-removed2\n"
        "+added1\n"
        "+added2\n"
        "+added3\n"
        " context\n"
    )
    result = _resumer_lockfiles(diff)
    assert "3 lines added" in result
    assert "2 deleted" in result


def test_lockfile_in_subdirectory_is_summarized() -> None:
    """backend/uv.lock is summarized even though it lives in a subdirectory."""
    diff = (
        "diff --git a/backend/uv.lock b/backend/uv.lock\n"
        "index abc..def 100644\n"
        "--- a/backend/uv.lock\n"
        "+++ b/backend/uv.lock\n"
        "@@ -1,2 +1,2 @@\n"
        "-dep==1.0\n"
        "+dep==2.0\n"
    )
    result = _resumer_lockfiles(diff)
    assert "backend/uv.lock: lockfile modified" in result
    assert "dep==1.0" not in result
    assert "dep==2.0" not in result


# ---------------------------------------------------------------------------
# sync_base_depuis_distant — ticket-264
# ---------------------------------------------------------------------------


async def _git_out(cwd: Path, *args: str) -> str:
    """Runs a git command and returns its stdout."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()
    return out.decode().strip()


@pytest.fixture
async def repo_avec_distant(tmp_path: Path) -> tuple[Path, Path]:
    """A local repo linked to a bare remote, with a 'develop' branch."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, "init", "--bare", "-q")

    local = tmp_path / "local"
    local.mkdir()
    await _git(local, "init", "-q")
    await _git(local, "config", "user.email", "test@tessera.local")
    await _git(local, "config", "user.name", "Tessera test")

    # Premier commit sur develop
    (local / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(local, "add", "README.md")
    await _git(local, "commit", "-q", "-m", "init")
    await _git(local, "branch", "-M", "develop")
    await _git(local, "remote", "add", "origin", str(bare))
    await _git(local, "push", "-q", "--set-upstream", "origin", "develop")

    return local, bare


async def test_sync_base_depuis_distant_apres_merge_squash(
    repo_avec_distant: tuple[Path, Path],
) -> None:
    """After a squash merge on the remote, _base_ref advances to the squash commit.

    Simulates a full queue cycle: ticket-1 gets approved and advance_base_ref()
    is called, then the remote 'develop' gains a squash commit.
    sync_base_depuis_distant() must reposition _base_ref so ticket-2 starts
    from the squash commit, not from the ticket-1 branch tip.

    Key invariant: ``advance_base_ref()`` sets ``_base_ref`` to the ticket branch
    tip, which is NOT an ancestor of the squash commit (squash starts from the
    original develop base, not from the ticket commits). The sync must check the
    local ``develop`` branch ref instead of ``_base_ref``, because the local develop
    IS an ancestor of the squash commit (it hasn't moved since the ticket forked).
    """
    local, _bare = repo_avec_distant

    service = GitWorkspaceService(local)

    # --- Ticket 1 cycle ---
    await service.create_branch("ticket-001", "feat-a")
    (local / "a.py").write_text("x = 1\n", encoding="utf-8")
    await _git(local, "add", "a.py")
    await _git(local, "commit", "-q", "-m", "feat: ticket-001")
    # Orchestrateur appelle advance_base_ref après approbation : _base_ref pointe
    # maintenant sur le commit du ticket, pas sur develop.
    await service.advance_base_ref()

    # Côté remote : squash commit sur develop via un worktree sur develop.
    # Le worktree avance la branche locale develop ET la pousse, simulant le
    # squash merge de GitHub : develop reçoit un nouveau commit qui n'est pas
    # dans la lignée directe du ticket.
    wt = local.parent / "worktree-squash"
    await _git(local, "worktree", "add", str(wt), "develop")
    try:
        await _git(wt, "config", "user.email", "test@tessera.local")
        await _git(wt, "config", "user.name", "Tessera test")
        (wt / "squash.py").write_text("# squash\n", encoding="utf-8")
        await _git(wt, "add", "squash.py")
        await _git(wt, "commit", "-q", "-m", "feat: squash commit (ticket-001)")
        await _git(wt, "push", "-q", "origin", "develop")
    finally:
        await _git(local, "worktree", "remove", "--force", str(wt))

    # Après le worktree : local/develop = SHA_squash = remote/develop
    squash_sha = await _git_out(local, "rev-parse", "refs/heads/develop")

    # Sync
    raison = await service.sync_base_depuis_distant("develop")

    assert raison is None, f"sync a échoué : {raison}"
    assert service._base_ref == squash_sha, (
        f"_base_ref devrait être le squash commit ({squash_sha[:7]}), "
        f"non {(service._base_ref or '')[:7]}"
    )

    # Ticket 2 doit partir du squash commit
    await service.create_branch("ticket-002", "feat-b")
    head2_sha = await _git_out(local, "rev-parse", "HEAD")

    # HEAD de ticket-002 est exactement le squash commit (aucun commit encore dessus)
    assert head2_sha == squash_sha, (
        f"ticket-002 ({head2_sha[:7]}) devrait démarrer du squash commit "
        f"({squash_sha[:7]})"
    )


async def test_sync_base_non_appelee_quand_non_merge(
    repo_avec_distant: tuple[Path, Path],
) -> None:
    """Without sync, the next ticket still starts from the previous ticket branch tip.

    When delivery did not merge (autonomy: commit or pr, or CI was red), the
    queue must stack on the approved branch tip — not on the remote develop.
    This test verifies that _base_ref stays where advance_base_ref() left it.
    """
    local, _bare = repo_avec_distant

    service = GitWorkspaceService(local)

    # Ticket 1 : approuvé, advance_base_ref avance sur la branche
    await service.create_branch("ticket-001", "feat-a")
    (local / "a.py").write_text("x = 1\n", encoding="utf-8")
    await _git(local, "add", "a.py")
    await _git(local, "commit", "-q", "-m", "feat: ticket-001")
    await service.advance_base_ref()
    base_ref_apres_ticket1 = service._base_ref

    # Pas de sync (livraison non mergée)

    # Ticket 2 repart de la branche du ticket 1
    await service.create_branch("ticket-002", "feat-b")
    head2_sha = await _git_out(local, "rev-parse", "HEAD")

    assert service._base_ref == base_ref_apres_ticket1, (
        "_base_ref ne doit pas avoir changé sans appel à sync"
    )
    # HEAD de ticket-002 est identique à _base_ref (aucun commit encore)
    assert head2_sha == base_ref_apres_ticket1


async def test_sync_base_divergee_retourne_une_raison_sans_modifier_base_ref(
    repo_avec_distant: tuple[Path, Path],
) -> None:
    """A diverged local develop is not rewritten and the reason is returned.

    We create a true divergence: local 'develop' is forced to a commit that is
    NOT an ancestor of the commit on the remote — both are children of the
    initial commit but with different content, so neither is ancestor of the other.
    """
    local, bare = repo_avec_distant

    service = GitWorkspaceService(local)
    await service.create_branch("ticket-001", "feat-a")

    # Commit on the ticket branch → SHA_ticket (child of SHA_init with 'a.py')
    (local / "a.py").write_text("x = 1\n", encoding="utf-8")
    await service.commit_all("feat: ticket-001")
    sha_ticket = await _git_out(local, "rev-parse", "HEAD")

    # Force la branche locale develop à pointer sur SHA_ticket.
    # SHA_ticket est un enfant de SHA_init avec le fichier 'a.py', alors que
    # le remote aura un commit différent (enfant de SHA_init sans 'a.py').
    # Ni l'un ni l'autre n'est ancêtre de l'autre → divergence vraie.
    proc = await asyncio.create_subprocess_exec(
        "git", "update-ref", "refs/heads/develop", sha_ticket,
        cwd=str(local),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    assert proc.returncode == 0

    # Dans le dépôt nu, crée un commit indépendant depuis l'état initial.
    # git commit-tree crée un commit sans travailler dans un arbre de travail.
    sha_init = await _git_out(bare, "rev-parse", "develop")
    tree_sha = await _git_out(bare, "rev-parse", "develop^{tree}")
    import os as _os
    git_env = {
        **_os.environ,
        "GIT_AUTHOR_NAME": "Tessera test",
        "GIT_AUTHOR_EMAIL": "test@tessera.local",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
        "GIT_COMMITTER_NAME": "Tessera test",
        "GIT_COMMITTER_EMAIL": "test@tessera.local",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000",
    }
    ct_proc = await asyncio.create_subprocess_exec(
        "git", "commit-tree", tree_sha, "-p", sha_init, "-m", "remote diverge",
        cwd=str(bare),
        env=git_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    ct_out, ct_err = await ct_proc.communicate()
    assert ct_proc.returncode == 0, ct_err.decode()
    sha_remote = ct_out.decode().strip()

    # Met à jour remote develop pour pointer sur ce commit indépendant.
    ur_proc = await asyncio.create_subprocess_exec(
        "git", "update-ref", "refs/heads/develop", sha_remote,
        cwd=str(bare),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await ur_proc.communicate()
    assert ur_proc.returncode == 0

    # local/develop = sha_ticket, remote/develop = sha_remote
    # Aucun n'est ancêtre de l'autre : divergence confirmée.
    raison = await service.sync_base_depuis_distant("develop")

    assert raison is not None, "sync devait retourner une raison pour une base divergée"
    assert "divergé" in raison, f"la raison devrait mentionner la divergence : {raison}"
    # _base_ref ne doit pas avoir changé
    current_base = service._base_ref
    assert current_base != sha_remote, (
        "_base_ref ne doit pas avoir été mis à jour sur une base divergée"
    )


# ------------------------------------------------------------------
# Fichiers suivis vidés pendant un run — ticket-277
# ------------------------------------------------------------------


async def test_commit_all_signale_un_fichier_suivi_vide(
    repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Un codeur qui vide un fichier suivi au lieu de le supprimer laisse un
    # fichier vide dans le dépôt. Le commit ne doit pas être bloqué, mais un
    # avertissement doit signaler le fichier concerné.
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-277", "signaler-vide")

    # README.md est suivi depuis le commit initial ; on le vide.
    (repo / "README.md").write_text("", encoding="utf-8")

    import logging
    with caplog.at_level(logging.WARNING, logger="tessera.services.git_workspace"):
        sha = await service.commit_all("feat: ticket-277 — vider un fichier")

    assert sha is not None
    assert any(
        record.getMessage() == "emptied_tracked_files"
        for record in caplog.records
    ), f"Aucun avertissement emptied_tracked_files dans {[r.getMessage() for r in caplog.records]}"

    # Le fichier vide est bien commité (pas bloqué).
    files_at_head = await service._run("ls-tree", "-r", "--name-only", "HEAD")
    assert "README.md" in files_at_head


async def test_commit_all_ne_signale_pas_un_fichier_supprime_par_rm(
    repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Un fichier supprimé par `rm` disparaît du système de fichiers : il ne
    # doit pas déclencher d'avertissement, et sa suppression doit être commitée.
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-277", "supprimer-par-rm")

    # Suppression par rm (comportement attendu du codeur).
    (repo / "README.md").unlink()

    import logging
    with caplog.at_level(logging.WARNING, logger="tessera.services.git_workspace"):
        sha = await service.commit_all("feat: ticket-277 — supprimer un fichier")

    assert sha is not None
    emptied_records = [
        r for r in caplog.records
        if r.getMessage() == "emptied_tracked_files"
    ]
    assert not emptied_records, (
        f"Aucun avertissement emptied_tracked_files ne devrait être émis pour un rm : {emptied_records}"
    )

    # Le fichier n'est plus dans l'arbre.
    files_at_head = await service._run("ls-tree", "-r", "--name-only", "HEAD")
    assert "README.md" not in files_at_head


async def test_commit_all_ne_signale_pas_un_fichier_vide_depuis_le_debut(
    repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Un fichier suivi qui était déjà vide dans HEAD (ex : __init__.py)
    # n'a pas été *réduit* à vide pendant ce run : aucun avertissement.
    (repo / "__init__.py").write_text("", encoding="utf-8")
    await _git(repo, "add", "__init__.py")
    await _git(repo, "commit", "-q", "-m", "chore: add empty init")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-277", "init-vide")
    # On ne touche pas à __init__.py — il reste vide comme en HEAD.

    import logging
    with caplog.at_level(logging.WARNING, logger="tessera.services.git_workspace"):
        await service.commit_all("chore: rien ne change")

    emptied_records = [
        r for r in caplog.records
        if r.getMessage() == "emptied_tracked_files"
    ]
    assert not emptied_records, (
        f"Un fichier déjà vide en HEAD ne doit pas déclencher d'avertissement : {emptied_records}"
    )


async def test_detect_emptied_ne_suit_pas_un_symlink_hors_projet(
    repo: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # ADR-031 : les deux côtés sont résolus, symlinks compris. Un dépôt qui
    # trace un symlink pointant hors du projet ne doit pas permettre de lire
    # le fichier cible lors de la détection des fichiers vidés.
    external = tmp_path / "externe.txt"
    external.write_text("contenu externe\n", encoding="utf-8")

    symlink = repo / "lien.txt"
    try:
        symlink.symlink_to(external)
    except (OSError, NotImplementedError):
        pytest.skip("Création de symlink non disponible dans cet environnement")

    await _git(repo, "add", "lien.txt")
    await _git(repo, "commit", "-q", "-m", "chore: add symlink")

    # On vide le fichier externe (le symlink pointe vers un fichier vide).
    external.write_text("", encoding="utf-8")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-277", "symlink-hors-projet")

    # Le symlink pointe hors du projet : _detect_emptied_tracked_files doit
    # l'ignorer, pas le lire ni le signaler.
    import logging
    with caplog.at_level(logging.WARNING, logger="tessera.services.git_workspace"):
        await service.commit_all("chore: symlink externe vide")

    emptied_records = [
        r for r in caplog.records
        if r.getMessage() == "emptied_tracked_files"
    ]
    assert not emptied_records, (
        f"Un symlink hors projet ne doit pas déclencher d'avertissement : {emptied_records}"
    )


# ------------------------------------------------------------------
# Initialisation de la base depuis le distant — ticket-285
# ------------------------------------------------------------------


async def test_initialiser_base_ref_depuis_origin(
    repo_avec_distant: tuple[Path, Path],
) -> None:
    """A run started when HEAD is on an old ticket branch forks from origin/develop.

    After a delivered ticket, the repo stays on the ticket branch. The next run
    must fork from origin/develop (the squash base), not from HEAD.
    """
    local, _bare = repo_avec_distant

    # Add a remote-only commit (simulates a squash merge on develop)
    autre = local.parent / "autre-clone"
    autre.mkdir()
    await _git(autre, "init", "-q")
    await _git(autre, "config", "user.email", "test@tessera.local")
    await _git(autre, "config", "user.name", "Tessera test")
    await _git(autre, "remote", "add", "origin", str(_bare))
    await _git(autre, "fetch", "-q", "origin")
    await _git(autre, "checkout", "-q", "-b", "develop", "origin/develop")
    (autre / "remote-commit.py").write_text("# remote\n", encoding="utf-8")
    await _git(autre, "add", "remote-commit.py")
    await _git(autre, "commit", "-q", "-m", "feat: remote commit on develop")
    await _git(autre, "push", "-q", "origin", "develop")

    remote_sha = await _git_out(local, "ls-remote", "origin", "refs/heads/develop")
    remote_sha = remote_sha.split("\t")[0].strip()

    # Local repo left on an old ticket branch (HEAD is not develop)
    await _git(local, "checkout", "-q", "-b", "ticket-old-branch")
    (local / "old.py").write_text("x = 1\n", encoding="utf-8")
    await _git(local, "add", "old.py")
    await _git(local, "commit", "-q", "-m", "feat: old ticket work")

    service = GitWorkspaceService(local)
    raison = await service.initialiser_base_ref("develop")

    assert raison is None
    assert service._base_ref == remote_sha, (
        f"_base_ref should point to remote commit ({remote_sha[:7]}), "
        f"not HEAD of ticket-old-branch ({(service._base_ref or '')[:7]})"
    )

    # New ticket branch forks from the remote SHA
    await service.create_branch("ticket-new", "nouvelle-feature")
    head_sha = await _git_out(local, "rev-parse", "HEAD")
    assert head_sha == remote_sha, (
        f"ticket-new ({head_sha[:7]}) should start from remote develop ({remote_sha[:7]})"
    )


async def test_initialiser_base_ref_sans_distant_utilise_base_locale(
    repo: Path,
) -> None:
    """Without a remote, initialiser_base_ref uses the local base_branch ref, not HEAD."""
    # Create a develop branch ahead of main
    await _git(repo, "checkout", "-q", "-b", "develop")
    (repo / "develop.py").write_text("on develop\n", encoding="utf-8")
    await _git(repo, "add", "develop.py")
    await _git(repo, "commit", "-q", "-m", "chore: develop commit")
    develop_sha = await _git_out(repo, "rev-parse", "HEAD")

    # Leave HEAD on an old ticket branch (different from develop)
    await _git(repo, "checkout", "-q", "-b", "ticket-old")
    (repo / "old.py").write_text("old\n", encoding="utf-8")
    await _git(repo, "add", "old.py")
    await _git(repo, "commit", "-q", "-m", "feat: old work")

    service = GitWorkspaceService(repo)
    raison = await service.initialiser_base_ref("develop")

    assert raison is None, f"Sans distant, pas de blocage attendu : {raison}"
    assert service._base_ref == develop_sha, (
        f"_base_ref devrait être develop ({develop_sha[:7]}), "
        f"non HEAD de ticket-old ({(service._base_ref or '')[:7]})"
    )


async def test_initialiser_base_ref_base_divergee_bloque(
    repo_avec_distant: tuple[Path, Path],
) -> None:
    """A locally diverged base_branch blocks the run with a reason naming the branch.

    We create a true divergence: local develop has a commit that is not an
    ancestor of the remote develop, and remote has a commit not in local.
    Neither is ancestor of the other.
    """
    local, bare = repo_avec_distant

    # Add a remote-only commit (via a separate clone)
    autre = local.parent / "autre-diverge"
    autre.mkdir()
    await _git(autre, "init", "-q")
    await _git(autre, "config", "user.email", "test@tessera.local")
    await _git(autre, "config", "user.name", "Tessera test")
    await _git(autre, "remote", "add", "origin", str(bare))
    await _git(autre, "fetch", "-q", "origin")
    await _git(autre, "checkout", "-q", "-b", "develop", "origin/develop")
    (autre / "remote-only.py").write_text("remote\n", encoding="utf-8")
    await _git(autre, "add", "remote-only.py")
    await _git(autre, "commit", "-q", "-m", "chore: remote only commit")
    await _git(autre, "push", "-q", "origin", "develop")

    # Add a LOCAL commit to local develop (without fetching → divergence)
    await _git(local, "checkout", "-q", "develop")
    (local / "local-only.py").write_text("local\n", encoding="utf-8")
    await _git(local, "add", "local-only.py")
    await _git(local, "commit", "-q", "-m", "chore: local only commit")
    local_sha_before = await _git_out(local, "rev-parse", "refs/heads/develop")

    service = GitWorkspaceService(local)
    raison = await service.initialiser_base_ref("develop")

    assert raison is not None, "A diverged base must return a blocking reason"
    assert "develop" in raison, f"The reason must name the branch: {raison}"
    # Local branch must NOT have been force-reset
    local_sha_after = await _git_out(local, "rev-parse", "refs/heads/develop")
    assert local_sha_after == local_sha_before, (
        "Local develop must not be rewritten on divergence"
    )


async def test_scenario_freelance_ticket_b_ne_contient_pas_les_commits_de_ticket_a(
    repo_avec_distant: tuple[Path, Path],
) -> None:
    """Ticket-285 scenario: ticket A squash-merged, repo on A's branch, ticket B is clean.

    After ticket A is squash-merged on the remote, the local repo is left on the
    ticket-A branch. The next run must fork from origin/develop (the squash),
    so ticket B's commits contain only ticket B's work — no duplicates of A.
    """
    local, bare = repo_avec_distant

    service_a = GitWorkspaceService(local)

    # --- Ticket A ---
    await service_a.create_branch("ticket-a", "feature-a")
    (local / "a.py").write_text("# work for A\n", encoding="utf-8")
    await service_a.commit_all("feat: ticket-a — feature a")
    branch_a = await _git_out(local, "rev-parse", "--abbrev-ref", "HEAD")

    # Simulate squash merge on remote: another clone adds A's content in a squash commit
    squash_clone = local.parent / "squash-clone"
    squash_clone.mkdir()
    await _git(squash_clone, "init", "-q")
    await _git(squash_clone, "config", "user.email", "test@tessera.local")
    await _git(squash_clone, "config", "user.name", "Tessera test")
    await _git(squash_clone, "remote", "add", "origin", str(bare))
    await _git(squash_clone, "fetch", "-q", "origin")
    await _git(squash_clone, "checkout", "-q", "-b", "develop", "origin/develop")
    (squash_clone / "a.py").write_text("# work for A\n", encoding="utf-8")
    await _git(squash_clone, "add", "a.py")
    await _git(squash_clone, "commit", "-q", "-m", "feat: ticket-a — feature a (squash)")
    await _git(squash_clone, "push", "-q", "origin", "develop")
    squash_sha = await _git_out(squash_clone, "rev-parse", "HEAD")

    # Local repo stays on ticket-a branch (as after a livraison push)
    current_branch = await _git_out(local, "rev-parse", "--abbrev-ref", "HEAD")
    assert current_branch == branch_a

    # --- Ticket B run: initialiser_base_ref syncs develop with remote ---
    service_b = GitWorkspaceService(local)
    raison = await service_b.initialiser_base_ref("develop")
    assert raison is None, f"No divergence expected: {raison}"
    assert service_b._base_ref == squash_sha, (
        f"_base_ref should be the squash commit ({squash_sha[:7]}), "
        f"not {(service_b._base_ref or '')[:7]}"
    )

    await service_b.create_branch("ticket-b", "feature-b")
    (local / "b.py").write_text("# work for B\n", encoding="utf-8")
    await service_b.commit_all("feat: ticket-b — feature b")

    # Commits from ticket-b above squash_sha must not include ticket-a's commits
    log = await _git_out(local, "log", f"{squash_sha}..HEAD", "--oneline")
    assert "feat: ticket-b" in log
    assert "feat: ticket-a" not in log, (
        "Ticket B's commits above the squash base must not include ticket A's commits"
    )


# ------------------------------------------------------------------
# Run-policy files — ticket-296
# ------------------------------------------------------------------


async def test_commit_all_ne_committe_pas_agents_json_modifie(
    repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A change to agents.json made during a run must not appear in the ticket commit.

    The policy file may be edited through the IDE's Agents screen while the
    pipeline is running. The commit must contain only the coder's work.
    """
    agents_json = repo / "agents.json"
    agents_json.write_text('{"autonomy": "commit"}\n', encoding="utf-8")
    await _git(repo, "add", "agents.json")
    await _git(repo, "commit", "-q", "-m", "chore: add agents.json")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-296", "no-agents-json")

    (repo / "feature.py").write_text("x = 1\n", encoding="utf-8")
    agents_json.write_text('{"autonomy": "pr", "provider": "claude"}\n', encoding="utf-8")

    import logging
    with caplog.at_level(logging.WARNING, logger="tessera.services.git_workspace"):
        sha = await service.commit_all("feat: ticket-296 — feature")

    assert sha is not None, "The coder's work must have been committed"

    files_in_commit = await _git_out(repo, "show", "--name-only", "--format=", sha)
    assert "agents.json" not in files_in_commit, (
        "agents.json must never appear in the ticket commit"
    )


async def test_agents_json_reste_dans_arbre_apres_commit(repo: Path) -> None:
    """A modified agents.json must remain in the working tree after the commit.

    The pipeline explicitly leaves it uncommitted: the next ticket should not
    find it missing, and the user's IDE edit must not be silently discarded.
    """
    agents_json = repo / "agents.json"
    agents_json.write_text('{"autonomy": "commit"}\n', encoding="utf-8")
    await _git(repo, "add", "agents.json")
    await _git(repo, "commit", "-q", "-m", "chore: add agents.json")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-296", "agents-reste-dans-arbre")

    (repo / "work.py").write_text("y = 2\n", encoding="utf-8")
    agents_json.write_text('{"autonomy": "merge"}\n', encoding="utf-8")

    await service.commit_all("feat: ticket-296 — work")

    assert agents_json.read_text(encoding="utf-8") == '{"autonomy": "merge"}\n', (
        "agents.json modification must remain in the working tree after the commit"
    )


async def test_commit_all_ne_committe_pas_github_workflows_modifie(
    repo: Path,
) -> None:
    """A file inside .github/workflows/ must not appear in the ticket commit."""
    workflows_dir = repo / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    ci_yml = workflows_dir / "ci.yml"
    ci_yml.write_text("name: CI\n", encoding="utf-8")
    await _git(repo, "add", ".github/workflows/ci.yml")
    await _git(repo, "commit", "-q", "-m", "chore: add ci workflow")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-296", "no-workflows")

    (repo / "main.py").write_text("main = True\n", encoding="utf-8")
    ci_yml.write_text("name: CI\non: [push]\n", encoding="utf-8")

    sha = await service.commit_all("feat: ticket-296 — main")

    assert sha is not None
    files_in_commit = await _git_out(repo, "show", "--name-only", "--format=", sha)
    assert ".github/workflows/ci.yml" not in files_in_commit, (
        ".github/workflows/ files must never appear in the ticket commit"
    )


async def test_commit_all_committe_le_travail_du_codeur_normalement(
    repo: Path,
) -> None:
    """Coder's own files must be committed normally even when policy files are modified."""
    agents_json = repo / "agents.json"
    agents_json.write_text('{"autonomy": "commit"}\n', encoding="utf-8")
    await _git(repo, "add", "agents.json")
    await _git(repo, "commit", "-q", "-m", "chore: add agents.json")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-296", "coder-work-committed")

    (repo / "solution.py").write_text("answer = 42\n", encoding="utf-8")
    agents_json.write_text('{"autonomy": "pr"}\n', encoding="utf-8")

    sha = await service.commit_all("feat: ticket-296 — solution")

    assert sha is not None, "The coder's file must have produced a commit"
    files_in_commit = await _git_out(repo, "show", "--name-only", "--format=", sha)
    assert "solution.py" in files_in_commit, (
        "The coder's solution.py must be in the ticket commit"
    )
    assert "agents.json" not in files_in_commit


async def test_is_clean_vrai_si_seul_agents_json_est_modifie(repo: Path) -> None:
    """A modified agents.json must not block the next ticket (ticket-296).

    When a pipeline commit intentionally leaves agents.json uncommitted,
    is_clean() must still return True so the next ticket in the queue
    can start without being refused.
    """
    agents_json = repo / "agents.json"
    agents_json.write_text('{"autonomy": "commit"}\n', encoding="utf-8")
    await _git(repo, "add", "agents.json")
    await _git(repo, "commit", "-q", "-m", "chore: add agents.json")

    agents_json.write_text('{"autonomy": "pr"}\n', encoding="utf-8")

    service = GitWorkspaceService(repo)
    assert await service.is_clean() is True, (
        "A modified agents.json must not block the next ticket"
    )


async def test_commit_all_logue_un_warning_si_agents_json_modifie(
    repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """commit_all must log a warning when a policy file is excluded from the commit."""
    agents_json = repo / "agents.json"
    agents_json.write_text('{"autonomy": "commit"}\n', encoding="utf-8")
    await _git(repo, "add", "agents.json")
    await _git(repo, "commit", "-q", "-m", "chore: add agents.json")

    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-296", "warning-policy")

    (repo / "code.py").write_text("pass\n", encoding="utf-8")
    agents_json.write_text('{"autonomy": "merge"}\n', encoding="utf-8")

    import logging
    with caplog.at_level(logging.WARNING, logger="tessera.services.git_workspace"):
        await service.commit_all("feat: ticket-296 — code")

    policy_records = [
        r for r in caplog.records
        if r.getMessage() == "run_policy_files_not_committed"
    ]
    assert policy_records, "A warning must be emitted when a policy file is excluded"
    assert "agents.json" in str(policy_records[0].__dict__)
