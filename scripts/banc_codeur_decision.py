"""Decision rule and report of the coder bench (ticket-1056, ADR-095, design §6).

Pure functions on the corpus and the results. The outcome is a recommendation:
the adoption of an arm, or keeping A, belongs to a human, in an ADR of its own.
Nothing here imports `tessera`.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from banc_codeur_cellule import Resultat
from banc_codeur_corpus import Corpus

# Conception §6 : des entiers, pas des pourcentages.
MIN_REPRODUITES_A = 7  # sur 9 entrées (14 sur 20 à l'ADR, proportion gardée, ticket-1058)
MAX_EXCLUES_PAR_BRAS = 2
MIN_ECART_T1 = 2
MAX_COUT_POUR_CENT = 60  # 40 % de coût en moins
MAX_DUREE_FACTEUR = 2
MIN_DIVERGENCES_A_A2 = 3  # sur les 5 entrées rejouées
TOLERANCE_T1_MOINS_CHER = 1

BRAS_REFERENCE = "A"
BRAS_BRUIT = "A2"

DEBUT_CONCLUSION = "<!-- banc-codeur-conclusion:debut -->"
FIN_CONCLUSION = "<!-- banc-codeur-conclusion:fin -->"


@dataclass(frozen=True)
class MesureBras:
    """The figures of one arm, on the entries common to every compared arm."""

    id: str
    cellules: int
    retenues: int
    t1: int
    v: int
    tours_moyens: float
    cout_moyen: float
    cout_max: float
    jetons: tuple[int, int, int]
    duree_moyenne_ms: int
    duree_max_ms: int
    reference_verts: int


@dataclass(frozen=True)
class Mesures:
    non_concluant: str | None
    a: MesureBras
    candidats: tuple[MesureBras, ...]
    bruit: str


@dataclass(frozen=True)
class Verdict:
    decision: Literal["non concluant", "meilleur", "moins cher", "garder A"]
    bras: str | None
    motif: str


def _moyenne(valeurs: Sequence[float]) -> float:
    return sum(valeurs) / len(valeurs) if valeurs else 0.0


def _mesure_bras(bras: str, tous: Sequence[Resultat], retenues: Sequence[Resultat]) -> MesureBras:
    couts = [r.cout_usd for r in retenues]
    durees = [r.duree_ms["total"] for r in retenues]
    return MesureBras(
        id=bras, cellules=len(tous), retenues=len(retenues),
        t1=sum(1 for r in retenues if r.approuve_t1),
        v=sum(1 for r in retenues if r.tests_verts),
        tours_moyens=_moyenne([r.tours for r in retenues if r.tours is not None]),
        cout_moyen=_moyenne(couts), cout_max=max(couts, default=0.0),
        jetons=(
            sum(r.jetons["entree"] for r in retenues),
            sum(r.jetons["sortie"] for r in retenues),
            sum(r.jetons["cache"] for r in retenues),
        ),
        duree_moyenne_ms=round(_moyenne(durees)), duree_max_ms=max(durees, default=0),
        reference_verts=sum(1 for r in retenues if r.tests_reference_verts),
    )


def _cellules(corpus: Corpus, resultats: Sequence[Resultat]) -> dict[str, dict[str, Resultat]]:
    """Cells by arm then entry; an `echec_env` entry leaves every arm first."""
    ids = {e.id for e in corpus.entrees if not e.pilote}
    for r in resultats:
        if r.gel_sha256 != corpus.gel_sha256:
            raise ValueError(f"{r.id}/{r.bras} : gel_sha256 différent de celui du corpus")
    sortis = {r.id for r in resultats if r.etat == "echec_env"}
    par_bras: dict[str, dict[str, Resultat]] = {}
    for r in resultats:
        if r.id in ids and r.id not in sortis:
            par_bras.setdefault(r.bras, {})[r.id] = r
    return par_bras


def _bruit(a: dict[str, Resultat], a2: dict[str, Resultat]) -> tuple[int, int]:
    """Entries replayed in A and A2 whose first-round approval differs, and how many."""
    communes = [i for i in a2 if i in a and a[i].etat == "ok" and a2[i].etat == "ok"]
    return sum(1 for i in communes if a[i].approuve_t1 != a2[i].approuve_t1), len(communes)


def _non_concluant(
    ids: Sequence[str], par_bras: dict[str, dict[str, Resultat]], divergences: int
) -> str | None:
    cellules_a = par_bras.get(BRAS_REFERENCE, {})
    reproduites = sum(1 for r in cellules_a.values() if r.etat == "ok" and r.approuve_final)
    if reproduites < MIN_REPRODUITES_A:
        return f"A reproduit {reproduites} entrée(s), moins de {MIN_REPRODUITES_A}"
    for bras in sorted(par_bras):
        if bras == BRAS_BRUIT:
            continue
        exclues = sum(1 for i in ids if i not in par_bras[bras] or par_bras[bras][i].etat != "ok")
        if exclues > MAX_EXCLUES_PAR_BRAS:
            return f"le bras {bras} exclut {exclues} cellule(s), plus de {MAX_EXCLUES_PAR_BRAS}"
    if divergences >= MIN_DIVERGENCES_A_A2:
        return f"A et A2 divergent sur {divergences} entrée(s), seuil {MIN_DIVERGENCES_A_A2}"
    return None


def mesures_depuis(corpus: Corpus, resultats: Sequence[Resultat]) -> Mesures:
    """Pairs the arms on the same entries, then applies the validity checks."""
    par_bras = _cellules(corpus, resultats)
    ids = sorted({e.id for e in corpus.entrees if not e.pilote} - {
        r.id for r in resultats if r.etat == "echec_env"})
    principaux = [b for b in sorted(par_bras) if b != BRAS_BRUIT]
    communs = [
        i for i in ids
        if all(i in par_bras[b] and par_bras[b][i].etat == "ok" for b in principaux)
    ]
    mesures = {
        b: _mesure_bras(b, list(par_bras[b].values()), [par_bras[b][i] for i in communs])
        for b in principaux
    }
    a2 = par_bras.get(BRAS_BRUIT, {})
    divergences, rejouees = _bruit(par_bras.get(BRAS_REFERENCE, {}), a2)
    motif = None if BRAS_REFERENCE in mesures else "le bras A est absent"
    if motif is None:
        motif = _non_concluant(ids, par_bras, divergences)
    vide = _mesure_bras(BRAS_REFERENCE, [], [])
    return Mesures(
        non_concluant=motif, a=mesures.get(BRAS_REFERENCE, vide),
        candidats=tuple(m for b, m in mesures.items() if b != BRAS_REFERENCE),
        bruit=f"{divergences} divergence(s) A/A2 sur {rejouees} entrée(s) rejouée(s)",
    )


def _meilleur(a: MesureBras, x: MesureBras) -> bool:
    return (
        x.t1 - a.t1 >= MIN_ECART_T1 and x.v >= a.v
        and x.duree_moyenne_ms <= MAX_DUREE_FACTEUR * a.duree_moyenne_ms
    )


def _moins_cher(a: MesureBras, x: MesureBras) -> bool:
    return (
        x.t1 >= a.t1 - TOLERANCE_T1_MOINS_CHER
        and x.cout_moyen * 100 <= MAX_COUT_POUR_CENT * a.cout_moyen
    )


def decision(m: Mesures) -> Verdict:
    """Applies the rule of ADR-095, in order: inconclusive, better, cheaper, keep A."""
    if m.non_concluant is not None:
        return Verdict("non concluant", None, m.non_concluant)
    # Plus grand T1, puis le moins cher, puis l'identifiant : un ordre total.
    ordre = sorted(m.candidats, key=lambda x: (-x.t1, x.cout_moyen, x.id))
    for x in (x for x in ordre if _meilleur(m.a, x)):
        return Verdict("meilleur", x.id, f"T1 {x.t1} contre {m.a.t1} pour A, tests verts {x.v} contre {m.a.v}")
    for x in sorted(m.candidats, key=lambda x: (x.cout_moyen, -x.t1, x.id)):
        if _moins_cher(m.a, x):
            return Verdict("moins cher", x.id, f"T1 {x.t1} contre {m.a.t1}, coût moyen {x.cout_moyen:.4f} $ contre {m.a.cout_moyen:.4f} $")
    return Verdict("garder A", None, "aucun bras ne passe un seuil")


def _ligne(x: MesureBras) -> str:
    e, s, c = x.jetons
    return (
        f"| {x.id} | {x.cellules} | {x.retenues} | {x.t1} | {x.v} | {x.tours_moyens:.2f} "
        f"| {x.cout_moyen:.4f} | {x.cout_max:.4f} | {e}/{s}/{c} "
        f"| {x.duree_moyenne_ms} | {x.duree_max_ms} | {x.reference_verts} |"
    )


def rapport(corpus: Corpus, resultats: Sequence[Resultat]) -> str:
    """The Markdown of `docs/essais/banc-codeur.md`, conclusion block included."""
    m = mesures_depuis(corpus, resultats)
    verdict = decision(m)
    cible = f" : {verdict.bras}" if verdict.bras else ""
    lignes = [
        "# Banc d'essai du codeur", "",
        f"Corpus : {len(corpus.entrees)} entrées, gel `{corpus.gel_sha256}`.", "",
        "## Par bras", "",
        "Chaque bras se lit sur les mêmes entrées (appariées) ; `tests de référence verts` "
        "est indicatif et n'entre dans aucune décision.", "",
        "| bras | cellules | retenues | T1 | V | tours moyens | coût moyen ($) | coût max ($) "
        "| jetons (entrée/sortie/cache) | durée moyenne (ms) | durée max (ms) "
        "| tests de référence verts |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
        *[_ligne(x) for x in (m.a, *m.candidats)],
        "", "## Bruit", "",
        f"{m.bruit}. Le seuil repose sur 5 entrées : il ne détecte qu'un bruit grossier.", "",
        "## Conclusion", "", DEBUT_CONCLUSION,
        f"**Recommandation : {verdict.decision}{cible}.** {verdict.motif}.", "",
        "C'est une recommandation : l'ADR qui décide appartient à un humain.",
        FIN_CONCLUSION, "",
    ]
    return "\n".join(lignes)


def ecrire_rapport(corpus: Corpus, resultats: Sequence[Resultat], chemin: Path) -> None:
    """Writes the report with `\\n` endings, so a rerun is identical byte for byte."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(rapport(corpus, resultats).encode("utf-8"))
