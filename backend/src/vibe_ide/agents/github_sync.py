from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from vibe_ide.services.github_service import GitHubIssue, GitHubService
from vibe_ide.services.ticket_service import TicketService

_TYPE_MAP: dict[str, TicketType] = {
    "feat": TicketType.feat,
    "feature": TicketType.feat,
    "fix": TicketType.fix,
    "bug": TicketType.fix,
    "chore": TicketType.chore,
    "design": TicketType.design,
    "docs": TicketType.docs,
    "documentation": TicketType.docs,
}


def _extract_type(labels: list[str]) -> TicketType:
    for label in labels:
        ticket_type = _TYPE_MAP.get(label.lower())
        if ticket_type is not None:
            return ticket_type
    return TicketType.feat


class GithubSyncAgent:
    def __init__(self, github_svc: GitHubService, ticket_svc: TicketService) -> None:
        self._github = github_svc
        self._tickets = ticket_svc

    async def run(self) -> list[Ticket]:
        issues = await self._github.list_agent_ready_issues()
        all_tickets = await self._tickets.list_tickets()
        existing_urls = {t.github_issue_url for t in all_tickets if t.github_issue_url}

        created: list[Ticket] = []
        for issue in issues:
            if issue.html_url in existing_urls:
                continue
            ticket = await self._sync_issue(issue)
            await self._github.remove_label(issue.number, "agent-ready")
            await self._github.add_label(issue.number, "synced-to-agent")
            created.append(ticket)

        return created

    async def _sync_issue(self, issue: GitHubIssue) -> Ticket:
        draft = Ticket(
            id=f"ticket-{issue.number:03d}",
            title=issue.title,
            type=_extract_type(issue.labels),
            status=TicketStatus.todo,
            priority=TicketPriority.medium,
            agent="orchestrateur",
            github_issue_url=issue.html_url,
            body=issue.body,
        )
        return await self._tickets.create_ticket(draft)
