import json
from pathlib import Path

import pytest

from vibe_ide.services.sync_map import SyncEntry, SyncMapService


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    (tmp_path / "memory").mkdir()
    return tmp_path


def _svc() -> SyncMapService:
    return SyncMapService()


# ------------------------------------------------------------------
# load
# ------------------------------------------------------------------


def test_load_returns_empty_when_no_file(tmp_project: Path) -> None:
    assert _svc().load(tmp_project) == {}


def test_load_returns_empty_when_memory_dir_missing(tmp_path: Path) -> None:
    assert _svc().load(tmp_path) == {}


def test_load_returns_mapping_new_format(tmp_project: Path) -> None:
    data = {"ticket-042": {"issue": 7, "pr": None}, "ticket-043": {"issue": 12, "pr": 5}}
    (tmp_project / "memory" / "github-sync-map.json").write_text(
        json.dumps(data), encoding="utf-8"
    )
    result = _svc().load(tmp_project)
    assert result["ticket-042"] == SyncEntry(issue=7, pr=None)
    assert result["ticket-043"] == SyncEntry(issue=12, pr=5)


def test_load_backward_compat_plain_int(tmp_project: Path) -> None:
    data = {"ticket-042": 7, "ticket-043": 12}
    (tmp_project / "memory" / "github-sync-map.json").write_text(
        json.dumps(data), encoding="utf-8"
    )
    result = _svc().load(tmp_project)
    assert result["ticket-042"] == SyncEntry(issue=7, pr=None)
    assert result["ticket-043"] == SyncEntry(issue=12, pr=None)


def test_load_returns_empty_on_corrupt_file(tmp_project: Path) -> None:
    (tmp_project / "memory" / "github-sync-map.json").write_text(
        "not-json", encoding="utf-8"
    )
    assert _svc().load(tmp_project) == {}


def test_load_skips_unknown_value_types(tmp_project: Path) -> None:
    data: dict = {"ticket-001": {"issue": 1, "pr": None}, "ticket-bad": "abc"}
    (tmp_project / "memory" / "github-sync-map.json").write_text(
        json.dumps(data), encoding="utf-8"
    )
    result = _svc().load(tmp_project)
    assert "ticket-001" in result
    assert "ticket-bad" not in result


# ------------------------------------------------------------------
# save
# ------------------------------------------------------------------


def test_save_creates_file(tmp_path: Path) -> None:
    mapping = {"ticket-001": SyncEntry(issue=5, pr=None)}
    _svc().save(tmp_path, mapping)
    written = json.loads((tmp_path / "memory" / "github-sync-map.json").read_text())
    assert written == {"ticket-001": {"issue": 5, "pr": None}}


def test_save_creates_memory_dir_if_missing(tmp_path: Path) -> None:
    _svc().save(tmp_path, {"ticket-001": SyncEntry(issue=1)})
    assert (tmp_path / "memory").is_dir()


def test_save_stores_pr_number(tmp_path: Path) -> None:
    mapping = {"ticket-001": SyncEntry(issue=5, pr=15)}
    _svc().save(tmp_path, mapping)
    written = json.loads((tmp_path / "memory" / "github-sync-map.json").read_text())
    assert written["ticket-001"]["pr"] == 15


def test_save_overwrites_existing(tmp_project: Path) -> None:
    svc = _svc()
    svc.save(tmp_project, {"ticket-001": SyncEntry(issue=1)})
    svc.save(tmp_project, {"ticket-002": SyncEntry(issue=2)})
    result = json.loads((tmp_project / "memory" / "github-sync-map.json").read_text())
    assert list(result.keys()) == ["ticket-002"]


def test_save_roundtrips_with_load(tmp_project: Path) -> None:
    svc = _svc()
    original = {
        "ticket-042": SyncEntry(issue=7, pr=None),
        "ticket-043": SyncEntry(issue=12, pr=3),
    }
    svc.save(tmp_project, original)
    assert svc.load(tmp_project) == original


# ------------------------------------------------------------------
# ticket_for_issue
# ------------------------------------------------------------------


def test_ticket_for_issue_returns_ticket_id() -> None:
    mapping = {
        "ticket-042": SyncEntry(issue=7),
        "ticket-043": SyncEntry(issue=12),
    }
    assert _svc().ticket_for_issue(mapping, 7) == "ticket-042"
    assert _svc().ticket_for_issue(mapping, 12) == "ticket-043"


def test_ticket_for_issue_returns_none_when_not_found() -> None:
    assert _svc().ticket_for_issue({"ticket-001": SyncEntry(issue=1)}, 99) is None


def test_ticket_for_issue_returns_none_on_empty_mapping() -> None:
    assert _svc().ticket_for_issue({}, 1) is None


# ------------------------------------------------------------------
# issue_for_ticket
# ------------------------------------------------------------------


def test_issue_for_ticket_returns_issue_number() -> None:
    mapping = {
        "ticket-042": SyncEntry(issue=7),
        "ticket-043": SyncEntry(issue=12),
    }
    assert _svc().issue_for_ticket(mapping, "ticket-042") == 7
    assert _svc().issue_for_ticket(mapping, "ticket-043") == 12


def test_issue_for_ticket_returns_none_when_not_found() -> None:
    assert _svc().issue_for_ticket({"ticket-001": SyncEntry(issue=1)}, "ticket-999") is None


def test_issue_for_ticket_returns_none_on_empty_mapping() -> None:
    assert _svc().issue_for_ticket({}, "ticket-001") is None


# ------------------------------------------------------------------
# pr_for_ticket
# ------------------------------------------------------------------


def test_pr_for_ticket_returns_pr_number() -> None:
    mapping = {"ticket-042": SyncEntry(issue=7, pr=15)}
    assert _svc().pr_for_ticket(mapping, "ticket-042") == 15


def test_pr_for_ticket_returns_none_when_no_pr() -> None:
    mapping = {"ticket-042": SyncEntry(issue=7, pr=None)}
    assert _svc().pr_for_ticket(mapping, "ticket-042") is None


def test_pr_for_ticket_returns_none_when_not_found() -> None:
    assert _svc().pr_for_ticket({}, "ticket-001") is None


# ------------------------------------------------------------------
# set_pr
# ------------------------------------------------------------------


def test_set_pr_returns_new_mapping() -> None:
    svc = _svc()
    mapping = {"ticket-042": SyncEntry(issue=7)}
    result = svc.set_pr(mapping, "ticket-042", 15)
    assert result["ticket-042"].pr == 15
    assert result["ticket-042"].issue == 7


def test_set_pr_preserves_existing_issue() -> None:
    svc = _svc()
    mapping = {"ticket-001": SyncEntry(issue=3, pr=None)}
    result = svc.set_pr(mapping, "ticket-001", 99)
    assert result["ticket-001"].issue == 3
    assert result["ticket-001"].pr == 99


def test_set_pr_creates_entry_if_missing() -> None:
    svc = _svc()
    result = svc.set_pr({}, "ticket-new", 5)
    assert result["ticket-new"].pr == 5
    assert result["ticket-new"].issue is None


def test_set_pr_does_not_mutate_original() -> None:
    svc = _svc()
    original = {"ticket-001": SyncEntry(issue=1)}
    svc.set_pr(original, "ticket-001", 7)
    assert original["ticket-001"].pr is None
