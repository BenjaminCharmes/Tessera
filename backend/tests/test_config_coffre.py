"""Settings read their secrets from the vault, then from .env (ticket-795, ADR-073).

Each test writes a throwaway .env with fictitious values in ``tmp_path`` and
replaces ``coffre_du_systeme`` by an in-memory double.
"""
import logging
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from tessera import config_coffre
from tessera.coffre import NOMS_SECRETS, CoffreAbsent, CoffreEnErreur
from tessera.config import Settings, load_settings
from tessera.config_errors import ConfigurationError, describe_validation_error
from tests.coffre_double import CoffreDouble, ouvrant

FAUX_COFFRE = "faux-jeton-du-coffre-1234"
FAUX_ENV = "faux-jeton-du-dotenv-5678"


@pytest.fixture(autouse=True)
def _environnement_neutre(monkeypatch: pytest.MonkeyPatch) -> None:
    """No secret from the developer's shell, and the default mode."""
    for nom in NOMS_SECRETS:
        monkeypatch.delenv(nom, raising=False)
    monkeypatch.setenv("SECRETS_SOURCE", "auto")


def _dotenv(tmp_path: Path, *lignes: str) -> Path:
    fichier = tmp_path / ".env"
    fichier.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return fichier


def _avec_coffre(monkeypatch: pytest.MonkeyPatch, coffre: CoffreDouble) -> None:
    monkeypatch.setattr(config_coffre, "coffre_du_systeme", ouvrant(coffre))


def _sans_coffre(monkeypatch: pytest.MonkeyPatch, erreur: Exception) -> None:
    monkeypatch.setattr(config_coffre, "coffre_du_systeme", ouvrant(erreur=erreur))


def _messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "tessera.config"]


def _texte_des_journaux(caplog: pytest.LogCaptureFixture) -> str:
    return " ".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)


def test_coffre_value_wins_over_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _avec_coffre(monkeypatch, CoffreDouble({"GITHUB_TOKEN": FAUX_COFFRE}))
    reglages = load_settings(_dotenv(tmp_path, f"GITHUB_TOKEN={FAUX_ENV}"))
    assert reglages.github_token == FAUX_COFFRE


def test_environment_variable_wins_over_the_vault(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _avec_coffre(monkeypatch, CoffreDouble({"VERCEL_TOKEN": FAUX_COFFRE}))
    monkeypatch.setenv("VERCEL_TOKEN", "jeton-de-l-environnement")
    reglages = load_settings(_dotenv(tmp_path))
    assert reglages.vercel_token.get_secret_value() == "jeton-de-l-environnement"


def test_missing_entry_falls_back_to_dotenv_and_warns_by_name_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _avec_coffre(monkeypatch, CoffreDouble())
    with caplog.at_level(logging.WARNING, logger="tessera.config"):
        reglages = load_settings(_dotenv(tmp_path, f"STATIC_TOKEN={FAUX_ENV}"))
    assert reglages.static_token == FAUX_ENV
    assert "secret_en_clair_dans_env" in _messages(caplog)
    assert "STATIC_TOKEN" in _texte_des_journaux(caplog)
    assert FAUX_ENV not in _texte_des_journaux(caplog)


def test_missing_entry_everywhere_keeps_the_empty_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _avec_coffre(monkeypatch, CoffreDouble())
    reglages = load_settings(_dotenv(tmp_path))
    assert reglages.anthropic_api_key == ""
    assert reglages.stripe_api_key == SecretStr("")


def test_absent_vault_in_auto_mode_starts_on_dotenv_and_warns_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _sans_coffre(monkeypatch, CoffreAbsent("aucun coffre"))
    fichier = _dotenv(tmp_path, f"GITHUB_TOKEN={FAUX_ENV}", f"FORBIDDEN_TERMS={FAUX_ENV}")
    with caplog.at_level(logging.WARNING, logger="tessera.config"):
        reglages = load_settings(fichier)
    assert reglages.github_token == FAUX_ENV
    assert reglages.forbidden_terms == FAUX_ENV
    assert _messages(caplog).count("coffre_indisponible_repli_env") == 1
    assert FAUX_ENV not in _texte_des_journaux(caplog)


def test_locked_vault_in_auto_mode_starts_on_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _avec_coffre(monkeypatch, CoffreDouble(erreur=CoffreEnErreur("verrouillé")))
    reglages = load_settings(_dotenv(tmp_path, f"GITHUB_TOKEN={FAUX_ENV}"))
    assert reglages.github_token == FAUX_ENV


def test_absent_vault_in_auto_mode_refuses_when_dotenv_marks_a_migrated_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _sans_coffre(monkeypatch, CoffreAbsent("aucun coffre"))
    fichier = _dotenv(
        tmp_path,
        "# STATIC_TOKEN : dans le coffre (tessera.ps1 secrets)",
        f"GITHUB_TOKEN={FAUX_ENV}",
    )
    with pytest.raises(ConfigurationError) as erreur:
        load_settings(fichier)
    assert "STATIC_TOKEN" in str(erreur.value)
    assert FAUX_ENV not in str(erreur.value)


def test_absent_vault_in_coffre_mode_refuses_to_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "coffre")
    _sans_coffre(monkeypatch, CoffreAbsent("aucun coffre"))
    with pytest.raises(ConfigurationError) as erreur:
        load_settings(_dotenv(tmp_path, f"GITHUB_TOKEN={FAUX_ENV}"))
    message = str(erreur.value)
    assert "SECRETS_SOURCE=auto" in message
    assert "env" in message
    assert FAUX_ENV not in message


def test_env_mode_never_calls_the_vault(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "env")
    double = CoffreDouble({"GITHUB_TOKEN": FAUX_COFFRE}, erreur=AssertionError("appelé"))
    _avec_coffre(monkeypatch, double)

    def jamais() -> CoffreDouble:
        raise AssertionError("coffre_du_systeme ne doit pas être appelé")

    monkeypatch.setattr(config_coffre, "coffre_du_systeme", jamais)
    reglages = load_settings(_dotenv(tmp_path, f"GITHUB_TOKEN={FAUX_ENV}"))
    assert reglages.github_token == FAUX_ENV
    assert double.appels == 0


def test_secrets_source_defaults_to_auto(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SECRETS_SOURCE")
    _avec_coffre(monkeypatch, CoffreDouble())
    assert load_settings(_dotenv(tmp_path)).secrets_source == "auto"
    assert config_coffre.lire_secrets_source(tmp_path / "absent.env") == "auto"
    fichier = _dotenv(tmp_path, "SECRETS_SOURCE=env")
    assert config_coffre.lire_secrets_source(fichier) == "env"


def test_validation_error_for_a_vault_value_does_not_echo_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class ReglagesStricts(Settings):
        static_token: int = 0  # type: ignore[assignment]

    _avec_coffre(monkeypatch, CoffreDouble({"STATIC_TOKEN": FAUX_COFFRE}))
    with pytest.raises(ValidationError) as erreur:
        ReglagesStricts(_env_file=_dotenv(tmp_path))  # type: ignore[call-arg]
    assert FAUX_COFFRE not in str(erreur.value)
    assert FAUX_COFFRE not in describe_validation_error(erreur.value)
