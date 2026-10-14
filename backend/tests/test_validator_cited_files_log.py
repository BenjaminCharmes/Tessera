"""What the validator receives of the cited files, and the journal line (ticket-434)."""

import json
from pathlib import Path

import httpx
import respx

from tessera.services.providers.ollama import OllamaProvider, _reset_cooldowns
from tessera.services.validator import ValidatorService
from tessera.services.validator_cited_files import (
    CITED_FILES_MAX_CHARS,
    CitedFilesReport,
    build_cited_files_section,
    format_cited_files_log,
)

_BASE = "http://ollama.test:11434"
_MODEL = "qwen3-coder:30b"
_APPROVED = json.dumps(
    {
        "criteria": [{"index": 1, "criterion": "x", "passed": True, "note": ""}],
        "feedback": "ok",
    }
)


def _ollama_answer() -> dict[str, object]:
    return {
        "model": _MODEL,
        "message": {"role": "assistant", "content": _APPROVED},
        "done": True,
        "prompt_eval_count": 10,
        "eval_count": 5,
    }


@respx.mock
async def test_ollama_receives_the_cited_file_untouched_by_the_diff(
    tmp_path: Path,
) -> None:
    _reset_cooldowns()
    (tmp_path / "charter-contrast.test.ts").write_text(
        "describe('contrast', () => { it('checks 8 rows', () => {}) })",
        encoding="utf-8",
    )
    respx.get(f"{_BASE}/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": _MODEL}]})
    )
    route = respx.post(f"{_BASE}/api/chat").mock(
        return_value=httpx.Response(200, json=_ollama_answer())
    )
    service = ValidatorService(
        OllamaProvider(base_url=_BASE), Path("agents/prompts"), model=_MODEL
    )

    await service.validate(
        criteria=["`charter-contrast.test.ts` checks the 8 rows"],
        code_produced="+unrelated change",
        test_result=None,
        project_root=tmp_path,
    )

    body = json.loads(route.calls[0].request.content)
    message = body["messages"][-1]["content"]
    assert "it('checks 8 rows'" in message
    assert body["options"]["num_ctx"] * 3 >= len(message)


async def test_log_line_lists_joined_and_absent_files(tmp_path: Path) -> None:
    (tmp_path / "a.test.ts").write_text("a", encoding="utf-8")

    _, report = build_cited_files_section(["a.test.ts", "c.test.ts"], tmp_path)

    assert report.joined == ["a.test.ts"]
    assert report.absent == ["c.test.ts"]
    assert format_cited_files_log(report) == (
        "validateur: fichiers cités joints : a.test.ts ; absents : c.test.ts"
    )


async def test_log_line_flags_a_file_too_long_for_the_limit(tmp_path: Path) -> None:
    (tmp_path / "big.test.ts").write_text(
        "x" * (CITED_FILES_MAX_CHARS + 100), encoding="utf-8"
    )

    _, report = build_cited_files_section(["big.test.ts"], tmp_path)

    assert report.truncated == ["big.test.ts"]
    assert "big.test.ts (tronqué)" in format_cited_files_log(report)


async def test_file_cited_after_the_budget_is_reported_not_dropped(
    tmp_path: Path,
) -> None:
    (tmp_path / "big.test.ts").write_text(
        "x" * (CITED_FILES_MAX_CHARS + 100), encoding="utf-8"
    )
    (tmp_path / "late.test.ts").write_text("late", encoding="utf-8")

    section, report = build_cited_files_section(
        ["big.test.ts", "late.test.ts"], tmp_path
    )

    assert report.omitted == ["late.test.ts"]
    assert "### late.test.ts" in section
    assert "budget épuisé" in format_cited_files_log(report)


def test_log_line_is_empty_when_no_file_is_cited() -> None:
    assert format_cited_files_log(CitedFilesReport()) == ""


async def test_validation_result_carries_the_report(tmp_path: Path) -> None:
    from tests.test_providers_base import FakeProvider

    provider = FakeProvider()
    provider.set_content(_APPROVED)
    (tmp_path / "a.test.ts").write_text("a", encoding="utf-8")
    service = ValidatorService(provider, Path("agents/prompts"))

    result = await service.validate(
        criteria=["`a.test.ts` exists"],
        code_produced="diff",
        test_result=None,
        project_root=tmp_path,
    )

    assert result.cited_files is not None
    assert result.cited_files.joined == ["a.test.ts"]
