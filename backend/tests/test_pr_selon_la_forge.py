"""L'ouverture de PR n'est proposee que la ou elle marche — ticket-081."""
import pytest

from vibe_ide.services.github_workflow import forge_supportee, nom_de_la_forge


@pytest.mark.parametrize(
    "remote",
    [
        "https://github.com/moi/mon-repo.git",
        "git@github.com:moi/mon-repo.git",
    ],
)
def test_github_est_supporte(remote: str) -> None:
    assert forge_supportee(remote) is True


@pytest.mark.parametrize(
    "remote",
    [
        "https://gitlab.interne.exemple-forge.net/gitlab/groupe/equipe/orion.git",
        "https://exemple-org@dev.azure.com/exemple-org/Lyra/_git/Lyra",
        "git@bitbucket.org:moi/repo.git",
    ],
)
def test_les_autres_forges_ne_le_sont_pas(remote: str) -> None:
    # Le bouton poussait la branche **puis** appelait api.github.com : sur un
    # depot GitLab ou Azure, il poussait donc sans rien demander avant
    # d'echouer. Sur un depot client, pousser est precisement ce qui demande
    # une decision (ticket-081).
    assert forge_supportee(remote) is False


def test_sans_remote_rien_n_est_propose() -> None:
    assert forge_supportee(None) is False


@pytest.mark.parametrize(
    "remote,attendu",
    [
        ("https://github.com/moi/repo.git", "GitHub"),
        ("https://dev.azure.com/org/p/_git/p", "Azure DevOps"),
        ("https://gitlab.exemple-forge.net/it/orion.git", "GitLab"),
        ("git@bitbucket.org:moi/repo.git", "bitbucket.org"),
    ],
)
def test_la_forge_est_nommee_pour_l_utilisateur(remote: str, attendu: str) -> None:
    # Dire « ce dépôt n'est pas sur GitHub » sans dire où il est n'aide pas.
    assert nom_de_la_forge(remote) == attendu
