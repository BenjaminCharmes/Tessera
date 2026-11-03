"""Un diff qui touche la configuration des tests le dit au reviewer — ticket-490.

Modifier `conftest.py`, la section pytest ou mypy de `pyproject.toml`, les
scripts de `package.json` est souvent légitime : on ne l'interdit donc pas. Mais
c'est aussi la façon la plus discrète d'affaiblir la vérification qui juge le
diff. La liste est fermée ; quand elle correspond, le reviewer le lit en tête
de son message, avec les fichiers nommés.

Ticket-725 ajoute la porte : un avertissement lu par un LLM ne tient pas. Si
aucun des fichiers touchés n'est cité dans le texte du ticket, le verdict
devient `CHANGES_REQUESTED`. Un ticket qui nomme le fichier garde l'avertissement
seul.

Pour `pyproject.toml` et `package.json`, seul un changement **dans** la section
visée compte : on relit donc le fichier sur le disque pour savoir où il tombe.
Un fichier qu'on ne peut plus relire (supprimé) est signalé, par prudence.
"""
import re
from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import Path

from tessera.services.diff_changements import Changement, FichierModifie, lire_diff

#: Le titre sous lequel le reviewer lit l'avertissement.
TITRE_CONFIG_TESTS = "Attention : ce diff modifie la configuration des tests"

_CONSIGNE = (
    "Vérifie que la vérification n'est pas affaiblie : un test retiré ou "
    "assoupli, une étape supprimée, un seuil abaissé, une règle désactivée, "
    "un dossier exclu. Une modification de configuration peut être légitime ; "
    "elle doit alors se justifier par le ticket."
)

#: Les fichiers signalés dès qu'ils changent, par motif de nom.
_NOMS_SIGNALES = ("conftest.py", "vitest.config.*", "eslint.config.*", "tsconfig*.json")

_ENTETE_TOML = re.compile(r"^\s*\[\[?\s*(?P<nom>[^\]]+?)\s*\]\]?\s*(?:#.*)?$")
_CLE_SCRIPTS = re.compile(r'^\s*"scripts"\s*:')


def fichiers_de_config_touches(diff: str, racines: list[Path]) -> list[str]:
    """The test-configuration files `diff` changes, as written in the diff.

    `racines` are the folders a diff path may be relative to (the project and
    its ancestors); the first one holding the file is used to read it back.
    """
    touches: list[str] = []
    for fichier in lire_diff(diff):
        if _touche_la_configuration(fichier, racines) and fichier.chemin not in touches:
            touches.append(fichier.chemin)
    return touches


def avertissement_config_tests(fichiers: list[str]) -> str:
    """The warning that opens the reviewer's message, empty without files."""
    if not fichiers:
        return ""
    liste = "\n".join(f"- `{chemin}`" for chemin in fichiers)
    return f"## {TITRE_CONFIG_TESTS}\n{liste}\n\n{_CONSIGNE}\n\n"


def fichiers_non_nommes(fichiers: list[str], texte_du_ticket: str) -> list[str]:
    """The files of `fichiers` the ticket text cites neither by path nor by name."""
    return [
        chemin
        for chemin in fichiers
        if chemin not in texte_du_ticket
        and chemin.rsplit("/", 1)[-1] not in texte_du_ticket
    ]


def remarque_config_non_nommee(fichiers: list[str]) -> str:
    """The blocking remark for test-config files the ticket does not ask to touch."""
    liste = ", ".join(f"`{chemin}`" for chemin in fichiers)
    return (
        "Ce ticket ne demande pas de modifier la configuration des tests : "
        f"retire ce changement ({liste})."
    )


