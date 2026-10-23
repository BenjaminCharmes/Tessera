"""Creating, adopting and resuming the ticket branch."""

from pathlib import Path

from tessera.services.git_attributes import declare_union_merge
from tessera.services.git_workspace.base import GitBase
from tessera.services.git_workspace.chemins import _JOURNAL_PIPELINE
from tessera.services.git_workspace.commits import GitCommits
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.noms import _branch_name
from tessera.services.git_workspace.rebase import GitRebase
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitBranch(GitBase, GitRebase, GitCommits):
    """Creating, adopting and resuming the ticket branch."""

    async def adopter_worktree(self, branche: str, base_branch: str) -> str:
        """Take over the run worktree, already on `branche` from `origin/<base>` (ADR-056).

        Records what `create_branch` records, without switching anything: the
        worktree was created on the branch, and the checkout is not touched.
        A resumed branch that lags behind the base is rebased at delivery.
        """
        await self._ensure_own_repository()
        await self._declarer_union_journal()
        self._base_ref = await self._base_distante(base_branch)
        self._preexisting_untracked = await self._untracked_files()
        self._tracked_ticket_basenames = await self._list_tracked_ticket_basenames()
        self._fork_point = await self._merge_base("HEAD") or self._base_ref
        self.commits_repris = await self._compter_commits_depuis_depart()
        return branche

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        """Create `ticket-<id>-<slug>` and switch to it; idempotent if it already exists.

        New branches always fork from the base ref recorded on first use of
        this service, not from whatever branch happens to be checked out —
        that is what keeps consecutive tickets in an autonomous run isolated
        from each other.
        """
        await self._ensure_own_repository()
        await self._declarer_union_journal()
        if self._base_ref is None:
            self._base_ref = (await self._run("rev-parse", "HEAD")).strip()
        self._preexisting_untracked = await self._untracked_files()
        self._tracked_ticket_basenames = await self._list_tracked_ticket_basenames()

        branch_name = _branch_name(ticket_id, slug)

        self.commits_repris = 0
        exists = await self._branch_exists(branch_name)
        if exists:
            await self._run("checkout", branch_name)
            # Le point de départ d'une branche reprise se déduit de la base :
            # aucune ref à tenir, et les branches créées avant ce correctif
            # sont couvertes aussi (ticket-208).
            self._fork_point = await self._merge_base(branch_name)
            # Si la branche diverge de la base actuelle (relance après que
            # develop a avancé), rejouer avant de donner la main au codeur
            # plutôt qu'envoyer une PR sur une base périmée (ticket-329).
            if (
                self._fork_point is not None
                and self._base_ref is not None
                and self._fork_point != self._base_ref
            ):
                await self._rejouer_branche_en_retard(branch_name)
            self.commits_repris = await self._compter_commits_depuis_depart()
        else:
            await self._run("checkout", "-b", branch_name, self._base_ref)
            self._fork_point = self._base_ref
        return branch_name

    async def _compter_commits_depuis_depart(self) -> int:
        """Commits de HEAD au-delà de ``_fork_point`` ; 0 si le point est inconnu.

        Après un renommage ``stale/``, ``_fork_point`` est la base et HEAD
        aussi : le compte tombe à 0 sans cas particulier.
        """
        if self._fork_point is None:
            return 0
        try:
            sortie = await self._run("rev-list", "--count", f"{self._fork_point}..HEAD")
            return int(sortie.strip())
        except (GitCommandError, ValueError):
            return 0

    async def _declarer_union_journal(self) -> None:
        """Déclare le journal du pipeline en fusion `union`, localement (ticket-418).

        Écrit dans `.git/info/attributes` du dépôt, jamais dans le dépôt
        versionné. Le motif est relatif à la racine du dépôt : sous
        `git_root: ancestor`, il porte le préfixe du projet. Un échec ne
        bloque pas le run — le rebase retombe sur la résolution en union.
        """
        try:
            prefixe = (await self._run("rev-parse", "--show-prefix")).strip()
            brut = (await self._run("rev-parse", "--git-path", "info/attributes")).strip()
            chemin = Path(brut)
            if not chemin.is_absolute():
                chemin = self._project_path / chemin
            declare_union_merge(chemin, f"{prefixe}{_JOURNAL_PIPELINE}")
        except (GitCommandError, OSError) as exc:
            _logger.warning("union_journal_non_declaree", extra={"erreur": str(exc)})

    async def _rejouer_branche_en_retard(self, branch_name: str) -> None:
        """Rebase ``branch_name`` (already checked out) on the current base ref.

        Called when a resumed branch's fork point is behind ``_base_ref``.
        On success the branch is up to date and ``_fork_point`` is updated.
        On conflict the rebase is aborted, the stale branch is preserved under
        ``stale/<name>`` and a fresh branch is created from ``_base_ref``.
        """
        assert self._base_ref is not None  # guaranteed by the caller
        _logger.info(
            "branche_en_retard_rejeu",
            extra={
                "branche": branch_name,
                "fork_point": (self._fork_point or "")[:7],
                "base": self._base_ref[:7],
            },
        )
        conflits = await self.rejouer_sur(self._base_ref)
        if not conflits:
            # Rebase réussi : le point de départ est maintenant la base actuelle.
            self._fork_point = self._base_ref
            _logger.info("branche_en_retard_rejouee", extra={"branche": branch_name})
            return

        # Conflit irrécupérable : conserver l'ancienne branche sous stale/…
        # pour ne rien perdre et repartir proprement depuis la base.
        stale_name = await self._choisir_nom_stale(branch_name)
        await self._run("branch", "-m", branch_name, stale_name)
        _logger.warning(
            "branche_en_retard_renommee_stale",
            extra={
                "ancienne": branch_name,
                "stale": stale_name,
                "conflits": conflits,
            },
        )
        await self._run("checkout", "-b", branch_name, self._base_ref)
        self._fork_point = self._base_ref
        _logger.info(
            "branche_neuve_depuis_base",
            extra={"branche": branch_name, "base": self._base_ref[:7]},
        )

    async def _choisir_nom_stale(self, branch_name: str) -> str:
        """Return ``stale/<branch>`` or ``stale/<branch>-<n>`` if the former exists."""
        candidat = f"stale/{branch_name}"
        if not await self._branch_exists(candidat):
            return candidat
        n = 1
        while n < 100:  # noqa: PLR2004 — borne de sécurité, pas une constante métier
            candidat = f"stale/{branch_name}-{n}"
            if not await self._branch_exists(candidat):
                return candidat
            n += 1
        # Cas extrêmement improbable : on repasse 100 fois sur le même ticket.
        return f"stale/{branch_name}-{n}"
