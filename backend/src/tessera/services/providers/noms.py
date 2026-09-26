"""The provider names a manifest may declare, and what a provider may raise.

Ce module n'importe rien : `models/agent.py` doit pouvoir le lire sans tirer
les SDK derrière lui.
"""

#: Les valeurs acceptées pour `provider` dans `agents.json` (ticket-188).
PROVIDERS_CONNUS: tuple[str, ...] = ("agent_sdk", "anthropic_api")

#: Ceux dont le modèle doit être dans la grille tarifaire : le coût d'un
#: appel s'y calcule depuis les tokens (ticket-080). Un provider hors de
#: cette liste rapporte son coût lui-même, ou n'en a pas.
PROVIDERS_ANTHROPIC: frozenset[str] = frozenset({"agent_sdk", "anthropic_api"})


class ProviderInconnu(ValueError):
    """`agents.json` nomme un provider que l'application ne sait pas construire."""


class ProviderIndisponible(RuntimeError):
    """Le provider ne peut pas répondre : connexion refusée, délai dépassé,
    modèle absent. C'est la seule condition qui déclenche un repli — une
    réponse illisible n'en est pas une, ADR-039 la traite en échouant fermé.
    """
