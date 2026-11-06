"""The deterministic guards of the supervisor's triage — ticket-855, ADR-080.

Pure functions: no model call, no write, no I/O. The model proposes a `PlanTri`
(title, type, priority, criteria, dependencies); the code checks every field
here and refuses the whole plan on the first doubt, so the ticket stays raw and
the case goes to « À toi » (fail closed, ADR-039).
"""
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from tessera.models.ticket import TicketPriority, TicketType
from tessera.services.supervision.superviseur_actions import SCHEMA_DECISION, _plier

_Enum = TypeVar("_Enum", TicketType, TicketPriority)

TITRE_MAX = 120
CRITERE_MIN = 15
CRITERES_MAX = 8
#: A report from a professional project is not rewritten with more detail than it carries.
CRITERES_MAX_PRO = 3
CRITERE_MAX_PRO = 160

SCHEMA_TRI: dict[str, Any] = {
    "type": "object",
    "properties": {
        **SCHEMA_DECISION["properties"],
        "titre": {"type": "string", "maxLength": TITRE_MAX},
        "type": {"type": "string", "enum": [t.value for t in TicketType]},
        "priorite": {"type": "string", "enum": [p.value for p in TicketPriority]},
        "criteres": {"type": "array", "items": {"type": "string"}},
        "depends_on": {"type": "array", "items": {"type": "string"}},
        "hors_portee": {"type": "string"},
    },
    "required": SCHEMA_DECISION["required"],
}

_PLACEHOLDER = re.compile(
    r"\b(a ecrire|a definir|a preciser|a completer|a determiner|tbd|todo|xxx|lorem ipsum)\b"
)
_ID_TICKET = re.compile(r"^ticket-\d+$")
_PUCE_CASE = re.compile(r"^(?:-\s*)?(?:\[[ xX]\]\s*)?")


class RefusTri(ValueError):
    """A plan the code refuses: the message is the reason shown in « À toi »."""


@dataclass(frozen=True)
class PlanTri:
    """What a triaged ticket becomes: the fields the model chose, once checked."""

    titre: str
    type: TicketType
    priorite: TicketPriority
    criteres: tuple[str, ...]
    depends_on: tuple[str, ...]
    hors_portee: str


def _texte(brut: Mapping[str, object], champ: str) -> str:
    valeur = brut.get(champ)
    if not isinstance(valeur, str):
        raise RefusTri(f"« {champ} » manque ou n'est pas un texte")
    return valeur.strip()


def _enumeration(brut: Mapping[str, object], champ: str, enum: type[_Enum]) -> _Enum:
    valeur = _texte(brut, champ)
    try:
        return enum(valeur)
    except ValueError:
        raise RefusTri(f"« {champ} » hors énumération : {valeur[:30]!r}") from None


def _titre(brut: Mapping[str, object]) -> str:
    titre = _texte(brut, "titre")
    if not titre or "\n" in titre or len(titre) > TITRE_MAX:
        raise RefusTri(f"« titre » vide, sur plusieurs lignes ou au-delà de {TITRE_MAX} caractères")
    return titre


def _un_critere(valeur: object) -> str:
    if not isinstance(valeur, str):
        raise RefusTri("un critère n'est pas un texte")
    critere = " ".join(_PUCE_CASE.sub("", valeur.strip(), count=1).split())
    if len(critere) < CRITERE_MIN:
        raise RefusTri(f"critère de moins de {CRITERE_MIN} caractères : {critere[:40]!r}")
    if _PLACEHOLDER.search(_plier(critere)):
        raise RefusTri(f"critère qui n'en est pas un (à écrire, à définir…) : {critere[:40]!r}")
    return critere


def _criteres(brut: Mapping[str, object], professionnel: bool) -> tuple[str, ...]:
    valeurs = brut.get("criteres")
    if not isinstance(valeurs, list) or not valeurs:
        raise RefusTri("aucun critère d'acceptation valable")
    criteres = tuple(_un_critere(valeur) for valeur in valeurs)
    if len(criteres) > CRITERES_MAX:
        raise RefusTri(f"plus de {CRITERES_MAX} critères")
    if professionnel and (
        len(criteres) > CRITERES_MAX_PRO or any(len(c) > CRITERE_MAX_PRO for c in criteres)
    ):
        raise RefusTri("signalement d'un projet professionnel : plus de détail que le signalement n'en porte")
    return criteres


def _dependances(brut: Mapping[str, object], existants: Collection[str], propre_id: str) -> tuple[str, ...]:
    valeurs = brut.get("depends_on", [])
    if not isinstance(valeurs, list) or not all(isinstance(v, str) for v in valeurs):
        raise RefusTri("« depends_on » doit être une liste d'identifiants")
    uniques = tuple(dict.fromkeys(v.strip() for v in valeurs))
    for dep in uniques:
        if not _ID_TICKET.match(dep) or dep == propre_id or dep not in existants:
            raise RefusTri(f"depends_on inconnu ou invalide : {dep[:30]!r}")
    return uniques


def _hors_portee(brut: Mapping[str, object], professionnel: bool) -> str:
    valeur = brut.get("hors_portee", "")
    if professionnel or not isinstance(valeur, str):
        return ""
    return valeur.strip()


def lire_plan(
    brut: Mapping[str, object], *, existants: Collection[str], propre_id: str,
    titre_actuel: str, professionnel: bool,
) -> PlanTri:
    """Read the triage fields of a model output; `RefusTri` with the reason if any is off.

    `existants` are the ids of every ticket of the project. A professional
    source keeps its title and gets no free text beyond its few criteria.
    """
    return PlanTri(
        titre=titre_actuel if professionnel else _titre(brut),
        type=_enumeration(brut, "type", TicketType),
        priorite=_enumeration(brut, "priorite", TicketPriority),
        criteres=_criteres(brut, professionnel),
        depends_on=_dependances(brut, existants, propre_id),
        hors_portee=_hors_portee(brut, professionnel),
    )
