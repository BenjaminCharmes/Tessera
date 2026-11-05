"""Base class for the `GitWorkspaceService` test doubles.

Every asynchronous method the orchestrator, the pipeline stages and the delivery
call on the workspace answers a neutral value here. A test double inherits from
`GitWorkspaceDouble` and redefines only what its test observes: adding a method
to the service then breaks no double that does not use it (ticket-742).
"""

from collections.abc import Awaitable, Callable

from tessera.services.gardes.termes_interdits import CommitInfo


class GitWorkspaceDouble:
    """Neutral answers: clean tree, nothing to commit, nothing unknown to report.

    `branche_courante`, `head_sha` and `fichiers_non_suivis_laisses` are left out
    on purpose: the pipeline reads them through `getattr(..., None)` and treats
    their absence as "not available". Defining them here would change what
    every double inheriting from this class makes the pipeline do.
    """

    async def advance_base_ref(self) -> None:
        return None

    async def adopter_worktree(self, branche: str, base_branch: str) -> str:
        return branche

    async def commit_all(self, message: str) -> str | None:
        return None

    async def commit_bookkeeping(self) -> None:
        return None

    async def commit_chemins(self, message: str, chemins: list[str]) -> bool:
        return False

    async def commits_depuis_base(self, base: str, branch: str) -> list[CommitInfo]:
        return []

    async def commits_hors_rangement(self, depuis: str) -> list[str]:
        return []

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        return f"{ticket_id}-{slug}"

    async def chemins_modifies(self, gauche: str, droite: str) -> list[str] | None:
        return None

    async def current_diff(self) -> str:
        return ""

    async def diff_de_branche(self, base: str, branch: str) -> str:
        return ""

    async def diff_depuis_base(self) -> str:
        return ""

    async def dirty_files(self) -> list[str]:
        return []

    async def est_ancetre(self, ancetre: str, descendant: str) -> bool | None:
        return None

    async def initialiser_base_ref(
        self, base_branch: str | None = None, *, exiger_distant: bool = False
    ) -> str | None:
        return None

    async def is_clean(self) -> bool:
        return True

    async def lire_ticket_sur_la_base(
        self, ticket_id: str, *, fetch: bool = True
    ) -> tuple[str, str] | None:
        return None

    async def push_branch(self, branch_name: str) -> None:
        return None

    async def rejouer_sur(
        self,
        base: str,
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]] | None = None,
    ) -> tuple[str, ...]:
        return ()

    async def restaurer_ticket_depuis_base(self, ticket_id: str) -> bool:
        return False

    async def retourner_sur_base(self, base_branch: str) -> None:
        return None

    async def sha_distant(self, branch: str) -> str | None:
        return None

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        return None
