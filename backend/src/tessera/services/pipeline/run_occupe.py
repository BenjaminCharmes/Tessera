"""The refusal of a second run on a busy project (ADR-038).

Sorti de `run_registry.py` pour qu'il tienne sous son plafond de longueur.
"""


class RunAlreadyInProgress(Exception):
    """A pipeline is already running on this project."""

    def __init__(self, project_id: str, ticket_id: str | None = None) -> None:
        self.project_id = project_id
        self.ticket_id = ticket_id
        en_cours = f" ({ticket_id})" if ticket_id else ""
        super().__init__(
            f"Un pipeline tourne déjà sur le projet '{project_id}'{en_cours}. "
            "Deux exécutions simultanées se marcheraient dessus dans le même "
            "arbre de travail : attends la fin de celle en cours."
        )