def imposer_config_nommee(
    approved: bool, reason: str, review_text: str, non_nommes: list[str]
) -> tuple[bool, str, str]:
    """Turn the review into `CHANGES_REQUESTED` when unnamed config files changed.

    Takes and returns the `(approved, reason, rendered review)` triple of
    `juger_revue`, unchanged when `non_nommes` is empty. The remark opens the
    rendered review, ahead of what the reviewer wrote, so the coder reads it
    next round like any other (ticket-725).
    """
    if not non_nommes:
        return approved, reason, review_text
    remarque = remarque_config_non_nommee(non_nommes)
    _, _, reste = review_text.partition("\n")
    texte = f"CHANGES_REQUESTED\n\n## Remarques\n- {remarque}"
    if reste.strip():
        texte += f"\n\n{reste.strip()}"
    raison = remarque if approved or not reason else f"{reason}\n\n{remarque}"
    return False, raison, texte


def config_tests_du_diff(
    diff: str, projet: Path | None, journal: Callable[[str], None]
) -> list[str]:
    """The test-config files `diff` touches, named in one `journal` line if any.

    The project and its ancestors are the roots a diff path may be relative to.
    """
    racines = [projet.resolve(), *projet.resolve().parents] if projet else []
    fichiers = fichiers_de_config_touches(diff, racines)
    if fichiers:
        journal("configuration des tests modifiée : " + ", ".join(fichiers))
    return fichiers


def porte_config_nommee(
    revue: tuple[bool, str, str],
    touches: list[str],
    texte_du_ticket: str,
    journal: Callable[[str], None],
) -> tuple[bool, str, str]:
    """The review after the gate: refused if `touches` holds files the ticket omits.

    `revue` is the triple of `juger_revue`; `journal` receives one line naming
    the unrequested files when there are some.
    """
    non_nommes = fichiers_non_nommes(touches, texte_du_ticket)
    if non_nommes:
        journal("configuration des tests non demandée : " + ", ".join(non_nommes))
    return imposer_config_nommee(*revue, non_nommes)


def _touche_la_configuration(fichier: FichierModifie, racines: list[Path]) -> bool:
    nom = fichier.chemin.rsplit("/", 1)[-1]
    if any(fnmatch(nom, motif) for motif in _NOMS_SIGNALES):
        return True
    if nom not in ("pyproject.toml", "package.json"):
        return False
    lignes = _relire(fichier.chemin, racines)
    if lignes is None:
        return True
    if nom == "pyproject.toml":
        return any(_dans_section_toml(c, lignes) for c in fichier.changements)
    return any(_dans_scripts(c, lignes) for c in fichier.changements)


def _relire(chemin: str, racines: list[Path]) -> list[str] | None:
    for racine in racines:
        try:
            cible = racine / chemin
            if cible.is_file():
                return cible.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return None
    return None


def _entete(texte: str) -> str | None:
    trouve = _ENTETE_TOML.match(texte)
    return trouve.group("nom") if trouve else None


def _est_visee(section: str | None) -> bool:
    return section is not None and (
        section.startswith("tool.pytest") or section.startswith("tool.mypy")
    )


def _dans_section_toml(changement: Changement, lignes: list[str]) -> bool:
    """True if the change sits in (or is the header of) a pytest or mypy section."""
    if not changement.ajoute and _est_visee(_entete(changement.texte)):
        return True
    section: str | None = None
    for texte in lignes[: changement.limite]:
        section = _entete(texte) or section
    return _est_visee(section)


def _dans_scripts(changement: Changement, lignes: list[str]) -> bool:
    """True if the change sits in the `scripts` object of a package.json."""
    if _CLE_SCRIPTS.match(changement.texte):
        return True
    debut = next((i for i, t in enumerate(lignes, 1) if _CLE_SCRIPTS.match(t)), None)
    if debut is None:
        return False
    fin = _fin_du_bloc(lignes, debut)
    if changement.ajoute:
        return debut <= changement.limite <= fin
    return debut <= changement.limite < fin


def _fin_du_bloc(lignes: list[str], debut: int) -> int:
    """The 1-based line where the object opened on line `debut` closes."""
    profondeur = 0
    for numero in range(debut, len(lignes) + 1):
        texte = lignes[numero - 1]
        profondeur += texte.count("{") - texte.count("}")
        if profondeur <= 0:
            return numero
    return len(lignes)
