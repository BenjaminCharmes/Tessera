"""Deterministic secret check on the diff before a push — ticket-547."""
from __future__ import annotations

import pytest

from tessera.services.github_workflow import GitHubWorkflowService, WorkflowError
from tessera.services.politique_run import PolitiqueRun
from tessera.services.secrets_diff import (
    ViolationSecret,
    chercher_secrets,
    refus_secrets,
)

# Les valeurs se construisent à l'exécution : ce fichier traverse lui-même le
# contrôle quand Tessera livre son propre dépôt, et ne doit pas s'y reconnaître.
_AWS = "AK" + "IA" + "A" * 16
_GITHUB = "gh" + "p_" + "a" * 36
_GITHUB_PAT = "github" + "_pat_" + "A" * 30
_GITLAB = "gl" + "pat-" + "a" * 20
_ANTHROPIC = "sk-" + "ant-" + "a" * 24
_STRIPE = "sk_" + "live_" + "a" * 24
_CLE_PRIVEE = "-----" + "BEGIN " + "RSA " + "PRIVATE KEY-----"
_URL = "postgres://" + "admin:hunter2" + "@db.internal/app"

_MOTIFS: list[tuple[str, str]] = [
    ("aws-access-key", f'key = "{_AWS}"'),
    ("github-token", f"token: {_GITHUB}"),
    ("github-token", f"token: {_GITHUB_PAT}"),
    ("gitlab-token", f"token: {_GITLAB}"),
    ("anthropic-key", f'API_KEY = "{_ANTHROPIC}"'),
    ("stripe-live-key", f"STRIPE={_STRIPE}"),
    ("private-key", _CLE_PRIVEE),
    ("url-credentials", f"DATABASE_URL={_URL}"),
]


def _diff(contenu: str, signe: str = "+", chemin: str = "src/app.py") -> str:
    return (
        f"diff --git a/{chemin} b/{chemin}\n"
        f"--- a/{chemin}\n"
        f"+++ b/{chemin}\n"
        "@@ -1,2 +1,2 @@\n"
        " import os\n"
        f"{signe}{contenu}\n"
    )


def _diff_fichier_ajoute(chemin: str) -> str:
    return (
        f"diff --git a/{chemin} b/{chemin}\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        f"+++ b/{chemin}\n"
        "@@ -0,0 +1 @@\n"
        "+rien\n"
    )


@pytest.mark.parametrize(("type_secret", "ligne"), _MOTIFS)
def test_added_line_is_detected(type_secret: str, ligne: str) -> None:
    violations = chercher_secrets(_diff(ligne))

    assert violations == [ViolationSecret("src/app.py", 2, type_secret)]


@pytest.mark.parametrize(("type_secret", "ligne"), _MOTIFS)
def test_removed_line_is_ignored(type_secret: str, ligne: str) -> None:
    assert chercher_secrets(_diff(ligne, signe="-")) == []


@pytest.mark.parametrize(("type_secret", "ligne"), _MOTIFS)
def test_context_line_is_ignored(type_secret: str, ligne: str) -> None:
    assert chercher_secrets(_diff(ligne, signe=" ")) == []


@pytest.mark.parametrize(
    "chemin", [".env", "deploy/.env", "certs/server.pem", "home/id_rsa"]
)
def test_added_secret_file_is_detected(chemin: str) -> None:
    violations = chercher_secrets(_diff_fichier_ajoute(chemin))

    assert [v.fichier for v in violations] == [chemin]
    assert violations[0].ligne == 1


def test_deleted_secret_file_is_ignored() -> None:
    diff = (
        "diff --git a/.env b/.env\n"
        "deleted file mode 100644\n"
        "--- a/.env\n"
        "+++ /dev/null\n"
        "@@ -1 +0,0 @@\n"
        "-X=1\n"
    )

    assert chercher_secrets(diff) == []


@pytest.mark.parametrize(
    "chemin", [".env.example", "id_rsa.pub", "docs/env.md", "src/pem.py"]
)
def test_ordinary_file_name_is_not_flagged(chemin: str) -> None:
    assert chercher_secrets(_diff_fichier_ajoute(chemin)) == []


def test_placeholder_and_short_key_are_not_detected() -> None:
    placeholder = 'API_KEY = "sk-ant-..."'
    trop_courte = 'key = "AK' + "IA" + 'ABC123"'
    url_de_doc = "exemple : postgres://user:password@localhost/db"
    url_gabarit = 'f"postgres://{user}:{mot_de_passe}@{hote}/db"'

    for ligne in (placeholder, trop_courte, url_de_doc, url_gabarit):
        assert chercher_secrets(_diff(ligne)) == [], ligne


