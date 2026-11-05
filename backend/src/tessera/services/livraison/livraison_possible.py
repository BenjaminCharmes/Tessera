"""Un run qui doit livrer peut-il le faire ? — ticket-413.

Un projet en `autonomy: pr` ou `merge` pousse sa branche et ouvre une PR. Sans
dépôt distant déclaré ou sans jeton, la livraison s'arrête à la fin du run,
après un tour complet d'agents. La condition est connue dès le lancement : on
la lit ici, avant de réserver le projet.
"""
from pathlib import Path

from tessera.services.autonomie import peut_pousser
from tessera.services.project_loader import load_project


def raison_de_refus_livraison(project_path: Path, github_token: str) -> str | None:
    """Return why a run could not be delivered, or `None` when it can.

    Only projects that push (`pr` or `merge`) are checked. The token is not
    tested against the repository: that is a network call, and the delivery
    reports it clearly.
    """
    if not project_path.is_dir() or not peut_pousser(project_path):
        return None
    manque: list[str] = []
    if not load_project(project_path).github_remote:
        manque.append("`github_remote` n'est pas déclaré : ajoute-le dans agents.json")
    if not github_token:
        manque.append("aucun jeton : renseigne GITHUB_TOKEN")
    if not manque:
        return None
    return (
        "Ce projet livre seul (autonomy `pr` ou `merge`) mais GitHub n'est pas "
        "configuré : " + " ; ".join(manque) + ". "
        'Ou déclare `"autonomy": "commit"` pour ne rien pousser.'
    )
