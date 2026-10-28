"""Table and spec-block rendering for scripts/mesurer_compression.py (ticket-605)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mesure_calculs import cellule
from mesure_verdict import Mesures, Verdict

MARQUEUR_TABLEAU = "mesure-605"
MARQUEUR_CONCLUSION = "mesure-605-conclusion"
MARQUEUR_USAGE = "mesure-605-usage"
MARQUEUR_DIFF = "mesure-605-diff"

_ENTETE = (
    "| Run | Rôle | Entrée mesurée (tokens) | Après compression (est.) "
    "| Lignes perdues |\n| --- | --- | ---: | ---: | ---: |"
)


@dataclass(frozen=True)
class LigneTableau:
    """One run x role row; ``raison`` explains every `non mesuré` cell."""

    run: str
    role: str
    entree: int | None
    apres: int | None
    perdues: int | None
    raison: str = ""
    cout_entree_usd: float = 0.0
    gain_usd: float = 0.0


def rendre_ligne(ligne: LigneTableau) -> str:
    """Render one row; a missing figure becomes `non mesuré (raison)`."""
    perdues = "—" if ligne.perdues is None else str(ligne.perdues)
    return (
        f"| {ligne.run[:8]} | {ligne.role} | {cellule(ligne.entree, ligne.raison)} "
        f"| {cellule(ligne.apres, ligne.raison)} | {perdues} |"
    )


def rendre_tableau(lignes: list[LigneTableau]) -> str:
    """Render the whole table; an empty list says so instead of an empty body."""
    if not lignes:
        return _ENTETE + "\n| — | — | non mesuré (aucun run donné) | non mesuré | — |"
    return "\n".join([_ENTETE, *(rendre_ligne(ligne) for ligne in lignes)])


@dataclass(frozen=True)
class LigneDiff:
    """The diff of one run alone, before and after compression (estimated tokens)."""

    run: str
    avant: int | None
    apres: int | None
    raison: str = ""

    @property
    def taux(self) -> float | None:
        if self.avant is None or self.apres is None or self.avant <= 0:
            return None
        return max(0, self.avant - self.apres) / self.avant


def rendre_diffs(lignes: list[LigneDiff]) -> str:
    """Render the diff-only table; a missing figure carries its reason."""
    corps = [
        f"| {d.run[:8]} | {cellule(d.avant, d.raison)} | {cellule(d.apres, d.raison)} "
        f"| {'non mesuré' if d.taux is None else f'{d.taux:.1%}'} |"
        for d in lignes
    ]
    entete = (
        "| Run | Diff (tokens est.) | Après compression (est.) | Retiré |\n"
        "| --- | ---: | ---: | ---: |"
    )
    return "\n".join([entete, *corps])


def rendre_conclusion(verdict: Verdict, mesures: Mesures) -> str:
    """The closing line of the spec: decision, motive and the figures behind it."""
    ratio = "non mesuré" if mesures.ratio_texte is None else f"{mesures.ratio_texte:.1%}"
    perdues = "non mesuré" if mesures.lignes_perdues is None else str(mesures.lignes_perdues)
    part = (
        "non mesurée" if mesures.part_entree_codeur is None
        else f"{mesures.part_entree_codeur:.1%}"
    )
    taux = "non mesuré" if mesures.taux_diff is None else f"{mesures.taux_diff:.1%}"
    return (
        f"**Conclusion du ticket-605 : {verdict.decision}.** {verdict.motif}. "
        f"Chiffres : {mesures.runs_mesures} run(s) mesuré(s), gain texte {ratio}, "
        f"taux sur le diff seul {taux}, lignes perdues {perdues}, "
        f"part d'entrée du codeur {part}."
    )


def _bornes(nom: str) -> tuple[str, str]:
    return f"<!-- {nom}:debut -->", f"<!-- {nom}:fin -->"


def remplacer_bloc(texte: str, nom: str, contenu: str) -> str:
    """Replace what sits between the two markers of ``nom``, nothing else.

    Raises ``ValueError`` when a marker is missing: the script never guesses
    where to write inside a spec.
    """
    debut, fin = _bornes(nom)
    i, j = texte.find(debut), texte.find(fin)
    if i < 0 or j < i:
        raise ValueError(f"marqueurs {nom} absents ou inversés")
    return f"{texte[: i + len(debut)]}\n{contenu}\n{texte[j:]}"


def ecrire_blocs(spec: Path, blocs: dict[str, str]) -> None:
    """Rewrite every named block of ``spec``; nothing is written if one fails."""
    texte = spec.read_text(encoding="utf-8")
    for nom, contenu in blocs.items():
        texte = remplacer_bloc(texte, nom, contenu)
    spec.write_text(texte, encoding="utf-8")
