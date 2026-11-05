"""A unified diff cut into sections — ticket-757, ADR-057.

Une preuve de documentation doit être du code livré, d'un seul tenant. Ce
module découpe un diff en sections (une par bloc `@@`) et dit, pour chacune,
ce qui est livré : lignes ajoutées et lignes de contexte, sans marqueur. Les
lignes `-` ne sont pas du code livré ; les en-têtes de fichier non plus, mais
seulement tant qu'aucun `@@` n'a été lu : dans un bloc, `+++i` est l'ajout de
`++i`.
"""
from dataclasses import dataclass, field

_MARQUEURS = ("+", "-", " ")
_LIVREES = ("+", " ")
_ENTETES_DE_FICHIER = ("+++ ", "--- ")


@dataclass
class SectionDeDiff:
    """The content lines of one hunk, markers kept."""

    lignes: list[str] = field(default_factory=list)

    @property
    def livrees(self) -> list[str]:
        """Added and context lines, without their marker."""
        return [ligne[1:] for ligne in self.lignes if ligne.startswith(_LIVREES)]

    @property
    def avec_marqueurs(self) -> list[str]:
        """Added and context lines, marker kept: the diff as a reader sees it."""
        return [ligne for ligne in self.lignes if ligne.startswith(_LIVREES)]


def _est_un_contenu(ligne: str, dans_un_bloc: bool) -> bool:
    """Whether ``ligne`` is a content line rather than a header or a note."""
    if not ligne.startswith(_MARQUEURS):
        return False
    return dans_un_bloc or not ligne.startswith(_ENTETES_DE_FICHIER)


def sections_du_diff(diff: str) -> list[SectionDeDiff]:
    """Cut ``diff`` into sections: one per `@@` block, one per header-less run."""
    sections: list[SectionDeDiff] = []
    courante: SectionDeDiff | None = None
    dans_un_bloc = False
    for ligne in diff.splitlines():
        if ligne.startswith("diff --git"):
            courante, dans_un_bloc = None, False
        elif ligne.startswith("@@"):
            courante, dans_un_bloc = SectionDeDiff(), True
            sections.append(courante)
        elif _est_un_contenu(ligne, dans_un_bloc):
            if courante is None:
                courante = SectionDeDiff()
                sections.append(courante)
            courante.lignes.append(ligne)
    return sections
