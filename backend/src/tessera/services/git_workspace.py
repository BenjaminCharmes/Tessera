"""GitWorkspaceService — ticket-045.

Isolates the git operations the orchestrator needs to drive an agent
pipeline on a dedicated branch: create/resume a branch, read the current
diff (including untracked files) and commit the work.
"""
import asyncio
import json
import re
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.services.termes_interdits import CommitInfo
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.politique_run import PolitiqueRun

_MAX_BRANCH_LENGTH = 60

# Git's well-known hash for the empty tree object — exists in every
# repository regardless of history, so diffing against it works even
# before the first commit, when `HEAD` itself is an ambiguous revision.
_EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# Paths Tessera itself rewrites during a pipeline run — never files the
# coder agent produced. `TicketService.update_status` rewrites the ticket's
# Markdown file twice per run (in-progress, then in-review), and `_log`
# appends to the pipeline log at every step. If these show up in the diff
# fed to the reviewer/security-auditor/validator/documentation agents, they
# mistake the orchestrator's own bookkeeping for the coder's work, and an
# approved run would commit it under the ticket's message. Excluded from
# both the reviewed diff and the ticket's own commit via git's magic
# pathspec `:(exclude)`.
_ORCHESTRATOR_ARTIFACT_PATHS: tuple[str, ...] = ("tickets/", "memory/pipeline-log.md")

#: Journal du pipeline, relatif au dossier du projet.
_JOURNAL_PIPELINE = "memory/pipeline-log.md"

# The same paths, without the `:(exclude)` magic, used to stage and commit
# them separately from the ticket's own code changes (see `commit_all`).
_ORCHESTRATOR_ARTIFACT_EXCLUDE_PATHSPECS: tuple[str, ...] = tuple(
    f":(exclude){p}" for p in _ORCHESTRATOR_ARTIFACT_PATHS
)

# Fichiers journal résolubles en union lors du rebase de livraison (ticket-391).
# Seuls ces deux fichiers ne font qu'ajouter des entrées : une union n'y laisse
# jamais de contenu ambigu, contrairement à un fichier de code modifié des
# deux côtés.
_JOURNAL_UNION_SUFFIXES: frozenset[str] = frozenset({
    "memory/pipeline-log.md",
    "memory/documentation.json",
})

# Fixed, non-ticket-branded message for the bookkeeping-only commit: ticket
# status changes and pipeline-log growth are Tessera's own housekeeping,
# never the coder's work, so they must never ride under a ticket's message.
_BOOKKEEPING_COMMIT_MESSAGE = "chore: tessera pipeline bookkeeping"

# Paths that hold the run policy the orchestrator reads once before the first
# agent. The user may edit them through the IDE while the run is in progress
# (e.g. changing the provider in the Agents screen). Those edits must never
# ride along with the coder's work — ticket-296, ADR-027.
# Files are excluded from both the reviewed diff and the ticket commit;
# they are left uncommitted in the working tree and the run logs a warning.
_RUN_POLICY_PATHS: tuple[str, ...] = (
    "agents.json",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".github/workflows/",
)


def _is_orchestrator_artifact_path(path: str) -> bool:
    """True when ``path`` belongs to Tessera's own pipeline bookkeeping.

    Directory entries (ending with ``/``) match any file under them;
    file entries match exactly, so ``memory/pipeline-log.md`` does not
    accidentally match ``memory/pipeline-log.md.bak``.
    """
    for artifact in _ORCHESTRATOR_ARTIFACT_PATHS:
        if artifact.endswith("/"):
            if path.startswith(artifact):
                return True
        elif path == artifact:
            return True
    return False


def _is_journal_union_file(path: str) -> bool:
    """True when ``path`` is a journal file eligible for automatic union resolution.

    Matches both ``memory/pipeline-log.md`` (project root) and
    ``projects/ide-core/memory/pipeline-log.md`` (git_root: ancestor).
    """
    return any(
        path == suffix or path.endswith(f"/{suffix}")
        for suffix in _JOURNAL_UNION_SUFFIXES
    )


def _union_lines(base: str, theirs: str) -> str:
    """Union of two append-only text files, base lines first, no duplicates."""
    base_lines = base.splitlines(keepends=True)
    theirs_lines = theirs.splitlines(keepends=True)
    base_set = set(base_lines)
    extra = [line for line in theirs_lines if line not in base_set]
    return "".join(base_lines + extra)


