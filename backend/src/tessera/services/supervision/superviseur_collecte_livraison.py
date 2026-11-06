"""The production sources of the two model-free actions — ticket-867, ADR-080.

`Collecteur` adds to the triage and decision candidates the two that call no
model: the hand-back of an approved PR (`reconfier_pr`) and the restart of a
queue cut by the infrastructure (`relancer_file`). Each source is read on its
own: one that fails is logged and skipped, the others still offer theirs.

- The hand-back is read only on a project in `merge` autonomy, as the resume at
  startup does (ticket-510): below it the watcher never merges, so there is
  nothing to give back. The watcher stays the only one to merge (ADR-039).
- The restart needs the entry that opens a queue (`rouvrir`); without it nothing
  is offered. One `SuperviseurFile` lives per project in the process, because
  « once per cause » is remembered in it: a queue reopened and cut again by the
  same cause goes to « À toi » instead of a third attempt.
- The real subscription quota has no reader outside a run: here it is unknown,
  and an unknown quota never blocks (ADR-020). The daily spend still does.
"""
from collections.abc import Awaitable
from datetime import UTC, datetime
from pathlib import Path

from tessera.config import settings
from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.models.ticket import TicketStatus
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.livraison.ci_watcher import CI_WATCHER
from tessera.services.livraison.reprise_outils import prs_a_reprendre
from tessera.services.livraison.surveillance_run import surveillance_pour, workflow_de_lecture
from tessera.services.noyau.event_hub import EVENT_HUB, EventHub
from tessera.services.pipeline.run_registry import RUN_REGISTRY, RunRegistry
from tessera.services.projets.autonomie import NiveauAutonomie
from tessera.services.projets.superviseur_declaration import load_config_superviseur
from tessera.services.projets.ticket_service import TicketService
from tessera.services.supervision.superviseur_boucle import SuperviseurBoucle
from tessera.services.supervision.superviseur_boucle_etat import NOM_FICHIER, EtatIdempotence
from tessera.services.supervision.superviseur_boucle_ports import Candidat, depense_du_jour, projets_supervises
from tessera.services.supervision.superviseur_collecte import collecter
from tessera.services.supervision.superviseur_collecte_file import SourcesFile, candidats_file, files_coupees
from tessera.services.supervision.superviseur_collecte_pr import RunPousse, SourcesPr, candidats_pr, runs_pousses
from tessera.services.supervision.superviseur_file import Rouvrir, SuperviseurFile
from tessera.services.supervision.superviseur_pr import SuperviseurPr
from tessera.utils.exceptions import decrire_exception
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def _superviseur_pr(project_id: str, politique: PolitiqueRun) -> SuperviseurPr:
    lecture = workflow_de_lecture(project_id, politique)

    async def etat(_projet: str, pr: int) -> str:
        return await lecture.pr_state(pr)

    async def tete(_projet: str, pr: int) -> str | None:
        return await lecture.tete_pr(pr)

    return SuperviseurPr(CI_WATCHER, surveillance_pour(project_id, politique=politique), etat, tete)


def _sources_pr(project_id: str, politique: PolitiqueRun) -> SourcesPr:
    lecture = workflow_de_lecture(project_id, politique)

    async def runs() -> list[RunPousse]:
        return await runs_pousses(settings.ide_db_path, project_id)

    async def ouvertes() -> dict[str, int]:
        return dict(prs_a_reprendre(await lecture.prs_ouvertes(), lecture.base_branch))

    return SourcesPr(runs, ouvertes, lecture.tete_pr)


async def _termines(project_id: str, project_path: Path) -> set[str]:
    """The tickets a restart never takes again: done or cancelled."""
    service = TicketService(project_path, project_id)
    tickets = await service.list_tickets() + await service.list_archived_tickets()
    return {t.id for t in tickets if t.status in (TicketStatus.done, TicketStatus.cancelled)}


class Collecteur:
    """The candidates of a project: triage, decision, hand-back of a PR, restart of a queue."""

    def __init__(self, rouvrir: Rouvrir | None = None, hub: EventHub = EVENT_HUB) -> None:
        self._rouvrir = rouvrir
        self._hub = hub
        self._files: dict[str, SuperviseurFile] = {}

    async def __call__(self, project_id: str, project_path: Path) -> list[Candidat]:
        candidats = await collecter(project_id, project_path)
        candidats.extend(await self._source("pr", project_id, self._livraison(project_id, project_path)))
        candidats.extend(await self._source("file", project_id, self._file(project_id, project_path)))
        return candidats

    async def _source(self, nom: str, project_id: str, lecture: Awaitable[list[Candidat]]) -> list[Candidat]:
        try:
            return await lecture
        except Exception as exc:  # noqa: BLE001 — une source en panne n'empêche pas les autres
            _logger.warning(
                f"superviseur_collecte_{nom}_en_echec", extra={"project": project_id, "erreur": decrire_exception(exc)}
            )
            return []

    async def _livraison(self, project_id: str, project_path: Path) -> list[Candidat]:
        politique = PolitiqueRun.lire(project_path)
        if politique.autonomy is not NiveauAutonomie.merge:
            return []
        return await candidats_pr(
            project_id, _sources_pr(project_id, politique), lambda: _superviseur_pr(project_id, politique), self._hub.publish
        )

    async def _file(self, project_id: str, project_path: Path) -> list[Candidat]:
        config = load_config_superviseur(project_path)
        if self._rouvrir is None or not config.relance_file:
            return []
        sources = SourcesFile(lambda: files_coupees(
            settings.ide_db_path, project_id, lambda: _termines(project_id, project_path)
        ))
        rouvrir = self._rouvrir
        return await candidats_file(project_id, config, sources, lambda: self._superviseur_file(project_id, config, rouvrir))

    def _superviseur_file(self, project_id: str, config: ConfigSuperviseur, rouvrir: Rouvrir) -> SuperviseurFile:
        """The project's restart service, the same one for the life of the process."""
        if project_id not in self._files:
            self._files[project_id] = SuperviseurFile(config, rouvrir, RUN_REGISTRY.projet_occupe, _depense, _quota_inconnu)
        return self._files[project_id]


async def _depense() -> float:
    return await depense_du_jour(settings.ide_db_path, datetime.now(UTC))


async def _quota_inconnu() -> bool:
    return False


def boucle_du_superviseur(
    registre: RunRegistry = RUN_REGISTRY, hub: EventHub = EVENT_HUB, rouvrir: Rouvrir | None = None
) -> SuperviseurBoucle:
    """The production loop: the workspace's declared projects, the usage base, the state file.

    `rouvrir` opens a queue (the entry of ADR-041); without it no restart is offered.
    """
    return SuperviseurBoucle(
        registre,
        hub,
        lambda: projets_supervises(settings.ide_workspace_dir),
        Collecteur(rouvrir, hub),
        _depense,
        EtatIdempotence(settings.ide_state_dir / NOM_FICHIER),
    )
