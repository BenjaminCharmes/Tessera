"""Decision rule and report of the second-review trial (ticket-845, ADR-079).

Pure functions on the corpus, the results and the human review. The outcome is
a recommendation: the adoption, the reserve or the abandon belongs to a human,
in an ADR of its own.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from seconde_revue_corpus import Corpus, Entree
from seconde_revue_lecture import Resultat

# Spec §4 et §5 : des entiers, pas des pourcentages.
MIN_DEFAUTS_EN_PLUS = 3
MAX_FAUX_POSITIFS_EN_PLUS = 2
MAX_DUREE_AJOUTEE_MS = 300_000
MIN_DEFAUTS_SENSIBLES = 2
MAX_FAUX_POSITIFS_SENSIBLES = 1
MIN_APPROBATION_B_POUR_CENT = 80
MAX_EXCLUES_C_POUR_CENT = 25  # strictement sous cette part

DEBUT_CONCLUSION = "<!-- seconde-revue-conclusion:debut -->"
FIN_CONCLUSION = "<!-- seconde-revue-conclusion:fin -->"

_JUGEMENTS = ("confirme", "autre_defaut", "infonde")


@dataclass(frozen=True)
class Mesures:
    """The figures the rule is applied to."""

    valide: bool
    defauts_en_plus: int
    defauts_en_plus_sensibles: int
    faux_positifs_en_plus: int
    faux_positifs_en_plus_sensibles: int
    duree_ajoutee_ms: int
    cout_c_moyen: float
    cout_b_moyen: float


@dataclass(frozen=True)
class Verdict:
    decision: Literal["adopter", "reserver", "abandonner", "non concluant"]
    motif: str


@dataclass(frozen=True)
class Jugement:
    """The human judgement of one remark raised (`relecture.json`)."""

    id: str
    bras: Literal["B", "C"]
    rang: int
    jugement: Literal["confirme", "autre_defaut", "infonde"]


def decision(m: Mesures) -> Verdict:
    """Applies the rule of ADR-079, in order."""
    if not m.valide:
        return Verdict("non concluant", "rejeu non valide : B approuve trop peu ou C exclut trop")
    adopte = (
        m.defauts_en_plus >= MIN_DEFAUTS_EN_PLUS
        and m.faux_positifs_en_plus <= MAX_FAUX_POSITIFS_EN_PLUS
        and m.duree_ajoutee_ms <= MAX_DUREE_AJOUTEE_MS
        and m.cout_c_moyen <= m.cout_b_moyen
    )
    if adopte:
        return Verdict(
            "adopter",
            f"{m.defauts_en_plus} défaut(s) en plus, {m.faux_positifs_en_plus} faux positif(s) "
            f"en plus, {m.duree_ajoutee_ms} ms ajoutées, coût de C au plus celui de B",
        )
    if (
        m.defauts_en_plus_sensibles >= MIN_DEFAUTS_SENSIBLES
        and m.faux_positifs_en_plus_sensibles <= MAX_FAUX_POSITIFS_SENSIBLES
    ):
        return Verdict(
            "reserver",
            f"{m.defauts_en_plus_sensibles} défaut(s) en plus sur les diffs sensibles, "
            f"{m.faux_positifs_en_plus_sensibles} faux positif(s) en plus sur ces diffs",
        )
    return Verdict(
        "abandonner",
        f"{m.defauts_en_plus} défaut(s) en plus dont {m.defauts_en_plus_sensibles} sensible(s), "
        "sous les seuils",
    )


def _par_cle(resultats: Sequence[Resultat], bras: str) -> dict[str, Resultat]:
    return {r.id: r for r in resultats if r.bras == bras}


def _moyenne(valeurs: Sequence[float]) -> float:
    return sum(valeurs) / len(valeurs) if valeurs else 0.0


def _jugements_de_c(relecture: Sequence[Jugement], entree: Entree) -> set[str]:
    return {j.jugement for j in relecture if j.id == entree.id and j.bras == "C"}


def _valide(corpus: Corpus, b: dict[str, Resultat], c: dict[str, Resultat]) -> bool:
    total = len(corpus.entrees)
    if total == 0:
        return False
    approuvees = sum(
        1 for e in corpus.entrees
        if e.id in b and b[e.id].etat == "ok" and b[e.id].leve is False
    )
    exclues = sum(1 for e in corpus.entrees if e.id not in c or c[e.id].etat != "ok")
    return (
        approuvees * 100 >= MIN_APPROBATION_B_POUR_CENT * total
        and exclues * 100 < MAX_EXCLUES_C_POUR_CENT * total
    )


def mesures_depuis(
    corpus: Corpus, resultats: Sequence[Resultat], relecture: Sequence[Jugement]
) -> Mesures:
    """Counts the extra defects and false positives of C over B (spec §4)."""
    b, c = _par_cle(resultats, "B"), _par_cle(resultats, "C")
    defauts = defauts_s = faux = faux_s = 0
    for entree in corpus.entrees:
        rb, rc = b.get(entree.id), c.get(entree.id)
        # Une entrée que C n'a pas jugée, ou que B n'a pas lue, ne se compare pas.
        if rc is None or rc.etat != "ok" or rb is None or rb.etat != "ok":
            continue
        if not rc.leve or rb.leve:
            continue
        jugements = _jugements_de_c(relecture, entree)
        if entree.classe == "defaut" and jugements & {"confirme", "autre_defaut"}:
            defauts += 1
            defauts_s += int(entree.sensible)
        elif entree.classe == "sain" and "infonde" in jugements:
            faux += 1
            faux_s += int(entree.sensible)
    rendus_c = [r for r in c.values() if r.etat == "ok"]
    rendus_b = [r for r in b.values() if r.etat == "ok"]
    return Mesures(
        valide=_valide(corpus, b, c),
        defauts_en_plus=defauts, defauts_en_plus_sensibles=defauts_s,
        faux_positifs_en_plus=faux, faux_positifs_en_plus_sensibles=faux_s,
        duree_ajoutee_ms=round(_moyenne([r.duree_ms for r in rendus_c])),
        cout_c_moyen=_moyenne([r.cout_usd for r in rendus_c]),
        cout_b_moyen=_moyenne([r.cout_usd for r in rendus_b]),
    )


def _ligne_de_bras(nom: str, rendus: Sequence[Resultat], tous: Sequence[Resultat]) -> str:
    leves = sum(1 for r in rendus if r.leve)
    couts = [r.cout_usd for r in rendus] or [0.0]
    durees = [r.duree_ms for r in rendus] or [0]
    return (
        f"| {nom} | {len(tous)} | {len(rendus)} | {leves} | "
        f"{_moyenne(couts):.4f} | {max(couts):.4f} | "
        f"{round(_moyenne(durees))} | {max(durees)} |"
    )


def rapport(
    corpus: Corpus, resultats: Sequence[Resultat], relecture: Sequence[Jugement]
) -> str:
    """The Markdown of `docs/essais/seconde-revue.md`, conclusion block included."""
    m = mesures_depuis(corpus, resultats, relecture)
    verdict = decision(m)
    lignes = [
        "# Essai d'une seconde revue par un autre modèle",
        "",
        f"Corpus : {len(corpus.entrees)} entrées, gel `{corpus.gel_sha256}`.",
        "",
        "## Par bras",
        "",
        "| bras | appels | ok | verdicts levés | coût moyen ($) | coût max ($) "
        "| durée moyenne (ms) | durée max (ms) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nom in ("B", "C"):
        tous = [r for r in resultats if r.bras == nom]
        lignes.append(_ligne_de_bras(nom, [r for r in tous if r.etat == "ok"], tous))
    lignes += [
        "",
        "## Comptes",
        "",
        f"- rejeu valide : {'oui' if m.valide else 'non'}",
        f"- défauts en plus : {m.defauts_en_plus} (dont {m.defauts_en_plus_sensibles} sensibles)",
        f"- faux positifs en plus : {m.faux_positifs_en_plus} "
        f"(dont {m.faux_positifs_en_plus_sensibles} sensibles)",
        f"- durée ajoutée par revue : {m.duree_ajoutee_ms} ms",
        f"- coût moyen : C {m.cout_c_moyen:.4f} $, B {m.cout_b_moyen:.4f} $",
        "",
        "## Conclusion",
        "",
        DEBUT_CONCLUSION,
        f"**Recommandation : {verdict.decision}.** {verdict.motif}.",
        "",
        "C'est une recommandation : l'ADR qui décide appartient à un humain.",
        FIN_CONCLUSION,
        "",
    ]
    return "\n".join(lignes)


def _jugement(brut: Any) -> Jugement:
    if not isinstance(brut, dict) or brut.get("jugement") not in _JUGEMENTS:
        raise ValueError(f"jugement illisible : {brut!r}")
    if brut.get("bras") not in ("B", "C"):
        raise ValueError(f"bras illisible : {brut!r}")
    return Jugement(
        id=str(brut["id"]), bras=cast(Literal["B", "C"], brut["bras"]),
        rang=int(brut["rang"]),
        jugement=cast(Literal["confirme", "autre_defaut", "infonde"], brut["jugement"]),
    )


def lire_relecture(chemin: Path) -> list[Jugement]:
    """Reads `relecture.json`: one judgement per line, or a JSON list. Absent: empty."""
    if not chemin.is_file():
        return []
    texte = chemin.read_text(encoding="utf-8").strip()
    if not texte:
        return []
    if texte.startswith("["):
        brutes = json.loads(texte)
    else:
        brutes = [json.loads(ligne) for ligne in texte.splitlines() if ligne.strip()]
    return [_jugement(b) for b in brutes]
