"""Ce que `documentation` et `documentation_preuve` partagent — ticket-542.

Un refus d'édition et la typographie tolérée y vivent pour que le contrôle de
la preuve puisse les utiliser sans importer le service (import circulaire).
"""


class EditionRefusee(Exception):
    """Une modification proposée ne s'applique pas. Rien n'a été écrit.

    ``extrait`` is an optional excerpt of the targeted file, for the corrective
    round only: ``str(exc)`` stays the message alone.
    """

    def __init__(self, message: str, extrait: str = "") -> None:
        super().__init__(message)
        self.extrait = extrait


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


def _titres_markdown(contenu: str) -> str:
    """Extracts Markdown heading lines (starting with #) from file content."""
    return "\n".join(ln for ln in contenu.splitlines() if ln.startswith("#"))
