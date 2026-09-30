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
