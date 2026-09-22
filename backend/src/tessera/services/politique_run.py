"""Ce qu'un run a le droit de faire, figé avant le premier agent — ticket-119.

`autonomy`, `git_root`, `artifacts` et `test_command` bornent le run : jusqu'où
il livre, où il stage, ce qui reste hors du dépôt, ce qui rend la suite verte.
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

from tessera.services.artifacts import ArtifactMode, read_artifact_mode
from tessera.services.autonomie import NiveauAutonomie, lire_niveau
from tessera.services.project_loader import load_pipeline_config

#: La seule valeur qui ouvre le dépôt parent (ADR-028). Une valeur inconnue
#: ne désarme rien.
_GIT_ROOT_ANCESTOR = "ancestor"


@dataclass(frozen=True)
class PolitiqueRun:
    """Les quatre réglages d'`agents.json` qui bornent un run."""

    autonomy: NiveauAutonomie = NiveauAutonomie.commit
    git_root: str | None = None
    artifacts: ArtifactMode = "local"
    test_command: str | None = None

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
        )

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
    agents_json = project_path / "agents.json"
    if not agents_json.is_file():
        return None
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    valeur = data.get("git_root")
    return valeur if isinstance(valeur, str) else None
