import pytest

from vibe_ide.config import Settings


def test_settings_boot_sans_cle_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """The backend must boot without ANTHROPIC_API_KEY (subscription usage)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert Settings(_env_file=None).anthropic_api_key == ""


def test_settings_provider_par_defaut() -> None:
    assert Settings(_env_file=None).llm_provider == "agent_sdk"


def test_settings_llm_max_turns_par_defaut() -> None:
    assert Settings(_env_file=None).llm_max_turns == 30


def test_settings_llm_max_budget_usd_par_defaut_non_none() -> None:
    """Regression — ticket-044 review, finding 1: the budget guardrail must
    have a real, non-None default in production, not just be configurable."""
    assert Settings(_env_file=None).llm_max_budget_usd == 1.0


def test_settings_llm_max_turns_surchargeable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MAX_TURNS", "10")
    assert Settings(_env_file=None).llm_max_turns == 10


def test_settings_llm_max_budget_usd_surchargeable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MAX_BUDGET_USD", "2.5")
    assert Settings(_env_file=None).llm_max_budget_usd == 2.5
