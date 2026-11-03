"""Appliquer des éditions Markdown, toutes ou aucune — t.092, extrait par t.692.

Fonctions pures du point de vue du service : elles reçoivent ce que l'agent a
rendu et un dossier racine, et n'écrivent qu'une fois toutes les éditions
validées. Le contrat et ses raisons sont décrits dans ``documentation``.
"""
import re
from pathlib import Path

from tessera.services import documentation_claude_md as claude_md_doc
from tessera.services.documentation_base import EditionRefusee
from tessera.services.documentation_base import normaliser_typo as _normaliser_typo
from tessera.services.documentation_code import MatiereCode
from tessera.services.documentation_preuve import ControleDePreuve

#: Ce qu'un agent de documentation a le droit de toucher. Il documente ; le
#: code, les tickets et les ADR ne sont pas à lui.
_DOCUMENTABLE = ("README.md", "docs/")

#: En dessous de cette part du fichier d'origine, un remplacement n'est plus
#: une modification : c'est une amputation.
_PART_MINIMALE = 0.5


def _documentable(chemin: str) -> bool:
    normalise = chemin.replace("\\", "/")
    if ".." in normalise or normalise.startswith("/"):
        return False
    return any(normalise.startswith(prefixe) for prefixe in _DOCUMENTABLE)


def appliquer_editions(
    racine: Path,
    editions: list[dict[str, object]],
    claude_md: Path | None = None,
    matiere: MatiereCode | None = None,
    tickets: str = "",
    agents_md: Path | None = None,
) -> list[str]:
    """Applique toutes les modifications, ou aucune.

    Une documentation à moitié mise à jour est pire qu'une documentation en
    retard : elle a l'air à jour.

    ``claude_md`` est le CLAUDE.md du projet quand il le déclare documentable
    (ticket-244) ; sans lui, une modification de « CLAUDE.md » est refusée.
    ``agents_md`` est l'AGENTS.md, fourni aux mêmes conditions (ticket-724).

    Une édition ``contenu`` crée un fichier absent (ticket-342) : sans elle, un
    guide qui n'existe pas encore ne pouvait jamais naître. Elle n'écrase
    jamais un fichier existant.

    ``matiere`` et ``tickets`` sont ce que l'agent a lu : le code livré et le
    texte des tickets. Avec elle, chaque édition doit citer le code qui la fonde
    et ses jetons vérifiables doivent y figurer (ticket-542, ADR-057). Sans
    elle, rien n'est contrôlé : seul le service sait ce que l'agent a reçu, et
    il la passe toujours.
    """
    resultat: dict[Path, str] = {}
    controle = None if matiere is None else ControleDePreuve(matiere, tickets)

    for edition in editions:
        chemin = str(edition.get("fichier", ""))
        if chemin == claude_md_doc.NOM and claude_md is not None:
            fichier = claude_md
        elif chemin == claude_md_doc.NOM_AGENTS and agents_md is not None:
            fichier = agents_md
        elif not _documentable(chemin):
            raise EditionRefusee(
                f"{chemin} n'est pas de la documentation : un agent de "
                "documentation ne touche ni au code, ni aux tickets, ni aux ADR."
            )
        else:
            fichier = racine / chemin

        if controle is not None:
            controle.verifier(edition, chemin)

        if "contenu" in edition:
            if fichier in resultat or fichier.exists():
                raise EditionRefusee(
                    f"{chemin} existe déjà : `contenu` ne sert qu'à créer un fichier "
                    "absent. Modifier un fichier passe par `ancien` ou `apres_section`."
                )
            contenu = str(edition.get("contenu", ""))
            if not contenu.strip():
                raise EditionRefusee(f"{chemin} : création sans contenu.")
            resultat[fichier] = contenu
            continue

        if fichier not in resultat and not fichier.is_file():
            raise EditionRefusee(
                f"{chemin} : fichier introuvable. Pour le créer, donner son texte "
                "entier dans `contenu`."
            )

        # Pas de `resultat.get(fichier, read_text())` : le défaut serait lu sur
        # disque même pour un fichier que ce lot vient de créer.
        avant = resultat[fichier] if fichier in resultat else fichier.read_text(encoding="utf-8")

        if "apres_section" in edition:
            resultat[fichier] = _inserer(avant, edition, chemin)
            continue

        resultat[fichier] = _remplacer(avant, edition, chemin)

    claude_md_doc.verifier_budgets(resultat, claude_md, agents_md)

    for fichier, contenu in resultat.items():
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(contenu, encoding="utf-8")
    return [str(f) for f in resultat]


