from collections import Counter
from datetime import date
from pathlib import Path

from tessera.services.git_workspace.archive_journal import archiver_journal

_JOURNAL = (
    "- 2026-08-03 10:00:00 UTC — a\n"
    "suite sans date\n"
    "- 2026-09-03 10:00:00 UTC — b\n"
    "- 2026-10-03 10:00:00 UTC — c\n"
    "- 2026-11-03 10:00:00 UTC — d\n"
)
_JOUR = date(2026, 11, 11)


def _projet(tmp_path: Path) -> Path:
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "pipeline-log.md").write_text(_JOURNAL, encoding="utf-8", newline="")
    return tmp_path


def _lire(chemin: Path) -> str:
    with chemin.open(encoding="utf-8", newline="") as f:
        return f.read()


def test_old_months_move_and_last_two_stay(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    deplaces = archiver_journal(projet, 2, _JOUR)
    assert deplaces == {"2026-08": 2, "2026-09": 1}
    journal = _lire(projet / "memory" / "pipeline-log.md")
    assert "— c" in journal and "— d" in journal and "— b" not in journal
    assert (projet / "memory" / "journal" / "pipeline-log-2026-09.md").is_file()


def test_undated_line_follows_previous_dated_line(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    archiver_journal(projet, 2, _JOUR)
    archive = _lire(projet / "memory" / "journal" / "pipeline-log-2026-08.md")
    assert "suite sans date" in archive


def test_existing_archive_is_completed_at_the_end(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    dossier = projet / "memory" / "journal"
    dossier.mkdir()
    (dossier / "pipeline-log-2026-09.md").write_text("- ancienne\n", encoding="utf-8", newline="")
    archiver_journal(projet, 2, _JOUR)
    assert _lire(dossier / "pipeline-log-2026-09.md").startswith("- ancienne\n- 2026-09-03")


def test_lines_are_identical_before_and_after(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    archiver_journal(projet, 2, _JOUR)
    textes = [_lire(projet / "memory" / "pipeline-log.md")]
    textes += [_lire(p) for p in (projet / "memory" / "journal").iterdir()]
    apres = Counter(l for t in textes for l in t.splitlines(keepends=True))
    assert apres == Counter(_JOURNAL.splitlines(keepends=True))


def test_missing_log_and_invalid_window(tmp_path: Path) -> None:
    assert archiver_journal(tmp_path, 2, _JOUR) == {}
    try:
        archiver_journal(tmp_path, 0, _JOUR)
    except ValueError:
        return
    raise AssertionError("garder_mois=0 must be refused")
