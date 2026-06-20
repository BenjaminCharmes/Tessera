# Ce fichier est conservé pour la compatibilité mais les tests d'archivage
# sont maintenant dans test_ticket_service.py (via TicketService).
# On garde ici un smoke test minimal pour vérifier l'import.

from vibe_ide.services.ticket_service import TicketService


def test_ticket_service_importable() -> None:
    assert TicketService is not None
