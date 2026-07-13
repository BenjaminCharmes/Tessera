import pytest

from vibe_ide.services.cost_calculator import calculate_cost


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
