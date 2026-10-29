"""Renumbering of the tickets and ADRs a run adds, before delivery — ticket-659.

Deux branches parties du même `develop` prennent les mêmes numéros ; la seconde
livrée écrase ou double la première. Avant le rebase, on relève ce que le diff
du run ajoute, et ce dont le numéro est déjà pris sur `origin/<base>` passe au
numéro libre suivant : nom du fichier, `id`, titre, `depends_on` et mentions.

Les mentions ne se réécrivent que sur les **lignes que le diff ajoute** : un
`ticket-611` d'un code déjà mergé désigne le ticket de la base, il ne bouge pas.
"""
import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tessera.services.journal_pipeline import ajouter_ligne
from tessera.services.numerotation import (
    FICHIERS_ADR,
    Genre,
    noms_de_tickets_sur_la_base,
    numeros_de_noms,
    numeros_pris,
    titres_d_adr,
    titres_d_adr_sur_la_base,
)
from tessera.services.reecriture_des_numeros import (
    JOURNAL,
    nommer,
    reecrire_les_mentions,
    renommer_les_fiches,
)
from tessera.services.releve_du_diff import Releve, lire_lignes, releve_du_diff
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)
_MESSAGE_DE_COMMIT = "chore: renumber the tickets and ADRs a run added"


@dataclass(frozen=True)
class Renumerotation:
    genre: Genre
    ancien: int
    nouveau: int

    def __str__(self) -> str:
        return f"{nommer(self.genre, self.ancien)} → {nommer(self.genre, self.nouveau)}"


@dataclass(frozen=True)
class Resultat:
    renumerotations: tuple[Renumerotation, ...] = ()
    #: Chemins relatifs au projet touchés : anciens noms, nouveaux, fichiers réécrits.
    chemins: tuple[str, ...] = ()


class _Commit(Protocol):
    async def commit_chemins(self, message: str, chemins: list[str]) -> bool: ...


def _tickets_en_collision(depot: Path, base: str, releve: Releve) -> set[int]:
    """Numbers of added tickets whose number is taken by another ticket of the base.

    Un ticket qui change de dossier de statut garde son nom : il apparaît
    « ajouté » dans le diff mais le nom existe déjà sur la base, ce n'est pas
    une collision.
    """
    noms_base = noms_de_tickets_sur_la_base(depot, base)
    numeros_base = numeros_de_noms(noms_base)
    collisions: set[int] = set()
    for chemin in releve.ajoutes:
        if not chemin.startswith("tickets/") or chemin.rsplit("/", 1)[-1] in noms_base:
            continue
        collisions |= numeros_de_noms([chemin]) & numeros_base
    return collisions


def _adr_en_collision(depot: Path, base: str, releve: Releve) -> set[int]:
    """Numbers of added ADR headings that name another decision on the base."""
    titres_base = titres_d_adr_sur_la_base(depot, base)
    collisions: set[int] = set()
    for fichier in FICHIERS_ADR:
        ajoutees = lire_lignes(depot, fichier, releve.lignes.get(fichier, set()))
        for numero, titre in titres_d_adr("\n".join(ajoutees)).items():
            if numero in titres_base and titres_base[numero] != titre:
                collisions.add(numero)
    return collisions


def _correspondances(
    depot: Path, base: str, genre: Genre, collisions: set[int]
) -> dict[int, int]:
    """Each colliding number → the next free one, allocated in ascending order."""
    if not collisions:
        return {}
    pris = numeros_pris(depot, genre, base, strict=True)
    attribues: dict[int, int] = {}
    for ancien in sorted(collisions):
        nouveau = max(pris, default=0) + 1
        pris.add(nouveau)
        attribues[ancien] = nouveau
    return attribues


def renumeroter(depot: Path, base: str) -> Resultat:
    """Renumber what the diff against `origin/<base>` adds and the base already holds.

    Synchrone ; lève GitIllisible quand une lecture échoue, pour que la
    livraison refuse plutôt que de pousser un numéro douteux (ADR-039).
    """
    releve = releve_du_diff(depot, base)
    tickets = _correspondances(
        depot, base, "ticket", _tickets_en_collision(depot, base, releve)
    )
    adr = _correspondances(depot, base, "adr", _adr_en_collision(depot, base, releve))
    if not tickets and not adr:
        return Resultat()
    touches = reecrire_les_mentions(depot, releve, {"ticket": tickets, "adr": adr})
    touches |= renommer_les_fiches(depot, releve, tickets)
    faites = tuple(
        [Renumerotation("ticket", a, n) for a, n in tickets.items()]
        + [Renumerotation("adr", a, n) for a, n in adr.items()]
    )
    for une in faites:
        ajouter_ligne(
            depot / JOURNAL,
            f"renumérotation : {une} (numéro déjà pris sur origin/{base})",
        )
    return Resultat(faites, tuple(sorted(touches | {JOURNAL})))


class Renumeroteur:
    """The delivery step: renumber in the tree, then commit what moved."""

    def __init__(self, git: _Commit, depot: Path, base: str) -> None:
        self._git = git
        self._depot = depot
        self._base = base

    async def __call__(self) -> tuple[str, ...]:
        resultat = await asyncio.to_thread(renumeroter, self._depot, self._base)
        if resultat.renumerotations:
            await self._git.commit_chemins(_MESSAGE_DE_COMMIT, list(resultat.chemins))
        return tuple(str(une) for une in resultat.renumerotations)


async def etape_de_numerotation(
    renumeroter: Callable[[], Awaitable[tuple[str, ...]]] | None,
    etapes: list[str],
    durees_ms: list[float],
) -> str | None:
    """The stop when numbering cannot be checked, else None.

    Fails closed (ADR-039): a numbering that cannot be read is not pushed.
    """
    if renumeroter is None:
        return None
    t0 = time.monotonic()
    try:
        faites = await renumeroter()
    except Exception as exc:  # noqa: BLE001 — échec fermé : rien ne part
        _logger.warning("renumerotation_echouee", extra={"erreur": str(exc)})
        return f"la numérotation n'a pas pu être vérifiée : {type(exc).__name__}: {exc}"
    if faites:
        etapes.append("renumérotation : " + ", ".join(faites))
        durees_ms.append((time.monotonic() - t0) * 1000)
    return None
