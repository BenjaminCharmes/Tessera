"""Prix par million de tokens par modèle Anthropic.

Mettre à jour ce dict si les tarifs changent sur https://www.anthropic.com/pricing
"""

#: Les modèles que l'application sait tarifer. C'est la liste proposée à
#: l'utilisateur : choisir un modèle hors grille fausserait la ventilation des
#: coûts, qui est justement ce sur quoi on s'appuie pour descendre en gamme
#: (ticket-080).
_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00, "cache_read": 0.30},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00, "cache_read": 0.08},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00, "cache_read": 0.08},
    "claude-opus-4-8": {"input": 15.00, "output": 75.00, "cache_read": 1.50},
    "claude-opus-4-5": {"input": 15.00, "output": 75.00, "cache_read": 1.50},
    "claude-fable-5": {"input": 3.00, "output": 15.00, "cache_read": 0.30},
}

_DEFAULT = {"input": 3.00, "output": 15.00, "cache_read": 0.30}


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
) -> float:
    """Retourne le coût en USD pour un appel LLM donné."""
    pricing = _PRICING.get(model, _DEFAULT)
    cost = (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
        + (cache_read_tokens / 1_000_000) * pricing["cache_read"]
    )
    return round(cost, 6)


def modeles_connus() -> list[str]:
    """Les identifiants de modèles dont le coût est calculable."""
    return sorted(_PRICING)
