"""Tell a quota exhaustion apart from any other agent failure — ticket-498.

When the subscription quota runs out *during* an agent call, the CLI exits with
code 1 and an empty stderr: the SDK surfaces it as a bare `ProcessError`, which
reads like a crash. This module reads the exception together with the last
quota snapshot the provider reported, so the run can say what really happened.

Pure on purpose: no I/O, no import of the SDK. A `ProcessError` is recognised by
class name, so the module loads even where the SDK is absent.
"""
import re
from datetime import timezone

from tessera.services.quota_tracker import QuotaSnapshot

_QUOTA_TEXT_RE = re.compile(r"usage limit|rate limit|allowance", re.IGNORECASE)


def _is_process_error(exc: BaseException) -> bool:
    return any(cls.__name__ == "ProcessError" for cls in type(exc).__mro__)


def _stderr_is_empty(exc: BaseException) -> bool:
    stderr = getattr(exc, "stderr", None)
    return not (isinstance(stderr, str) and stderr.strip())


def is_quota_exhausted(exc: BaseException, snapshot: QuotaSnapshot | None) -> bool:
    """Return True when an agent call failed because the quota ran out.

    Three signals, any one is enough: the last snapshot was `rejected`; the
    error text speaks of a usage or rate limit; or a `ProcessError` with an
    empty stderr followed a snapshot that was already `allowed_warning`.
    An ordinary `ProcessError` with an `allowed` (or no) snapshot is not one.
    """
    if snapshot is not None and snapshot.status == "rejected":
        return True
    if _QUOTA_TEXT_RE.search(str(exc)):
        return True
    return (
        snapshot is not None
        and snapshot.status == "allowed_warning"
        and _is_process_error(exc)
        and _stderr_is_empty(exc)
    )


def resume_label(snapshot: QuotaSnapshot | None) -> str:
    """Return the resume time as `HH:MM UTC`, or `heure inconnue`."""
    if snapshot is None or snapshot.resets_at is None:
        return "heure inconnue"
    return snapshot.resets_at.astimezone(timezone.utc).strftime("%H:%M UTC")
