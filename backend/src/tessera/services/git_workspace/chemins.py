"""Paths Tessera owns inside a project, and the pathspecs derived from them."""

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

    Paths are relative to the project: callers holding repository-root paths
    (``git diff --name-only`` under ``git_root: ancestor``) strip the project
    prefix first (``_relatif_au_projet``), so that a ``tickets/`` folder
    elsewhere in the repository is never taken for Tessera's own.
    """
    for artifact in _ORCHESTRATOR_ARTIFACT_PATHS:
        if artifact.endswith("/"):
            if path.startswith(artifact):
                return True
        elif path == artifact:
            return True
    return False


def _relatif_au_projet(chemin: str, prefixe: str) -> str | None:
    """Repository-root path → project-relative path, or None outside the project.

    ``prefixe`` is ``git rev-parse --show-prefix`` from the project folder:
    empty for a project at the root of its repository.
    """
    if not prefixe:
        return chemin
    return chemin[len(prefixe):] if chemin.startswith(prefixe) else None


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