def test_line_number_follows_the_new_file() -> None:
    diff = (
        "diff --git a/a.py b/a.py\n"
        "--- a/a.py\n"
        "+++ b/a.py\n"
        "@@ -10,3 +20,4 @@\n"
        " contexte\n"
        "-ancienne\n"
        "+nouvelle\n"
        f"+k = {_AWS}\n"
    )

    assert chercher_secrets(diff) == [ViolationSecret("a.py", 22, "aws-access-key")]


def test_each_file_of_a_diff_is_reported_with_its_own_path() -> None:
    diff = _diff(f"a = {_AWS}", chemin="un.py") + _diff(
        f"b = {_GITLAB}", chemin="deux.py"
    )

    assert [(v.fichier, v.type_secret) for v in chercher_secrets(diff)] == [
        ("un.py", "aws-access-key"),
        ("deux.py", "gitlab-token"),
    ]


def test_violation_message_never_carries_the_secret() -> None:
    valeurs = [_AWS, _GITHUB, _GITLAB, _ANTHROPIC, _STRIPE, "hunter2"]
    for _, ligne in _MOTIFS:
        for violation in chercher_secrets(_diff(ligne)):
            message = str(violation) + repr(violation)
            assert not any(valeur in message for valeur in valeurs)
            assert "src/app.py:2" in message


def test_refus_secrets_is_none_on_a_clean_diff_and_names_the_source_otherwise() -> None:
    assert refus_secrets(_diff("x = 1")) is None

    refus = refus_secrets(_diff(f"k = {_AWS}"))

    assert refus is not None
    assert "src/app.py:2 (aws-access-key)" in refus
    assert _AWS not in refus


# ---------------------------------------------------------------------------
# GitHubWorkflowService.open_pull_request — le push est refusé
# ---------------------------------------------------------------------------


class _FakeGit:
    def __init__(self, diff: str) -> None:
        self._diff = diff
        self.pushed: list[str] = []

    async def push_branch(self, branch_name: str) -> None:
        self.pushed.append(branch_name)

    async def current_diff(self) -> str:
        return self._diff

    async def diff_de_branche(self, base: str, branch: str) -> str:
        return self._diff

    async def commits_depuis_base(self, base: str, branch: str) -> list[object]:
        return []


class _FakeGitHub:
    def __init__(self) -> None:
        self.created = 0

    async def create_pull_request(self, **kwargs: object) -> tuple[int, str]:
        self.created += 1
        return 1, "https://github.com/o/r/pull/1"


def _service(
    git: _FakeGit, github: _FakeGitHub, confidentialite: str | None = None
) -> GitHubWorkflowService:
    return GitHubWorkflowService(
        git_workspace=git,  # type: ignore[arg-type]
        github=github,  # type: ignore[arg-type]
        base_branch="develop",
        politique=PolitiqueRun(confidentialite=confidentialite),
    )


async def _ouvrir(service: GitHubWorkflowService) -> None:
    await service.open_pull_request(
        branch="ticket-001-x",
        ticket_id="ticket-001",
        ticket_title="T",
        ticket_body="",
        autonome=False,
    )


async def test_push_is_refused_when_the_diff_carries_a_secret() -> None:
    git, github = _FakeGit(_diff(f"k = {_AWS}")), _FakeGitHub()

    with pytest.raises(WorkflowError) as exc:
        await _ouvrir(_service(git, github))

    assert "src/app.py:2 (aws-access-key)" in str(exc.value)
    assert _AWS not in str(exc.value)
    assert git.pushed == []
    assert github.created == 0


async def test_professional_confidentiality_does_not_skip_the_secret_check() -> None:
    git, github = _FakeGit(_diff(f"k = {_GITHUB}")), _FakeGitHub()

    with pytest.raises(WorkflowError, match="secret détecté"):
        await _ouvrir(_service(git, github, confidentialite="professional"))

    assert git.pushed == []


async def test_push_goes_through_on_a_clean_diff() -> None:
    git, github = _FakeGit(_diff("x = 1")), _FakeGitHub()

    await _ouvrir(_service(git, github))

    assert git.pushed == ["ticket-001-x"]
    assert github.created == 1
