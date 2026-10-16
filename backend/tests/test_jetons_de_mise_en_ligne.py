"""Online-service tokens stay in the backend — ADR-053, ticket-464."""
import json
import logging
from typing import Any

import pytest
from pydantic import SecretStr

from tessera.config import CHAMPS_JETONS, VARIABLES_JETONS, Settings, settings
from tessera.routers.orchestrator import _livraison_interrompue
from tessera.services.github_workflow import GitHubWorkflowService, WorkflowError
from tessera.services.politique_run import PolitiqueRun
from tessera.services.providers.agent_sdk import _build_options
from tessera.services.termes_interdits import CommitInfo, TermesInterditsService
from tessera.utils.logger import _JsonFormatter, get_logger
from tessera.utils.secrets import MASQUE, SECRETS, SecretRegistry

# Des valeurs inventées, de la forme d'un jeton.
_JETONS = {
    "vercel_token": "vrc_Zk3fQ9aLmN27xPw",
    "neon_api_key": "neon_8hT2vRb5YcD4eUq",
    "resend_api_key": "re_J6sG1oWzX0nKi8M",
    "stripe_api_key": "rk_test_Ab12Cd34Ef56Gh",
    "cloudflare_api_token": "cf_Qw9ErTy7UiOp5As",
}


def _reglages() -> Settings:
    return Settings(_env_file=None, **_JETONS)  # type: ignore[arg-type]


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------


def test_the_five_tokens_are_empty_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in VARIABLES_JETONS:
        monkeypatch.delenv(variable, raising=False)

    vides = Settings(_env_file=None)

    assert vides.valeurs_des_jetons() == []
    assert vides.vercel_team_id == ""


def test_settings_hide_every_token_value() -> None:
    reglages = _reglages()

    rendus = [
        repr(reglages),
        str(reglages),
        str(reglages.model_dump()),
        repr(reglages.model_dump()),
        reglages.model_dump_json(),
        json.dumps(reglages.model_dump(mode="json")),
    ]

    for valeur in _JETONS.values():
        assert all(valeur not in rendu for rendu in rendus)


def test_settings_still_hand_the_values_to_the_backend() -> None:
    assert set(_reglages().valeurs_des_jetons()) == set(_JETONS.values())


def test_the_environment_feeds_the_token_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_TOKEN", "vrc_depuis_l_environnement")
    monkeypatch.setenv("VERCEL_TEAM_ID", "team_abc")

    reglages = Settings(_env_file=None)

    assert reglages.vercel_token.get_secret_value() == "vrc_depuis_l_environnement"
    assert reglages.vercel_team_id == "team_abc"
    assert VARIABLES_JETONS == tuple(c.upper() for c in CHAMPS_JETONS)


def test_the_env_file_is_the_one_at_the_repository_root() -> None:
    assert Settings.env_file.name == ".env"
    assert (Settings.env_file.parent / "backend").is_dir()


# ------------------------------------------------------------------
# Registry and logger
# ------------------------------------------------------------------


def test_registry_masks_registered_values_and_ignores_blanks() -> None:
    registre = SecretRegistry()
    registre.register("   ")
    registre.register("")
    registre.register("s3cret-value")

    assert registre.mask("a s3cret-value b") == f"a {MASQUE} b"
    assert registre.valeurs() == frozenset({"s3cret-value"})


def test_registry_masks_the_longest_value_first() -> None:
    registre = SecretRegistry()
    registre.register_all(["abcd1234", "abcd1234-extended"])

    assert registre.mask("x abcd1234-extended y") == f"x {MASQUE} y"


def test_registry_masks_a_value_that_json_escapes() -> None:
    registre = SecretRegistry()
    registre.register('with"quote\\slash')

    ligne = json.dumps({"m": 'with"quote\\slash'})

    assert 'quote' not in registre.mask(ligne)


def _enregistrement(message: str, **extra: Any) -> logging.LogRecord:
    record = logging.LogRecord("t", logging.WARNING, __file__, 1, message, (), None)
    record.__dict__.update(extra)
    return record


def test_logger_masks_a_configured_token() -> None:
    SECRETS.register_all(_reglages().valeurs_des_jetons())

    ligne = _JsonFormatter().format(
        _enregistrement(
            f"appel avec {_JETONS['vercel_token']}",
            detail=f"Bearer {_JETONS['stripe_api_key']}",
        )
    )

    assert _JETONS["vercel_token"] not in ligne
    assert _JETONS["stripe_api_key"] not in ligne
    assert MASQUE in ligne


def test_logger_masks_a_secret_registered_at_run_time() -> None:
    SECRETS.register("whsec_recu_pendant_l_appel")

    ligne = _JsonFormatter().format(
        _enregistrement("webhook créé", extra_secret="whsec_recu_pendant_l_appel")
    )

    assert "whsec_recu_pendant_l_appel" not in ligne
    assert MASQUE in ligne


