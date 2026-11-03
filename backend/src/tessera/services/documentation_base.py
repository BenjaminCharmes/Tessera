"""Ce que `documentation` et `documentation_preuve` partagent — ticket-542.

Un refus d'édition et la typographie tolérée y vivent pour que le contrôle de
la preuve puisse les utiliser sans importer le service (import circulaire).
"""


class EditionRefusee(Exception):
    """Une modification proposée ne s'applique pas. Rien n'a été écrit."""


#: Typographie française ramenée à son équivalent ASCII (ticket-402). Chaque
#: caractère devient exactement un caractère : les positions se correspondent.
_TYPO = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "«": '"',
        "»": '"',
        " ": " ",
        " ": " ",
    }
)


def normaliser_typo(texte: str) -> tuple[str, list[int]]:
    """Normalize typographic punctuation and non-breaking spaces.

    Returns the normalized text and, for each of its characters, the position
    of the originating character in ``texte``. The ellipsis is the only
    character that expands to three, hence the position map.
    """
    sortie: list[str] = []
    positions: list[int] = []
    for i, c in enumerate(texte):
        rendu = "..." if c == "…" else c.translate(_TYPO)
        sortie.append(rendu)
        positions.extend([i] * len(rendu))
    return "".join(sortie), positions
