"""Un diff n'écrit dans contraintes.md que sous `## Proposées` — ticket-493.

`contraintes.md` part dans chaque appel d'agent : une ligne qu'un run y ajoute
et qui se merge seule change la consigne de tous les suivants, sans relecture
humaine. Un run peut donc **proposer** une règle (la section `## Proposées`,
que le chargeur n'injecte nulle part), jamais l'imposer.

On relit le fichier sur le disque pour savoir dans quelle section tombe chaque
ligne changée, comme `config_tests_touchee` le fait pour `pyproject.toml`.
"""
from pathlib import Path

from tessera.services.adr import est_titre_proposees
from tessera.services.diff_changements import Changement, FichierModifie, lire_diff

_FIN_DE_CHEMIN = "memory/contraintes.md"


def lignes_hors_proposees(diff: str, racines: list[Path]) -> list[str]:
    """The lines `diff` changes in contraintes.md outside `## Proposées`.

    `racines` are the folders a diff path may be relative to (the project and
    its ancestors). A file that cannot be read back (deleted) is flagged whole.
    """
    hors: list[str] = []
    for fichier in lire_diff(diff):
        if not _est_contraintes(fichier.chemin):
            continue
        lignes = _relire(fichier.chemin, racines)
        if lignes is None:
            hors.append(f"{fichier.chemin} (illisible après le diff)")
            continue
        hors.extend(_hors_section(fichier, lignes))
    return hors


def _est_contraintes(chemin: str) -> bool:
    return chemin == _FIN_DE_CHEMIN or chemin.endswith("/" + _FIN_DE_CHEMIN)


def _relire(chemin: str, racines: list[Path]) -> list[str] | None:
    for racine in racines:
        try:
            cible = racine / chemin
            if cible.is_file():
                return cible.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return None
    return None


def _hors_section(fichier: FichierModifie, lignes: list[str]) -> list[str]:
    ajoutees = {c.limite for c in fichier.changements if c.ajoute}
    return [
        f"{fichier.chemin} : {c.texte.strip()}"
        for c in fichier.changements
        if c.texte.strip() and _hors_proposees(c, lignes, ajoutees)
    ]


def _hors_proposees(changement: Changement, lignes: list[str], ajoutees: set[int]) -> bool:
    """True if this change is not inside the `## Proposées` section."""
    texte = changement.texte.strip()
    if texte.startswith("## "):
        # Un titre retiré ou autre que `## Proposées` rattacherait ses règles
        # à la section voisine : jamais admis.
        return not (
            changement.ajoute
            and est_titre_proposees(texte)
            and _section_entierement_ajoutee(changement.limite, lignes, ajoutees)
        )
    section = next(
        (t for t in reversed(lignes[: changement.limite]) if t.lstrip().startswith("## ")),
        None,
    )
    return section is None or not est_titre_proposees(section)


def _section_entierement_ajoutee(titre: int, lignes: list[str], ajoutees: set[int]) -> bool:
    """True if every non-blank line under the header (1-based `titre`) is new.

    Poser `## Proposées` au milieu du fichier avalerait les règles existantes
    qui suivent : elles cesseraient d'être injectées sans qu'un humain l'ait lu.
    """
    for numero in range(titre + 1, len(lignes) + 1):
        texte = lignes[numero - 1]
        if texte.lstrip().startswith("## "):
            return True
        if texte.strip() and numero not in ajoutees:
            return False
    return True
