"""A system prompt too long for a Windows command line goes to the SDK by file (ticket-575)."""
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage

from tessera.services.providers import agent_sdk as agent_sdk_module
from tessera.services.providers.agent_sdk import (
    SYSTEM_PROMPT_FILE_THRESHOLD_BYTES,
    ClaudeAgentSDKProvider,
)


class _Capture:
    """Records the system prompt the SDK receives, and the file's content at that moment."""

    def __init__(self, fail: bool = False) -> None:
        self.system_prompt: Any = None
        self.file_content: str | None = None
        self.fail = fail

    async def gen(
        self, prompt: str, options: ClaudeAgentOptions
    ) -> AsyncGenerator[ResultMessage, None]:
        self.system_prompt = options.system_prompt
        if isinstance(self.system_prompt, dict):
            self.file_content = Path(self.system_prompt["path"]).read_text(
                encoding="utf-8"
            )
        if self.fail:
            raise RuntimeError("boom")
        yield ResultMessage(
            subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
            num_turns=1, session_id="sess-1", total_cost_usd=None, usage=None,
        )


async def _appel(
    monkeypatch: pytest.MonkeyPatch, capture: _Capture, system: str, cwd: Path
) -> None:
    monkeypatch.setattr(agent_sdk_module, "_sdk_gen", capture.gen)
    provider = ClaudeAgentSDKProvider(silence_max_s=0)
    await provider.complete(
        system=system, user="u", model="m", max_tokens=10, cwd=cwd
    )


async def test_long_prompt_goes_by_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    system = "x" * 40_000
    capture = _Capture()
    await _appel(monkeypatch, capture, system, tmp_path)
    assert isinstance(capture.system_prompt, dict)
    assert capture.system_prompt["type"] == "file"
    assert capture.file_content == system


async def test_short_prompt_stays_a_string(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    capture = _Capture()
    await _appel(monkeypatch, capture, "y" * 2_000, tmp_path)
    assert capture.system_prompt == "y" * 2_000


async def test_temp_file_is_outside_project_and_removed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projet = tmp_path / "projet"
    projet.mkdir()
    capture = _Capture()
    await _appel(monkeypatch, capture, "x" * 40_000, projet)
    chemin = Path(capture.system_prompt["path"]).resolve()
    assert not chemin.is_relative_to(projet.resolve())
    assert not chemin.exists()


async def test_temp_file_is_removed_when_the_call_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    capture = _Capture(fail=True)
    with pytest.raises(RuntimeError, match="boom"):
        await _appel(monkeypatch, capture, "x" * 40_000, tmp_path)
    assert not Path(capture.system_prompt["path"]).exists()


async def test_threshold_is_measured_in_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seuil = SYSTEM_PROMPT_FILE_THRESHOLD_BYTES
    au_seuil = _Capture()
    await _appel(monkeypatch, au_seuil, "a" * seuil, tmp_path)
    assert isinstance(au_seuil.system_prompt, str)
    au_dessus = _Capture()
    await _appel(monkeypatch, au_dessus, "a" * (seuil + 1), tmp_path)
    assert isinstance(au_dessus.system_prompt, dict)
    # « é » pèse deux octets : la moitié du seuil en caractères le dépasse.
    accents = _Capture()
    await _appel(monkeypatch, accents, "é" * (seuil // 2 + 1), tmp_path)
    assert isinstance(accents.system_prompt, dict)
    assert accents.file_content == "é" * (seuil // 2 + 1)


async def test_temp_dir_inside_project_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    capture = _Capture()
    with pytest.raises(RuntimeError, match="inside the project"):
        await _appel(monkeypatch, capture, "x" * 40_000, tmp_path)
    assert list((tmp_path / "tmp").iterdir()) == []
