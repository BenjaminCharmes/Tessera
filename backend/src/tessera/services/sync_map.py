import json
from dataclasses import dataclass
from pathlib import Path

_FILENAME = "github-sync-map.json"


@dataclass
class SyncEntry:
    issue: int | None = None
    pr: int | None = None


class SyncMapService:
    """Persiste et interroge le mapping ticket_id ↔ { issue, pr }."""

    def load(self, project_path: Path) -> dict[str, SyncEntry]:
        map_file = project_path / "memory" / _FILENAME
        if not map_file.exists():
            return {}
        try:
            data = json.loads(map_file.read_text(encoding="utf-8"))
            result: dict[str, SyncEntry] = {}
            for k, v in data.items():
                if isinstance(v, int):
                    # backward compat: old format stored a plain issue number
                    result[k] = SyncEntry(issue=v)
                elif isinstance(v, dict):
                    issue_raw = v.get("issue")
                    pr_raw = v.get("pr")
                    result[k] = SyncEntry(
                        issue=int(issue_raw) if isinstance(issue_raw, int) else None,
                        pr=int(pr_raw) if isinstance(pr_raw, int) else None,
                    )
            return result
        except Exception:
            return {}

    def save(self, project_path: Path, mapping: dict[str, SyncEntry]) -> None:
        memory_dir = project_path / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        data = {k: {"issue": e.issue, "pr": e.pr} for k, e in mapping.items()}
        (memory_dir / _FILENAME).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def ticket_for_issue(
        self, mapping: dict[str, SyncEntry], issue_number: int
    ) -> str | None:
        for ticket_id, entry in mapping.items():
            if entry.issue == issue_number:
                return ticket_id
        return None

    def issue_for_ticket(
        self, mapping: dict[str, SyncEntry], ticket_id: str
    ) -> int | None:
        entry = mapping.get(ticket_id)
        return entry.issue if entry else None

    def pr_for_ticket(
        self, mapping: dict[str, SyncEntry], ticket_id: str
    ) -> int | None:
        entry = mapping.get(ticket_id)
        return entry.pr if entry else None

    def set_pr(
        self,
        mapping: dict[str, SyncEntry],
        ticket_id: str,
        pr_number: int,
    ) -> dict[str, SyncEntry]:
        """Returns a new mapping with pr_number set for the given ticket."""
        existing = mapping.get(ticket_id, SyncEntry())
        return {**mapping, ticket_id: SyncEntry(issue=existing.issue, pr=pr_number)}
