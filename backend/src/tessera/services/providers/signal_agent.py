"""Decide whether an agent's ``signaler`` call is received — ticket-862, ADR-080.

Pure functions: no tool, no ticket written here (ticket-863 serves the tool, the
backend writes the report). The project, the role and the ticket come from the
run, never from the arguments: an ``args["projet"]`` is ignored.

Three leaks are closed here. A ``professional`` project passes only the two
enumerations (ADR-043); a secret or a forbidden term refuses the call (ADR-073,
ADR-050) without the text being rewritten; the bounds keep an agent from
flooding the backlog.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

from tessera.services.gardes.termes_interdits import TermesInterditsService

MAX_TITRE = 120
MAX_DESCRIPTION = 1500
MAX_PAR_RUN = 3
MAX_PAR_JOUR = 10

#: What the source reads when the project is professional: no name leaves.
SOURCE_PROFESSIONNELLE = "un projet professionnel"

CATEGORIES: frozenset[str] = frozenset(
    {"garde_trop_strict", "outil_casse", "consigne_contradictoire", "autre"}
)
# Liste fermée : le design ne l'énumère pas, ce sont les organes de Tessera
# qu'un agent peut rencontrer en travaillant.
COMPOSANTS: frozenset[str] = frozenset(
    {
        "garde_ecriture",
        "garde_git",
        "garde_secrets",
        "garde_perimetre",
        "outil_agent",
        "provider",
        "pipeline",
        "livraison",
        "verification",
        "consignes",
        "interface",
        "autre",
    }
)


@dataclass(frozen=True)
class SignalValide:
    """A report that passed every check, ready to be written by the backend.

    ``projet`` is what the report may show of its origin; ``source`` is the
    ``agent:<role>@<ticket>`` line. For a professional project ``description``
    is empty and ``projet`` is ``SOURCE_PROFESSIONNELLE``.
    """

    titre: str
    description: str
    categorie: str
    composant: str
    projet: str
    source: str


@dataclass(frozen=True)
class Refus:
    """A refused call, with the reason the agent reads."""

    raison: str


def normaliser_titre(titre: str) -> str:
    """Lowercase, strip accents and punctuation, collapse spaces (duplicate key)."""
    nfkd = unicodedata.normalize("NFKD", titre.lower())
    sans_accents = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", sans_accents).strip()


def _texte(args: Mapping[str, object], cle: str) -> str | None:
    valeur = args.get(cle)
    return valeur.strip() if isinstance(valeur, str) else None


def _refus_de_bornes(deja_emis_run: int, deja_emis_jour: int) -> Refus | None:
    if deja_emis_run >= MAX_PAR_RUN:
        return Refus(f"Signalement refusé : {MAX_PAR_RUN} par run au plus, déjà atteints.")
    if deja_emis_jour >= MAX_PAR_JOUR:
        return Refus(
            f"Signalement refusé : {MAX_PAR_JOUR} par projet et par jour au plus, "
            "déjà atteints."
        )
    return None


def _enumerations(args: Mapping[str, object]) -> tuple[str, str] | Refus:
    categorie, composant = _texte(args, "categorie"), _texte(args, "composant")
    if categorie is None or categorie not in CATEGORIES:
        return Refus(f"Signalement refusé : `categorie` doit être l'une de {sorted(CATEGORIES)}.")
    if composant is None or composant not in COMPOSANTS:
        return Refus(f"Signalement refusé : `composant` doit être l'un de {sorted(COMPOSANTS)}.")
    return categorie, composant


def _textes(args: Mapping[str, object]) -> tuple[str, str] | Refus:
    titre, description = _texte(args, "titre"), _texte(args, "description")
    if not titre:
        return Refus("Signalement refusé : `titre` est obligatoire.")
    if len(titre) > MAX_TITRE:
        return Refus(f"Signalement refusé : `titre` dépasse {MAX_TITRE} caractères. Raccourcis-le.")
    if not description:
        return Refus("Signalement refusé : `description` est obligatoire.")
    if len(description) > MAX_DESCRIPTION:
        return Refus(
            f"Signalement refusé : `description` dépasse {MAX_DESCRIPTION} caractères "
            "(elle n'est pas tronquée). Raccourcis-la."
        )
    return titre, description


def _refus_de_confidentialite(champs: Mapping[str, str]) -> Refus | None:
    """Refuse when a field holds a forbidden term or a secret, without naming it."""
    service = TermesInterditsService()
    for nom, texte in champs.items():
        a_plat = " ".join(texte.split())
        # Préfixe « + » suivi d'une espace : `verifier` ignore toute ligne qui
        # commence par `+++` (en-tête de fichier), un texte en `++` y échapperait.
        if service.verifier(lignes_ajoutees=["+ " + a_plat], commits=[]):
            return Refus(
                f"Signalement refusé : `{nom}` contient un terme interdit ou un secret "
                "(ADR-050, ADR-073). Retire-le et reformule, sans le recopier."
            )
    return None


def _professionnel(role: str, ticket: str, categorie: str, composant: str) -> SignalValide:
    return SignalValide(
        titre=f"[{role}] {categorie} — {composant}",
        description="",
        categorie=categorie,
        composant=composant,
        projet=SOURCE_PROFESSIONNELLE,
        source=f"agent:{role}@{ticket}",
    )


def valider_signal(
    args: Mapping[str, object],
    *,
    projet: str,
    confidentialite: str,
    role: str,
    ticket: str,
    deja_emis_run: int,
    deja_emis_jour: int,
) -> SignalValide | Refus:
    """Check one ``signaler`` call: bounds, enumerations, sizes, guards.

    ``projet``, ``role`` and ``ticket`` are the run's. A ``professional``
    project keeps only the enumerations: the title is built here and the free
    text is dropped. Duplicates are the job of ``signal_agent_registre``.
    """
    refus = _refus_de_bornes(deja_emis_run, deja_emis_jour)
    if refus is not None:
        return refus
    enumerations = _enumerations(args)
    if isinstance(enumerations, Refus):
        return enumerations
    categorie, composant = enumerations
    source = f"agent:{role}@{ticket}"
    if confidentialite == "professional":
        return _professionnel(role, ticket, categorie, composant)
    textes = _textes(args)
    if isinstance(textes, Refus):
        return textes
    titre, description = textes
    refus = _refus_de_confidentialite({"titre": titre, "description": description})
    if refus is not None:
        return refus
    return SignalValide(titre, description, categorie, composant, projet, source)
