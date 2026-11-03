"""The workspace test double carries what the orchestrator calls (ticket-742)."""

import inspect

import pytest

from tessera.services.git_workspace import GitWorkspaceService
from tests.doubles_git import GitWorkspaceDouble

# Méthodes asynchrones publiques du workspace appelées par l'orchestrateur, ses
# étapes (`pipeline_*`, `run_dans_worktree`, `retest_apres_rebase`) et la livraison.
APPELEES_PAR_L_ORCHESTRATEUR = [
    "advance_base_ref",
    "adopter_worktree",
    "chemins_modifies",
    "commit_all",
    "commit_bookkeeping",
    "commit_chemins",
    "commits_depuis_base",
    "commits_hors_rangement",
    "create_branch",
    "current_diff",
    "diff_de_branche",
    "diff_depuis_base",
    "dirty_files",
    "est_ancetre",
    "initialiser_base_ref",
    "is_clean",
    "lire_ticket_sur_la_base",
    "push_branch",
    "rejouer_sur",
    "restaurer_ticket_depuis_base",
    "retourner_sur_base",
    "sha_distant",
    "sync_base_depuis_distant",
]

# Lues par `getattr(..., None)` : l'absence signifie « indisponible ».
SONDEES_PAR_GETATTR = ["branche_courante", "head_sha", "fichiers_non_suivis_laisses"]


@pytest.mark.parametrize("nom", APPELEES_PAR_L_ORCHESTRATEUR)
def test_the_base_carries_every_method_the_orchestrator_calls(nom: str) -> None:
    assert inspect.iscoroutinefunction(getattr(GitWorkspaceDouble, nom))


@pytest.mark.parametrize("nom", APPELEES_PAR_L_ORCHESTRATEUR)
def test_each_method_keeps_the_signature_of_the_real_service(nom: str) -> None:
    reel = inspect.signature(getattr(GitWorkspaceService, nom))
    double = inspect.signature(getattr(GitWorkspaceDouble, nom))
    assert list(double.parameters) == list(reel.parameters)
    for param_reel, param_double in zip(
        reel.parameters.values(), double.parameters.values(), strict=True
    ):
        assert param_double.kind == param_reel.kind
        assert (param_double.default is inspect.Parameter.empty) == (
            param_reel.default is inspect.Parameter.empty
        )


@pytest.mark.parametrize("nom", SONDEES_PAR_GETATTR)
def test_the_base_leaves_the_probed_methods_undefined(nom: str) -> None:
    assert not hasattr(GitWorkspaceDouble, nom)


async def test_the_base_answers_neutral_values() -> None:
    git = GitWorkspaceDouble()
    assert await git.is_clean() is True
    assert await git.dirty_files() == []
    assert await git.commit_all("message") is None
    assert await git.diff_depuis_base() == ""
    assert await git.create_branch("ticket-001", "slug") == "ticket-001-slug"
    assert await git.restaurer_ticket_depuis_base("ticket-001") is False
    assert await git.rejouer_sur("develop") == ()
    assert await git.sync_base_depuis_distant("develop") is None
