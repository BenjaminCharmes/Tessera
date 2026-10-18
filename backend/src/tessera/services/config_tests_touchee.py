"""Un diff qui touche la configuration des tests le dit au reviewer — ticket-490.

Modifier `conftest.py`, la section pytest ou mypy de `pyproject.toml`, les
scripts de `package.json` est souvent légitime : on ne l'interdit donc pas. Mais
c'est aussi la façon la plus discrète d'affaiblir la vérification qui juge le
diff. La liste est fermée ; quand elle correspond, le reviewer le lit en tête
de son message, avec les fichiers nommés.

Pour `pyproject.toml` et `package.json`, seul un changement **dans** la section
visée compte : on relit donc le fichier sur le disque pour savoir où il tombe.
Un fichier qu'on ne peut plus relire (supprimé) est signalé, par prudence.
"""
import re
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
