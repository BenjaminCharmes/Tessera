"""CI check of a pull request against FORBIDDEN_TERMS — ticket-230."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _charger() -> types.ModuleType:
    chemin = Path(__file__).resolve().parents[2] / "scripts" / "termes_interdits_ci.py"
    loader = importlib.machinery.SourceFileLoader("termes_interdits_ci", str(chemin))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


CI = _charger()


def _git_vide(cmd: list[str], **kwargs: object) -> MagicMock:
    resultat = MagicMock()
    resultat.stdout = ""
    return resultat


@pytest.fixture
def pr(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setenv("FORBIDDEN_TERMS", "zorglub")
    monkeypatch.setenv("BASE_SHA", "a" * 40)
    monkeypatch.setenv("HEAD_SHA", "b" * 40)
    monkeypatch.setenv("PR_TITLE", "feat: something")
    monkeypatch.setenv("PR_BODY", "")
    return monkeypatch


def test_a_missing_list_refuses_the_pr(pr: pytest.MonkeyPatch) -> None:
    pr.setenv("FORBIDDEN_TERMS", "")
    assert CI.main() == 1


def test_a_term_in_the_pr_body_refuses_the_pr(
    pr: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pr.setenv("PR_BODY", "Built for Zorglub.")
    with patch.object(subprocess, "run", side_effect=_git_vide):
        assert CI.main() == 1
    sortie = capsys.readouterr()
    assert "pr:corps" in sortie.err
    assert "zorglub" not in (sortie.err + sortie.out).lower()


def test_a_term_in_an_added_line_refuses_the_pr(pr: pytest.MonkeyPatch) -> None:
    def git(cmd: list[str], **kwargs: object) -> MagicMock:
        resultat = MagicMock()
        resultat.stdout = "diff --git a/n.md b/n.md\n+++ b/n.md\n+chez Zorglub\n" if "diff" in cmd else ""
        return resultat

    with patch.object(subprocess, "run", side_effect=git):
        assert CI.main() == 1


def test_a_clean_pr_passes(pr: pytest.MonkeyPatch) -> None:
    with patch.object(subprocess, "run", side_effect=_git_vide):
        assert CI.main() == 0


def test_a_git_failure_refuses_the_pr(pr: pytest.MonkeyPatch) -> None:
    def git(cmd: list[str], **kwargs: object) -> MagicMock:
        raise subprocess.CalledProcessError(128, cmd)

    with patch.object(subprocess, "run", side_effect=git):
        assert CI.main() == 1
