"""Contrôle des termes interdits avant publication — ADR-048.

Un push ne sort jamais si une ligne ajoutée, un message de commit ou un auteur
contient un terme de la liste. La liste vit dans FORBIDDEN_TERMS (.env local,
jamais versionné) ; vide ou absente, le service est inactif.

Le service ne nomme jamais le terme dans sa sortie : un log se partage, un nom
interdit aussi.

Intégration : `GitHubWorkflowService.open_pull_request()` appelle `verifier()`
avant le push. `PolitiqueRun.confidentialite == "professional"` court-circuite
le contrôle pour les dépôts professionnels (ADR-048).
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CommitInfo:
    """Short SHA, message and author of a single commit."""

    sha7: str
    message: str
    auteur: str


@dataclass(frozen=True)
class ViolationTerme:
    """Localisation d'un terme interdit.

    `source` identifie l'endroit où le terme a été trouvé — jamais le terme
    lui-même. Formes attendues : ``"commit:<sha7>"``, ``"file:<chemin>"``.
    """

    source: str


class TermesInterditsChecker(Protocol):
    """Contrat que doit satisfaire l'implémentation concrète."""

    @property
    def actif(self) -> bool:
        """False quand FORBIDDEN_TERMS est vide ou absent : aucun appel réseau."""
        ...

    def verifier(
        self,
        *,
        lignes_ajoutees: list[str],
        commits: list[CommitInfo],
    ) -> list[ViolationTerme]:
        """Rend les violations trouvées. Liste vide signifie « rien à signaler »."""
        ...


def _normaliser(texte: str) -> str:
    """Normalize text for term comparison.

    Applies NFKD decomposition to remove accents, lowercases, and converts
    separators (``-``, ``_``, ``.``) to spaces so that ``foo-bar`` matches a
    term ``foo bar``.
    """
    nfkd = unicodedata.normalize("NFKD", texte.lower())
    # Mn = Mark, Nonspacing — combining diacritics added by NFKD
    sans_accents = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"[-_.]", " ", sans_accents)


class TermesInterditsService:
    """Vérifie l'absence de termes interdits dans un push — ADR-048.

    Charge ``FORBIDDEN_TERMS`` depuis l'environnement (virgules comme
    séparateurs). Inactif quand la liste est vide ou absente.

    La normalisation est symétrique : termes et textes inspecté passent par
    ``_normaliser`` avant toute comparaison, ce qui rend le contrôle
    insensible à la casse, aux accents et aux séparateurs courants.
    """

    def __init__(self) -> None:
        # Le backend lit `.env` dans ses réglages sans l'exporter dans
        # l'environnement : lire `os.environ` seul laissait le service inactif
        # en production. Une variable d'environnement explicite garde la main.
        from tessera.config import settings
        from tessera.utils.secrets import SECRETS

        raw = os.environ.get("FORBIDDEN_TERMS") or settings.forbidden_terms
        self._termes: list[str] = [
            _normaliser(t.strip()) for t in raw.split(",") if t.strip()
        ]
        # Compile word-boundary patterns on normalized terms once at init.
        self._patterns: list[re.Pattern[str]] = [
            re.compile(r"\b" + re.escape(terme) + r"\b")
            for terme in self._termes
        ]
        # Les jetons de mise en ligne configurés, et tout secret reçu d'une API
        # pendant l'exécution, sont des termes interdits (ADR-053). Sans bornes
        # de mot : un secret collé à d'autres caractères reste un secret.
        secrets = {*settings.valeurs_des_jetons(), *SECRETS.valeurs()}
        self._patterns += [
            re.compile(re.escape(_normaliser(secret)))
            for secret in sorted(secrets)
            if _normaliser(secret).strip()
        ]

    @property
    def actif(self) -> bool:
        """False quand ni FORBIDDEN_TERMS ni un jeton configuré n'existe."""
        return bool(self._patterns)

    def _contient_terme(self, texte: str) -> bool:
        normalise = _normaliser(texte)
        return any(p.search(normalise) for p in self._patterns)

    def verifier(
        self,
        *,
        lignes_ajoutees: list[str],
        commits: list[CommitInfo],
    ) -> list[ViolationTerme]:
        """Rend les violations trouvées. Liste vide signifie « rien à signaler ».

        ``lignes_ajoutees`` doit contenir toutes les lignes commençant par
        ``+`` dans le diff unifié, y compris les en-têtes ``+++ b/<chemin>``
        (utilisés pour identifier le fichier en cause). Les lignes ``+++`` ne
        sont pas inspectées pour les termes.

        Une seule violation par fichier et par commit : l'objectif est de
        bloquer, pas d'inventorier.
        """
        if not self._patterns:
            return []

        violations: list[ViolationTerme] = []

        # --- Lignes ajoutées du diff ---
        chemin_courant: str | None = None
        fichiers_signales: set[str | None] = set()

        for ligne in lignes_ajoutees:
            if ligne.startswith("+++"):
                # En-tête de fichier : +++ b/<chemin> (ajouté) ou +++ /dev/null
                chemin_courant = (
                    ligne[6:].strip() if ligne.startswith("+++ b/") else None
                )
                continue
            # Ligne de contenu — ne pas inspecter si le fichier est déjà signalé
            if chemin_courant in fichiers_signales:
                continue
            contenu = ligne[1:] if ligne else ""
            if self._contient_terme(contenu):
                fichiers_signales.add(chemin_courant)
                source = (
                    f"file:{chemin_courant}" if chemin_courant else "file:unknown"
                )
                violations.append(ViolationTerme(source=source))

        # --- Messages et auteurs des commits ---
        commits_signales: set[str] = set()
        for commit in commits:
            if commit.sha7 in commits_signales:
                continue
            if self._contient_terme(commit.message) or self._contient_terme(
                commit.auteur
            ):
                commits_signales.add(commit.sha7)
                violations.append(ViolationTerme(source=f"commit:{commit.sha7}"))

        return violations
