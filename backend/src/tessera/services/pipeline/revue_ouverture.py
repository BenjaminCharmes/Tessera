"""Ouverture d'une revue de projet : la fiche de synthèse et son plafond — ticket-864, ADR-080."""
from tessera.config import settings
from tessera.models.ticket import Ticket
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.pipeline.revue_projet import plafond_de_revue, reserver_numero, ticket_de_revue
from tessera.services.pipeline.run_dans_worktree import base_du_projet
from tessera.services.pipeline.run_registry import RUN_REGISTRY, RunActif


class NumeroNonReserve(Exception):
    """The number of the summary ticket could not be reserved."""


async def fiche_de_revue(project_id: str, run: RunActif) -> tuple[Ticket, float]:
    """Reserve the number of the review's summary ticket, give it to the run.

    Réservé sous le verrou du projet : un projet occupé a déjà répondu 409, sans
    prendre de numéro. Un échec libère le projet (ADR-038) et lève
    `NumeroNonReserve`. Rend la fiche et le plafond de dépense, figé ici.
    """
    project_path = settings.ide_workspace_dir / project_id
    try:
        base = base_du_projet(PolitiqueRun.lire(project_path))
        numero = await reserver_numero(project_path, base)
    except Exception as exc:  # noqa: BLE001 — rien n'a démarré : on libère le projet
        RUN_REGISTRY.fermer(run.run_id)
        raise NumeroNonReserve(str(exc)) from exc
    fiche = ticket_de_revue(project_id, numero)
    run.ticket_id = run.ticket_titre_de = fiche.id
    return fiche, plafond_de_revue(run.reglages.run_max_budget_usd)
