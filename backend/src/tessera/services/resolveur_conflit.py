"""Faire résoudre un conflit de rebase par un agent — ticket-090.

ticket-083 détectait les conflits, les nommait et annulait proprement. C'était
honnête mais s'arrêtait là : sur un projet censé aller jusqu'au merge, un
conflit rendait la main pour un travail de cinq minutes.

Ce service fait la tentative. Il ne décide rien de ce qui suit : c'est
`GitWorkspaceService` qui vérifie l'arbre et annule tout au moindre doute, et
c'est `LivraisonService` qui refuse de merger une résolution que personne n'a
relue — même sur un projet qui déclare `merge`. Un conflit est l'endroit où
deux intentions divergent ; c'est le pire endroit pour deviner.
"""
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.agent_runner import AgentRunner

_logger = get_logger(__name__)

_ROLE = "resolveur-conflit"

#: Au-delà, on n'envoie pas le fichier entier : un conflit se lit autour de ses
#: marqueurs, et un fichier de dix mille lignes noierait le reste du prompt.
_TAILLE_MAX = 20_000


class ResolveurConflitService:
    def __init__(self, runner: "AgentRunner", project_path: Path) -> None:
        self._runner = runner
        self._project_path = project_path

    async def resoudre(self, fichiers: tuple[str, ...]) -> None:
        """Demande à l'agent de réécrire les fichiers en conflit.

        Ne rend rien et ne lève pas : la seule preuve qui compte est l'état de
        l'arbre après coup, et c'est `GitWorkspaceService` qui la lit.
        """
        if not fichiers:
            return

        _logger.info("resolution_de_conflit", extra={"fichiers": fichiers})
        await self._runner.run(
            role=_ROLE,
            ticket=self._ticket(fichiers),
            project_context="",
        )

    def _ticket(self, fichiers: tuple[str, ...]) -> Ticket:
        """Un ticket de synthèse : le runner en attend un, il n'en existe pas.

        Le contenu marqué part dans le prompt plutôt que d'être laissé à lire
        à l'agent : c'est un tour d'outil de moins, et une occasion de moins de
        se tromper de fichier.
        """
        morceaux: list[str] = [
            "Un rebase a laissé des conflits. Réécris chaque fichier ci-dessous "
            "dans son état final, sans marqueur de conflit.",
            "",
            "Garde les deux intentions quand elles sont compatibles. Quand elles "
            "ne le sont pas, garde celle de la branche du ticket et signale-le.",
            "",
            "N'utilise aucune commande git : le rebase est en cours et c'est "
            "l'IDE qui le termine.",
            "",
        ]
        for chemin in fichiers:
            fichier = self._project_path / chemin
            contenu = (
                fichier.read_text(encoding="utf-8", errors="replace")[:_TAILLE_MAX]
                if fichier.is_file()
                else "_(fichier introuvable — il a été supprimé d'un côté)_"
            )
            morceaux.append(f"## {chemin}\n\n```\n{contenu}\n```\n")

        return Ticket(
            id="conflit",
            title="Résoudre un conflit de rebase",
            type=TicketType.fix,
            status=TicketStatus.in_progress,
            priority=TicketPriority.high,
            agent=_ROLE,
            body="\n".join(morceaux),
            project_id=self._project_path.name,
            file_path=str(self._project_path / "conflit.md"),
            created="",
        )
