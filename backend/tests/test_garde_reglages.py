"""The Bash guard refuses network commands that name the settings route (ticket-809)."""
import logging
from pathlib import Path
from typing import Any, cast

import pytest
from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

from tessera.services.providers.garde_jetons import hook_refus_env_tessera
from tessera.services.providers.garde_reglages import REGLAGES_REFUS

_ROUTE = "http://127.0.0.1:8100/api/v1/reglages/run_max_budget_usd"


async def _sortie(tmp_path: Path, outil: str, entrees: dict[str, Any]) -> HookJSONOutput:
    env = tmp_path / ".env"
    env.write_text("X=1\n", encoding="utf-8")
    projet = tmp_path / "projects" / "client"
    projet.mkdir(parents=True, exist_ok=True)
    hook = hook_refus_env_tessera(projet, env_file=env)
    entree = cast(HookInput, {"tool_name": outil, "tool_input": entrees})
    return await hook(entree, None, cast(HookContext, None))


async def _refuse(tmp_path: Path, commande: str) -> bool:
    sortie = cast(dict[str, Any], await _sortie(tmp_path, "Bash", {"command": commande}))
    decision = sortie.get("hookSpecificOutput", {})
    return bool(
        decision.get("permissionDecision") == "deny"
        and decision.get("permissionDecisionReason") == REGLAGES_REFUS
    )


async def test_refuses_curl_put_on_the_settings_route(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, f"curl -X PUT -d '{{\"valeur\": 50}}' {_ROUTE}")
    assert await _refuse(tmp_path, f"C:/outils/CURL.exe {_ROUTE}")


async def test_refuses_wget(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, f"wget -O- {_ROUTE}")


async def test_refuses_invoke_webrequest(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, f"Invoke-WebRequest -Method Put {_ROUTE}")
    assert await _refuse(tmp_path, f"iwr {_ROUTE}")


async def test_refuses_invoke_restmethod(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, f"Invoke-RestMethod -Method Delete {_ROUTE}")
    assert await _refuse(tmp_path, f"irm {_ROUTE}")


async def test_refuses_httpie(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, f"http PUT {_ROUTE} valeur:=50")


async def test_refuses_python_dash_c_with_urllib(tmp_path: Path) -> None:
    code = f"import urllib.request as u; u.urlopen('{_ROUTE}')"
    assert await _refuse(tmp_path, f'python -c "{code}"')
    assert await _refuse(tmp_path, f'python3 -c "{code}"')
    assert await _refuse(tmp_path, f'uv run python -c "{code}"')


async def test_refuses_after_a_separator(tmp_path: Path) -> None:
    assert await _refuse(tmp_path, f"echo x; curl -X PUT {_ROUTE}")
    assert await _refuse(tmp_path, f"cd . && curl {_ROUTE}")


async def test_allows_curl_on_another_route(tmp_path: Path) -> None:
    assert not await _refuse(tmp_path, "curl http://127.0.0.1:8100/api/v1/projects")


async def test_allows_grep_for_the_settings_route(tmp_path: Path) -> None:
    assert not await _refuse(tmp_path, "grep -rn /api/v1/reglages backend/src")
    assert not await _refuse(tmp_path, "rg api/v1/reglages")


async def test_allows_uv_run_pytest_on_the_settings_tests(tmp_path: Path) -> None:
    assert not await _refuse(tmp_path, "uv run pytest backend/tests/test_routes_reglages.py")


async def test_allows_read_and_glob_that_cite_the_route(tmp_path: Path) -> None:
    assert await _sortie(tmp_path, "Read", {"file_path": "docs/api/v1/reglages.md"}) == {}
    assert await _sortie(tmp_path, "Glob", {"pattern": "**/api/v1/reglages*"}) == {}


def test_refusal_message_states_the_ceiling() -> None:
    assert "réservée à l'interface" in REGLAGES_REFUS
    assert "lexical" in REGLAGES_REFUS
    assert "pas une évasion" in REGLAGES_REFUS
    assert "bornes" in REGLAGES_REFUS


async def test_refusal_log_holds_the_tool_name_only(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        assert await _refuse(tmp_path, f"curl -X PUT {_ROUTE}")
    records = [r for r in caplog.records if r.getMessage() == "route_reglages_refusee"]
    assert len(records) == 1
    assert getattr(records[0], "outil") == "Bash"
    assert "127.0.0.1" not in str(records[0].__dict__)
    assert "curl" not in str(records[0].__dict__)
