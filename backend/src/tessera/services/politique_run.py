"""Ce qu'un run a le droit de faire, figé avant le premier agent — ticket-119.

`autonomy`, `git_root`, `artifacts`, `test_command` et `base_branch` bornent le
run : jusqu'où il livre, où il stage, ce qui reste hors du dépôt, ce qui rend la
suite verte, et sur quelle branche il rejoue.
Chaque service les relisait dans `agents.json` **au moment d'agir** — donc
après le passage du codeur. Or `agents.json` est sous la racine du projet, et
un agent a `Edit` : un ticket pouvait déclarer `merge` + `ancestor` au milieu
du run, et la livraison obéissait au fichier réécrit. ADR-029 et ADR-031
tenaient sur le papier, pas en exécution.

La politique se lit donc **une fois**, par l'orchestrateur, et voyage jusqu'aux
services qui en dépendent. Ce qu'un agent écrit dans `agents.json` ne vaut
qu'au run suivant — et le hook de périmètre le lui refuse de toute façon.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tessera.services.artifacts import ArtifactMode, read_artifact_mode
from tessera.services.autonomie import NiveauAutonomie, lire_niveau
from tessera.services.project_loader import load_pipeline_config

#: Méthodes de merge acceptées par GitHub.
MergeMethod = Literal["squash", "merge", "rebase"]

#: Valeurs reconnues — toute autre valeur retombe sur le défaut fermé.
_MERGE_METHODS_VALIDES: frozenset[str] = frozenset({"squash", "merge", "rebase"})

#: La seule valeur qui ouvre le dépôt parent (ADR-028). Une valeur inconnue
#: ne désarme rien.
_GIT_ROOT_ANCESTOR = "ancestor"


@dataclass(frozen=True)
class PolitiqueRun:
    """Les réglages d'`agents.json` qui bornent un run."""

    autonomy: NiveauAutonomie = NiveauAutonomie.commit
    git_root: str | None = None
    artifacts: ArtifactMode = "local"
    test_command: str | None = None
    #: La branche sur laquelle la livraison rejoue. `None` — le projet ne
    #: déclare rien — laisse l'appelant choisir son repli : rendre le défaut
    #: global ici empêcherait de distinguer « non déclaré » de « déclaré
    #: develop » (ticket-166).
    base_branch: str | None = None
    #: Le projet déclare n'avoir pas de CI, et accepte que le verdict du
    #: pipeline suffise à merger (ADR-045). Faux par défaut : le défaut
    #: protège, l'exception s'énonce.
    merge_without_ci: bool = False
    #: Valeur de la clef `confidentiality` dans agents.json. `None` si absente.
    #: Seule la valeur `"professional"` exempte le projet du contrôle des
    #: termes interdits (ADR-048).
    confidentialite: str | None = None
    #: Méthode de merge transmise à GitHub pour les PR de ticket (ticket-265).
    #: Absente ou inconnue dans agents.json : `squash`. Le défaut protège :
    #: squash est la convention de ce dépôt (CLAUDE.md, section Git).
    merge_method: MergeMethod = "squash"

    @classmethod
    def lire(cls, project_path: Path) -> "PolitiqueRun":
        """Lit la politique **maintenant** ; l'appelant la garde pour tout le run.

        Réutilise les lecteurs existants plutôt que d'en écrire un cinquième :
        chacun porte son défaut fermé et son traitement du fichier illisible.
        """
        return cls(
            autonomy=lire_niveau(project_path),
            git_root=_lire_git_root(project_path),
            artifacts=read_artifact_mode(project_path),
            test_command=load_pipeline_config(project_path).test_command,
            base_branch=_lire_chaine(project_path, "base_branch"),
            merge_without_ci=_lire_booleen(project_path, "merge_without_ci"),
            confidentialite=_lire_chaine(project_path, "confidentiality"),
            merge_method=_lire_merge_method(project_path),
        )

    @property
    def exempte_controle_termes(self) -> bool:
        """True ssi le projet se déclare professionnel (ADR-048).

        Un dépôt professionnel peut légitimement contenir des noms d'employeur
        ou de client dans son code. Seule la valeur exacte ``"professional"``
        ouvre l'exemption — une valeur inconnue ne la désarme pas.
        """
        return self.confidentialite == "professional"

    @property
    def dans_le_depot_parent(self) -> bool:
        """True si le projet travaille dans le dépôt qui le contient (ADR-028)."""
        return self.git_root == _GIT_ROOT_ANCESTOR

    def racine_ecriture(self, project_path: Path) -> Path:
        """Le dossier sous lequel les agents de ce run ont le droit d'écrire.

        Le dossier du projet, ou le dépôt qui le contient s'il l'a déclaré —
        le dépôt, pas le simple parent : `projects/` ne serait ni la bonne
        racine ni une racine qui veut dire quelque chose (ADR-031).
        """
        racine = project_path.resolve()
        if not self.dans_le_depot_parent:
            return racine
        for candidat in racine.parents:
            if (candidat / ".git").exists():
                return candidat
        return racine.parent


def _lire_git_root(project_path: Path) -> str | None:
    return _lire_chaine(project_path, "git_root")


def _lire_booleen(project_path: Path, clef: str) -> bool:
    """Un booléen du manifeste. Tout ce qui n'est pas `True` ne désarme rien.

    Une chaîne « oui », un entier, une clef absente : le défaut fermé d'ADR-023
    vaut ici aussi — une valeur qu'on ne comprend pas ne lève pas une garde.
    """
    agents_json = project_path / "agents.json"
    if not agents_json.is_file():
        return False
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return data.get(clef) is True


def _lire_merge_method(project_path: Path) -> MergeMethod:
    """La méthode de merge déclarée dans agents.json, ou `squash` par défaut.

    Une valeur absente, illisible ou inconnue retombe sur `squash` : le défaut
    protège, l'exception s'énonce (ADR-023). `squash` est la convention de
    ticket → develop sur ce dépôt (CLAUDE.md, section Git).
    """
    valeur = _lire_chaine(project_path, "merge_method")
    if valeur in _MERGE_METHODS_VALIDES:
        return valeur  # type: ignore[return-value]
    return "squash"


def _lire_chaine(project_path: Path, clef: str) -> str | None:
    """Une chaîne du manifeste, `None` si absente, illisible ou mal typée.

    Un seul lecteur pour les clefs de cette forme : `git_root` en avait le
    sien, et `base_branch` aurait été le deuxième à répéter les mêmes quatre
    gardes.
    """
    agents_json = project_path / "agents.json"
    if not agents_json.is_file():
        return None
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    valeur = data.get(clef)
    return valeur if isinstance(valeur, str) else None
