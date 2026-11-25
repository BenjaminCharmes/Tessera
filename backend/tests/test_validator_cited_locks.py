from pathlib import Path

from tessera.services.verdicts.validator_cited_files import build_cited_files_section, format_cited_files_log

_DIFF = (
    "diff --git a/frontend/package-lock.json b/frontend/package-lock.json\n"
    "--- a/frontend/package-lock.json\n"
    "+++ b/frontend/package-lock.json\n"
    '+      "version": "9.9.9"\n'
    "diff --git a/other.py b/other.py\n"
    "+print_other\n"
)


def _write_lock(tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package-lock.json").write_text(
        "LOCK_HEAD_CONTENT " * 5000, encoding="utf-8"
    )


def test_lockfile_is_joined_by_its_diff(tmp_path: Path) -> None:
    _write_lock(tmp_path)
    section, report = build_cited_files_section(
        ["frontend/package-lock.json"], tmp_path, _DIFF
    )
    assert '"version": "9.9.9"' in section
    assert "LOCK_HEAD_CONTENT" not in section
    assert "print_other" not in section
    assert report.diffs == ["frontend/package-lock.json"]


def test_unmodified_lockfile_says_so(tmp_path: Path) -> None:
    _write_lock(tmp_path)
    section, _ = build_cited_files_section(
        ["frontend/package-lock.json"], tmp_path, "diff --git a/x.py b/x.py\n+y\n"
    )
    assert "non modifié par le run" in section
    assert "LOCK_HEAD_CONTENT" not in section


def test_non_lockfile_is_joined_as_before(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "demo"}', encoding="utf-8")
    section, report = build_cited_files_section(["package.json"], tmp_path, _DIFF)
    assert '"name": "demo"' in section
    assert report.diffs == []


def test_log_marks_lockfile_as_diff(tmp_path: Path) -> None:
    _write_lock(tmp_path)
    _, report = build_cited_files_section(
        ["frontend/package-lock.json"], tmp_path, _DIFF
    )
    assert "frontend/package-lock.json (diff)" in format_cited_files_log(report)
