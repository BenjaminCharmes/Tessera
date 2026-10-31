"""The OpenAPI schema is exported to a versioned file — ticket-684."""
import json
from pathlib import Path

import pytest

from tessera.openapi_export import (
    SCHEMA_PATH,
    is_up_to_date,
    main,
    render_schema,
    write_schema,
)


def test_versioned_schema_matches_the_app() -> None:
    assert is_up_to_date(), (
        "docs/openapi.json is stale: run "
        "`cd backend && uv run python -m tessera.openapi_export` and commit it"
    )


def test_render_is_stable_and_ends_with_a_newline() -> None:
    first = render_schema()

    assert first == render_schema()
    assert first.endswith("}\n")
    assert list(json.loads(first)) == sorted(json.loads(first))


def test_render_stays_short_enough_to_read_in_a_diff() -> None:
    document = json.loads(render_schema())
    entries = len(document["paths"]) + len(document["components"]["schemas"])

    # Une ligne par route et par modèle, plus quelques lignes de structure.
    assert len(render_schema().splitlines()) <= entries + 20


def test_render_describes_the_routes_the_frontend_contract_reads() -> None:
    paths = json.loads(render_schema())["paths"]

    for route in (
        "/api/v1/runs/{run_id}",
        "/api/v1/usage/quota",
        "/api/v1/projects/{project_id}/usage/breakdown",
        "/api/v1/projects/{project_id}/services/start",
        "/api/v1/projects/{project_id}/branches/cleanup",
    ):
        assert route in paths


def test_schema_path_is_the_docs_file_at_the_repository_root() -> None:
    assert SCHEMA_PATH.name == "openapi.json"
    assert SCHEMA_PATH.parent.name == "docs"
    assert (SCHEMA_PATH.parent.parent / "backend" / "pyproject.toml").exists()


def test_write_then_up_to_date(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "openapi.json"

    assert not is_up_to_date(target)
    write_schema(target)

    assert is_up_to_date(target)
    assert target.read_text(encoding="utf-8") == render_schema()


def test_a_stale_file_is_detected(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"
    write_schema(target)
    stale = target.read_text(encoding="utf-8").replace('"Tessera"', '"Autre"')
    target.write_text(stale, encoding="utf-8")

    assert not is_up_to_date(target)


def test_main_check_fails_on_a_stale_file_and_names_the_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "openapi.json"
    target.write_text("{}\n", encoding="utf-8")

    assert main(["--check"], target) == 1
    assert "python -m tessera.openapi_export" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == "{}\n"


def test_main_without_argument_rewrites_and_check_then_passes(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"
    target.write_text("{}\n", encoding="utf-8")

    assert main([], target) == 0
    assert main(["--check"], target) == 0


def test_main_refuses_an_unknown_argument(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--force"], tmp_path / "openapi.json") == 2
    assert "usage" in capsys.readouterr().err
    assert not (tmp_path / "openapi.json").exists()

