"""Markdown headings of the files an edition targets, for the corrective round."""
from pathlib import Path

from tessera.services.documentation.documentation_base import _titres_markdown
from tessera.services.documentation.documentation_editions import _documentable

#: Upper bound on the excerpt added to the corrective brief.
EXTRAIT_MAX = 3000


def titres_fichiers_vises(racine: Path, editions: list[dict[str, object]]) -> str:
    """Get Markdown headings of files targeted by the editions.

    Returns a formatted string listing headings per file, to be included in the
    corrective-round message so the agent can pick a valid existing section.
    """
    morceaux: list[str] = []
    vus: set[str] = set()
    for ed in editions:
        chemin = str(ed.get("fichier", ""))
        if chemin in vus:
            continue
        vus.add(chemin)
        # `fichier` vient de la réponse de l'agent : seule la documentation se
        # lit, comme seule elle s'écrit (`appliquer_editions`), et jamais hors
        # de la racine — un « ../../.env » ne doit rien renvoyer au modèle.
        if not _documentable(chemin):
            continue
        fichier = (racine / chemin).resolve()
        if not fichier.is_relative_to(racine.resolve()):
            continue
        if fichier.is_file():
            titres = _titres_markdown(fichier.read_text(encoding="utf-8"))
            if titres:
                morceaux.append(f"\n### {chemin}\n\n{titres}")
    return "".join(morceaux)


def brief_correction(
    user_original: str,
    reponse_precedente: str,
    motif_refus: str,
    titres_fichiers: str,
    fichiers_matiere: list[str] | None = None,
    extrait: str = "",
) -> str:
    """Message for the one-shot corrective round (ticket-395).

    ``fichiers_matiere`` lists the files the agent was given: a ``preuve`` can
    only cite one of them (ticket-542). ``extrait`` is the excerpt carried by
    the refusal, capped at ``EXTRAIT_MAX`` characters.
    """
    parties: list[str] = [
        user_original,
        "\n\n---\n\nTa réponse précédente a été refusée.\n\n"
        f"Motif du refus : {motif_refus}",
    ]
    if extrait:
        parties.append(
            "\n\nPassage du fichier visé, lignes numérotées. Recopie-le tel quel "
            "dans `ancien`, en l'allongeant jusqu'à ce que l'ancre soit unique :\n"
            + extrait[:EXTRAIT_MAX]
        )
    if titres_fichiers:
        parties.append(
            "\n\nTitres Markdown des fichiers visés (liste exhaustive) :" + titres_fichiers
        )
    if fichiers_matiere:
        parties.append(
            "\n\nFichiers du code fourni, où une preuve peut puiser : "
            + ", ".join(fichiers_matiere)
        )
    parties.append("\n\nPropose une nouvelle liste d'éditions corrigée.")
    return "".join(parties)