def _remplacer(avant: str, edition: dict[str, object], chemin: str) -> str:
    ancien = str(edition.get("ancien", ""))
    nouveau = str(edition.get("nouveau", ""))
    if not ancien:
        raise EditionRefusee(f"{chemin} : modification sans texte à remplacer.")

    debut, fin = _localiser(avant, ancien, chemin)
    apres = avant[:debut] + nouveau + avant[fin:]
    if len(apres) < len(avant) * _PART_MINIMALE:
        raise EditionRefusee(
            f"{chemin} : le fichier serait amputé de plus de la moitié "
            f"({len(avant)} → {len(apres)} caractères). C'est la panne que ce "
            "contrat existe pour empêcher."
        )
    return apres


def _positions_de(texte: str, motif: str) -> list[int]:
    """Start offsets of every non-overlapping occurrence of ``motif``."""
    trouvees: list[int] = []
    debut = texte.find(motif)
    while debut != -1:
        trouvees.append(debut)
        debut = texte.find(motif, debut + len(motif))
    return trouvees


def _localiser(avant: str, ancien: str, chemin: str) -> tuple[int, int]:
    """Locate ``ancien`` in ``avant`` and return its (start, end) offsets.

    An exact match wins. Otherwise the search is retried after normalizing
    typography on both sides, and the offsets are mapped back to ``avant`` so
    the rest of the file keeps its typography.
    """
    exactes = _positions_de(avant, ancien)
    if len(exactes) == 1:
        return exactes[0], exactes[0] + len(ancien)

    if len(exactes) == 0:
        norm_avant, pos_avant = _normaliser_typo(avant)
        norm_ancien, _ = _normaliser_typo(ancien)
        trouvees = _positions_de(norm_avant, norm_ancien) if norm_ancien else []
        if len(trouvees) == 1:
            debut = trouvees[0]
            dernier = pos_avant[debut + len(norm_ancien) - 1]
            return pos_avant[debut], dernier + 1
        exactes = trouvees

    if not exactes:
        raise EditionRefusee(
            f"{chemin} : texte introuvable — « {ancien[:60]} ». "
            "L'agent a proposé une modification sur un texte qui n'existe pas."
        )
    raise EditionRefusee(
        f"{chemin} : texte présent {len(exactes)} fois — on ne devine pas "
        "laquelle remplacer."
    )


def _normaliser_section(texte: str) -> str:
    """Normalize a section title for case-, whitespace- and typography-tolerant comparison.

    Collapses multiple spaces, strips leading/trailing whitespace, lowercases
    and flattens typographic punctuation (ticket-402).
    Applied to both the requested section and each candidate heading line.
    """
    plat, _ = _normaliser_typo(texte)
    return re.sub(r"\s+", " ", plat.strip()).lower()


def _inserer(avant: str, edition: dict[str, object], chemin: str) -> str:
    """Insert text after a Markdown section, with tolerant anchor matching.

    The section is matched after normalizing casse and extra whitespace (ticket-395).
    A unique match at the exact heading level is required; zero or two+ matches → refused.
    """
    section = str(edition.get("apres_section", ""))
    texte = str(edition.get("texte", ""))

    niveau = len(section) - len(section.lstrip("#"))
    prefixe = "#" * niveau + " "
    section_norm = _normaliser_section(section)

    lignes = avant.splitlines(keepends=True)
    # Candidats : lignes qui démarrent au bon niveau de titre et correspondent
    # après normalisation (casse et espaces multiples tolérés).
    candidats = [
        i
        for i, l in enumerate(lignes)
        if l.startswith(prefixe) and _normaliser_section(l.rstrip()) == section_norm
    ]

    if len(candidats) == 0:
        raise EditionRefusee(f"{chemin} : section « {section} » introuvable.")
    if len(candidats) > 1:
        raise EditionRefusee(
            f"{chemin} : section « {section} » correspond à {len(candidats)} titres "
            "après normalisation — titre ambigu."
        )

    debut = candidats[0]
    fin = len(lignes)
    for i in range(debut + 1, len(lignes)):
        titre = lignes[i].lstrip()
        if titre.startswith("#"):
            if len(titre) - len(titre.lstrip("#")) <= niveau:
                fin = i
                break
    return "".join(lignes[:fin]) + texte.rstrip("\n") + "\n\n" + "".join(lignes[fin:])
