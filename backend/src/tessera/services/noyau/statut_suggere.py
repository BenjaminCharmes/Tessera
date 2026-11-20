"""The status an agent suggests at the end of its answer."""
import re

from tessera.models.ticket import TicketStatus


def _parse_suggested_status(content: str) -> TicketStatus:
    """Extracts the suggested status from the agent's dedicated response section."""
    in_section = False
    for line in content.splitlines():
        if re.search(r"statut\s+sugg[eé]r[eé]", line, re.IGNORECASE):
            in_section = True
            continue
        if in_section and line.strip():
            upper = line.upper()
            if "IN_REVIEW" in upper or "IN-REVIEW" in upper:
                return TicketStatus.in_review
            if "BLOCKED" in upper:
                return TicketStatus.blocked
            if "DONE" in upper:
                return TicketStatus.done
            if "TODO" in upper:
                return TicketStatus.todo
            break
    return TicketStatus.in_review
