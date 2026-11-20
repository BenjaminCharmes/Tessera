"""Tests of the weekly report — ticket-910."""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from tessera.services.projets.releve_semaine import LIGNE_APPROUVE, LIGNE_PR_MERGEE, releve_semaine

DU, AU = date(2026, 11, 3), date(2026, 11, 9)
RACINE_DEPOT = Path(__file__).resolve().parents[2]


def _projet(racine: Path, nom: str, journal: str = "", config: dict[str, str] | None = None) -> Path:
    dossier = racine / nom
    (dossier / "memory").mkdir(parents=True)
    (dossier / "tickets" / "done").mkdir(parents=True)
    (dossier / "CLAUDE.md").write_text(f"# {nom}\n", encoding="utf-8")
    (dossier / "memory" / "pipeline-log.md").write_text(journal, encoding="utf-8")
    if config:
        (dossier / "agents.json").write_text(json.dumps(config), encoding="utf-8")
    return dossier


def _journal(jour: str, ticket: str = "910", pr: str = "7") -> str:
    return (
        f"- {jour} 10:00:00 UTC — [ticket-{ticket}] validateur: APPROVED — ok\n"
        f"- {jour} 10:00:01 UTC — [ticket-{ticket}] APPROVED après 1 tour(s)\n"
        f"- {jour} 10:05:00 UTC — [ticket-{ticket}] livraison: PR #{pr} mergée (3797ms)\n"
    )


@pytest.fixture(autouse=True)
def _sans_depot_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))


def test_patterns_match_real_log_lines() -> None:
    ligne = "- 2026-10-02 00:16:07 UTC — [ticket-302] livraison: PR #188 mergée (3797ms)"
    assert LIGNE_PR_MERGEE.match(ligne)
    ciwatcher = "- 2026-11-09 10:53:53 UTC — [ide-core] ticket-889 PR #991 mergée (CI verte)"
    assert LIGNE_PR_MERGEE.match(ciwatcher)
    citation = "- 2026-11-11 08:34:50 UTC — [ticket-910] CHANGES_REQUESTED tour 2: voir PR #5 mergée"
    assert not LIGNE_PR_MERGEE.match(citation)
    assert LIGNE_APPROUVE.match("- 2026-09-28 10:15:41 UTC — [ticket-203] APPROVED après 1 tour(s)")
    assert not LIGNE_APPROUVE.match("- 2026-09-29 07:31:13 UTC — [ticket-220] validateur: APPROVED — ok")


def test_professional_project_only_in_excluded_line(tmp_path: Path) -> None:
    _projet(tmp_path, "secret", _journal("2026-11-04"), {"confidentiality": "professional"})
    _projet(tmp_path, "ouvert", _journal("2026-11-04"))
    out = releve_semaine(tmp_path, DU, AU)
    assert "## secret" not in out
    assert "## ouvert" in out
    assert out.rstrip().endswith("Projets exclus : secret")


def test_excluded_project_is_absent(tmp_path: Path) -> None:
    _projet(tmp_path, "a", _journal("2026-11-04"))
    out = releve_semaine(tmp_path, DU, AU, ["a"])
    assert "## a" not in out
    assert "Projets exclus : a" in out


def test_only_dated_lines_in_period_inclusive(tmp_path: Path) -> None:
    journal = (
        _journal("2026-11-02", "101", "1")
        + _journal("2026-11-03", "102", "2")
        + _journal("2026-11-09", "103", "3")
        + _journal("2026-11-10", "104", "4")
    )
    _projet(tmp_path, "p", journal)
    out = releve_semaine(tmp_path, DU, AU)
    assert "ticket-102" in out and "ticket-103" in out
    assert "ticket-101" not in out and "ticket-104" not in out
    assert "PR mergées : #2, #3" in out


def test_ticket_title_read_from_ticket_file(tmp_path: Path) -> None:
    dossier = _projet(tmp_path, "p", _journal("2026-11-04", "910"))
    (dossier / "tickets" / "done" / "ticket-910-x.md").write_text(
        "# ticket-910 — Un relevé utile\n\ncorps\n", encoding="utf-8"
    )
    assert "ticket-910 — Un relevé utile" in releve_semaine(tmp_path, DU, AU)


def test_notable_facts_filtered_and_file_optional(tmp_path: Path) -> None:
    dossier = _projet(tmp_path, "p", "")
    assert "Fait notable" not in releve_semaine(tmp_path, DU, AU)
    (dossier / "memory" / "faits-notables.md").write_text(
        "- 2026-11-05 — un bug coriace\n- 2026-10-01 — trop ancien\n", encoding="utf-8"
    )
    out = releve_semaine(tmp_path, DU, AU)
    assert "un bug coriace" in out
    assert "trop ancien" not in out


def test_project_without_git_repo_is_marked_unreadable(tmp_path: Path) -> None:
    _projet(tmp_path, "p", _journal("2026-11-04"))
    out = releve_semaine(tmp_path, DU, AU)
    assert "source illisible : dépôt" in out
    assert "PR mergées : #7" in out


def test_missing_log_is_marked_unreadable(tmp_path: Path) -> None:
    dossier = _projet(tmp_path, "p")
    (dossier / "memory" / "pipeline-log.md").unlink()
    assert "source illisible : memory/pipeline-log.md" in releve_semaine(tmp_path, DU, AU)


def test_script_runs_on_temp_folder(tmp_path: Path) -> None:
    racine = tmp_path / "projets"
    racine.mkdir()
    _projet(racine, "p", _journal("2026-11-04"))
    _projet(racine, "z", _journal("2026-11-04"))
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(tmp_path)}
    res = subprocess.run(
        [sys.executable, str(RACINE_DEPOT / "scripts" / "releve_semaine.py"),
         "--du", "2026-11-03", "--au", "2026-11-09", "--exclure", "z", "--racine", str(racine)],
        capture_output=True, text=True, encoding="utf-8", env=env, check=False,
    )
    assert res.returncode == 0, res.stderr
    assert "## p" in res.stdout and "## z" not in res.stdout
    assert "Projets exclus : z" in res.stdout


def test_both_pr_formats_read_and_deduplicated(tmp_path: Path) -> None:
    journal = (
        "- 2026-11-04 10:00:00 UTC — [p] ticket-1 PR #9 mergée (CI verte)\n"
        "- 2026-11-04 10:00:01 UTC — [ticket-1] livraison: PR #9 mergée (12ms)\n"
        "- 2026-11-05 10:00:00 UTC — [p] ticket-2 PR #10 mergée (CI verte)\n"
    )
    _projet(tmp_path, "p", journal)
    assert "PR mergées : #9, #10" in releve_semaine(tmp_path, DU, AU)
