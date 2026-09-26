"""Session resume between two review rounds — ticket-187.

Au tour 2, le codeur repartait d'une session SDK vide et redécouvrait le
dépôt : 227 k tokens relus en moyenne par appel, pour 9,6 k produits. Le SDK
sait reprendre une conversation ; ces tests verrouillent que le pipeline s'en
sert, et seulement là où c'est voulu.
"""
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

import tessera.services.providers.agent_sdk as agent_sdk_module
from tessera.models.agent import AgentConfig, AgentResult, AgentRole
from tessera.models.ticket import Ticket, TicketStatus
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.anthropic_api import AnthropicApiProvider
from tessera.services.providers.base import ProviderResult
from tests.test_agent_runner import _make_ticket as _ticket_runner
from tests.test_agent_runner import _runner
from tests.test_orchestrator import (
    _make_agent_result,
    _make_orchestrator,
    _make_ticket,
    _noop,
)
from tests.test_providers_base import FakeProvider


def _result_message(session_id: str) -> ResultMessage:
    return ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
        num_turns=1, session_id=session_id, total_cost_usd=None, usage=None,
    )


# ------------------------------------------------------------------
# Protocole et providers
# ------------------------------------------------------------------


def test_provider_result_sans_session_par_defaut() -> None:
    assert ProviderResult(content="x").session_id is None


async def test_le_provider_sdk_rend_l_identifiant_de_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Sans cet identifiant, rien ne peut être repris : c'est le maillon que
    # tout le ticket suspend.
    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        yield AssistantMessage(content=[TextBlock(text="ok")], model="m")
        yield _result_message("sess-42")

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)
    outcome = await ClaudeAgentSDKProvider().complete(
        system="s", user="u", model="claude-sonnet-4-6", max_tokens=1
    )
    assert outcome.session_id == "sess-42"


async def test_le_provider_sdk_passe_la_session_dans_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        captured["resume"] = options.resume
        yield _result_message("sess-43")

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)
    await ClaudeAgentSDKProvider().complete(
        system="s", user="u", model="claude-sonnet-4-6", max_tokens=1,
        session="sess-42",
    )
    assert captured["resume"] == "sess-42"


async def test_le_provider_sdk_sans_session_ne_reprend_rien(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        captured["resume"] = options.resume
        yield _result_message("sess-1")

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)
    await ClaudeAgentSDKProvider().complete(
        system="s", user="u", model="claude-sonnet-4-6", max_tokens=1
    )
    assert captured["resume"] is None


async def test_une_reprise_qui_echoue_retombe_sur_un_appel_complet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Le SDK retrouve une session par `cwd` sur le disque : une session
    # introuvable ne doit pas coûter le run, seulement l'économie espérée.
    tentatives: list[str | None] = []

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        tentatives.append(options.resume)
        if options.resume is not None:
            raise RuntimeError("No conversation found with session ID")
        yield AssistantMessage(content=[TextBlock(text="repris à froid")], model="m")
        yield _result_message("sess-neuve")

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)
    outcome = await ClaudeAgentSDKProvider().complete(
        system="s", user="u", model="claude-sonnet-4-6", max_tokens=1,
        session="sess-perdue",
    )
    assert tentatives == ["sess-perdue", None]
    assert outcome.content == "repris à froid"
    assert outcome.session_id == "sess-neuve"


async def test_un_echec_sans_session_remonte_tel_quel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Le repli ne concerne que la reprise : un appel neuf qui échoue ne se
    # rejoue pas, il aurait le même résultat et coûterait deux fois.
    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        raise RuntimeError("panne")
        yield  # pragma: no cover

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)
    with pytest.raises(RuntimeError, match="panne"):
        await ClaudeAgentSDKProvider().complete(
            system="s", user="u", model="claude-sonnet-4-6", max_tokens=1
        )


async def test_le_provider_api_accepte_une_session_et_la_laisse_a_none() -> None:
    client = MagicMock()
    resp = MagicMock()
    resp.content = [MagicMock(text="r")]
    resp.usage = MagicMock(input_tokens=1, output_tokens=1,
                           cache_creation_input_tokens=0, cache_read_input_tokens=0)
    client.messages.create = AsyncMock(return_value=resp)
    outcome = await AnthropicApiProvider(client).complete(
        system="s", user="u", model="claude-sonnet-4-6", max_tokens=1,
        session="sess-ignoree",
    )
    assert outcome.session_id is None


# ------------------------------------------------------------------
# AgentRunner
# ------------------------------------------------------------------


class _SessionProvider(FakeProvider):
    """A FakeProvider that hands back a session id, like the SDK does."""

    def __init__(self, session_id: str = "sess-1") -> None:
        super().__init__()
        self._session_id = session_id

    async def complete(self, **kwargs: Any) -> ProviderResult:
        result = await super().complete(**kwargs)
        result.session_id = self._session_id
        return result


async def test_le_runner_rend_la_session_du_provider(tmp_path: Path) -> None:
    runner = _runner(tmp_path, _SessionProvider("sess-7"))
    result = await runner.run(
        role=AgentRole.codeur, ticket=_ticket_runner(), project_context="ctx"
    )
    assert result.session_id == "sess-7"


async def test_le_runner_sans_session_ne_transmet_pas_le_parametre(
    tmp_path: Path,
) -> None:
    # Les doubles de provider n'ont pas tous le paramètre : comme `ask_user`,
    # il n'est transmis que s'il y a quelque chose à transmettre.
    provider = FakeProvider()
    runner = _runner(tmp_path, provider)
    await runner.run(role=AgentRole.codeur, ticket=_ticket_runner(), project_context="ctx")
    assert "session" not in provider.calls[0]


