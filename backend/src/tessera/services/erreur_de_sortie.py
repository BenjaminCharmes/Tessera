"""Find the line that says why a test step failed, in unstructured output."""

import re

# Lignes qui ressemblent à une erreur. Volontairement larges : elles ne servent
# que quand ni pytest ni vitest n'ont de section reconnue (ticket-473).
_MOTIFS_ERREUR = re.compile(
    r"\berror\b|n'est pas reconnu|not recognized|command not found"
    r"|\bENOENT\b|Cannot find module",
    re.IGNORECASE,
)

# Signale qu'un exécutable est absent du PATH, par opposition à une erreur de code.
_COMMANDE_INTROUVABLE = re.compile(
    r"n'est pas reconnu|not recognized|command not found", re.IGNORECASE
)

_GESTIONNAIRES = re.compile(r"\b(?:pnpm|npm|yarn|npx)\b", re.IGNORECASE)

_PHRASE_COMMANDE_INTROUVABLE = (
    "commande introuvable dans l'environnement du testeur : "
    "passer par corepack ou par node_modules/.bin"
)


def premiere_ligne_d_erreur(sortie: str) -> str:
    """Return the first line of ``sortie`` that looks like an error, or ``""``."""
    for ligne in sortie.splitlines():
        if _MOTIFS_ERREUR.search(ligne):
            return ligne.strip()[:300]
    return ""


def detail_avec_erreur(sortie: str, queue: str) -> str:
    """Put the first error line, and a hint if a package manager is missing, before ``queue``.

    Without any error-looking line, ``queue`` is returned unchanged.
    """
    erreur = premiere_ligne_d_erreur(sortie)
    if not erreur:
        return queue
    tete = [erreur]
    if _COMMANDE_INTROUVABLE.search(erreur) and _GESTIONNAIRES.search(erreur):
        tete.append(_PHRASE_COMMANDE_INTROUVABLE)
    return "\n".join([*tete, "", queue]) if queue else "\n".join(tete)
