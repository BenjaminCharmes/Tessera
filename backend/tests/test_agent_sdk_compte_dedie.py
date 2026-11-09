"""The CLI starts under the dedicated agent account (ticket-894, ADR-083)."""
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from anyio.abc import Process
from claude_agent_sdk import ClaudeAgentOptions
from pydantic import SecretStr

from tessera.coffre import NOMS_SECRETS
from tessera.config import settings
from tessera.services.providers.agent_sdk import _build_options
from tessera.services.providers.env_agent import CLES_AUTORISEES, CLI_PARTAGE, env_de_l_agent
from tessera.services.providers.lanceur_windows import message_de_logon, texte_d_environnement
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.transport_agent import TransportCompteAgent, transport_du_compte

COMPTE = "agent-test"


class LanceurDouble:
    """Records what it is asked to launch; never starts anything."""

    def __init__(self, refus: ProviderIndisponible | None = None) -> None:
        self.appels: list[dict[str, object]] = []
        self.refus = refus

    async def lancer(
        self, commande: Sequence[str], *, compte: str, mot_de_passe: str,
        env: Mapping[str, str], cwd: str | None, avec_stderr: bool,
    ) -> Process:
        if self.refus is not None:
            raise self.refus
        self.appels.append(
            {"commande": list(commande), "compte": compte, "env": dict(env), "cwd": cwd}
        )
        raise RuntimeError("stop")


def _options() -> ClaudeAgentOptions:
    return _build_options(
        system="s", model="m", max_turns=1, max_budget_usd=None, cwd=Path.cwd(),
        allowed_tools=[],
    )


@pytest.fixture
def compte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr("mdp-factice"))
    monkeypatch.setattr(settings, "agent_oauth_token", SecretStr("jeton-factice"))
    monkeypatch.setattr(settings, "static_token", "statique-factice")


async def _appel(lanceur: LanceurDouble) -> dict[str, object]:
    transport = transport_du_compte("p", _options(), lanceur)
    assert isinstance(transport, TransportCompteAgent)
    with pytest.raises(RuntimeError):
        await transport.connect()
    return lanceur.appels[0]


def test_empty_agent_user_leaves_the_options_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    options = _options()
    assert options.cli_path is None
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in options.env
    assert transport_du_compte("p", options) is None


def test_agent_user_sets_cli_path_and_environment(compte: None) -> None:
    options = _options()
    assert str(options.cli_path) == CLI_PARTAGE
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == "jeton-factice"
    assert options.env["USERPROFILE"] == rf"C:\Users\{COMPTE}"


def test_agent_environment_holds_no_backend_variable(
    compte: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VARIABLE_DU_BACKEND", "x")
    env = env_de_l_agent(COMPTE, r"C:\Git\bin\bash.exe")
    assert set(env) <= CLES_AUTORISEES
    assert "AGENT_LOGON_PASSWORD" not in env
    assert "STATIC_TOKEN" not in env
    assert "VARIABLE_DU_BACKEND" not in env
    assert "mdp-factice" not in env.values()
    assert env["CLAUDE_CODE_GIT_BASH_PATH"] == r"C:\Git\bin\bash.exe"


def test_noms_secrets_holds_the_two_agent_secrets() -> None:
    assert {"AGENT_LOGON_PASSWORD", "AGENT_OAUTH_TOKEN"} <= set(NOMS_SECRETS)


def test_missing_oauth_token_refuses(compte: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_oauth_token", SecretStr(""))
    with pytest.raises(ProviderIndisponible):
        _options()


def test_missing_password_refuses(compte: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr(""))
    with pytest.raises(ProviderIndisponible):
        transport_du_compte("p", _options(), LanceurDouble())


async def test_unknown_account_refuses(compte: None) -> None:
    refus = ProviderIndisponible(message_de_logon(1326, COMPTE))
    transport = transport_du_compte("p", _options(), LanceurDouble(refus))
    assert transport is not None
    with pytest.raises(ProviderIndisponible):
        await transport.connect()


async def test_transport_passes_account_and_environment_to_the_launcher(compte: None) -> None:
    appel = await _appel(LanceurDouble())
    env = appel["env"]
    commande = appel["commande"]
    assert isinstance(env, dict) and isinstance(commande, list)
    assert appel["compte"] == COMPTE
    assert commande[0] == CLI_PARTAGE
    assert env["USERPROFILE"] == rf"C:\Users\{COMPTE}"
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "jeton-factice"
    assert "STATIC_TOKEN" not in env and "AGENT_LOGON_PASSWORD" not in env
    assert env["PATH"].startswith(env["SystemRoot"])


async def test_transport_keeps_the_sdk_command_flags(compte: None) -> None:
    commande = (await _appel(LanceurDouble()))["commande"]
    assert isinstance(commande, list)
    assert "--input-format" in commande and "--model" in commande


def test_logon_message_never_carries_the_password() -> None:
    assert "mdp" not in message_de_logon(1326, COMPTE)
    assert "erreur Windows 5" in message_de_logon(5, COMPTE)


def test_environment_block_is_sorted_and_double_terminated() -> None:
    texte = texte_d_environnement({"B": "2", "A": "1"})
    assert texte == "A=1\0B=2\0\0"
