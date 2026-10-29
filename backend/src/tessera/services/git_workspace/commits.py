"""Committing the ticket's work and the pipeline bookkeeping."""

from pathlib import Path

from tessera.services.git_workspace.chemins import (
    _BOOKKEEPING_COMMIT_MESSAGE,
    _ORCHESTRATOR_ARTIFACT_PATHS,
)
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.etat import GitState
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitCommits(GitState):
    """Committing the ticket's work and the pipeline bookkeeping."""

    async def commit_all(self, message: str) -> str | None:
        """Commit the ticket's changes under `message`; return the short SHA.

        Tessera's own bookkeeping (`_ORCHESTRATOR_ARTIFACT_PATHS`) is staged
        and committed separately, under a fixed non-ticket message, instead
        of being swept into this commit by a blanket `git add -A`: it is the
        orchestrator rewriting ticket status and the pipeline log, not the
        coder's work, and must never be committed under a ticket's message.
        The bookkeeping commit still happens — via `_BOOKKEEPING_COMMIT_MESSAGE`
        — so the working tree ends up clean either way, which the next run's
        dirty-tree check relies on.

        Run-policy files (`_RUN_POLICY_PATHS`) are also excluded: a change
        made through the IDE during the run (e.g. updating the provider in the
        Agents screen) must not ride along with the coder's work. They remain
        in the working tree, uncommitted, and a warning is logged so the run
        report makes the exclusion visible (ticket-296, ADR-027).

        Returns the short SHA of the ticket commit, or None if nothing
        outside bookkeeping changed (a bookkeeping-only commit may still be
        created even when this returns None).

        Tracked files reduced to empty or blank content are signalled via a
        warning log entry (``emptied_tracked_files``): the coder should have
        removed them with ``rm`` so they disappear from the repository rather
        than staying as empty files. The commit is not blocked.
        """
        policy_modifiees = await self._detect_modified_policy_files()
        if policy_modifiees:
            _logger.warning(
                "run_policy_files_not_committed",
                extra={
                    "fichiers": policy_modifiees,
                    "raison": "politique du run — modifiée pendant le run, exclue du commit du ticket",
                },
            )
        emptied = await self._detect_emptied_tracked_files()
        if emptied:
            _logger.warning(
                "emptied_tracked_files",
                extra={"fichiers": emptied, "conseil": "utiliser rm pour supprimer"},
            )

        # `.` borne l'ajout au dossier du projet. C'est ce qu'on veut d'un
        # projet ordinaire — il *est* la racine de son dépôt — mais pas du
        # projet bootstrap, dont le travail est dans `backend/` et `frontend/`,
        # au-dessus de lui. `:/` désigne la racine du dépôt (ticket-081).
        racine = ":/" if self._travaille_dans_le_parent() else "."
        await self._run(
            "add",
            "-A",
            "--",
            racine,
            *await self._exclude_pathspecs(),
            *(f":(exclude){path}" for path in self._preexisting_untracked),
        )
        # Retire de l'index les fichiers devenus ignorés après le `git add -A`.
        # `git add -A` ne dé-stage pas automatiquement des fichiers déjà dans
        # l'index dont le chemin est maintenant couvert par `.gitignore` — par
        # exemple des WAL SQLite capturés par `intent-to-add` lors d'un diff
        # pendant qu'un serveur tournait, avant l'ajout de `*.db-shm` dans le
        # `.gitignore` (ticket-219).
        await self._purger_stage_ignoré()
        staged = await self._run("diff", "--cached", "--name-only")
        sha: str | None = None
        if staged.strip():
            await self._run("commit", "-m", message)
            sha = (await self._run("rev-parse", "--short", "HEAD")).strip()

        await self.commit_bookkeeping()
        return sha

    async def commit_chemins(self, message: str, chemins: list[str]) -> bool:
        """Stage exactly `chemins` (project-relative) and commit them (ticket-659).

        Renames and deletions are staged too. A path the repository ignores —
        the pipeline log of a project in `local` mode (ADR-021) — is skipped, as
        naming it would make `git add` exit 1. Returns False when nothing was
        staged, so no empty commit is made.
        """
        retenus = [c for c in chemins if not await self._is_ignored(c)]
        if not retenus:
            return False
        await self._run("add", "-A", "--", *retenus)
        if not (await self._run("diff", "--cached", "--name-only")).strip():
            return False
        await self._run("commit", "-m", message)
        return True

    async def _list_tracked_ticket_basenames(self) -> frozenset[str]:
        """Return the basenames of tracked files under ``tickets/`` at call time.

        Used by ``commit_bookkeeping`` to distinguish a status-folder move
        (the ticket's basename reappears in a new folder) from a ticket file
        created from scratch during the run, which must not ride along in the
        bookkeeping commit (ticket-343).
        """
        try:
            listing = await self._run("ls-files", "--", "tickets/")
        except GitCommandError:
            return frozenset()
        return frozenset(
            Path(p).name for p in listing.splitlines() if p.strip()
        )

    async def _stage_tickets_selectively(self) -> None:
        """Stage ticket files for the bookkeeping commit without sweeping new ones.

        Stages modifications and deletions of already-tracked ticket files (via
        ``git add --update``) and untracked files according to context:

        - Before ``create_branch`` (``_tracked_ticket_basenames is None``): every
          untracked ticket file is staged minus pre-existing ones.  This preserves
          the original behaviour needed when bookkeeping is committed before the
          branch switch (ticket-314).
        - After ``create_branch``: only untracked files whose basename was tracked
          at run start are staged (status-folder moves).  Files created from
          scratch during the run are left untracked (ticket-343).
        """
        # Run --update only when tickets/ has tracked content; an empty pathspec
        # match causes git to exit 128 on some platforms.
        try:
            tracked_under_tickets = await self._run("ls-files", "--", "tickets/")
        except GitCommandError:
            tracked_under_tickets = ""
        if tracked_under_tickets.strip():
            try:
                await self._run("add", "--update", "--", "tickets/")
            except GitCommandError as exc:
                _logger.warning("stage_tickets_update_failed", extra={"error": str(exc)})

        try:
            listing = await self._run(
                "ls-files", "--others", "--exclude-standard", "--", "tickets/"
            )
        except GitCommandError:
            return
        for untracked in listing.splitlines():
            untracked = untracked.strip()
            if not untracked:
                continue
            if untracked in self._preexisting_untracked:
                continue
            # None → create_branch not yet called, use original permissive behaviour.
            # frozenset → use the selective (basename-match) behaviour.
            if (
                self._tracked_ticket_basenames is None
                or Path(untracked).name in self._tracked_ticket_basenames
            ):
                await self._run("add", "--", untracked)

    async def commit_bookkeeping(self) -> None:
        """Commit only Tessera's own bookkeeping, under its fixed message.

        The PR-number write, commit and push now happen inside livraison via
        `post_pr_callback` *before* any merge, so no bookkeeping commit is
        ever stranded on the ticket branch after a merged PR (ticket-270).

        Files that were untracked at run start (`_preexisting_untracked`) are
        excluded: they were not produced by Tessera's own bookkeeping, and
        `commit_all` already excludes them from the main ticket commit.
        """
        # A project that has neither tickets/ nor memory/pipeline-log.md
        # yet (e.g. a git_workspace used outside the ticket pipeline, or a
        # fresh repository) must not fail `git add` on a pathspec matching
        # nothing — only add whichever bookkeeping paths actually exist.
        # Un chemin que le dépôt ignore est hors du dépôt **par décision** :
        # c'est le mode `local` d'ADR-021, qui écrit `tickets/` et `memory/`
        # dans `.git/info/exclude`. Tenter de le stager fait sortir git en
        # code 1 — et faisait donc échouer tout le commit de fin de run, donc
        # tout le run (ticket-072). Depuis ticket-068 cet échec est bruyant,
        # ce qui est précisément ce qui l'a rendu visible.
        existing_bookkeeping_paths = [
            p
            for p in _ORCHESTRATOR_ARTIFACT_PATHS
            if (self._project_path / p.rstrip("/")).exists()
        ]
        conservees: list[str] = []
        for chemin in existing_bookkeeping_paths:
            if not await self._is_ignored(chemin):
                conservees.append(chemin)
        existing_bookkeeping_paths = conservees
        if existing_bookkeeping_paths:
            # Stage each bookkeeping path selectively:
            # - tickets/ : modifications/deletions of tracked files + untracked
            #   status moves only — new tickets created during the run are left
            #   untracked (ticket-343).
            # - memory/pipeline-log.md : always Tessera's own file, stage directly.
            for chemin in existing_bookkeeping_paths:
                if chemin == "tickets/":
                    await self._stage_tickets_selectively()
                else:
                    await self._run("add", "--", chemin)
            staged_bookkeeping = await self._run("diff", "--cached", "--name-only")
            if staged_bookkeeping.strip():
                await self._run("commit", "-m", _BOOKKEEPING_COMMIT_MESSAGE)
