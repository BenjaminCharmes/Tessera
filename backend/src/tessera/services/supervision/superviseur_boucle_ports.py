"""What the supervisor's background task reads and is given — ticket-859, ADR-080.

`Candidat` is one thing the supervisor could do on one exact state; the loop
neither knows how it is carried out nor what it writes (that is `intervenir`,
ticket-854). `projets_supervises` names the projects that declared the
`superviseur` role active; a `professional` project is never one of them
(ADR-080). `depense_du_jour` reads the supervisor's own calls in the usage base.
"""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.services.projets.manifeste import lire_chaine
from tessera.services.projets.project_loader import load_agents_config
from tessera.services.projets.superviseur_declaration import load_config_superviseur
from tessera.services.supervision.anomalies.lecture_base import ouvrir_en_lecture
from tessera.services.supervision.intervention import Resultat
from tessera.services.supervision.superviseur_actions import Action, Decision
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

ROLE = "superviseur"


@dataclass(frozen=True)
class ProjetSupervise:
    """A project whose `agents.json` declares the supervisor active."""

    project_id: str
    path: Path
    config: ConfigSuperviseur


@dataclass(frozen=True)
class Candidat:
    """One action on one target and one exact state (`sha`), with how to carry it out.

    `sans_modele`: the action calls no model, so the daily budget never holds it
    back. `executer` returns the decisions it took, and raises when it failed.
    """

    project_id: str
    action: Action
    cible: str
    sha: str
    sans_modele: bool
    executer: Callable[[], Awaitable[list[Decision]]]

    @property
    def cle(self) -> str:
        """The idempotence key `action:projet/cible:sha`."""
        return f"{self.action.value}:{self.project_id}/{self.cible}:{self.sha}"


#: Lists what the supervisor could do on a project, now.
Collecter = Callable[[str, Path], Awaitable[list[Candidat]]]
ProjetsSupervises = Callable[[], list[ProjetSupervise]]
#: Writes the journal line of the « À toi » decisions of one key (ticket-868); `None` if none to write.
Journaliser = Callable[[str, list[Decision]], Awaitable[Resultat | None]]
DepenseDuJour = Callable[[], Awaitable[float]]


def _declare_actif(dossier: Path) -> bool:
    try:
        agents = load_agents_config(dossier)
    except Exception:  # noqa: BLE001 — un manifeste refusé n'active rien
        _logger.warning("superviseur_manifeste_refuse", extra={"project": dossier.name})
        return False
    return any(agent.role == ROLE and agent.active for agent in agents)


def projets_supervises(workspace: Path) -> list[ProjetSupervise]:
    """The workspace projects that declare the `superviseur` role active, never a professional one."""
    if not workspace.is_dir():
        return []
    projets: list[ProjetSupervise] = []
    for dossier in sorted(workspace.iterdir()):
        if not dossier.is_dir() or dossier.name.startswith(".") or not _declare_actif(dossier):
            continue
        if lire_chaine(dossier, "confidentiality") == "professional":
            continue
        projets.append(ProjetSupervise(dossier.name, dossier, load_config_superviseur(dossier)))
    return projets


async def depense_du_jour(db_path: Path | str, maintenant: datetime) -> float:
    """What the `superviseur` role spent since 00:00 UTC, in USD, from `agent_calls`."""
    debut = maintenant.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    requete = "SELECT COALESCE(SUM(cost_usd), 0) FROM agent_calls WHERE role = ? AND created_at >= ?"
    async with ouvrir_en_lecture(db_path) as db, db.execute(requete, (ROLE, debut.isoformat())) as curseur:
        ligne = await curseur.fetchone()
    return float(ligne[0]) if ligne else 0.0
