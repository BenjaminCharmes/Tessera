"""Bringing the local base up to date with the remote one."""

import asyncio

from tessera.services.git_workspace.base import GitBase
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitSync(GitBase):
    """Bringing the local base up to date with the remote one."""

    async def _sync_base_du_worktree(self, base_branch: str) -> str | None:
        """Fetch the remote base and point `_base_ref` at it; no local ref moves."""
        try:
            await self._run("fetch", "origin", base_branch)
            self._base_ref = (await self._run("rev-parse", f"origin/{base_branch}")).strip()
        except GitCommandError as exc:
            raison = f"fetch origin {base_branch} échoué : {exc.stderr.strip()}"
            _logger.warning("sync_base_fetch_echoue", extra={"erreur": raison})
            return raison
        return None

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        """Fetch the remote base and fast-forward the local branch to it.

        Called after a merged delivery: the squash on the remote means that
        ``_base_ref`` (which points to the ticket branch tip) and the remote
        base have diverged. Re-aligning ``_base_ref`` with the remote ensures
        the next ticket in a queue starts from the squash commit, not from
        the previous ticket's branch tip — which would carry duplicate commits
        into the next PR (ticket-264).

        Returns ``None`` on success, or a human-readable reason when the sync
        was skipped (no remote configured, diverged local history). Never
        force-pushes or hard-resets (ADR-022).

        In a run worktree (ADR-056) only ``_base_ref`` moves: the local base
        branch belongs to the checkout, which this run never touches.
        """
        if self._worktree is not None:
            return await self._sync_base_du_worktree(base_branch)
        try:
            await self._run("fetch", "origin", base_branch)
        except GitCommandError as exc:
            raison = f"fetch origin {base_branch} échoué : {exc.stderr.strip()}"
            _logger.warning("sync_base_fetch_echoue", extra={"erreur": raison})
            return raison

        # Read FETCH_HEAD immediately after fetch to avoid a race with another
        # concurrent git process overwriting the file (FETCH_HEAD is not a
        # named ref, but a plain file that any fetch overwrites).
        try:
            fetch_sha = (await self._run("rev-parse", "FETCH_HEAD")).strip()
        except GitCommandError as exc:
            raison = f"rev-parse FETCH_HEAD échoué : {exc.stderr.strip()}"
            _logger.warning("sync_base_rev_parse_echoue", extra={"erreur": raison})
            return raison

        # Verify fast-forward against the LOCAL base branch, not ``_base_ref``.
        # After ``advance_base_ref()`` the latter points to the ticket branch tip,
        # which is NOT an ancestor of the squash commit — yet the local base branch
        # (e.g. develop) IS, because it has not moved since the ticket forked
        # (ticket-264). Checking the wrong ref was what caused the squash scenario
        # to be incorrectly treated as a divergence.
        try:
            local_sha = (
                await self._run("rev-parse", f"refs/heads/{base_branch}")
            ).strip()
        except GitCommandError:
            # Branch doesn't exist locally; nothing to check, proceed safely.
            local_sha = None

        if local_sha is not None and local_sha != fetch_sha:
            proc = await asyncio.create_subprocess_exec(
                "git", "merge-base", "--is-ancestor", local_sha, fetch_sha,
                cwd=str(self._project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode != 0:
                raison = (
                    f"La branche locale « {base_branch} » ({local_sha[:7]}) a divergé "
                    f"de la base distante ({fetch_sha[:7]}) : mise à jour ignorée."
                )
                _logger.warning("sync_base_diverge", extra={"raison": raison})
                return raison

        # La base est la branche active depuis ticket-390 (retour sur la base
        # après livraison) : `update-ref` y avancerait la référence sans
        # l'index ni les fichiers, et l'arbre paraîtrait sale à l'envers.
        if await self.branche_courante() == base_branch:
            raison_ff = await self._avancer_base_active(fetch_sha)
            if raison_ff is not None:
                _logger.warning("sync_base_ff_echoue", extra={"erreur": raison_ff})
                return raison_ff
        else:
            # Safe: update the local branch ref and reposition _base_ref.
            try:
                await self._run("update-ref", f"refs/heads/{base_branch}", fetch_sha)
            except GitCommandError as exc:
                raison = f"update-ref refs/heads/{base_branch} échoué : {exc.stderr.strip()}"
                _logger.warning("sync_base_update_ref_echoue", extra={"erreur": raison})
                return raison

        self._base_ref = fetch_sha
        _logger.info("sync_base_depuis_distant_ok", extra={"sha": fetch_sha[:7]})
        return None
