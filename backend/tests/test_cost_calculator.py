import pytest

import tessera.services.agent_creator as agent_creator
import tessera.services.agent_runner as agent_runner
import tessera.services.chat_service as chat_service
import tessera.services.planner as planner
import tessera.services.project_analyzer as project_analyzer
import tessera.services.project_creator as project_creator
from tessera.services.cost_calculator import DEFAULT_MODEL, calculate_cost, modeles_connus


def test_sonnet_cost() -> None:
    cost = calculate_cost("claude-sonnet-4-6", input_tokens=1_000_000, output_tokens=0, cache_read_tokens=0)
    assert cost == pytest.approx(3.0)


def test_output_tokens_more_expensive() -> None:
    input_cost = calculate_cost("claude-sonnet-4-6", 1_000_000, 0, 0)
    output_cost = calculate_cost("claude-sonnet-4-6", 0, 1_000_000, 0)
    assert output_cost > input_cost


def test_cache_read_cheaper_than_input() -> None:
    input_cost = calculate_cost("claude-sonnet-4-6", 1_000_000, 0, 0)
    cache_cost = calculate_cost("claude-sonnet-4-6", 0, 0, 1_000_000)
    assert cache_cost < input_cost


def test_haiku_cheaper_than_sonnet() -> None:
    sonnet = calculate_cost("claude-sonnet-4-6", 1_000, 500, 0)
    haiku = calculate_cost("claude-haiku-4-5", 1_000, 500, 0)
    assert haiku < sonnet


def test_unknown_model_uses_default() -> None:
    cost_known = calculate_cost("claude-sonnet-4-6", 1_000, 500, 100)
    cost_unknown = calculate_cost("claude-unknown-model", 1_000, 500, 100)
    assert cost_unknown == cost_known


def test_zero_tokens_zero_cost() -> None:
    assert calculate_cost("claude-sonnet-4-6", 0, 0, 0) == 0.0


def test_combined_cost() -> None:
    # 1M input @ $3 + 1M output @ $15 + 1M cache_read @ $0.30 = $18.30
    cost = calculate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000, 1_000_000)
    assert cost == pytest.approx(18.30)


# --- Critères d'acceptation ticket-312 ---


def test_sonnet_5_5_cost() -> None:
    # 1M input @ $2 + 1M output @ $10 = $12.00
    cost = calculate_cost("claude-sonnet-5-5", 1_000_000, 1_000_000, 0)
    assert cost == pytest.approx(12.00)


def test_nouveaux_modeles_dans_la_liste() -> None:
    connus = modeles_connus()
    assert "claude-fable-5-1" in connus
    assert "claude-opus-5-5" in connus
    assert "claude-sonnet-5-5" in connus
    assert "claude-haiku-4-5" in connus


def test_tarif_corrige_fable_5() -> None:
    # claude-fable-5 était à 3$/15$ — corrigé à 10$/50$
    cost_input = calculate_cost("claude-fable-5", 1_000_000, 0, 0)
    cost_output = calculate_cost("claude-fable-5", 0, 1_000_000, 0)
    assert cost_input == pytest.approx(10.00)
    assert cost_output == pytest.approx(50.00)


def test_modele_inconnu_utilise_tarif_defaut_sans_exception() -> None:
    # Ne doit pas lever, et doit rendre une valeur positive
    cost = calculate_cost("claude-modele-inexistant", 1_000_000, 1_000_000, 0)
    assert cost > 0


def test_default_model_est_sonnet_5_5() -> None:
    assert DEFAULT_MODEL == "claude-sonnet-5-5"


def test_six_services_partagent_le_meme_default_model() -> None:
    # Chaque service doit utiliser DEFAULT_MODEL de cost_calculator
    assert agent_runner._DEFAULT_MODEL == DEFAULT_MODEL
    assert agent_creator._DEFAULT_MODEL == DEFAULT_MODEL
    assert planner._DEFAULT_MODEL == DEFAULT_MODEL
    assert project_analyzer._DEFAULT_MODEL == DEFAULT_MODEL
    assert project_creator._DEFAULT_MODEL == DEFAULT_MODEL
    assert chat_service._DEFAULT_MODEL == DEFAULT_MODEL
