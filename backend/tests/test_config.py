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


def test_ide_prompts_dir_par_defaut_pointe_sur_des_prompts_existants() -> None:
    # Le défaut était `Path("agents") / "prompts"`, relatif au cwd du process.
    # `make dev` lance depuis `backend/`, où `agents/` n'existe pas : tous les
    # agents tournaient sans leur system prompt, en dégradant silencieusement
    # (un simple WARNING `prompt_file_missing`). Le défaut doit être ancré sur
    # la racine du dépôt, pas sur le répertoire de lancement.
    prompts_dir = Settings(_env_file=None).ide_prompts_dir

    assert prompts_dir.is_absolute()
    assert prompts_dir.is_dir(), f"{prompts_dir} n'existe pas"
    assert (prompts_dir / "codeur.md").is_file()
    assert (prompts_dir / "planificateur.md").is_file()
