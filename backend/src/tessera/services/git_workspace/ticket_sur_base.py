"""Reading and restoring a ticket file from the base branch."""

from pathlib import Path

from tessera.config import settings
from tessera.services.git_workspace.base import GitBase
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.textes import _chemin_du_ticket
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitTicketOnBase(GitBase):
    """Reading and restoring a ticket file from the base branch."""

    async def restaurer_ticket_depuis_base(self, ticket_id: str) -> bool:
        """Restore a ticket file from ``_base_ref`` when it is absent from the tree.

        Searches every file under ``tickets/`` on the base ref and writes the
        first one whose name contains ``ticket_id`` to disk.  Returns True when
        a file was restored, False when nothing was found or no base can be
        resolved (method is safe to call unconditionally).

        A fresh workspace — one per request (ADR-008) — has no ``_base_ref``
        yet: it aligns it with the remote base first, so that a ticket added
        on the base while the repo sat on a delivered branch is found
        (ticket-336).
        """
        if self._base_ref is None:
            await self.initialiser_base_ref()
        if self._base_ref is None:
            return False

        try:
            prefix = (await self._run("rev-parse", "--show-prefix")).strip()
        except GitCommandError:
            return False

        # Chemin du dossier tickets/ depuis la racine du dépôt.
        tickets_root = f"{prefix}tickets/" if prefix else "tickets/"
        try:
            listing = await self._run(
                "ls-tree", "-r", "--name-only", self._base_ref, "--", tickets_root
            )
        except GitCommandError:
            return False

        for path_in_repo in listing.splitlines():
            path_in_repo = path_in_repo.strip()
            if not path_in_repo:
                continue
            if ticket_id not in Path(path_in_repo).name:
                continue

            # Lit le contenu depuis l'historique.
            try:
                content = await self._run("show", f"{self._base_ref}:{path_in_repo}")
            except GitCommandError:
                continue

            # Chemin relatif au projet (strip du prefix si on est dans un sous-dossier).
            if prefix and path_in_repo.startswith(prefix):
                rel_path = path_in_repo[len(prefix):]
            else:
                rel_path = path_in_repo

            dest = self._project_path / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            _logger.info(
                "ticket_restaure_depuis_base",
                extra={
                    "ticket_id": ticket_id,
                    "chemin": rel_path,
                    "base": self._base_ref[:7],
                },
            )
            return True

        return False

    async def lire_ticket_sur_la_base(self, ticket_id: str) -> tuple[str, str] | None:
        """Read a ticket file from ``origin/<base>`` without touching the tree.

        Returns ``(path from the repository root, content)``, or None when the
        fetch fails or the base holds no such ticket (ticket-504). The base is
        the declared ``base_branch``, else ``settings.github_base_branch`` — the
        same fallback as the delivery (ticket-508). Read-only on purpose: no
        checkout, no ``update-ref``, no file written. ``--no-write-fetch-head``
        keeps a concurrent fetch from overwriting the ``FETCH_HEAD`` that
        ``initialiser_base_ref`` reads right after its own.
        """
        declaree = self._politique.base_branch if self._politique is not None else None
        base = declaree or settings.github_base_branch
        try:
            await self._run("fetch", "--no-write-fetch-head", "origin", base)
            prefix = (await self._run("rev-parse", "--show-prefix")).strip()
            ref = f"refs/remotes/origin/{base}"
            listing = await self._run(
                "ls-tree", "--full-tree", "-r", "--name-only", ref, "--", f"{prefix}tickets/"
            )
            chemin = _chemin_du_ticket(listing, ticket_id)
            if chemin is None:
                return None
            return chemin, await self._run("show", f"{ref}:{chemin}")
        except GitCommandError as exc:
            _logger.info(
                "ticket_sur_la_base_illisible",
                extra={"ticket_id": ticket_id, "erreur": exc.stderr.strip()},
            )
            return None
