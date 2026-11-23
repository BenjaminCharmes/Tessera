"""Sections à la demande d'un gros fichier de documentation — ticket-1038.

Un fichier donné par ses titres ne se lit pas. Le rôle peut répondre
``{"sections": [{"fichier", "titre"}]}`` à la place des éditions : le service
le rappelle une fois, avec le texte entier de ces sections, pour qu'il puisse
recopier un ``ancien``.
"""
from pathlib import Path

from tessera.services.documentation.documentation_base import EditionRefusee
from tessera.services.documentation.documentation_editions import _documentable, bornes_section
from tessera.services.documentation.documentation_reponse import lire_json
from tessera.services.providers.base import LLMProvider, ProviderResult

#: Volume total des sections rendues dans un rappel (en caractères).
LIMITE_SECTIONS = 40_000


def sections_demandees(donnees: dict[str, object]) -> list[tuple[str, str]]:
    """The ``(fichier, titre)`` pairs a role asked for, malformed entries dropped."""
    brut = donnees.get("sections")
    if not isinstance(brut, list):
        return []
    demandes: list[tuple[str, str]] = []
    for entree in brut:
        if isinstance(entree, dict):
            fichier, titre = entree.get("fichier"), entree.get("titre")
            if isinstance(fichier, str) and isinstance(titre, str):
                demandes.append((fichier, titre))
    return demandes


def _lire_section(racine: Path, fichier: str, titre: str) -> str:
    """Full text of one section; ``EditionRefusee`` says why it cannot be read."""
    if not _documentable(fichier):
        raise EditionRefusee(f"{fichier} n'est pas de la documentation.")
    chemin = (racine / fichier).resolve()
    if not chemin.is_relative_to(racine.resolve()) or not chemin.is_file():
        raise EditionRefusee(f"{fichier} : fichier introuvable.")
    lignes, debut, fin = bornes_section(chemin.read_text(encoding="utf-8"), titre, fichier)
    return "".join(lignes[debut:fin])


def texte_des_sections(
    racine: Path, demandes: list[tuple[str, str]], limite: int = LIMITE_SECTIONS
) -> tuple[str, list[str]]:
    """Text of the requested sections, and the requests that were not served.

    A request is ignored when the file is not documentation, lies outside
    ``racine``, or the heading is absent or ambiguous. A section that would
    push the total over ``limite`` is named, not given.
    """
    morceaux: list[str] = []
    ignorees: list[str] = []
    restant = limite
    for fichier, titre in demandes:
        try:
            texte = _lire_section(racine, fichier, titre)
        except (EditionRefusee, OSError, UnicodeDecodeError) as exc:
            ignorees.append(f"{fichier} « {titre} » ignorée : {exc}")
            continue
        if len(texte) > restant:
            ignorees.append(f"{fichier} « {titre} » ignorée : au-delà de la limite de {limite} caractères")
            continue
        restant -= len(texte)
        morceaux.append(f"\n### {fichier} — {titre}\n\n{texte}")
    return "".join(morceaux), ignorees


def message_de_rappel(user: str, texte: str, ignorees: list[str]) -> str:
    """The original message, augmented with the sections and the ignored requests."""
    bloc = "\n---\nSections demandées (texte entier, à recopier pour un `ancien`) :\n" + texte
    if ignorees:
        bloc += "\n---\nDemandes non servies :\n" + "\n".join(f"- {i}" for i in ignorees)
    return user + bloc


async def avec_sections(
    reponse: ProviderResult,
    reduits: list[str],
    racine: Path,
    provider: LLMProvider,
    systeme: str,
    user: str,
    modele: str,
    max_tokens: int,
    cwd: Path,
) -> ProviderResult:
    """Re-ask the role once when it answered with ``sections``; else keep its answer.

    Without a reduced file, nothing is re-asked.
    """
    donnees = lire_json(str(reponse.content))
    demandes = sections_demandees(donnees) if donnees is not None and reduits else []
    if not demandes:
        return reponse
    texte, ignorees = texte_des_sections(racine, demandes)
    return await provider.complete(
        system=systeme,
        user=message_de_rappel(user, texte, ignorees),
        model=modele,
        max_tokens=max_tokens,
        cwd=cwd,
    )
