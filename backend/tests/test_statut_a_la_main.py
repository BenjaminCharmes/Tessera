"""Changing a ticket's status by hand announces it — ticket-194.

Le PATCH existait et déplaçait le fichier, mais rien ne le disait aux
onglets ouverts : la liste et le Kanban attendaient le prochain sondage.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType

_TICKET_MD = """---
id: ticket-001
title: "Un ticket"
type: feat
status: blocked
priority: medium
agent: codeur
---

# ticket-001 — Un ticket
"""


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    for status in ("todo", "in-progress", "in-review", "done", "blocked"):
        (project / "tickets" / status).mkdir(parents=True)
    (project / "tickets" / "blocked" / "ticket-001.md").write_text(_TICKET_MD, encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


def test_le_patch_publie_ticket_status_changed_sur_le_canal(workspace: Path) -> None:
    abonnement = EVENT_HUB.subscribe()
    try:
        resp = TestClient(app).patch(
            "/api/v1/projects/mon-projet/tickets/ticket-001", json={"status": "todo"}
        )
        evenements = [e for e in abonnement.vider() if e.type == EventType.TICKET_STATUS_CHANGED]
    finally:
        EVENT_HUB.retirer(abonnement)

    assert resp.status_code == 200
    assert (workspace / "mon-projet" / "tickets" / "todo" / "ticket-001.md").is_file()
    [evenement] = evenements
    assert evenement.project_id == "mon-projet"
    assert evenement.ticket_id == "ticket-001"
    assert evenement.data == {"status": "todo", "manuel": True}


def test_un_ticket_introuvable_ne_publie_rien(workspace: Path) -> None:
    abonnement = EVENT_HUB.subscribe()
    try:
        resp = TestClient(app).patch(
            "/api/v1/projects/mon-projet/tickets/ticket-999", json={"status": "todo"}
        )
        evenements = abonnement.vider()
    finally:
        EVENT_HUB.retirer(abonnement)

    assert resp.status_code == 404
    assert evenements == []