def test_logger_masks_a_secret_inside_an_exception_trace() -> None:
    SECRETS.register("tok_dans_la_trace")
    try:
        raise RuntimeError("échec avec tok_dans_la_trace")
    except RuntimeError as exc:
        record = _enregistrement("boom")
        record.exc_info = (type(exc), exc, exc.__traceback__)

    assert "tok_dans_la_trace" not in _JsonFormatter().format(record)


def test_a_real_logger_writes_the_masked_line(capsys: pytest.CaptureFixture[str]) -> None:
    SECRETS.register("tok_via_get_logger")

    get_logger("test.jetons.stdout").warning("x tok_via_get_logger", extra={"k": "tok_via_get_logger"})

    sortie = capsys.readouterr().out
    assert "tok_via_get_logger" not in sortie
    assert MASQUE in sortie


# ------------------------------------------------------------------
# Environment of the SDK subprocess
# ------------------------------------------------------------------


def test_sdk_options_empty_the_five_variables_even_when_exported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in VARIABLES_JETONS:
        monkeypatch.setenv(variable, "exporte-dans-le-shell")

    options = _build_options(
        system="s", model="m", max_turns=1, max_budget_usd=None, cwd=None
    )

    assert options.env is not None
    assert len(VARIABLES_JETONS) == 5
    for variable in VARIABLES_JETONS:
        assert options.env.get(variable) == ""


# ------------------------------------------------------------------
# Push gate
# ------------------------------------------------------------------


class _Git:
    def __init__(self, diff: str, commits: list[CommitInfo] | None = None) -> None:
        self._diff = diff
        self._commits = commits or []
        self.pushed: list[str] = []

    async def push_branch(self, branch_name: str) -> None:
        self.pushed.append(branch_name)

    async def diff_de_branche(self, base: str, branch: str) -> str:
        return self._diff

    async def commits_depuis_base(self, base: str, branch: str) -> list[CommitInfo]:
        return self._commits


class _GitHub:
    async def create_pull_request(self, **kwargs: object) -> tuple[int, str]:
        return 1, "https://github.com/o/r/pull/1"


def _service(git: _Git) -> GitHubWorkflowService:
    return GitHubWorkflowService(
        git_workspace=git,  # type: ignore[arg-type]
        github=_GitHub(),  # type: ignore[arg-type]
        base_branch="develop",
        politique=PolitiqueRun(confidentialite=None),
        termes=TermesInterditsService(),
    )


async def _pousser(git: _Git) -> WorkflowError:
    with pytest.raises(WorkflowError) as exc:
        await _service(git).open_pull_request(
            branch="b", ticket_id="t", ticket_title="T", ticket_body="", autonome=False
        )
    return exc.value


def _configurer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vercel_token", SecretStr(_JETONS["vercel_token"]))


def test_configured_tokens_make_the_push_gate_active(monkeypatch: pytest.MonkeyPatch) -> None:
    assert TermesInterditsService().actif is False

    _configurer(monkeypatch)

    assert TermesInterditsService().actif is True


async def test_a_diff_adding_a_configured_token_stops_the_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configurer(monkeypatch)
    git = _Git(f"+++ b/src/deploy.py\n+TOKEN = '{_JETONS['vercel_token']}'\n")

    erreur = await _pousser(git)

    assert git.pushed == []
    assert "file:src/deploy.py" in str(erreur)
    assert _JETONS["vercel_token"] not in str(erreur)


async def test_livraison_arret_names_the_place_not_the_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configurer(monkeypatch)
    git = _Git(f"+++ b/src/deploy.py\n+TOKEN = '{_JETONS['vercel_token']}'\n")

    livraison = _livraison_interrompue(await _pousser(git))

    assert livraison.arret is not None
    assert "src/deploy.py" in livraison.arret
    assert _JETONS["vercel_token"] not in livraison.arret


async def test_a_token_in_a_commit_message_stops_the_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configurer(monkeypatch)
    commit = CommitInfo(
        sha7="abc1234", message=f"fix: use {_JETONS['vercel_token']}", auteur="A <a@a.local>"
    )

    erreur = await _pousser(_Git("", [commit]))

    assert "commit:abc1234" in str(erreur)
    assert _JETONS["vercel_token"] not in str(erreur)


async def test_a_secret_registered_at_run_time_stops_the_push() -> None:
    # Pas d'arobase : le test des traces professionnelles lirait un domaine.
    SECRETS.register("postgres://u:p4ssw0rd/app?host=db-interne-inventee")
    git = _Git("+++ b/.env.sample\n+DB=postgres://u:p4ssw0rd/app?host=db-interne-inventee\n")

    erreur = await _pousser(git)

    assert git.pushed == []
    assert "p4ssw0rd" not in str(erreur)


async def test_a_token_embedded_in_a_longer_word_is_still_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configurer(monkeypatch)
    git = _Git(f"+++ b/a.txt\n+Bearer{_JETONS['vercel_token']}x\n")

    await _pousser(git)

    assert git.pushed == []


def test_a_clean_diff_passes_with_tokens_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configurer(monkeypatch)

    violations = TermesInterditsService().verifier(
        lignes_ajoutees=["+++ b/a.py", "+print('ok')"], commits=[]
    )

    assert violations == []
