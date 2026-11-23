"""Current documentation handed to the documentation agents — ticket-954."""
from pathlib import Path

from tessera.services.documentation.documentation_base import _titres_markdown

#: Taille au-delà de laquelle un fichier est donné par ses seuls titres
#: Markdown, quel que soit son rang (ticket-1038). Ses sections se lisent à
#: la demande.
BORNE_FICHIER = 20_000

#: Volume total de documentation du message : dernier recours, quand même des
#: fichiers sous la borne par fichier dépassent ce total (en caractères).
BORNE_DOC = 200_000


def contenu_documentable(racine: Path, borne: int = BORNE_DOC) -> str:
    """Current content of documentable files, bounded to `borne` characters total."""
    return contenu_et_reduits(racine, borne)[0]


def contenu_et_reduits(
    racine: Path, borne: int = BORNE_DOC
) -> tuple[str, list[str]]:
    """Documentation text, plus the files reduced to their headings.

    A file of at most ``BORNE_FICHIER`` characters is included in full; a
    larger one is given by its headings, whatever its rank. ``borne`` is only
    a last resort for the total. Each reduced file is reported as
    ``"<path> (<N> caractères)"``.
    """
    fichiers: list[tuple[str, str]] = []

    readme = racine / "README.md"
    if readme.is_file():
        fichiers.append(("README.md", readme.read_text(encoding="utf-8")))

    docs_dir = racine / "docs"
    if docs_dir.is_dir():
        for f in sorted(docs_dir.glob("*.md")):
            fichiers.append((f"docs/{f.name}", f.read_text(encoding="utf-8")))

    if not fichiers:
        return "", []

    morceaux: list[str] = []
    reduits: list[str] = []
    budget = borne

    for chemin, contenu in fichiers:
        entete = f"\n### {chemin}\n\n"
        if len(contenu) <= BORNE_FICHIER and len(entete) + len(contenu) <= budget:
            morceaux.append(entete + contenu)
            budget -= len(entete) + len(contenu)
        else:
            titres = _titres_markdown(contenu)
            resume = entete + f"[fichier donné par ses titres]\n{titres}\n"
            morceaux.append(resume)
            reduits.append(f"{chemin} ({len(contenu)} caractères)")
            budget -= len(resume)

    return "\n---\nDocumentation actuelle :\n" + "".join(morceaux), reduits
