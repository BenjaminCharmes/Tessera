"""Rules judged against the history of the project — tickets 836 to 838 (ADR-078).

Pures : l'historique (médianes, derniers runs) est lu par l'appelant.
"""
import re
from collections.abc import Sequence
from datetime import datetime
from statistics import median

from tessera.services.anomalies.modeles import Anomalie, Etape, RunFini


def mediane_si_assez(echantillon: Sequence[float], minimum: int = 10) -> float | None:
    """Median of the sample, or None below `minimum` values: too few to judge."""
    if len(echantillon) < minimum:
        return None
    return float(median(echantillon))


def etape_longue(
    etape: Etape,
    maintenant: datetime,
    passees_s: Sequence[float],
    *,
    ticket_id: str,
    plancher_s: float = 300.0,
    facteur: float = 3.0,
    minimum: int = 10,
) -> Anomalie | None:
    """An open stage lasting more than `max(facteur x median, plancher_s)`.

    Le plancher évite qu'un audit médian à 20 s n'alerte à 60 s.
    """
    if etape.fin is not None or etape.abandonnee:
        return None
    mediane = mediane_si_assez(passees_s, minimum)
    if mediane is None:
        return None
    seuil = max(facteur * mediane, plancher_s)
    duree = (maintenant - etape.debut).total_seconds()
    if duree <= seuil:
        return None
    return Anomalie(
        regle="etape_longue",
        cle=f"etape_longue:{etape.nom}:{etape.debut.isoformat()}",
        ticket_id=ticket_id,
        message=(
            f"L'étape {etape.nom} dure depuis {int(duree // 60)} min, "
            f"pour une médiane de {int(mediane // 60)} min."
        ),
        mesure=duree,
        seuil=seuil,
        unite="s",
        etape=etape.nom,
        agent=etape.agent,
    )


def cout_median(
    cout_usd: float,
    passes_usd: Sequence[float],
    *,
    ticket_id: str,
    ligne_id: str,
    plancher_usd: float = 0.5,
    facteur: float = 3.0,
    minimum: int = 10,
) -> Anomalie | None:
    """A ticket costing more than `max(facteur x median, plancher_usd)`."""
    mediane = mediane_si_assez(passes_usd, minimum)
    if mediane is None:
        return None
    seuil = max(facteur * mediane, plancher_usd)
    if cout_usd <= seuil:
        return None
    return Anomalie(
        regle="cout_anormal",
        cle=f"cout_median:{ligne_id}",
        ticket_id=ticket_id,
        message=(
            f"Ce ticket a déjà coûté {cout_usd:.2f} USD, "
            f"pour une médiane de {mediane:.2f} USD sur le projet."
        ),
        mesure=cout_usd,
        seuil=seuil,
        unite="usd",
    )


def cout_budget(
    cumul_usd: float,
    budget_usd: float,
    *,
    ticket_id: str,
    run_id: str,
    part: float = 0.8,
) -> Anomalie | None:
    """An autonomous run at `part` of its budget or more (ADR-020 only acts between tickets)."""
    if budget_usd <= 0 or cumul_usd < part * budget_usd:
        return None
    return Anomalie(
        regle="cout_anormal",
        cle=f"cout_budget:{run_id}",
        ticket_id=ticket_id,
        message=(
            f"Le run autonome a dépensé {cumul_usd:.2f} USD "
            f"sur un budget de {budget_usd:.2f} USD."
        ),
        mesure=cumul_usd / budget_usd * 100,
        seuil=part * 100,
        unite="pourcent",
    )


def cout_anormal(
    cout_usd: float,
    passes_usd: Sequence[float],
    *,
    ticket_id: str,
    ligne_id: str = "",
    run_id: str = "",
    plancher_usd: float = 0.5,
    cumul_usd: float | None = None,
    budget_usd: float | None = None,
    facteur: float = 3.0,
    minimum: int = 10,
    part: float = 0.8,
) -> Anomalie | None:
    """The cost rule: the median rule first, then the budget rule (autonomous runs only).

    Le détecteur appelle `cout_median` et `cout_budget` séparément pour signaler
    les deux quand les deux valent ; ici, le premier constat l'emporte.
    """
    constat = cout_median(
        cout_usd, passes_usd, ticket_id=ticket_id, ligne_id=ligne_id,
        plancher_usd=plancher_usd, facteur=facteur, minimum=minimum,
    )
    if constat is not None or cumul_usd is None or budget_usd is None:
        return constat
    return cout_budget(cumul_usd, budget_usd, ticket_id=ticket_id, run_id=run_id, part=part)


# Une cause se dit toujours pareil ; seuls varient un nombre, un chemin, un
# identifiant ou un nom entre guillemets. La signature efface ce qui varie.
# L'apostrophe n'ouvre une citation qu'en début de mot : « d'un » reste un mot.
_CITATION = re.compile(r"(?<!\w)'[^']*'(?!\w)|\"[^\"]*\"|«[^»]*»|‘[^’]*’|“[^”]*”")
_URL = re.compile(r"https?://\S+")
_CHEMIN = re.compile(r"(?<!\w)[a-z]:[\\/]\S*|(?<!\w)(?:/[\w.\-]+){2,}")
_HEXA = re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")
_NOMBRE = re.compile(r"\d+(?:[.,]\d+)?")
SIGNATURE_MAX = 120


def signature_d_arret(arret: str | None) -> str | None:
    """The comparable form of a block cause: its first line with the variable parts erased.

    Minuscules ; chaînes entre guillemets, URL, chemins, hexadécimaux et nombres
    remplacés par un marqueur ; coupée à 120 caractères. `None` si `arret` est vide.
    """
    if arret is None or not arret.strip():
        return None
    ligne = arret.strip().splitlines()[0].lower()
    for motif, marqueur in (
        (_CITATION, "<texte>"), (_URL, "<url>"), (_CHEMIN, "<chemin>"),
        (_HEXA, "<hexa>"), (_NOMBRE, "<n>"),
    ):
        ligne = motif.sub(marqueur, ligne)
    return " ".join(ligne.split())[:SIGNATURE_MAX]


def blocages_identiques(derniers: Sequence[RunFini]) -> Anomalie | None:
    """The two latest finished runs of the ticket are blocked for the same cause.

    `derniers` va du plus récent au plus ancien ; seuls les deux premiers comptent.
    """
    if len(derniers) < 2:
        return None
    recent, precedent = derniers[0], derniers[1]
    if recent.final_status != "blocked" or precedent.final_status != "blocked":
        return None
    signature = signature_d_arret(recent.arret)
    if signature is None or signature != signature_d_arret(precedent.arret):
        return None
    return Anomalie(
        regle="blocages_identiques",
        cle=f"blocages:{recent.id}",
        ticket_id=recent.ticket_id,
        message="Les deux derniers runs de ce ticket se sont bloqués pour la même cause.",
        mesure=2.0,
        seuil=2.0,
        unite="runs",
    )
