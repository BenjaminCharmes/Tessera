"""Une affectation d'environnement devant git ou gh se refuse — ticket-746."""
import pytest

from tessera.services.providers.git_guard import commande_git_interdite
from tessera.services.providers.git_guard_lexique import affecte_environnement


@pytest.mark.parametrize(
    "commande",
    [
        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.fsmonitor GIT_CONFIG_VALUE_0='x' git status",
        "GIT_CONFIG_PARAMETERS=\"'core.fsmonitor=./x.sh'\" git status",
        "GIT_EXTERNAL_DIFF=./x.sh git diff",
    ],
)
def test_git_environment_assignment_before_git_is_refused(commande: str) -> None:
    assert commande_git_interdite(commande) is True


@pytest.mark.parametrize(
    "commande",
    [
        "env GIT_EXTERNAL_DIFF=./x.sh git diff",
        "FOO=1 env GIT_PAGER=./x.sh git log",
        "env -i GIT_SSH_COMMAND=./x.sh git status",
        "timeout 30 env EDITOR=./x.sh git status",
        "GH_TOKEN=abc gh pr view 1",
        "PAGER=./x.sh gh pr list",
        "VISUAL=./x.sh git status",
        "SSH_ASKPASS=./x.sh git status",
        "git_external_diff=./x.sh git diff",
        "GIT_EXTERNAL_DIFF=./x.sh sh -c 'git diff'",
        "GIT_EXTERNAL_DIFF=./x.sh eval git diff",
        "echo ok; GIT_EXTERNAL_DIFF=./x.sh git diff",
    ],
)
def test_environment_assignment_behind_a_wrapper_is_refused(commande: str) -> None:
    assert commande_git_interdite(commande) is True


@pytest.mark.parametrize(
    "commande",
    [
        "FOO=bar git status",
        "FOO=bar env BAR=1 git diff",
        "GITHUB=1 git log",
        "MY_GIT_X=1 git status",
        "env FOO=bar git status",
        "GIT_EXTERNAL_DIFF=./x.sh ls",
        "GIT_EXTERNAL_DIFF=./x.sh",
        "GIT_EXTERNAL_DIFF=./x.sh sh -c 'ls'",
        "GIT_EXTERNAL_DIFF=./x.sh pytest",
    ],
)
def test_other_assignments_and_other_commands_still_pass(commande: str) -> None:
    assert commande_git_interdite(commande) is False


def test_affecte_environnement_reads_only_the_skipped_prefix() -> None:
    avant = ["GIT_PAGER=x", "git", "status"]
    assert affecte_environnement(avant, ["git", "status"]) is True
    assert affecte_environnement(avant, avant) is False
    assert affecte_environnement(["FOO=1", "git"], ["git"]) is False
