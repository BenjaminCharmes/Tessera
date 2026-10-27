"""Branch position, push and commit history reads."""

from tessera.services.git_workspace.chemins import (
    _JOURNAL_PIPELINE,
    _is_orchestrator_artifact_path,
    _relatif_au_projet,
)
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.socle import GitCore
from tessera.services.termes_interdits import CommitInfo
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitHistory(GitCore):
    """Branch position, push and commit history reads."""

    async def retourner_sur_base(self, base_branch: str) -> None:
        """Check out the base branch after a delivered run (ticket-378).

        Leaves the working tree on the base branch so the next ticket
        starts from a clean, known state (ADR-018). Safe to call when
        already on the base branch — git treats it as a no-op. In a run worktree
        (ADR-056) it does nothing: the base may be checked out elsewhere, and
        the worktree is removed at the end of the run.
        """
        if self._worktree is not None:
            return
        await self._run("checkout", base_branch)

    async def branche_courante(self) -> str:
        """Name of the checked-out branch (``HEAD`` when detached)."""
        return (await self._run("rev-parse", "--abbrev-ref", "HEAD")).strip()

    async def _untracked_files(self) -> tuple[str, ...]:
        """Paths git reports as untracked (respecting .gitignore), as a tuple."""
        listing = await self._run("ls-files", "--others", "--exclude-standard")
        return tuple(path for path in listing.splitlines() if path)

    async def fichiers_non_suivis_laisses(self) -> tuple[str, ...]:
        """Untracked, non-ignored files that appeared since the run started.

        Read-only (ticket-480): nothing is deleted, the caller only reports
        them. Files already untracked at run start are not the run's doing.
        """
        presents = await self._untracked_files()
        return tuple(
            chemin
            for chemin in presents
            if chemin not in self._preexisting_untracked
            and chemin != _JOURNAL_PIPELINE
        )

    async def push_branch(self, branch_name: str) -> None:
        """Pousse `branch_name` sur `origin`, en suivi de branche.

        C'était le maillon manquant : `create-pr` demandait à GitHub une
        branche `head` que rien n'avait jamais poussée, et GitHub refusait une
        référence qu'il ne connaissait pas.

        **Jamais de push forcé.** Cette branche part dans le dépôt de
        l'utilisateur, parfois celui d'un client : écraser une référence
        distante peut détruire du travail qui n'est pas le nôtre. Si le push
        est refusé, c'est à l'utilisateur de trancher.
        """
        await self._run("push", "--set-upstream", "origin", branch_name)

    async def head_sha(self) -> str:
        """Full SHA of the branch head (ticket-492). A failure raises."""
        return (await self._run("rev-parse", "HEAD")).strip()

    async def sha_distant(self, branch: str) -> str | None:
        """Full SHA of `origin/<branch>` as last pushed, or None when unknown.

        The local remote-tracking ref is read first. A clone that follows a
        single branch has no such ref for a pushed ticket branch: the remote
        is then asked directly (ticket-517). Any failure gives None, so the
        CI watcher stays closed (ADR-039).
        """
        try:
            sortie = await self._run(
                "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}"
            )
        except GitCommandError:
            return await self._sha_lu_sur_le_distant(branch)
        return sortie.strip() or await self._sha_lu_sur_le_distant(branch)

    async def _sha_lu_sur_le_distant(self, branch: str) -> str | None:
        """Head of `refs/heads/<branch>` on `origin` via `ls-remote`, or None."""
        ref = f"refs/heads/{branch}"
        try:
            sortie = await self._run("ls-remote", "origin", ref)
        except GitCommandError as exc:
            _logger.warning(
                "sha_distant_ls_remote_echoue",
                extra={"branche": branch, "erreur": exc.stderr.strip()},
            )
            return None
        for ligne in sortie.splitlines():
            sha, _, nom = ligne.partition("\t")
            if nom.strip() == ref and sha:
                # Branche poussée mais sans référence locale : le refspec du
                # remote ne couvre pas `refs/heads/*`.
                _logger.warning(
                    "refspec_reduit",
                    extra={"projet": self._project_path.name, "branche": branch},
                )
                return sha.strip()
        return None

    async def commits_hors_rangement(self, depuis: str) -> list[str]:
        """SHAs added after `depuis` that are not the pipeline's own bookkeeping.

        A commit is bookkeeping when it has one parent and its diff touches only
        `tickets/` and `memory/pipeline-log.md` of the project (ticket-492).
        A head that no longer descends from `depuis` — reset, rewritten history
        — is reported as the head itself: nothing can be said of what lies
        between. A failure raises, so the caller fails closed.
        """
        if not await self._descend_de(depuis):
            return [await self.head_sha()]
        prefixe = (await self._run("rev-parse", "--show-prefix")).strip()
        journal = await self._run("log", "--reverse", "--format=%H %P", f"{depuis}..HEAD")
        hors_rangement: list[str] = []
        for ligne in journal.splitlines():
            sha, *parents = ligne.split()
            if len(parents) != 1 or not await self._est_rangement(sha, prefixe):
                hors_rangement.append(sha)
        return hors_rangement

    async def _descend_de(self, ancetre: str) -> bool:
        """True when `ancetre` is an ancestor of HEAD (or HEAD itself)."""
        try:
            await self._run("merge-base", "--is-ancestor", ancetre, "HEAD")
        except GitCommandError as exc:
            if exc.returncode == 1:
                return False
            raise
        return True

    async def est_ancetre(self, ancetre: str, descendant: str) -> bool | None:
        """True when `ancetre` is an ancestor of `descendant` (ticket-527).

        `None` when it cannot be told — a commit unknown to this clone, or any
        other git failure — so the caller can wait instead of concluding.
        """
        try:
            await self._run("merge-base", "--is-ancestor", ancetre, descendant)
        except GitCommandError as exc:
            return False if exc.returncode == 1 else None
        return True

    async def chemins_modifies(self, gauche: str, droite: str) -> list[str] | None:
        """Paths changed on `droite` since its merge base with `gauche` (ticket-584).

        `git diff --name-only gauche...droite`, chemins relatifs à la racine du
        dépôt. `None` quand git ne sait pas dire : l'appelant échoue fermé.
        """
        try:
            sortie = await self._run("diff", "--name-only", f"{gauche}...{droite}")
        except GitCommandError:
            return None
        return [chemin for chemin in sortie.splitlines() if chemin.strip()]

    async def _est_rangement(self, sha: str, prefixe: str) -> bool:
        """True when the commit touches only Tessera's bookkeeping paths."""
        sortie = await self._run(
            "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha
        )
        for chemin in sortie.splitlines():
            relatif = _relatif_au_projet(chemin, prefixe)
            if relatif is None or not _is_orchestrator_artifact_path(relatif):
                return False
        return True

    async def commits_depuis_base(self, base: str, branch: str) -> list[CommitInfo]:
        """Short SHA, message and author of each commit between base and branch.

        Uses ``base..branch`` range so only commits reachable from ``branch``
        but not from ``base`` are returned — exactly the commits the pipeline
        added. Returns an empty list when the range is empty or when git fails
        (missing refs, unborn repository).
        """
        try:
            # Message complet (%B) et committer compris : un corps de commit
            # ou un committer mal configuré publient autant qu'un sujet.
            output = await self._run(
                "log", f"{base}..{branch}",
                "--pretty=format:%h%x1f%aN <%aE> | %cN <%cE>%x1f%B%x1e",
            )
        except GitCommandError:
            return []
        commits: list[CommitInfo] = []
        for bloc in output.split("\x1e"):
            bloc = bloc.strip()
            if not bloc:
                continue
            parts = bloc.split("\x1f", 2)
            if len(parts) != 3:  # noqa: PLR2004
                continue
            sha7, auteur, message = parts
            commits.append(CommitInfo(sha7=sha7, message=message.strip(), auteur=auteur))
        return commits

    async def diff_de_branche(self, base: str, branch: str) -> str:
        """What `branch` commits on top of `base` — what a push publishes.

        ``base...branch`` diffs from their merge-base, so work already on the
        base is not counted twice. A failure raises: the push check must not
        pass on a diff it could not read.
        """
        return await self._run("diff", f"{base}...{branch}")
