"""Due dates of recurring rituals — ticket-902.

Everything here is pure: "now" is a parameter, times are naive local times.
"""
from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, Field

JOURS: tuple[str, ...] = (
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
)
Statut = Literal["fait", "a_venir", "en_retard"]


class Hebdo(BaseModel):
    type: Literal["hebdo"]
    jour: Literal["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    heure: time


class Mensuel(BaseModel):
    type: Literal["mensuel"]
    jour: int = Field(ge=1, le=28)
    heure: time
    avant: int | None = Field(default=None, ge=1, le=31)


class Unique(BaseModel):
    type: Literal["unique"]
    du: date
    au: date


Rythme = Annotated[Hebdo | Mensuel | Unique, Field(discriminator="type")]


class Echeances(BaseModel):
    statut: Statut
    derniere: datetime | None
    prochaine: datetime | None
    depasse: bool


def _mensuel_du_mois(annee: int, mois: int, rythme: Mensuel) -> datetime:
    return datetime.combine(date(annee, mois, rythme.jour), rythme.heure)


def _decaler_mois(annee: int, mois: int, delta: int) -> tuple[int, int]:
    indice = annee * 12 + (mois - 1) + delta
    return indice // 12, indice % 12 + 1


def _bornes(
    rythme: Hebdo | Mensuel | Unique, maintenant: datetime
) -> tuple[datetime | None, datetime | None]:
    """Return (last due date passed, next one)."""
    if isinstance(rythme, Unique):
        debut = datetime.combine(rythme.du, time.min)
        return (None, debut) if maintenant < debut else (debut, None)
    if isinstance(rythme, Hebdo):
        jour = JOURS.index(rythme.jour)
        ecart = (maintenant.weekday() - jour) % 7
        candidate = datetime.combine(maintenant.date() - timedelta(days=ecart), rythme.heure)
        if candidate > maintenant:
            candidate -= timedelta(days=7)
        return candidate, candidate + timedelta(days=7)
    courante = _mensuel_du_mois(maintenant.year, maintenant.month, rythme)
    if courante <= maintenant:
        suivante = _mensuel_du_mois(*_decaler_mois(maintenant.year, maintenant.month, 1), rythme)
        return courante, suivante
    precedente = _mensuel_du_mois(*_decaler_mois(maintenant.year, maintenant.month, -1), rythme)
    return precedente, courante


def _limite(rythme: Hebdo | Mensuel | Unique, derniere: datetime) -> datetime | None:
    """First instant after the deadline, if the rhythm has one."""
    if isinstance(rythme, Unique):
        return datetime.combine(rythme.au + timedelta(days=1), time.min)
    if isinstance(rythme, Mensuel) and rythme.avant is not None:
        jour = date(derniere.year, derniere.month, 1) + timedelta(days=rythme.avant - 1)
        return datetime.combine(jour + timedelta(days=1), time.min)
    return None


def calculer_echeances(
    rythme: Hebdo | Mensuel | Unique,
    maintenant: datetime,
    fait_le: datetime | None,
    reporte_jusqua: datetime | None,
) -> Echeances:
    """Status, last/next due date and overdue flag of one ritual at `maintenant`."""
    derniere, prochaine = _bornes(rythme, maintenant)
    if derniere is not None and fait_le is not None and fait_le >= derniere:
        statut: Statut = "fait"
    elif derniere is None or (reporte_jusqua is not None and reporte_jusqua > maintenant):
        statut = "a_venir"
    else:
        statut = "en_retard"
    limite = _limite(rythme, derniere) if derniere is not None else None
    depasse = statut == "en_retard" and limite is not None and maintenant >= limite
    return Echeances(statut=statut, derniere=derniere, prochaine=prochaine, depasse=depasse)
