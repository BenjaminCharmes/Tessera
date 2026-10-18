"""Le script que `test_command` lance se protège en écriture — ticket-490.

`test_command` vient d'`agents.json`, que le hook de périmètre refuse déjà. Mais
sur un projet comme ide-core, la commande est `uv run python ../scripts/verifier.py` :
le testeur exécute ce script **depuis la branche du run**, et rien ne le
protégeait. Un codeur pouvait y retirer une étape (mypy, eslint…) dans le même
diff que celle-ci devait juger.

Le script est le premier argument de la commande qui désigne un fichier
existant, résolu depuis `pipeline.test_cwd`. `npm test` ou `uv run pytest` n'en
désignent aucun : rien de plus n'est alors protégé.

Le manifeste est lu ici avec `json` seul, sans passer par `project_loader` :
celui-ci importe le paquet `providers`, et un import en retour fermerait un
cycle.
"""
import json
import shlex
from pathlib import Path

#: Ce que l'agent lit pour comprendre pourquoi ce fichier-là est refusé.
MOTIF_SCRIPT = (
    "`{nom}` est le script que `test_command` lance pour juger ce run : le "
    "modifier dans le diff qu'il doit juger permettrait d'affaiblir sa propre "
    "vérification"
)


def _pipeline(project_path: Path) -> dict[str, object]:
    """La section `pipeline` d'`agents.json`, vide si absente ou illisible."""
    agents_json = project_path / "agents.json"
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    section = data.get("pipeline") if isinstance(data, dict) else None
    return section if isinstance(section, dict) else {}


def script_de_verification(project_path: Path) -> Path | None:
    """Le fichier que `test_command` exécute, ou None si elle n'en désigne aucun.

    Le premier argument qui est un fichier existant, cherché depuis
    `pipeline.test_cwd` (le dossier du projet à défaut).
    """
    pipeline = _pipeline(project_path)
    commande = pipeline.get("test_command")
    cwd = pipeline.get("test_cwd")
    if not isinstance(commande, str) or not commande.strip():
        return None
    try:
        jetons = shlex.split(commande)
        base = (project_path / (cwd if isinstance(cwd, str) and cwd else ".")).resolve()
        for jeton in jetons:
            candidat = (base / jeton).resolve()
            if candidat.is_file():
                return candidat
    except (OSError, ValueError):
        return None
    return None


def motif_du_script(cible: Path, script: Path | None) -> str | None:
    """Le motif de refus si `cible` est le script de vérification, sinon None."""
    if script is None or cible != script:
        return None
    return MOTIF_SCRIPT.format(nom=script.name)
