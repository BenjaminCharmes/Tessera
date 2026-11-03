"""The base ref: initialisation, fetch and merge-base."""

import asyncio

from tessera.services.git_workspace.avance_base import GitAvanceBase
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


# Un `git fetch` qui échoue une fois — réseau, ou un autre fetch du même dépôt
# au même instant — réussit souvent à la tentative suivante (ticket-340).
_TENTATIVES_FETCH = 3


_ATTENTE_ENTRE_FETCH_S = 2.0


class GitBase(GitAvanceBase):
    """The base ref: initialisation, fetch and merge-base."""

    async def _base_distante(self, base_branch: str) -> str:
        """SHA of `origin/<base>`, else of HEAD when the remote ref is unknown."""
        try:
            return (await self._run("rev-parse", f"origin/{base_branch}")).strip()
        except GitCommandError:
            return (await self._run("rev-parse", "HEAD")).strip()

    async def advance_base_ref(self) -> None:
        """Move the base ref to the current HEAD, so the next ticket builds on it.

        Called by the orchestrator only after a run was *approved* and
        committed. Isolation-by-branch keeps a rejected ticket's work from
        leaking into the next one; it must not also keep an approved
        ticket's work from being visible to the tickets that follow, or a
        plan of sequential tickets would run every step against a stale
        base.
        """
        self._base_ref = (await self._run("rev-parse", "HEAD")).strip()

    async def _fetch_base(self, base_branch: str) -> None:
        """Fetch ``base_branch``, retrying a transient failure (ticket-340)."""
        for tentative in range(1, _TENTATIVES_FETCH + 1):
            try:
                await self._run("fetch", "origin", base_branch)
                return
            except GitCommandError:
                if tentative == _TENTATIVES_FETCH:
                    raise
                await asyncio.sleep(_ATTENTE_ENTRE_FETCH_S)

    async def _avancer_base_locale(self, base_branch: str, fetch_sha: str) -> str | None:
        """Move the local base branch to ``fetch_sha``; a reason when it must block.

        Sur la base active, `update-ref` avancerait la référence sans l'index ni
        les fichiers : ce que le nouveau commit ajoute paraîtrait supprimé, et
        le commit du run l'emporterait (ticket-572). La branche active avance
        donc par avance rapide, fichiers compris ; une autre branche active
        laisse la base à `update-ref`.
        """
        if await self.branche_courante() == base_branch:
            raison = await self._avancer_base_active(fetch_sha)
            if raison is not None:
                _logger.warning("base_ref_ff_echoue", extra={"erreur": raison})
            return raison
        try:
            await self._run("update-ref", f"refs/heads/{base_branch}", fetch_sha)
        except GitCommandError as exc:
            _logger.warning("base_ref_update_echoue", extra={"error": str(exc)})
        return None

    async def initialiser_base_ref(
        self, base_branch: str | None = None, *, exiger_distant: bool = False
    ) -> str | None:
        """Align ``_base_ref`` with the remote base branch before the first ticket.

        Called once by the pipeline before any ``create_branch`` : sets
        ``_base_ref`` so new ticket branches fork from the remote-synced base,
        not from whatever HEAD happens to be checked out (ticket-285).

        Returns ``None`` on success — ``_base_ref`` is now set, or the fallback
        (local branch / HEAD) will be used by ``create_branch``.  Returns a
        human-readable reason when the local branch has **diverged** from the
        remote: the caller must block the run in that case.

        Fall-back chain:
        1. ``origin/<base_branch>`` fast-forward → use remote SHA.
        2. No remote or unreachable → local ``base_branch`` ref.
        3. No local branch either → HEAD, via ``create_branch``'s own fallback.

        ``exiger_distant`` — the ticket depends on another one (ticket-340):
        a remote that cannot be read is then a reason to block, not to fall
        back. The local base may predate the dependency's merge, and the
        ticket would be coded against it, approved, then stopped by a
        conflict at delivery.
        """
        if base_branch is None and self._politique is not None:
            base_branch = self._politique.base_branch
        if not base_branch:
            return None

        # Attempt remote fetch
        try:
            await self._fetch_base(base_branch)
        except GitCommandError as exc:
            erreur = exc.stderr.strip() or str(exc)
            if exiger_distant:
                raison = (
                    f"La base distante « {base_branch} » est illisible ({erreur}) : "
                    "ce ticket dépend d'un autre, et la base locale peut précéder "
                    "son merge. Le run est bloqué plutôt que parti d'une base périmée."
                )
                _logger.warning("base_distante_exigee_illisible", extra={"raison": raison})
                return raison
            # No remote or network error: use local base_branch if it exists.
            # La raison est journalisée : son absence a caché l'origine de la
            # base périmée du ticket-034 de démineur (ticket-340).
            _logger.warning(
                "base_ref_fetch_echoue", extra={"branch": base_branch, "erreur": erreur}
            )
            try:
                local_sha = (
                    await self._run("rev-parse", f"refs/heads/{base_branch}")
                ).strip()
                self._base_ref = local_sha
                _logger.info(
                    "base_ref_initialisee_locale",
                    extra={"branch": base_branch, "sha": local_sha[:7]},
                )
            except GitCommandError:
                _logger.info(
                    "base_ref_locale_introuvable", extra={"branch": base_branch}
                )
            return None

        # Parse FETCH_HEAD
        try:
            fetch_sha = (await self._run("rev-parse", "FETCH_HEAD")).strip()
        except GitCommandError as exc:
            _logger.warning(
                "base_ref_fetch_head_introuvable", extra={"error": str(exc)}
            )
            return None

        # Check for divergence against local branch
        try:
            sha_locale = (
                await self._run("rev-parse", f"refs/heads/{base_branch}")
            ).strip()
        except GitCommandError:
            sha_locale = None

        if sha_locale is not None and sha_locale != fetch_sha:
            proc = await asyncio.create_subprocess_exec(
                "git", "merge-base", "--is-ancestor", sha_locale, fetch_sha,
                cwd=str(self._project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode != 0:
                raison = (
                    f"La branche locale « {base_branch} » ({sha_locale[:7]}) a divergé "
                    f"de la base distante ({fetch_sha[:7]}) : le run est bloqué."
                )
                _logger.warning("base_ref_divergee", extra={"raison": raison})
                return raison

        raison_ff = await self._avancer_base_locale(base_branch, fetch_sha)
        if raison_ff is not None:
            return raison_ff

        self._base_ref = fetch_sha
        _logger.info(
            "base_ref_initialisee_distante",
            extra={"branch": base_branch, "sha": fetch_sha[:7]},
        )
        return None

    # ------------------------------------------------------------------
    # Fork point of a ticket branch — ticket-208
    # ------------------------------------------------------------------

    async def _merge_base(self, branch_name: str) -> str | None:
        """Where `branch_name` left the base ref, or None if git cannot say."""
        if self._base_ref is None:
            return None
        try:
            return (await self._run("merge-base", branch_name, self._base_ref)).strip()
        except GitCommandError as exc:
            _logger.warning("fork_point_unknown", extra={"error": str(exc)})
            return None
