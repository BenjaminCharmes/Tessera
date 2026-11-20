"""Which GitHub HTTP errors are a doubt rather than a verdict."""
import httpx

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def statut_douteux(exc: httpx.HTTPStatusError) -> bool:
    """True for a 5xx or a 405 "Merge already in progress".

    The merge may well have happened on GitHub's side: the PR is reread
    before concluding. Any other status is a refusal.
    """
    statut = exc.response.status_code
    if statut >= 500:
        return True
    return statut == 405 and "merge already in progress" in exc.response.text.lower()


def refus_ou_doute(exc: httpx.HTTPStatusError, pr_number: int) -> bool:
    """Returns False for a refusal (logged); re-raises a doubtful status."""
    if statut_douteux(exc):
        raise exc
    _logger.warning(
        "merge_http_erreur",
        extra={"pr": pr_number, "status": exc.response.status_code},
    )
    return False
