"""Branch name construction from a ticket id and a slug."""

import re

from tessera.services.git_workspace.erreurs import InvalidSlugError


_MAX_BRANCH_LENGTH = 60


def _sanitize_slug(slug: str) -> str:
    """Reduce an arbitrary slug to lowercase alphanumerics and hyphens.

    Accents and punctuation become hyphens, consecutive hyphens are merged
    and leading/trailing hyphens are stripped.
    """
    lowered = slug.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    return normalized.strip("-")


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
