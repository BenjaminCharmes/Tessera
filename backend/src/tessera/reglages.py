"""The five global settings the interface may change (ADR-075).

One door: a closed registry with bounds, a SQLite table, an in-memory cache.
A missing row means the `.env` default; `.env` itself is never rewritten.
"""
import json
import math
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import aiosqlite

from tessera.config import settings
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True)
class Reglage:
    """One entry of the registry: a name, a type, hard bounds, how it applies."""

    nom: str
    type: Literal["float", "int", "bool"]
    minimum: float | None
    maximum: float | None
    libelle: str
    effet: Literal["prochain_run", "machine"]


@dataclass(frozen=True)
class ReglagesEffectifs:
    """The value of each setting at a given moment."""

    run_max_budget_usd: float
    llm_max_budget_usd: float
    dialogue_timeout_s: float
    max_parallel_test_runs: int
    keep_awake_during_runs: bool


class ReglageInvalide(ValueError):
    """The name is not in the registry, or the value is not acceptable."""


# Les bornes sont une proposition (design §1) : un tableau qu'un humain relit
# et change sans toucher au reste. `0` n'y figure jamais : « sans plafond »
# ne s'obtient que dans `.env`.
_LISTE: tuple[Reglage, ...] = (
    Reglage("run_max_budget_usd", "float", 0.5, 50.0,
            "Plafond de dépense d'un run (USD)", "prochain_run"),
    Reglage("llm_max_budget_usd", "float", 0.25, 10.0,
            "Plafond de dépense d'un appel (USD)", "prochain_run"),
    Reglage("dialogue_timeout_s", "float", 30.0, 3600.0,
            "Délai avant de reprendre sans réponse (s)", "prochain_run"),
    Reglage("max_parallel_test_runs", "int", 1, 8,
            "Suites de tests simultanées", "machine"),
    Reglage("keep_awake_during_runs", "bool", None, None,
            "Garder la machine éveillée pendant un run", "machine"),
)
REGISTRE: Mapping[str, Reglage] = {r.nom: r for r in _LISTE}

# Les surcharges lues dans la base ; le backend est un seul processus (ADR-008).
_SURCHARGES: dict[str, float | int | bool] = {}
_SNAPSHOT: ContextVar[ReglagesEffectifs | None] = ContextVar(
    "reglages_snapshot", default=None
)


def valider(nom: str, valeur: object) -> float | int | bool:
    """Return the value if it fits the registry, else raise `ReglageInvalide`."""
    reglage = REGISTRE.get(nom)
    if reglage is None:
        raise ReglageInvalide(f"réglage inconnu : {nom}")
    if reglage.type == "bool":
        if not isinstance(valeur, bool):
            raise ReglageInvalide(f"{nom} attend un booléen")
        return valeur
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise ReglageInvalide(f"{nom} attend un nombre")
    if reglage.type == "int" and not isinstance(valeur, int):
        raise ReglageInvalide(f"{nom} attend un entier")
    if isinstance(valeur, float) and not math.isfinite(valeur):
        raise ReglageInvalide(f"{nom} doit être fini")
    _verifier_bornes(reglage, valeur)
    return float(valeur) if reglage.type == "float" else int(valeur)


def _verifier_bornes(reglage: Reglage, valeur: float) -> None:
    """Refuse a value outside the registry bounds, and zero for a budget."""
    if valeur == 0 and reglage.nom.endswith("_budget_usd"):
        raise ReglageInvalide(f"{reglage.nom} : 0 ne se pose que dans .env")
    mini, maxi = reglage.minimum, reglage.maximum
    if (mini is not None and valeur < mini) or (maxi is not None and valeur > maxi):
        raise ReglageInvalide(f"{reglage.nom} doit être entre {mini} et {maxi}")


def _effectifs(source: Mapping[str, float | int | bool]) -> ReglagesEffectifs:
    """Build the snapshot from raw values, each coerced to its declared type."""
    return ReglagesEffectifs(
        run_max_budget_usd=float(source["run_max_budget_usd"]),
        llm_max_budget_usd=float(source["llm_max_budget_usd"]),
        dialogue_timeout_s=float(source["dialogue_timeout_s"]),
        max_parallel_test_runs=int(source["max_parallel_test_runs"]),
        keep_awake_during_runs=bool(source["keep_awake_during_runs"]),
    )


def du_moment() -> ReglagesEffectifs:
    """The `.env` defaults, read from `settings` at each call, plus overrides."""
    valeurs: dict[str, float | int | bool] = {
        nom: _SURCHARGES.get(nom, getattr(settings, nom)) for nom in REGISTRE
    }
    return _effectifs(valeurs)


def noms_modifies() -> frozenset[str]:
    """Names whose value currently differs from `.env` by an override."""
    return frozenset(_SURCHARGES)


def figer(valeurs: ReglagesEffectifs | None = None) -> ReglagesEffectifs:
    """Pin the settings for the current context (a run) and return them."""
    figees = valeurs if valeurs is not None else du_moment()
    _SNAPSHOT.set(figees)
    return figees


def courants() -> ReglagesEffectifs:
    """The pinned snapshot of the run if there is one, else the current moment."""
    figees = _SNAPSHOT.get()
    return figees if figees is not None else du_moment()


async def charger(db_path: Path) -> None:
    """Load the overrides into the cache; a bad row is ignored and logged."""
    _SURCHARGES.clear()
    async with aiosqlite.connect(str(db_path)) as db:
        curseur = await db.execute("SELECT nom, valeur FROM reglages")
        lignes = await curseur.fetchall()
    for nom, brut in lignes:
        try:
            _SURCHARGES[nom] = valider(nom, json.loads(brut))
        except (ReglageInvalide, ValueError):
            _logger.warning("reglage_ignore", extra={"nom": nom, "valeur": brut})


async def ecrire(db_path: Path, nom: str, valeur: object) -> ReglagesEffectifs:
    """Validate, store and cache an override, and return the new effective values."""
    posee = valider(nom, valeur)
    ancienne = du_moment()
    maintenant = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT INTO reglages (nom, valeur, modifie_le) VALUES (?, ?, ?) "
            "ON CONFLICT(nom) DO UPDATE SET valeur = excluded.valeur, "
            "modifie_le = excluded.modifie_le",
            (nom, json.dumps(posee), maintenant),
        )
        await db.commit()
    _SURCHARGES[nom] = posee
    _journaliser(nom, getattr(ancienne, nom), posee)
    return du_moment()


async def retirer(db_path: Path, nom: str) -> ReglagesEffectifs:
    """Drop an override: the setting returns to its `.env` default."""
    if nom not in REGISTRE:
        raise ReglageInvalide(f"réglage inconnu : {nom}")
    ancienne = getattr(du_moment(), nom)
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("DELETE FROM reglages WHERE nom = ?", (nom,))
        await db.commit()
    _SURCHARGES.pop(nom, None)
    _journaliser(nom, ancienne, getattr(du_moment(), nom))
    return du_moment()


def _journaliser(nom: str, ancienne: object, nouvelle: object) -> None:
    """Log a change: name, old and new value — nothing secret."""
    _logger.info(
        "reglage_modifie",
        extra={"nom": nom, "ancienne": ancienne, "nouvelle": nouvelle},
    )
