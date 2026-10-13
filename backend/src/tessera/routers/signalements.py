"""Signalements : un défaut ou une idée repérés ailleurs deviennent un ticket ide-core — ticket-407."""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from tessera.config import settings
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.ticket_service import TicketService
from tessera.utils.project_id import validate_project_id

#: Le projet qui reçoit tous les signalements : le backlog de Tessera lui-même.
PROJET_CIBLE = "ide-core"

#: Ligne unique des critères : un signalement brut est refusé par le validateur,
#: le triage reste une étape humaine.
LIGNE_CRITERES = "- [ ] À écrire au triage"

router = APIRouter(tags=["signalements"])


class SignalementCreate(BaseModel):
    """Body of ``POST /signalements``."""

    projet: str
    nature: Literal["bug", "idee"]
    titre: str
    description: str
    contexte: str = ""

    @field_validator("titre", "description")
    @classmethod
    def _non_vide(cls, value: str) -> str:
        """Reject a value that is empty once stripped."""
        if not value.strip():
            raise ValueError("ne peut pas être vide")
        return value.strip()


def _corps_du_ticket(body: SignalementCreate, recu_le: str) -> str:
    """Assemble the ticket body: origin, description, optional context, criteria."""
    sections = [
        "## Signalement\n\n"
        f"- Projet source : {body.projet}\n"
        f"- Nature : {body.nature}\n"
        f"- Reçu le : {recu_le}",
        f"## Description\n\n{body.description}",
    ]
    if body.contexte.strip():
        sections.append(f"## Contexte\n\n{body.contexte.strip()}")
    sections.append(f"## Critères d'acceptation\n\n{LIGNE_CRITERES}")
    return "\n\n".join(sections) + "\n"


def _exiger_projet(project_id: str) -> None:
    """Raise 404 unless ``project_id`` names an existing project of the workspace."""
    if not validate_project_id(project_id) or not (
        settings.ide_workspace_dir / project_id
    ).is_dir():
        raise HTTPException(status_code=404, detail=f"Projet introuvable : {project_id}")


@router.post("/signalements", response_model=Ticket, status_code=201)
async def create_signalement(body: SignalementCreate) -> Ticket:
    _exiger_projet(body.projet)
    _exiger_projet(PROJET_CIBLE)
    recu_le = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ticket = Ticket(
        id="",
        title=body.titre,
        type=TicketType.fix if body.nature == "bug" else TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body=_corps_du_ticket(body, recu_le),
    )
    service = TicketService(settings.ide_workspace_dir / PROJET_CIBLE, PROJET_CIBLE)
    return await service.create_ticket(ticket)
