"""Default models, defined once — ticket-397.

Utilisés quand un `agents.json` ne déclare pas le modèle d'un rôle, et pour
écrire le manifeste d'un nouveau projet. Production (codeur, architect,
reviewer) et documentation (doc-technique, doc-fonctionnelle, ADR-057) sur
Sonnet ; jugement (sécurité, validateur) sur Haiku. Décision et mesures :
ticket-397 (audit du 2026-10-12).
"""

MODELE_PRODUCTION = "claude-sonnet-5-5"
MODELE_JUGEMENT = "claude-haiku-4-5"

#: Rôles qui produisent ou relisent du code : ils reçoivent MODELE_PRODUCTION.
ROLES_PRODUCTION = frozenset({"codeur", "architect", "reviewer"})

#: Rôles de documentation : ils reçoivent aussi MODELE_PRODUCTION (ADR-057).
ROLES_REDACTION = frozenset({"doc-technique", "doc-fonctionnelle"})


def modele_par_defaut(role: str) -> str:
    """Default model of a role when its manifest does not declare one."""
    if role in ROLES_PRODUCTION or role in ROLES_REDACTION:
        return MODELE_PRODUCTION
    return MODELE_JUGEMENT
