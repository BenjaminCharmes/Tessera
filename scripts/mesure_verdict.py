"""The reopening threshold of the spec (section 4), as a function (ticket-605)."""
from __future__ import annotations

from dataclasses import dataclass

SEUIL_TEXTE = 0.15
SEUIL_PROXY = 0.25


@dataclass(frozen=True)
class Mesures:
    """The figures the threshold of section 4 is applied to."""

    runs_mesures: int
    ratio_texte: float | None
    lignes_perdues: int | None
    part_entree_codeur: float | None
    # Meilleur taux de compression du diff seul, sur les runs rejoués : un
    # plafond du gain réel du chemin texte, qui n'exige pas `agent_calls`.
    taux_diff: float | None = None


@dataclass(frozen=True)
class Verdict:
    decision: str
    motif: str


def _chemin_texte(m: Mesures) -> tuple[bool, bool, str]:
    """Return ``(ouvert, tranche, motif)`` for the text path.

    ``tranche`` is True when a figure settles it, open or closed. A diff
    compressed by less than the threshold caps the real saving below it, since
    the text removed cannot exceed that share of the text sent.
    """
    perdues = m.lignes_perdues
    if perdues is not None and perdues > 0:
        return False, True, f"{perdues} ligne(s) perdue(s) ferment le chemin texte"
    if m.taux_diff is not None and m.taux_diff < SEUIL_TEXTE:
        return False, True, (
            f"headroom retire au plus {m.taux_diff:.1%} du diff, sous {SEUIL_TEXTE:.0%} : "
            "plafond du gain du chemin texte"
        )
    if m.ratio_texte is None or perdues is None:
        return False, False, "chemin texte non mesuré (sortie de test ou headroom manquant)"
    return (
        m.ratio_texte >= SEUIL_TEXTE, True,
        f"gain texte {m.ratio_texte:.1%} pour un seuil de {SEUIL_TEXTE:.0%}",
    )


def verdict(m: Mesures) -> Verdict:
    """Apply section 4: adopt, defer or drop, with the figures that decide."""
    ouvert, tranche, bloc = _chemin_texte(m)
    if m.runs_mesures < 2:
        return Verdict("reporter", f"{m.runs_mesures} run mesuré sur 2 requis ; {bloc}")
    if ouvert:
        return Verdict("adopter", f"{bloc} et zéro ligne perdue : le chemin texte rouvre")
    part = m.part_entree_codeur
    if part is not None and part >= SEUIL_PROXY:
        return Verdict(
            "reporter",
            f"{bloc} ; entrée du codeur {part:.1%} (seuil {SEUIL_PROXY:.0%}), "
            "proxy conditionné au spike 621",
        )
    if part is not None and tranche:
        return Verdict("écarter", f"{bloc} ; entrée du codeur {part:.1%} sous {SEUIL_PROXY:.0%}")
    return Verdict("reporter", f"{bloc} ; part d'entrée du codeur non mesurée")
