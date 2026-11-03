"""Ce que le garde-fou a refusé pendant un tour — ticket-476.

Le refus d'une écriture (hors périmètre, chemin protégé, interpréteur) revient
au codeur, qui l'écrit dans son rapport. Mais le reviewer et le validateur ne
voient que le diff : ils constatent que la modification manque et la
redemandent, à chaque tour, pour un fichier que le pipeline ne laissera jamais
écrire. Le journal transporte le refus jusqu'à eux.

Un journal par orchestrateur, donc par requête (ADR-008) : il n'a pas à
survivre au run. Le pipeline le vide avant l'appel du codeur et le lit après,
ce qui borne son contenu au tour.
"""
from dataclasses import dataclass

#: Le titre sous lequel reviewer et validateur lisent les refus.
TITRE_REFUS = "Écritures refusées par le garde-fou pendant ce tour"

#: La consigne qui suit la liste.
_CONSIGNE_REFUS = (
    "Ne redemande pas une écriture que le pipeline interdit : elle ne sera "
    "pas faite aux tours suivants non plus. Une modification de ce genre est "
    "à faire à la main, et ne compte pas comme un manque du code produit."
)


@dataclass(frozen=True)
class Refus:
    """One refused write: the path the agent targeted and why it was refused."""

    chemin: str
    raison: str


class JournalDesRefus:
    """Collects the refusals of the write guard, without duplicates."""

    def __init__(self) -> None:
        self._refus: list[Refus] = []

    def noter(self, chemin: str, raison: str) -> None:
        """Record a refusal; the same path and reason twice counts once."""
        refus = Refus(chemin=chemin, raison=raison)
        if refus not in self._refus:
            self._refus.append(refus)

    def vider(self) -> list[Refus]:
        """Return what was recorded and start again from empty."""
        refus, self._refus = self._refus, []
        return refus


def section_refus(refus: list[Refus]) -> str:
    """The section handed to the reviewer and the validator, empty if no refusal."""
    if not refus:
        return ""
    lignes = "\n".join(f"- `{r.chemin}` — {r.raison}" for r in refus)
    return f"\n\n## {TITRE_REFUS}\n{lignes}\n\n{_CONSIGNE_REFUS}\n"


def refus_du_tour(orch: object) -> str:
    """Drain the orchestrator's journal into a section; empty without a journal.

    `orch` est typé `object` parce que les étapes du pipeline sont testées avec
    des orchestrateurs minimaux, qui n'ont pas de journal.
    """
    journal = getattr(orch, "_journal_refus", None)
    if not isinstance(journal, JournalDesRefus):
        return ""
    return section_refus(journal.vider())
