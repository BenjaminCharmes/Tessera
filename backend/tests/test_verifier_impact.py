"""Tests for the step durations and the `--impact` option of scripts/verifier.py (ticket-793)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from verifier import (  # noqa: E402
    BACKEND_STEPS,
    FRONTEND_STEPS,
    fichiers_de_test_impactes,
    ligne_des_durees,
    main,
)


def _depot(tmp_path: Path) -> Path:
    """A tiny backend: `a` is imported by `b`, a test imports each, one test imports nothing."""
    src = tmp_path / "backend" / "src" / "tessera" / "services"
    tests = tmp_path / "backend" / "tests"
    src.mkdir(parents=True)
    tests.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "a.py").write_text("X = 1\n", encoding="utf-8")
    (src / "b.py").write_text("from tessera.services import a\n", encoding="utf-8")
    (tests / "test_a.py").write_text("from tessera.services.a import X\n", encoding="utf-8")
    (tests / "test_b.py").write_text("import tessera.services.b\n", encoding="utf-8")
    (tests / "test_sans_rapport.py").write_text("def test_x(): pass\n", encoding="utf-8")
    return tmp_path


def test_the_duration_line_names_every_step() -> None:
    ligne = ligne_des_durees({"pytest": 871.2, "mypy": 151.0})
    assert ligne == "durées : pytest 871 s, mypy 151 s"


def test_a_changed_module_selects_its_tests_and_those_of_its_importers(tmp_path: Path) -> None:
    racine = _depot(tmp_path)
    choisis = fichiers_de_test_impactes(["backend/src/tessera/services/a.py"], racine)
    assert choisis == ["tests/test_a.py", "tests/test_b.py"]


def test_a_changed_test_is_selected_and_an_unrelated_one_is_not(tmp_path: Path) -> None:
    racine = _depot(tmp_path)
    assert fichiers_de_test_impactes(["backend/tests/test_sans_rapport.py"], racine) == ["tests/test_sans_rapport.py"]


def test_a_frontend_only_change_selects_no_backend_test(tmp_path: Path) -> None:
    racine = _depot(tmp_path)
    assert fichiers_de_test_impactes(["frontend/src/App.tsx"], racine) == []


def test_configuration_helpers_or_scripts_run_the_whole_suite(tmp_path: Path) -> None:
    racine = _depot(tmp_path)
    for chemin in ("backend/pyproject.toml", "backend/tests/conftest.py", "scripts/verifier.py"):
        assert fichiers_de_test_impactes([chemin], racine) is None


def test_main_with_impact_limits_pytest_to_the_impacted_files() -> None:
    with patch("verifier.changed_paths", return_value=["backend/src/tessera/x.py"]), \
         patch("verifier._git", return_value="backend/src/tessera/x.py\n"), \
         patch("verifier.fichiers_de_test_impactes", return_value=["tests/test_x.py"]), \
         patch("verifier.run_parallel", return_value=0) as run:
        assert main(["--impact", "abc123"]) == 0
    pytest_steps = run.call_args.args[0]
    assert len(pytest_steps) == 1 and pytest_steps[0].cmd[-1] == "tests/test_x.py"


def test_main_with_impact_runs_the_whole_suite_when_the_diff_is_unreadable() -> None:
    with patch("verifier.changed_paths", return_value=["backend/src/tessera/x.py"]), \
         patch("verifier._git", return_value=None), \
         patch("verifier.run_parallel", return_value=0) as run:
        assert main(["--impact", "abc123"]) == 0
    assert run.call_args.args[0] == BACKEND_STEPS


def test_main_with_impact_skips_pytest_when_no_test_is_concerned() -> None:
    with patch("verifier.changed_paths", return_value=["backend/src/tessera/x.py", "frontend/a.ts"]), \
         patch("verifier._git", return_value="frontend/a.ts\n"), \
         patch("verifier.run_parallel", return_value=0) as run:
        assert main(["--impact", "abc123"]) == 0
    pytest_steps, frontend, _types = run.call_args.args
    assert pytest_steps == [] and frontend == FRONTEND_STEPS