def _union_json_lists(base_text: str, theirs_text: str) -> str | None:
    """Union of two JSON array versions, base items first, no duplicates.

    Returns None when either side is not a valid JSON array.
    """
    try:
        base_list = json.loads(base_text)
        theirs_list = json.loads(theirs_text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(base_list, list) or not isinstance(theirs_list, list):
        return None
    seen: set[str] = set()
    result: list[object] = []
    for item in (*base_list, *theirs_list):
        key = json.dumps(item, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return json.dumps(result, ensure_ascii=False, indent=2)


def _extraire_fichiers_bloques(stderr: str) -> list[str]:
    """Extract untracked file paths that blocked a ``git rebase --abort``.

    Git emits, in this order:
        error: The following untracked working tree files would be overwritten by reset:
            path/to/file.md
        fatal: could not move back to <sha>

    Returns the list of file paths found between the header line and the
    ``fatal:`` line. Paths are returned as git reports them (relative to the
    repository root, with forward slashes on all platforms).
    """
    fichiers: list[str] = []
    en_section = False
    for ligne in stderr.splitlines():
        if "untracked working tree files" in ligne and "overwritten" in ligne:
            en_section = True
            continue
        if en_section:
            stripped = ligne.strip()
            if stripped and not any(
                stripped.startswith(p)
                for p in ("fatal:", "error:", "hint:", "Please")
            ):
                fichiers.append(stripped)
            else:
                en_section = False
    return fichiers


def _is_run_policy_path(path: str) -> bool:
    """True when ``path`` holds part of the run policy (ticket-296, ADR-027).

    These files are read once before the pipeline starts and must never
    appear in a ticket's commit, even when the user edits them during a run.
    Directory entries (ending with ``/``) match any file underneath them.
    """
    for policy in _RUN_POLICY_PATHS:
        if policy.endswith("/"):
            if path.startswith(policy):
                return True
        elif path == policy:
            return True
    return False

#: Lockfile names whose diff content is replaced by a one-line summary when
#: fed to reviewing agents.  The commit itself is not affected — lockfiles are
#: committed in full.  A single entry here covers every subdirectory
#: (``backend/uv.lock`` matches ``uv.lock``).
LOCKFILE_NAMES: frozenset[str] = frozenset({
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
})

# Captures the destination path from ``diff --git a/<src> b/<dst>``.
_DIFF_GIT_RE = re.compile(r"^diff --git a/.+ b/(.+)$")


class GitWorkspaceError(Exception):
    """Base class for all errors raised by GitWorkspaceService."""


# Un `git fetch` qui échoue une fois — réseau, ou un autre fetch du même dépôt
# au même instant — réussit souvent à la tentative suivante (ticket-340).
_TENTATIVES_FETCH = 3
_ATTENTE_ENTRE_FETCH_S = 2.0


class GitCommandError(GitWorkspaceError):
    """A git command failed; carries the context for logging."""

    def __init__(self, command: list[str], returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"git command failed (code {returncode}): {' '.join(command)}\n{stderr}"
        )


class BaseIntrouvable(GitWorkspaceError):
    """La branche de base du rejeu n'existe pas dans ce dépôt — ticket-166.

    `git rebase` répond `fatal: invalid upstream 'develop'`, qui ne dit ni que
    la branche vient d'un réglage, ni lequel, ni où le corriger.
    """

    def __init__(self, base: str) -> None:
        super().__init__(
            f"La branche de base « {base} » n'existe pas dans ce dépôt. "
            f"Déclare `base_branch` dans son agents.json, ou crée la branche."
        )
        self.base = base


class NotAGitRepository(GitCommandError):
    """The target directory is not (or no longer) a git repository."""


class InvalidSlugError(GitWorkspaceError):
    """Raised when a slug sanitizes to an empty string and cannot form a branch name."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(
            f"slug sanitizes to an empty string, cannot build a branch name: {slug!r}"
        )


def _sanitize_slug(slug: str) -> str:
    """Reduce an arbitrary slug to lowercase alphanumerics and hyphens.

    Accents and punctuation become hyphens, consecutive hyphens are merged
    and leading/trailing hyphens are stripped.
    """
    lowered = slug.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    return normalized.strip("-")


def _is_lockfile(path: str) -> bool:
    """True if the path's filename matches a known lockfile."""
    return Path(path).name in LOCKFILE_NAMES


def _resumer_lockfiles(diff: str) -> str:
    """Replace lockfile sections in a unified diff with a one-line summary.

    For each known lockfile, the full hunk content is replaced by:
      ``<path>: lockfile modified, N lines added, M deleted``

    Non-lockfile sections are left untouched.  This only filters what
    reviewing agents see — the commit itself is not affected.
    """
    if not diff:
        return diff

    lines = diff.splitlines(keepends=True)
    output: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.startswith("diff --git "):
            output.append(line)
            i += 1
            continue

        # Determine file path from the ``diff --git`` header.
        m = _DIFF_GIT_RE.match(line.rstrip("\n"))
        file_path = m.group(1) if m else ""

        # Scan the metadata header lines (index, ---, +++) for a better path.
        j = i + 1
        while j < len(lines) and not lines[j].startswith(("diff --git ", "@@")):
            if lines[j].startswith("+++ b/"):
                file_path = lines[j][6:].rstrip("\n")
            j += 1
        # ``j`` now points to the first hunk line (``@@``) or next file section.

        if not _is_lockfile(file_path):
            # Keep diff --git line, metadata header, and all hunk lines.
            output.append(lines[i])
            i += 1
            while i < len(lines) and not lines[i].startswith("diff --git "):
                output.append(lines[i])
                i += 1
            continue

        # Lockfile: skip header, count added/removed hunk lines, emit summary.
        i = j
        added = removed = 0
        while i < len(lines) and not lines[i].startswith("diff --git "):
            hunk_line = lines[i]
            if hunk_line.startswith("+") and not hunk_line.startswith("+++"):
                added += 1
            elif hunk_line.startswith("-") and not hunk_line.startswith("---"):
                removed += 1
            i += 1

        output.append(
            f"{file_path}: lockfile modified, {added} lines added, {removed} deleted\n"
        )

    return "".join(output)


def _branch_name(ticket_id: str, slug: str) -> str:
    # ticket_id is interpolated into a git ref just like slug, so it must
    # go through the same sanitizer: an unsanitized ticket_id containing a
    # character invalid in a ref (e.g. "/", "~", a space) makes `checkout -b`
    # fail, which — left unguarded upstream — used to still let the run
    # commit onto whatever branch happened to be checked out.
    sanitized_slug = _sanitize_slug(slug)
    if not sanitized_slug:
        raise InvalidSlugError(slug)
    sanitized_ticket_id = _sanitize_slug(ticket_id)
    if not sanitized_ticket_id:
        raise InvalidSlugError(ticket_id)
    name = f"{sanitized_ticket_id}-{sanitized_slug}"
    if len(name) > _MAX_BRANCH_LENGTH:
        name = name[:_MAX_BRANCH_LENGTH].rstrip("-")
    return name


_logger = get_logger(__name__)

#: Le marqueur que git laisse dans un fichier non résolu.
_MARQUEUR_CONFLIT = "<" * 7


def _dossier_sans_hooks() -> Path:
    """Un dossier vide, hors de tout projet, à donner comme `core.hooksPath`.

    Un chemin inexistant ferait aussi l'affaire pour git, mais un dossier qui
    existe et qu'on contrôle ne laisse aucune place à l'interprétation. Créé à
    la demande : `tempfile.gettempdir()` n'est pas connu au chargement du
    module sur toutes les plateformes.
    """
    dossier = Path(tempfile.gettempdir()) / "tessera-sans-hooks"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


class GitWorkspaceService:
    """Drives git on a single workspace project, never on Tessera itself."""

    def __init__(
        self, project_path: Path, politique: "PolitiqueRun | None" = None
    ) -> None:
        self._project_path = project_path
        # `git_root` décide d'où l'on stage (`.` ou `:/`). Figé par
        # l'orchestrateur avant le premier agent : lu au moment de committer,
        # il obéirait à ce qu'un codeur aurait écrit dans `agents.json` pendant
        # le run (ticket-119). Sans politique — chat, endpoints — on lit le
        # fichier, comme avant.
        self._politique = politique
        # The ref checked out the first time this service touches the repo.
        # Every subsequent ticket branch forks from this ref, never from the
        # previously created ticket branch — otherwise ticket N would carry
        # ticket N-1's commits (isolation-by-branch relies on this).
        self._base_ref: str | None = None
        # Untracked files already sitting in the tree when the run started.
        # They were not produced by the coder, so `commit_all`'s blanket
        # `git add -A` must not sweep them into the ticket's commit (that is
        # the counterpart of `is_clean` ignoring untracked files: both ends
        # agree on what "not ours" means).
        self._preexisting_untracked: tuple[str, ...] = ()
        # Basenames of tracked ticket files at run start (ticket-343).
        # Set by `create_branch`; `None` means it was not called yet.
        # `commit_bookkeeping` uses this to decide whether an untracked file
        # under `tickets/` is a status-folder move (basename was tracked → stage)
        # or a freshly created ticket (→ leave untracked).
        # When None, falls back to the original behaviour: stage every
        # untracked ticket file that is not pre-existing (ticket-314 scenario
        # where bookkeeping is committed before the branch switch).
        self._tracked_ticket_basenames: frozenset[str] | None = None
        # The commit from which the current ticket branch diverged from its
        # base. On a fresh branch this equals `_base_ref`; on a resumed branch
        # it is the merge-base of the branch and `_base_ref` (ticket-208). Used by `diff_depuis_base` to include all prior
        # commits on the branch, not only the uncommitted work of the current
        # turn.
        self._fork_point: str | None = None

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        """Create `ticket-<id>-<slug>` and switch to it; idempotent if it already exists.

        New branches always fork from the base ref recorded on first use of
        this service, not from whatever branch happens to be checked out —
        that is what keeps consecutive tickets in an autonomous run isolated
        from each other.
        """
        await self._ensure_own_repository()
        if self._base_ref is None:
            self._base_ref = (await self._run("rev-parse", "HEAD")).strip()
        self._preexisting_untracked = await self._untracked_files()
        self._tracked_ticket_basenames = await self._list_tracked_ticket_basenames()

        branch_name = _branch_name(ticket_id, slug)

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
        else:
            await self._run("checkout", "-b", branch_name, self._base_ref)
            self._fork_point = self._base_ref
        return branch_name

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

        # Fast-forward local branch ref
        try:
            await self._run("update-ref", f"refs/heads/{base_branch}", fetch_sha)
        except GitCommandError as exc:
            _logger.warning("base_ref_update_echoue", extra={"error": str(exc)})

        self._base_ref = fetch_sha
        _logger.info(
            "base_ref_initialisee_distante",
            extra={"branch": base_branch, "sha": fetch_sha[:7]},
        )
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
        """
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

    async def _avancer_base_active(self, cible: str) -> str | None:
        """Fast-forward the checked-out base branch to ``cible``, files included.

        Uncommitted pipeline-log lines are set aside and appended back after
        the fast-forward: the merged ticket's commit carries its own log
        lines, so a plain merge would refuse to overwrite the file. Any other
        local change makes ``merge --ff-only`` refuse, and the sync is skipped
        rather than forced (ADR-022).
        """
        journal = _JOURNAL_PIPELINE
        lignes: list[str] = []
        if (self._project_path / journal).is_file():
            diff = await self._run("diff", "-U0", "HEAD", "--", journal)
            lignes = [
                ligne[1:]
                for ligne in diff.splitlines()
                if ligne.startswith("+") and not ligne.startswith("+++")
            ]
            if lignes:
                await self._run("checkout", "HEAD", "--", journal)
        try:
            await self._run("merge", "--ff-only", "-q", cible)
            raison = None
        except GitCommandError as exc:
            raison = f"avance rapide de la base refusée : {exc.stderr.strip()}"
        if lignes:
            with (self._project_path / journal).open("a", encoding="utf-8") as f:
                f.write("\n".join(lignes) + "\n")
        return raison

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

    async def _exclude_pathspecs(self) -> tuple[str, ...]:
        """Les `:(exclude)` à poser, sans ceux que le dépôt ignore déjà.

        Nommer un chemin **déjà ignoré** dans un pathspec fait sortir
        `git add` en code 1 (« The following paths are ignored… »), alors que
        la même commande sans ce pathspec réussit et saute le chemin en
        silence. Sur un projet en mode artefacts `local` (ADR-021), où
        `tickets/` et `memory/` sont dans `.git/info/exclude`, ces exclusions
        n'étaient donc pas seulement inutiles : elles faisaient échouer le
        commit de fin de run, et donc le run entier (ticket-072).

        Les fichiers de politique du run (`_RUN_POLICY_PATHS`) sont également
        exclus : un réglage effectué dans l'IDE pendant le run ne doit jamais
        se retrouver dans le commit du ticket (ticket-296, ADR-027).
        """
        # Boucle explicite : une compréhension contenant un `await` produit un
        # générateur asynchrone, pas un tuple.
        pathspecs: list[str] = []
        for chemin in (*_ORCHESTRATOR_ARTIFACT_PATHS, *_RUN_POLICY_PATHS):
            if not await self._is_ignored(chemin):
                pathspecs.append(f":(exclude){chemin}")
        return tuple(pathspecs)

    async def _is_ignored(self, path: str) -> bool:
        """True si le dépôt ignore ce chemin (`.gitignore` ou `.git/info/exclude`)."""
        proc = await asyncio.create_subprocess_exec(
            "git", "check-ignore", "-q", "--", path,
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def _purger_stage_ignoré(self) -> None:
        """Retire de l'index les fichiers désormais couverts par `.gitignore`.

        `git add -A` ne dé-stage pas les fichiers déjà dans l'index — même
        stagés comme intent-to-add — si une règle `.gitignore` les couvre
        après coup. Cette méthode ferme ce gap : les fichiers listés par
        `git ls-files --cached --ignored` ne doivent pas finir dans le commit.

        Les artefacts de tenue de livres (`_ORCHESTRATOR_ARTIFACT_PATHS`) sont
        gérés par `commit_bookkeeping` et sont donc exclus ici.
        """
        try:
            out = await self._run(
                "ls-files", "--cached", "--ignored", "--exclude-standard"
            )
        except GitCommandError as exc:
            _logger.warning("staged_ignored_list_failed", extra={"error": str(exc)})
            return
        to_remove = [
            p for p in out.splitlines()
            if p and not any(
                p.startswith(a.rstrip("/")) for a in _ORCHESTRATOR_ARTIFACT_PATHS
            )
        ]
        if not to_remove:
            return
        try:
            await self._run("rm", "--cached", "--", *to_remove)
        except GitCommandError as exc:
            _logger.warning(
                "staged_ignored_cleanup_failed",
                extra={"error": str(exc), "paths": to_remove},
            )

    async def retourner_sur_base(self, base_branch: str) -> None:
        """Check out the base branch after a delivered run (ticket-378).

        Leaves the working tree on the base branch so the next ticket
        starts from a clean, known state (ADR-018). Safe to call when
        already on the base branch — git treats it as a no-op.
        """
        await self._run("checkout", base_branch)

    async def branche_courante(self) -> str:
        """Name of the checked-out branch (``HEAD`` when detached)."""
        return (await self._run("rev-parse", "--abbrev-ref", "HEAD")).strip()

    async def _untracked_files(self) -> tuple[str, ...]:
        """Paths git reports as untracked (respecting .gitignore), as a tuple."""
        listing = await self._run("ls-files", "--others", "--exclude-standard")
        return tuple(path for path in listing.splitlines() if path)

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

    async def rejouer_sur(
        self,
        base: str,
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]] | None = None,
    ) -> tuple[str, ...]:
        """Rejoue la branche courante sur `base`. Rend les fichiers en conflit.

        Une branche partie d'une base qui a depuis avancé produit une PR que
        GitHub déclare non mergeable : attendre sa CI ne mènerait nulle part.

        Sans `resolveur`, un conflit **annule** le rebase et laisse la branche
        exactement comme elle était. Avec, le résolveur est appelé pendant le
        rebase et peut réécrire les fichiers ; s'il aboutit, le rebase se
        termine. Sinon — il lève, il laisse des marqueurs, il oublie un
        fichier — tout est annulé.

        **L'arbre ne reste jamais à mi-rebase.** Le ticket suivant démarrerait
        dessus, et l'utilisateur hériterait d'un dépôt qu'il n'a pas choisi.
        """
        await self._ensure_own_repository()
        if not await self._ref_existe(base):
            raise BaseIntrouvable(base)

        sha_avant = (await self._run("rev-parse", "HEAD")).strip()

        try:
            await self._run("rebase", base)
        except GitCommandError as echec:
            refus = echec
        else:
            return ()

        conflits = await self._fichiers_en_conflit()
        if not conflits:
            # Un rebase refusé **sans conflit** n'a rien laissé en cours : la
            # commande s'est arrêtée avant de commencer — arbre sale, base
            # inconnue. `--abort` levait alors à son tour, et son « no rebase
            # in progress » remontait à la place de la vraie cause : la
            # livraison du premier run approuvé s'est plainte de l'annulation,
            # jamais de l'arbre que le pipeline venait de salir (ticket-159).
            await self._annuler_si_en_cours()
            raise refus

        # Résolution en union pour les fichiers journal (ticket-391, ADR-035) :
        # pipeline-log.md et documentation.json ne font qu'ajouter des entrées,
        # donc une union ne laisse jamais de contenu ambigu.
        if all(_is_journal_union_file(c) for c in conflits):
            if await self._resoudre_conflits_journal_en_union(conflits):
                return ()

        # Si tous les conflits sont des artefacts Tessera, les résoudre
        # automatiquement en faveur de la branche (ticket-300, ADR-033).
        if all(_is_orchestrator_artifact_path(c) for c in conflits):
            if await self._resoudre_conflits_artefacts(conflits):
                return ()

        if resolveur is None or not await self._faire_resoudre(conflits, resolveur):
            await self._annuler_rebase_robuste(sha_avant)
            return conflits
        return ()

    async def _ref_existe(self, ref: str) -> bool:
        """La ref est-elle résolvable ici ?

        Vérifié **avant** de rejouer : sinon la cause remonte dans les mots de
        git, et la vraie information — un réglage à écrire — se perd.
        """
        try:
            await self._run("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        except GitCommandError:
            return False
        return True

    async def _annuler_si_en_cours(self) -> None:
        """Annule le rebase s'il y en a un, sans jamais masquer l'erreur d'origine."""
        if await self._rebase_en_cours():
            try:
                await self._run("rebase", "--abort")
            except GitCommandError as exc:
                _logger.warning("rebase_abort_failed", extra={"error": str(exc)})

    async def _annuler_rebase_robuste(self, sha_avant: str) -> None:
        """Abort the rebase even when untracked Tessera files block ``--abort``.

        Sequence:
        1. Try ``rebase --abort``.
        2. On failure: remove any Tessera artifact paths that are blocking the
           reset (parsed from stderr), then retry ``--abort``.
        3. Last resort: manually remove the rebase state directory and
           hard-reset HEAD to *sha_avant*.

        Blocking paths come from git relative to the **repository root**, not
        the project directory.  For a project with ``git_root: ancestor`` the
        two differ (e.g. the git root is ``tessera/``, the project is
        ``tessera/projects/ide-core/``), so the absolute path is resolved from
        the git root and then re-expressed relative to the project before
        calling ``_is_orchestrator_artifact_path``.
        """
        try:
            await self._run("rebase", "--abort")
            return
        except GitCommandError as echec:
            bloquants = _extraire_fichiers_bloques(echec.stderr)
            artefacts_supprimes: list[str] = []
            if bloquants:
                git_root = await self._chemin_racine_git()
                project_root = self._project_path.resolve()
                for chemin_git in bloquants:
                    abs_path = (git_root / chemin_git).resolve()
                    try:
                        rel = str(abs_path.relative_to(project_root)).replace("\\", "/")
                    except ValueError:
                        continue
                    if _is_orchestrator_artifact_path(rel) and abs_path.is_file():
                        abs_path.unlink()
                        artefacts_supprimes.append(chemin_git)
                        _logger.info(
                            "artefact_supprime_pour_rebase_abort",
                            extra={"chemin": chemin_git},
                        )
            if artefacts_supprimes:
                try:
                    await self._run("rebase", "--abort")
                    return
                except GitCommandError:
                    pass

        _logger.warning("rebase_abort_dernier_recours", extra={"sha": sha_avant[:7]})
        await self._restaurer_depuis_sha(sha_avant)

    async def _chemin_racine_git(self) -> Path:
        """Return the absolute path of the git repository root (``--show-toplevel``)."""
        try:
            top = (await self._run("rev-parse", "--show-toplevel")).strip()
            return Path(top).resolve()
        except GitCommandError:
            return self._project_path.resolve()

    async def _restaurer_depuis_sha(self, sha: str) -> None:
        """Remove rebase state and hard-reset the branch to *sha*.

        Called only when both ``rebase --abort`` attempts have failed. Reads
        the original branch name from ``.git/rebase-merge/head-name`` before
        deleting the state directory so we can check it back out.
        """
        try:
            git_dir_str = (await self._run("rev-parse", "--git-dir")).strip()
            git_dir = Path(git_dir_str)
            if not git_dir.is_absolute():
                git_dir = self._project_path / git_dir
            head_name_file = git_dir / "rebase-merge" / "head-name"
            head_name = (
                head_name_file.read_text(encoding="utf-8").strip()
                if head_name_file.exists()
                else None
            )
            for nom in ("rebase-merge", "rebase-apply"):
                d = git_dir / nom
                if d.exists():
                    shutil.rmtree(str(d))
                    _logger.info("rebase_etat_supprime", extra={"dossier": nom})
            if head_name and head_name.startswith("refs/heads/"):
                branch = head_name[len("refs/heads/"):]
                try:
                    await self._run("checkout", branch)
                except GitCommandError:
                    pass
        except (GitCommandError, OSError) as exc:
            _logger.warning("rebase_etat_suppression_echoue", extra={"erreur": str(exc)})
        try:
            await self._run("reset", "--hard", sha)
        except GitCommandError as exc:
            _logger.error("rebase_reset_hard_echoue", extra={"erreur": str(exc)})

    async def _resoudre_conflits_artefacts(self, conflits: tuple[str, ...]) -> bool:
        """Auto-resolve conflicts where all files are Tessera artifacts.

        Accepts the branch version (theirs) for each conflict:
        - UD (updated by base, deleted by branch): stage the deletion via
          ``git rm -f``.
        - Any other conflict: check out theirs and stage.

        Also stages any untracked Tessera artifact files (e.g. a ``done/``
        ticket the cherry-pick added alongside the conflict), so that
        ``rebase --continue`` can create a clean commit.

        Returns True when the rebase completed successfully, False on any error.
        """
        try:
            for chemin in conflits:
                status_out = await self._run("status", "--porcelain", "--", chemin)
                code = status_out[:2] if len(status_out) >= 2 else "UU"  # noqa: PLR2004
                if code == "UD":
                    # Branch deleted the file; stage the deletion.
                    await self._run("rm", "-f", "--", chemin)
                else:
                    await self._run("checkout", "--theirs", "--", chemin)
                    await self._run("add", "--", chemin)

            if await self._fichiers_en_conflit():
                return False

            # Stage any untracked Tessera artifacts the cherry-pick was adding
            # (e.g. a tickets/done/ file written alongside the conflict).
            listing = await self._run("ls-files", "--others", "--exclude-standard")
            for untracked in listing.splitlines():
                untracked = untracked.strip()
                if untracked and _is_orchestrator_artifact_path(untracked):
                    await self._run("add", "--", untracked)

            await self._run("-c", "core.editor=true", "rebase", "--continue")
            return True
        except GitCommandError:
            return False

    async def _resoudre_conflits_journal_en_union(
        self, conflits: tuple[str, ...]
    ) -> bool:
        """Résout en union les conflits sur les fichiers journal (ticket-391).

        Appelée uniquement quand tous les fichiers en conflit sont dans
        ``_JOURNAL_UNION_SUFFIXES``. Pour chaque fichier :
        - ``pipeline-log.md`` : union des lignes, base en premier ;
        - ``documentation.json`` : union des listes JSON sans doublon ;
          JSON illisible → renvoie False, le conflit reste non résolu.

        Renvoie True quand le rebase s'est poursuivi avec succès.
        """
        try:
            for chemin in conflits:
                # Stage 2 = ours (base sur laquelle on rejoue), stage 3 = theirs (ticket).
                try:
                    base_content = await self._run("show", f":2:{chemin}")
                except GitCommandError:
                    base_content = ""
                try:
                    theirs_content = await self._run("show", f":3:{chemin}")
                except GitCommandError:
                    theirs_content = ""

                if chemin.endswith("pipeline-log.md"):
                    resolved: str = _union_lines(base_content, theirs_content)
                elif chemin.endswith("documentation.json"):
                    maybe = _union_json_lists(base_content, theirs_content)
                    if maybe is None:
                        _logger.warning(
                            "journal_union_json_illisible", extra={"chemin": chemin}
                        )
                        return False
                    resolved = maybe
                else:
                    return False

                # git show :2:path retourne le chemin depuis la racine du dépôt.
                # Pour un projet déclaré git_root: ancestor, ce chemin inclut
                # le préfixe (ex. projects/ide-core/memory/…). On le retire pour
                # écrire dans le bon emplacement sur le disque.
                rel_in_project = chemin
                if self._travaille_dans_le_parent():
                    try:
                        prefix = (await self._run("rev-parse", "--show-prefix")).strip()
                        if prefix and rel_in_project.startswith(prefix):
                            rel_in_project = rel_in_project[len(prefix):]
                    except GitCommandError:
                        pass
                dest = self._project_path / rel_in_project
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(resolved, encoding="utf-8")
                await self._run("add", "--", chemin)

            _logger.info("journal_union_resolu", extra={"fichiers": list(conflits)})
            await self._run("-c", "core.editor=true", "rebase", "--continue")
            return True
        except GitCommandError:
            return False

    async def _rebase_en_cours(self) -> bool:
        """Git a-t-il un rebase à moitié appliqué sous la main ?"""
        try:
            git_dir = Path((await self._run("rev-parse", "--git-dir")).strip())
        except GitCommandError:
            return False
        if not git_dir.is_absolute():
            git_dir = self._project_path / git_dir
        return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()

    async def _faire_resoudre(
        self,
        conflits: tuple[str, ...],
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]],
    ) -> bool:
        """Laisse le résolveur réécrire les fichiers, puis poursuit le rebase.

        Rend `False` dès que quoi que ce soit ne va pas. L'appelant annule :
        aucun état intermédiaire n'a besoin d'être compris ici.
        """
        try:
            await resolveur(conflits)
        except Exception:  # noqa: BLE001 — un résolveur qui échoue fait annuler
            _logger.warning("resolveur_en_echec", extra={"fichiers": conflits})
            return False

        for chemin in conflits:
            fichier = self._project_path / chemin
            if not fichier.is_file():
                return False
            # Un fichier qui garde ses marqueurs compile rarement et se relit
            # encore moins : le committer serait pire que ne rien faire.
            if _MARQUEUR_CONFLIT in fichier.read_text(encoding="utf-8", errors="replace"):
                _logger.warning("marqueurs_restants", extra={"fichier": chemin})
                return False

        try:
            await self._run("add", "--", *conflits)
            if await self._fichiers_en_conflit():
                return False
            await self._run(
                "-c", "core.editor=true", "rebase", "--continue"
            )
        except GitCommandError:
            return False
        return True

    async def _fichiers_en_conflit(self) -> tuple[str, ...]:
        sortie = await self._run("diff", "--name-only", "--diff-filter=U")
        return tuple(ligne.strip() for ligne in sortie.splitlines() if ligne.strip())

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

    async def _has_head(self) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--verify", "--quiet", "HEAD",
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def _branch_exists(self, branch_name: str) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch_name}",
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    def _travaille_dans_le_parent(self) -> bool:
        """True si le projet déclare travailler dans le dépôt qui le contient.

        ADR-024 refuse par défaut qu'un projet agisse sur un dépôt ancêtre :
        un dossier client posé dans `projects/` faisait sinon remonter git
        jusqu'à celui de Tessera, où le run créait sa branche et son commit.

        Mais c'est exactement ce que fait le projet bootstrap d'ADR-001 : il
        construit l'IDE, donc il travaille **volontairement** dans le dépôt qui
        le contient. L'exception se déclare donc, fichier par fichier, comme le
        mode des artefacts — le défaut protège, le cas particulier s'énonce
        (ticket-081).
        """
        if self._politique is not None:
            return self._politique.dans_le_depot_parent
        agents_json = self._project_path / "agents.json"
        if not agents_json.is_file():
            return False
        try:
            data = json.loads(agents_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        return bool(data.get("git_root") == "ancestor")

    async def _is_own_repository(self) -> bool:
        """True only if the project directory is itself the root of a repository.

        `--is-inside-work-tree` is not enough, and the difference is what let
        this class break its own promise never to touch Tessera. A project
        folder with no repository of its own makes git walk *up* the tree; in
        `projects/<client>/`, the repository it finds is Tessera's own. Every
        subsequent command then succeeds — against the wrong repository.

        Comparing the toplevel to the project path is the check that holds.
        Locale-independent: it reads a path, never stderr text.
        """
        if self._travaille_dans_le_parent():
            return await self._is_inside_any_work_tree()

        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--show-toplevel",
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return False
        toplevel = stdout.decode("utf-8", errors="replace").strip()
        if not toplevel:
            return False
        try:
            return Path(toplevel).resolve() == self._project_path.resolve()
        except OSError:
            return False

    async def _is_inside_any_work_tree(self) -> bool:
        """True si un dépôt existe, ici ou au-dessus — pour le cas déclaré."""
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--is-inside-work-tree",
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def _ensure_own_repository(self) -> None:
        """Refuse to act at all when the project has no repository of its own."""
        if await self._is_own_repository():
            return
        raise NotAGitRepository(
            command=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stderr=(
                f"{self._project_path} n'est pas la racine d'un dépôt git. "
                "Tessera refuse d'agir sur le dépôt parent : un projet qui "
                "contient plusieurs dépôts doit être déclaré par sous-dossier."
            ),
        )

    async def _run(self, *args: str) -> str:
        # Les hooks du dépôt ne tournent jamais depuis l'orchestrateur. Ils
        # vivent sous la racine du projet, donc à portée d'un agent : un
        # `pre-commit` déposé pendant le run s'exécutait au commit de fin de
        # run, sous l'identité de l'utilisateur, sans qu'une seule commande
        # git ait transité par `Bash` (ticket-119). Le hook de périmètre
        # refuse désormais `.git/`, mais un fichier arrivé par un autre chemin
        # — `python -c`, un clone déjà piégé — ne doit pas tourner non plus.
        # `-c` prime sur `.git/config`, donc sur un `core.hooksPath` qu'un
        # agent y aurait écrit.
        command = [
            "git",
            "-c", f"core.hooksPath={_dossier_sans_hooks()}",
            "-c", "core.quotePath=false",
            *args,
        ]
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            # `communicate()` has awaited the process, so returncode is set;
            # the `or 0` is only there to satisfy its `int | None` type.
            returncode = proc.returncode or 0
            if not await self._is_own_repository():
                raise NotAGitRepository(
                    command=command, returncode=returncode, stderr=stderr_text
                )
            raise GitCommandError(
                command=command, returncode=returncode, stderr=stderr_text
            )
        return stdout_text