async def test_le_runner_en_reprise_transmet_la_session(tmp_path: Path) -> None:
    provider = FakeProvider()
    runner = _runner(tmp_path, provider)
    await runner.run(
        role=AgentRole.codeur, ticket=_ticket_runner(), project_context="retours",
        session="sess-7",
    )
    assert provider.calls[0]["session"] == "sess-7"


async def test_le_prompt_de_reprise_ne_repete_ni_le_ticket_ni_les_adr(
    tmp_path: Path,
) -> None:
    # Tout cela est déjà dans la conversation reprise : le répéter paierait
    # deux fois ce que la reprise existe pour ne payer qu'une.
    provider = FakeProvider()
    runner = _runner(tmp_path, provider)
    ticket = _ticket_runner(body="## Corps unique du ticket\nDétail 12345.")
    await runner.run(
        role=AgentRole.codeur, ticket=ticket,
        project_context="## Retours reviewer précédents\nTour 1: ajoute un test",
        session="sess-7",
    )
    user = provider.calls[0]["user"]
    assert "Corps unique du ticket" not in user
    assert "Contexte projet" not in user
    assert "ajoute un test" in user
    assert "Ta mission" in user


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------


def _fake_run_recording(
    calls: list[dict[str, Any]], session_id: str = "sess-A"
) -> Any:
    """A runner whose reviewer rejects once, then approves."""
    reviews = 0

    async def fake_run(**kwargs: Any) -> AgentResult:
        nonlocal reviews
        calls.append(kwargs)
        role = kwargs["role"]
        if role == AgentRole.reviewer:
            reviews += 1
            verdict = "CHANGES_REQUESTED: manque un test" if reviews == 1 else "APPROVED"
            return _make_agent_result(verdict, AgentRole.reviewer)
        result = _make_agent_result("code", AgentRole.codeur)
        result.session_id = session_id
        return result

    runner = MagicMock()
    runner.run = fake_run
    return runner


def _ticket_service() -> AsyncMock:
    ticket = _make_ticket(body="## Corps du ticket\nUn corps reconnaissable.")
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket
    return svc


async def test_au_tour_2_le_codeur_reprend_la_session_du_tour_1(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    orc = _make_orchestrator(
        tmp_path, runner=_fake_run_recording(calls), ticket_service=_ticket_service(),
        project_context="## Décisions récentes\nADR-999 — décision reconnaissable",
    )
    await orc.run_pipeline("proj", "ticket-001", _noop)

    codeur = [c for c in calls if c["role"] == AgentRole.codeur]
    assert len(codeur) == 2
    assert "session" not in codeur[0]
    assert codeur[1]["session"] == "sess-A"


async def test_le_contexte_du_tour_2_ne_porte_que_les_retours(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    orc = _make_orchestrator(
        tmp_path, runner=_fake_run_recording(calls), ticket_service=_ticket_service(),
        project_context="## Décisions récentes\nADR-999 — décision reconnaissable",
    )
    await orc.run_pipeline("proj", "ticket-001", _noop)

    codeur = [c for c in calls if c["role"] == AgentRole.codeur]
    assert "décision reconnaissable" in codeur[0]["project_context"]
    assert "décision reconnaissable" not in codeur[1]["project_context"]
    assert "manque un test" in codeur[1]["project_context"]


async def test_le_reviewer_garde_un_contexte_complet_a_chaque_tour(tmp_path: Path) -> None:
    # Un regard frais est ce qu'on demande au reviewer : lui, ne reprend rien.
    calls: list[dict[str, Any]] = []
    orc = _make_orchestrator(
        tmp_path, runner=_fake_run_recording(calls), ticket_service=_ticket_service(),
        project_context="## Décisions récentes\nADR-999 — décision reconnaissable",
    )
    await orc.run_pipeline("proj", "ticket-001", _noop)

    reviewer = [c for c in calls if c["role"] == AgentRole.reviewer]
    assert len(reviewer) == 2
    assert all("session" not in c for c in reviewer)
    assert all("décision reconnaissable" in c["project_context"] for c in reviewer)


async def test_un_nouveau_run_repart_sans_session(tmp_path: Path) -> None:
    # La session est celle d'une branche : un autre ticket, une autre branche.
    calls: list[dict[str, Any]] = []
    runner = _fake_run_recording(calls)
    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=_ticket_service())
    await orc.run_pipeline("proj", "ticket-001", _noop)
    await orc.run_pipeline("proj", "ticket-001", _noop)

    premiers = [c for c in calls if c["role"] == AgentRole.codeur and "session" not in c]
    assert len(premiers) == 2


async def test_un_provider_muet_sur_la_session_laisse_le_tour_2_a_froid(
    tmp_path: Path,
) -> None:
    # `anthropic_api` ne rend aucune session : le tour 2 doit rester l'appel
    # complet d'aujourd'hui, pas une reprise de `None`.
    calls: list[dict[str, Any]] = []
    reviews = 0

    async def fake_run(**kwargs: Any) -> AgentResult:
        nonlocal reviews
        calls.append(kwargs)
        if kwargs["role"] == AgentRole.reviewer:
            reviews += 1
            return _make_agent_result(
                "CHANGES_REQUESTED: x" if reviews == 1 else "APPROVED", AgentRole.reviewer
            )
        return _make_agent_result("code", AgentRole.codeur)

    runner = MagicMock()
    runner.run = fake_run
    orc = _make_orchestrator(
        tmp_path, runner=runner, ticket_service=_ticket_service(),
        project_context="## Décisions récentes\nADR-999 — décision reconnaissable",
    )
    await orc.run_pipeline("proj", "ticket-001", _noop)

    codeur = [c for c in calls if c["role"] == AgentRole.codeur]
    assert len(codeur) == 2
    assert "session" not in codeur[1]
    assert "décision reconnaissable" in codeur[1]["project_context"]
