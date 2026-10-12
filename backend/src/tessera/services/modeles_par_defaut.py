"""Default models, defined once — ticket-397.

Utilisés quand un `agents.json` ne déclare pas le modèle d'un rôle, et pour
écrire le manifeste d'un nouveau projet. Production (codeur, architect,
reviewer) sur Sonnet ; jugement et documentation sur Haiku. Décision et
mesures : ticket-397 (audit du 2026-10-12).
"""

MODELE_PRODUCTION = "claude-sonnet-5-5"
MODELE_JUGEMENT = "claude-haiku-4-5"

#: Rôles qui produisent ou relisent du code : ils reçoivent MODELE_PRODUCTION.
ROLES_PRODUCTION = frozenset({"codeur", "architect", "reviewer"})


def modele_par_defaut(role: str) -> str:
    """Default model of a role when its manifest does not declare one."""
    return MODELE_PRODUCTION if role in ROLES_PRODUCTION else MODELE_JUGEMENT
