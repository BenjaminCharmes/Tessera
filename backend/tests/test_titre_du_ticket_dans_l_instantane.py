"""Le titre du ticket voyage dans l'instantané — ticket-286.

`RunActif` gagne un champ `ticket_titre`, sérialisé dans l'instantané WebSocket.
Quand le ticket change (file), le titre est lu depuis le projet et inclus dans
l'événement `ticket_status_changed` pour les observateurs déjà connectés.
"""
import pytest

from tessera.services.event_hub import EventHub
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_executor import emetteur
from tessera.services.run_registry import RunActif


def _run(
    ticket_id: str | None = "ticket-001",
    ticket_titre: str | None = None,
) -> RunActif:
    return RunActif(run_id="r1", project_id="proj", ticket_id=ticket_id, ticket_titre=ticket_titre)


def _ticket_status_event(ticket_id: str) -> OrchestratorEvent:
    return OrchestratorEvent(
        type=EventType.TICKET_STATUS_CHANGED,
        ticket_id=ticket_id,
        data={"status": "in-progress"},
    )


# ---------------------------------------------------------------------------
# en_dict
# ---------------------------------------------------------------------------


def test_en_dict_contient_ticket_titre() -> None:
    run = _run(ticket_titre="Implémenter la feature X")
    corps = run.en_dict()
    assert "ticket_titre" in corps
    assert corps["ticket_titre"] == "Implémenter la feature X"


def test_en_dict_ticket_titre_est_none_quand_absent() -> None:
    run = _run()
    corps = run.en_dict()
    assert "ticket_titre" in corps
    assert corps["ticket_titre"] is None


# ---------------------------------------------------------------------------
# Mise à jour lors d'un TICKET_STATUS_CHANGED
# ---------------------------------------------------------------------------


async def test_titre_mis_a_jour_apres_ticket_status_changed() -> None:
    """Après un événement portant un nouveau ticket_id, le titre est lu."""
    run = _run(ticket_id="ticket-001", ticket_titre=None)

    async def titre_getter(ticket_id: str) -> str | None:
        return f"Titre de {ticket_id}"

    hub = EventHub()
    envoyer = emetteur(hub, run, None, titre_getter=titre_getter)
    await envoyer(_ticket_status_event("ticket-002"))

    assert run.ticket_titre == "Titre de ticket-002"


async def test_titre_non_mis_a_jour_si_ticket_identique() -> None:
    """Même ticket, statut qui change : le titre ne doit pas être relu inutilement."""
    run = _run(ticket_id="ticket-001", ticket_titre="Titre d'origine")
    appels: list[str] = []

    async def titre_getter(ticket_id: str) -> str | None:
        appels.append(ticket_id)
        return "Nouveau titre"

    hub = EventHub()
    envoyer = emetteur(hub, run, None, titre_getter=titre_getter)
    # Même ticket, statut qui change de todo → in-progress
    await envoyer(_ticket_status_event("ticket-001"))

    assert run.ticket_titre == "Titre d'origine"  # inchangé
    assert appels == []  # pas appelé


async def test_ticket_illisible_laisse_titre_a_none_sans_exception() -> None:
    """Une lecture qui échoue laisse `ticket_titre` à None sans interrompre le run."""
    run = _run(ticket_id="ticket-001", ticket_titre="Ancien titre")

    async def titre_getter(ticket_id: str) -> str | None:
        raise RuntimeError("Fichier manquant")

    hub = EventHub()
    envoyer = emetteur(hub, run, None, titre_getter=titre_getter)
    # Ne doit pas lever
    await envoyer(_ticket_status_event("ticket-002"))

    assert run.ticket_titre is None


# ---------------------------------------------------------------------------
# File : titre renseigné avant tout événement
# ---------------------------------------------------------------------------


def test_file_a_ticket_id_et_titre_avant_tout_evenement() -> None:
    """Une file connaît son premier ticket dès la création du RunActif."""
    run = RunActif(
        run_id="r1",
        project_id="proj",
        mode="queue",
        ticket_id="ticket-001",
        ticket_titre="Premier ticket de la file",
    )
    corps = run.en_dict()
    assert corps["ticket_id"] == "ticket-001"
    assert corps["ticket_titre"] == "Premier ticket de la file"
