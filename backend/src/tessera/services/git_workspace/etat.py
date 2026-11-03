"""Working tree state: diffs, dirty files and policy file detection."""

from tessera.services.git_workspace.chemins import (
    _EMPTY_TREE_SHA,
    _is_orchestrator_artifact_path,
    _is_run_policy_path,
)
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.historique import GitHistory
from tessera.services.git_workspace.ignores import GitIgnores
from tessera.services.git_workspace.lockfiles import _resumer_lockfiles
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitState(GitIgnores, GitHistory):
    """Working tree state: diffs, dirty files and policy file detection."""

    async def diff_depuis_base(self) -> str:
        """Return the diff of the working tree against the branch's fork point.

        On a fresh branch this is identical to `current_diff()`: the branch
        was just created from the fork point, so HEAD is at that commit and
        the two ranges coincide.

        On a resumed branch (same ticket, second run) this extends the diff
        to cover every commit already on the branch — security, reviewer and
        validator then see the full accumulated work, not only the uncommitted
        changes of the current turn (ticket-208).

        Falls back to `current_diff()` when no fork point is known (no branch
        was created through this service instance, or the
        merge-base could not be computed).

        Lockfile sections are replaced by a one-line summary so that a large
        ``uv.lock`` or ``package-lock.json`` does not crowd out the actual
        code changes before the diff is truncated (ticket-272).
        """
        base = self._fork_point
        if base is None:
            return _resumer_lockfiles(await self.current_diff())

        non_suivis = await self._untracked_files()
        await self._run("add", "-A", "-N")
        pathspec = (
            ":/" if self._travaille_dans_le_parent() else ".",
            *await self._exclude_pathspecs(),
        )
        try:
            return _resumer_lockfiles(
                await self._run("diff", base, "--", *pathspec)
            )
        finally:
            await self._oublier_dans_l_index(non_suivis)

    async def current_diff(self) -> str:
        """Return the diff of the working tree against HEAD, staged or not.

        Untracked files never show up in a plain `git diff`; this stages
        them with intent-to-add (`git add -N`) first so the coder agent's
        newly created files are visible in the diff without actually being
        staged for commit. The diff is taken against `HEAD` rather than a
        bare `git diff` (which only shows the *unstaged* half) — a coding
        agent with shell access may well run `git add` on its own, and a
        bare `git diff` would then silently miss that staged work.

        On a repository with no commits yet, `HEAD` is an ambiguous
        revision; this falls back to diffing against git's empty-tree
        object, which exists in every repository and lets an intent-to-add
        entry show its full content even before the first commit.

        Tessera's own bookkeeping (`_ORCHESTRATOR_ARTIFACT_PATHS`) is
        excluded via pathspec: it is the orchestrator rewriting ticket
        status and the pipeline log, not code the coder agent produced, and
        must never be presented to the reviewer/auditor/validator/documentation
        agents as if it were.
        """
        # Relevé **avant** l'ajout : `-N` inscrit tout le non-suivi dans
        # l'index, et ce qui n'est pas commité ensuite y reste. Une entrée
        # *intent-to-add* suffit à faire refuser `git rebase` et à faire voir
        # l'arbre sale au ticket suivant — une file de trois n'en livrait
        # qu'un (ticket-170). Lire ne doit rien laisser derrière soi.
        non_suivis = await self._untracked_files()
        await self._run("add", "-A", "-N")
        pathspec = (
            ":/" if self._travaille_dans_le_parent() else ".",
            *await self._exclude_pathspecs(),
        )
        try:
            if await self._has_head():
                return await self._run("diff", "HEAD", "--", *pathspec)
            return await self._run("diff", _EMPTY_TREE_SHA, "--", *pathspec)
        finally:
            await self._oublier_dans_l_index(non_suivis)

    async def _oublier_dans_l_index(self, chemins: tuple[str, ...]) -> None:
        """Retire de l'index des chemins qui n'y étaient pas avant.

        Bornée aux fichiers **non suivis** au moment du relevé : le codeur ne
        peut pas les avoir stagés lui-même, donc les rendre à leur état ne
        perd rien. Sans `HEAD` — dépôt sans commit — `git reset` n'a rien à
        quoi se référer et sort en erreur ; il n'y a alors rien à défaire non
        plus, puisque tout l'index est neuf.
        """
        if not chemins or not await self._has_head():
            return
        try:
            await self._run("reset", "-q", "--", *chemins)
        except GitCommandError as exc:
            _logger.warning("index_non_restaure", extra={"erreur": str(exc)})

    async def dirty_files(self) -> list[str]:
        """Return tracked files modified outside Tessera's own bookkeeping.

        Same narrowing as ``is_clean``: restricted to tracked modifications
        (``--untracked-files=no``), with orchestrator-artifact and run-policy
        paths excluded.  Returns the list of files that would cause
        ``is_clean`` to return ``False``.
        """
        status = await self._run("status", "--porcelain", "--untracked-files=no")
        prefixe = (await self._run("rev-parse", "--show-prefix")).strip()
        fichiers: list[str] = []
        for line in status.splitlines():
            if len(line) < 3:  # noqa: PLR2004
                continue
            path = line[3:]
            if prefixe and path.startswith(prefixe):
                path = path[len(prefixe):]
            if not _is_orchestrator_artifact_path(path) and not _is_run_policy_path(path):
                fichiers.append(path)
        return fichiers

    async def is_clean(self) -> bool:
        """Return True when tracked files outside Tessera's bookkeeping have no changes.

        Deliberately narrowed to tracked modifications (`--untracked-files=no`):
        this is now a safety net for state changed *outside* Tessera, not the
        routine mechanism for isolating ticket runs (that job now belongs to
        per-run branches and commits). A plain `git status --porcelain` also
        reports untracked files, which would refuse a first run in any
        project holding a non-ignored untracked file (build output, scratch
        notes) before anything happened.

        Tessera's own bookkeeping paths (`_ORCHESTRATOR_ARTIFACT_PATHS`) are
        excluded: `_log` writes to `memory/pipeline-log.md` and ticket files
        are rewritten when a queue skips already-done tickets. Both are
        committed by the run's bookkeeping commit and must not be mistaken for
        an external modification that would block the next ticket.
        """
        status = await self._run("status", "--porcelain", "--untracked-files=no")
        # `--porcelain` donne les chemins depuis la racine du dépôt. Sous
        # `git_root: ancestor`, le journal est donc
        # `projects/ide-core/memory/pipeline-log.md`, que la comparaison avec
        # `memory/pipeline-log.md` ne reconnaissait pas : le ticket suivant
        # de la file était refusé dès que la livraison journalisait après son
        # dernier commit (ticket-301).
        prefixe = (await self._run("rev-parse", "--show-prefix")).strip()
        for line in status.splitlines():
            if len(line) < 3:  # noqa: PLR2004
                continue
            path = line[3:]
            if prefixe and path.startswith(prefixe):
                path = path[len(prefixe):]
            # Tolerates both Tessera's own bookkeeping (tickets/, pipeline-log)
            # and run-policy files (agents.json, .claude/settings*.json,
            # .github/workflows/) that the commit intentionally skips —
            # their presence in the working tree must not block the next ticket.
            if not _is_orchestrator_artifact_path(path) and not _is_run_policy_path(path):
                return False
        return True

    async def _file_had_content_in_head(self, rel_path: str) -> bool:
        """True when HEAD contains a non-empty, non-blank version of this file.

        A file that was already empty (or absent) in HEAD was not *reduced*
        to empty during this run — no warning needed.
        """
        if not await self._has_head():
            return False
        try:
            content = await self._run("show", f"HEAD:{rel_path}")
            return bool(content.strip())
        except GitCommandError:
            # File absent from HEAD (new file) — not a reduction.
            return False

    async def _detect_emptied_tracked_files(self) -> list[str]:
        """Return paths of tracked files *reduced* to empty or blank during this run.

        A file that was already empty in HEAD is excluded — only files whose
        tracked content was non-empty and are now empty on disk are reported.
        A brand-new empty file (not yet tracked) is also excluded.
        Called before ``git add`` so the working-tree state reflects what the
        coder left behind.
        """
        try:
            listing = await self._run("ls-files")
        except GitCommandError:
            return []

        emptied: list[str] = []
        root = self._project_path.resolve()
        for rel_path in listing.splitlines():
            rel_path = rel_path.strip()
            if not rel_path:
                continue
            full = self._project_path / rel_path
            if not full.is_file():
                # Deleted by rm — correct behaviour, not a warning.
                continue
            try:
                # Resolve symlinks before reading: a tracked symlink pointing
                # outside the project must never be followed (ADR-031).
                resolved = full.resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    continue
                content = resolved.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if content.strip():
                # File still has content — no problem.
                continue
            # File is empty or blank on disk; only warn if HEAD had content.
            if await self._file_had_content_in_head(rel_path):
                emptied.append(rel_path)
        return emptied

    async def _detect_modified_policy_files(self) -> list[str]:
        """Return paths of run-policy files modified in the working tree.

        These files are excluded from the ticket commit (ticket-296, ADR-027).
        Any modification found is logged as a warning in `commit_all` so the
        run report makes the exclusion visible, without blocking the commit.
        """
        try:
            status = await self._run("status", "--porcelain", "--untracked-files=no")
        except GitCommandError:
            return []
        prefixe = (await self._run("rev-parse", "--show-prefix")).strip()
        modified: list[str] = []
        for line in status.splitlines():
            if len(line) < 3:  # noqa: PLR2004
                continue
            path = line[3:]
            if prefixe and path.startswith(prefixe):
                path = path[len(prefixe):]
            if _is_run_policy_path(path):
                modified.append(path)
        return modified
