"""Housekeeping report — ticket-913.

Couverture : tri des fichiers de memory/, ADR citées ou non, plus vieille ligne
du journal, tickets bloqués selon l'âge, script en ligne de commande.
"""
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tessera.services.projets.releve_menage import releve_menage

_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from releve_menage import main  # noqa: E402


def _ecrire(chemin: Path, texte: str) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")


def _commit(projet: Path, chemin: str, jours: int) -> None:
    quand = (datetime.now(UTC) - timedelta(days=jours)).isoformat()
    env = {**os.environ, "GIT_COMMITTER_DATE": quand, "GIT_AUTHOR_DATE": quand}
    identite = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    base = ["git", *identite, "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "add", chemin], cwd=projet, check=True, env=env)
    subprocess.run([*base, "commit", "-m", "x"], cwd=projet, check=True, env=env, capture_output=True)


@pytest.fixture
def racine(tmp_path: Path) -> Path:
    projet = tmp_path / "demo"
    _ecrire(projet / "CLAUDE.md", "# Demo\nvoir ADR-002\n")
    _ecrire(projet / "memory" / "petit.md", "ab")
    _ecrire(projet / "memory" / "gros.md", "x" * 50)
    _ecrire(projet / "memory" / "decisions.md", "## ADR-001 — a\n\n## ADR-002 — b\n")
    _ecrire(projet / "memory" / "pipeline-log.md", "- 2026-06-20 21:01:25 UTC — a\n- 2026-09-21 11:22:20 UTC — b\n")
    _ecrire(tmp_path / "sans-claude" / "memory" / "x.md", "x")
    subprocess.run(["git", "init", "-q"], cwd=projet, check=True)
    _ecrire(projet / "tickets" / "blocked" / "ticket-001-vieux.md", "v")
    _ecrire(projet / "tickets" / "blocked" / "ticket-002-recent.md", "r")
    _commit(projet, "tickets/blocked/ticket-001-vieux.md", 90)
    _commit(projet, "tickets/blocked/ticket-002-recent.md", 2)
    return tmp_path


def test_memory_files_sorted_biggest_first(racine: Path) -> None:
    rapport = releve_menage(racine, 30)
    assert rapport.index("`gros.md` — 50 characters") < rapport.index("`petit.md` — 2 characters")
    assert "sans-claude" not in rapport


def test_adr_cited_elsewhere_is_not_flagged(racine: Path) -> None:
    rapport = releve_menage(racine, 30)
    assert "ADR-001 — cited by no other file" in rapport
    assert "ADR-002 — cited by no other file" not in rapport


def test_oldest_log_line_date_is_reported(racine: Path) -> None:
    assert "2 lines, oldest line: 2026-06-20" in releve_menage(racine, 30)


def test_blocked_ticket_flagged_only_when_older_than_age(racine: Path) -> None:
    rapport = releve_menage(racine, 30)
    assert "ticket-001-vieux.md" in rapport
    assert "ticket-002-recent.md" not in rapport


def test_script_runs_on_a_temporary_folder(racine: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--racine", str(racine), "--projets", "demo", "--age-jours", "1"])
    sortie = capsys.readouterr().out
    assert code == 0
    assert "## demo" in sortie and "ticket-002-recent.md" in sortie


def test_script_rejects_missing_folder(tmp_path: Path) -> None:
    assert main(["--racine", str(tmp_path / "absent")]) == 2
