"""Jusqu'où un agent va seul, projet par projet — ticket-082.

ADR-022 disait : « l'agent pousse et ouvre la PR, il ne merge jamais ». Le
raisonnement tenait à ceci — merger, c'est décider qu'un travail est bon, et
c'est le seul point du pipeline où un humain tranche. Sur le dépôt d'un client,
il tient toujours.

Mais il ne vaut pas partout. Sur un dépôt personnel, avec une CI qui dit
objectivement si le code passe, laisser l'IDE aller jusqu'au bout est un choix
défendable — et c'est le choix de l'utilisateur à faire, pas une règle à
imposer.

La règle ne tombe donc pas : elle devient **conditionnelle**, et se déclare
projet par projet, exactement comme le mode des artefacts (ADR-021) et la
racine git (ADR-028). Trois fois maintenant que le dépôt utilise cette forme,
et pour la même raison : **le défaut protège, l'exception s'énonce**, et une
valeur inconnue ne désarme rien.
"""
import json
from enum import Enum
from pathlib import Path

from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)


class NiveauAutonomie(str, Enum):
    """Ce qu'un run a le droit de faire de son travail, une fois terminé."""

    #: Il commite sur sa branche et s'arrête. Rien ne part sur le distant.
    commit = "commit"
    #: Il pousse la branche et ouvre la pull request. L'humain merge.
    pr = "pr"
    #: Il merge aussi — **si et seulement si** la CI est verte.
    merge = "merge"


def lire_niveau(project_path: Path) -> NiveauAutonomie:
    """Le niveau déclaré dans `agents.json`, `commit` à défaut."""
    agents_json = project_path / "agents.json"
    if not agents_json.is_file():
        return NiveauAutonomie.commit
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _logger.warning("agents_json_illisible", extra={"path": str(agents_json)})
        return NiveauAutonomie.commit
    try:
        return NiveauAutonomie(data.get("autonomy", "commit"))
    except ValueError:
        _logger.warning("autonomie_inconnue", extra={"valeur": data.get("autonomy")})
        return NiveauAutonomie.commit


def peut_pousser(project_path: Path) -> bool:
    """True si ce projet autorise l'IDE à pousser sur le distant."""
    return lire_niveau(project_path) in (NiveauAutonomie.pr, NiveauAutonomie.merge)


def peut_merger(project_path: Path, ci_status: str) -> bool:
    """True si l'IDE peut merger : niveau déclaré **et** CI verte.

    Les deux conditions comptent. La déclaration dit que l'utilisateur accepte
    de renoncer à sa relecture sur ce dépôt ; la CI verte est le seul signal
    objectif dont l'IDE dispose pour savoir que le code passe. Merger sur une
    CI rouge casserait `main` pour tous les tickets suivants — et l'IDE perdrait
    le seul fait sur lequel il s'appuie.

    Une CI absente (`none`) ou en cours (`pending`) ne suffit pas : l'absence de
    signal n'est pas un signal favorable.
    """
    return lire_niveau(project_path) is NiveauAutonomie.merge and ci_status == "passing"
