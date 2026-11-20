"""Which pipeline settings lower a gate — ticket-880.

A gate is what stands between an agent's work and the repository: security
audit, validator, tester, autonomy level, CI before merge, test command.
Lowering one is refused while any run is alive (the caller decides; this module
only names the fields).
"""

from collections.abc import Mapping

# Ordre croissant de confiance donnée au run : monter, c'est abaisser la porte.
_NIVEAUX_AUTONOMIE = ("commit", "pr", "merge")
_COUPE_A_FAUX = ("securite_enabled", "validateur_enabled", "testeur_enabled")


def _rang(niveau: object) -> int:
    """Rank of an autonomy level; an unknown value ranks above all (fail closed)."""
    if isinstance(niveau, str) and niveau in _NIVEAUX_AUTONOMIE:
        return _NIVEAUX_AUTONOMIE.index(niveau)
    return len(_NIVEAUX_AUTONOMIE)


def _commande(valeur: object) -> str:
    return valeur.strip() if isinstance(valeur, str) else ""


def abaisse_une_porte(actuel: Mapping[str, object], demande: Mapping[str, object]) -> list[str]:
    """Return the requested fields that lower a gate, given the current settings.

    `demande` holds only the fields the request sets; a field absent from it
    never lowers anything. A field set to its current value lowers nothing.
    """
    champs = [
        nom
        for nom in _COUPE_A_FAUX
        if nom in demande and demande[nom] is False and actuel.get(nom) is not False
    ]
    if "autonomy" in demande and _rang(demande["autonomy"]) > _rang(actuel.get("autonomy")):
        champs.append("autonomy")
    if demande.get("merge_without_ci") is True and actuel.get("merge_without_ci") is not True:
        champs.append("merge_without_ci")
    if "test_command" in demande and _commande(demande["test_command"]) != _commande(
        actuel.get("test_command")
    ):
        champs.append("test_command")
    return champs
