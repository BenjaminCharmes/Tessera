"""The three delivery time limits stay ordered and cover a real CI run."""

from tessera.services.livraison.attente_des_merges import _ATTENTE_MAX_S
from tessera.services.livraison.ci_watcher import _TIMEOUT_PHASE2_S
from tessera.services.livraison.livraison import _ATTENTE_CI_MAX_S


def test_ci_wait_covers_a_ci_run_with_the_e2e_job() -> None:
    """The CI took 20 minutes on PR #939 (05/11) and the 15-minute wait gave up on a green PR."""
    assert _ATTENTE_CI_MAX_S >= 30 * 60


def test_phase_two_outlasts_the_ci_wait_and_merge_waits_outlast_phase_two() -> None:
    """Phase 2 covers the CI wait plus the merge calls; a later delivery waits for phase 2 to end."""
    assert _TIMEOUT_PHASE2_S > _ATTENTE_CI_MAX_S
    assert _ATTENTE_MAX_S > _TIMEOUT_PHASE2_S
