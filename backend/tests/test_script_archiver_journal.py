import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from archiver_journal import main  # noqa: E402


def test_script_archives_an_old_month(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "pipeline-log.md").write_text(
        "- 2020-01-05 10:00:00 UTC — vieux\n- 2099-01-05 10:00:00 UTC — futur\n",
        encoding="utf-8",
    )
    code = main(["--projet", str(tmp_path), "--garder-mois", "1"])
    assert code == 0
    assert "2020-01 : 1 lignes" in capsys.readouterr().out
    assert (tmp_path / "memory" / "journal" / "pipeline-log-2020-01.md").is_file()


def test_script_refuses_a_folder_without_memory(tmp_path: Path) -> None:
    assert main(["--projet", str(tmp_path)]) == 2
