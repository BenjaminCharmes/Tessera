"""Les enveloppes courantes de Windows et de Git Bash — ticket-749."""
import pytest

from tessera.services.providers.git_guard import commande_git_interdite
from tessera.services.providers.git_guard_lectures import gh_sans_sous_commande, git_sans_sous_commande
from tessera.services.providers.git_guard_lexique import commande_opaque, jetons, sans_enveloppe


@pytest.mark.parametrize(
    "commande",
    [
        'cmd //c "git push"',
        "cmd //k git push",
        "powershell git push",
        "pwsh -NoProfile git push",
        "powershell -EncodedCommand ZwBpAHQA",
        "pwsh -enc ZwBpAHQA",
        "powershell -e ZwBpAHQA",
        "powershell -ec ZwBpAHQA",
    ],
)
def test_windows_shell_wrappers_are_refused(commande: str) -> None:
    assert commande_git_interdite(commande) is True


@pytest.mark.parametrize(
    "commande",
    [
        "echo push | xargs git",
        "echo push origin | xargs git -C .",
        "echo pr merge | xargs gh",
        "env -u HOME git push",
        "env -C /tmp git push",
        "timeout -s KILL 30 git push",
        "timeout -k 5 30 git push",
        "stdbuf -oL git push",
        "stdbuf -o L git push",
        "setsid git push",
        "flock /tmp/x.lock git push",
        "flock -w 5 /tmp/x.lock git push",
        "nice -n 10 git push",
        "xargs -n 1 git push",
    ],
)
def test_wrapper_options_do_not_hide_git(commande: str) -> None:
    assert commande_git_interdite(commande) is True


@pytest.mark.parametrize(
    "commande",
    [
        "xargs git status",
        "xargs -n 1 git log",
        "xargs gh auth status",
        "timeout 30 git log",
        "env -u HOME git status",
        "timeout -s KILL 30 git diff",
        "stdbuf -oL git status",
        "flock /tmp/x.lock git status",
        'cmd //c "git status"',
        "powershell git status",
        "powershell -NoProfile -Command ls",
        "powershell",
        "xargs echo",
        "xargs",
    ],
)
def test_reads_behind_wrappers_still_pass(commande: str) -> None:
    assert commande_git_interdite(commande) is False


def test_sans_enveloppe_consumes_the_value_of_a_known_option() -> None:
    assert sans_enveloppe(jetons("env -u HOME git push")) == ["git", "push"]
    assert sans_enveloppe(jetons("sudo -s git push")) == ["git", "push"]


def test_commande_opaque_only_matches_encoded_command() -> None:
    assert commande_opaque(jetons("powershell -EncodedCommand abc")) is True
    assert commande_opaque(jetons("powershell -ExecutionPolicy Bypass")) is False
    assert commande_opaque(jetons("bash -e script")) is False


def test_git_sans_sous_commande() -> None:
    assert git_sans_sous_commande([]) is True
    assert git_sans_sous_commande(["-C", "."]) is True
    assert git_sans_sous_commande(["status"]) is False


def test_gh_sans_sous_commande() -> None:
    assert gh_sans_sous_commande([]) is True
    assert gh_sans_sous_commande(["-R", "o/r"]) is True
    assert gh_sans_sous_commande(["pr", "view"]) is False
