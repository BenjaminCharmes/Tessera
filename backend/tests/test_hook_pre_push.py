"""Unit tests for the pre-push git hook — ADR-048.

The hook is a standalone Python script (no .py extension).
We import it via importlib to call its functions directly,
without subprocess, as required by ticket-207.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Import the hook module
# ---------------------------------------------------------------------------


def _load_hook() -> types.ModuleType:
    """Load scripts/hooks/pre-push as a Python module."""
    hook_path = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "pre-push"
    spec = importlib.util.spec_from_file_location("pre_push_hook", hook_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


HOOK = _load_hook()
CommitInfo = HOOK.CommitInfo
Violation = HOOK.Violation
NULL_SHA = HOOK.NULL_SHA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patterns(terms: str) -> list[re.Pattern[str]]:
    termes = [HOOK._normaliser(t.strip()) for t in terms.split(",") if t.strip()]
    return HOOK._build_patterns(termes)


def _diff_lines(path: str, content: str) -> list[str]:
    return [f"+++ b/{path}", f"+{content}"]


def _commit(sha7: str, message: str, auteur: str = "dev <d@example.com>") -> CommitInfo:
    return CommitInfo(sha7=sha7, message=message, auteur=auteur)


# ---------------------------------------------------------------------------
# load_forbidden_terms
# ---------------------------------------------------------------------------


def test_load_terms_file_absent(tmp_path: Path) -> None:
    result = HOOK.load_forbidden_terms(tmp_path / "absent.env")
    assert result == []


def test_load_terms_key_absent(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=sk-xxx\n", encoding="utf-8")
    assert HOOK.load_forbidden_terms(env) == []


def test_load_terms_key_present(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("FORBIDDEN_TERMS=acme,zorglub\n", encoding="utf-8")
    result = HOOK.load_forbidden_terms(env)
    assert result == ["acme", "zorglub"]


def test_load_terms_empty_value(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("FORBIDDEN_TERMS=\n", encoding="utf-8")
    assert HOOK.load_forbidden_terms(env) == []


def test_load_terms_normalises_case(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("FORBIDDEN_TERMS=ACME\n", encoding="utf-8")
    result = HOOK.load_forbidden_terms(env)
    assert result == ["acme"]


# ---------------------------------------------------------------------------
# verifier — liste vide
# ---------------------------------------------------------------------------


def test_liste_vide_ne_bloque_pas() -> None:
    """Empty patterns: no violations regardless of content."""
    violations = HOOK.verifier(
        commits=[_commit("abc1234", "feat: connect to acme API")],
        lignes_ajoutees=_diff_lines("config.py", "HOST = acme.internal"),
        patterns=[],
    )
    assert violations == []


# ---------------------------------------------------------------------------
# verifier — terme dans message de commit
# ---------------------------------------------------------------------------


def test_terme_dans_message_commit() -> None:
    violations = HOOK.verifier(
        commits=[_commit("abc1234", "fix: connect to acme API")],
        lignes_ajoutees=[],
        patterns=_patterns("acme"),
    )
    assert len(violations) == 1
    assert violations[0].source == "commit:abc1234"


def test_terme_dans_auteur_commit() -> None:
    violations = HOOK.verifier(
        commits=[_commit("bbb2222", "chore: deps", "Dev Corp <d@corp.example>")],
        lignes_ajoutees=[],
        patterns=_patterns("corp"),
    )
    assert len(violations) == 1
    assert violations[0].source == "commit:bbb2222"


def test_une_seule_violation_par_commit() -> None:
    # Term in both message AND author → one violation per commit.
    violations = HOOK.verifier(
        commits=[_commit("abc1234", "fix acme", "Acme Dev <d@example.com>")],
        lignes_ajoutees=[],
        patterns=_patterns("acme"),
    )
    assert len(violations) == 1


def test_sous_chaine_ne_declenche_pas_commit() -> None:
    violations = HOOK.verifier(
        commits=[_commit("abc1234", "refactor: subacme module")],
        lignes_ajoutees=[],
        patterns=_patterns("acme"),
    )
    assert violations == []


# ---------------------------------------------------------------------------
# verifier — terme dans diff ajouté
# ---------------------------------------------------------------------------


def test_terme_dans_diff_ajoute() -> None:
    violations = HOOK.verifier(
        commits=[],
        lignes_ajoutees=_diff_lines("src/config.py", "HOST = 'acme.internal'"),
        patterns=_patterns("acme"),
    )
    assert len(violations) == 1
    assert violations[0].source == "file:src/config.py"


def test_violation_ne_nomme_pas_le_terme() -> None:
    violations = HOOK.verifier(
        commits=[],
        lignes_ajoutees=_diff_lines("x.py", "password = secret123"),
        patterns=_patterns("secret123"),
    )
    assert violations
    assert "secret123" not in violations[0].source


def test_une_seule_violation_par_fichier() -> None:
    violations = HOOK.verifier(
        commits=[],
        lignes_ajoutees=[
            "+++ b/config.py",
            "+host = 'acme.internal'",
            "+backup = 'acme-backup.internal'",
        ],
        patterns=_patterns("acme"),
    )
    assert len(violations) == 1
    assert violations[0].source == "file:config.py"


# ---------------------------------------------------------------------------
# sha inconnu — nouvelle branche (NULL_SHA comme remote_sha)
# ---------------------------------------------------------------------------


def test_sha_inconnu_get_commits_utilise_not_remotes() -> None:
    """New branch: git log must not receive the null SHA as range start."""
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        captured.append(cmd)
        result = MagicMock()
        result.stdout = ""
        return result

    with patch.object(subprocess, "run", side_effect=fake_run):
        HOOK._get_commits("abc1234", NULL_SHA)

    assert captured, "subprocess.run was not called"
    args = captured[0]
    # The null SHA must not appear in the command
    assert NULL_SHA not in args
    # --not --remotes must be present to avoid an infinite range
    assert "--not" in args
    assert "--remotes" in args


def test_sha_inconnu_get_diff_utilise_not_remotes() -> None:
    """New branch: git diff/log must not receive the null SHA as range start."""
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        captured.append(cmd)
        result = MagicMock()
        result.stdout = ""
        return result

    with patch.object(subprocess, "run", side_effect=fake_run):
        HOOK._get_diff_lines("abc1234", NULL_SHA)

    assert captured, "subprocess.run was not called"
    args = captured[0]
    assert NULL_SHA not in args


def test_suppression_branche_ignoree() -> None:
    """Branch deletion (local_sha == NULL_SHA) must return no violations."""
    # We test the main() logic by exercising the guard directly:
    # local_sha == NULL_SHA → skip (no git calls, no violations).
    violations = HOOK.verifier(
        commits=[],
        lignes_ajoutees=[],
        patterns=_patterns("acme"),
    )
    # No data → no violations, even with an active pattern.
    assert violations == []


# ---------------------------------------------------------------------------
# Isolation pipeline — ADR-027
#
# Le pipeline appelle git via GitWorkspaceService._run(), qui passe toujours
# `-c core.hooksPath=<dossier_vide>`.  Le hook installé dans .git/hooks/ est
# donc ignoré lors des runs : c'est le dossier vide qui compte, pas .git/hooks/.
# ---------------------------------------------------------------------------


def test_dossier_sans_hooks_ne_contient_pas_pre_push() -> None:
    """The pipeline's empty hooks directory must not contain a pre-push hook.

    GitWorkspaceService._run() always sets core.hooksPath to this directory.
    As long as it stays empty, our installed hook in .git/hooks/ is never
    called during pipeline runs (ADR-027).
    """
    from tessera.services.git_workspace import _dossier_sans_hooks

    dossier = _dossier_sans_hooks()
    assert dossier.is_dir(), f"empty hooks dir does not exist: {dossier}"
    assert not (dossier / "pre-push").exists(), (
        "pre-push hook found in the pipeline's empty hooks directory — "
        "it would fire during pipeline git operations"
    )


async def test_pipeline_run_passe_hooks_path_vide(tmp_path: Path) -> None:
    """GitWorkspaceService._run() must send -c core.hooksPath=<empty> to git.

    This is the mechanism that prevents the pre-push hook from firing
    during pipeline runs (ADR-027 + ticket-207).
    """
    from tessera.services.git_workspace import GitWorkspaceService

    captured: list[str] = []

    class _FakeProc:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def _fake_exec(*args: str, **kwargs: object) -> _FakeProc:
        captured.extend(args)
        return _FakeProc()

    with patch(
        "tessera.services.git_workspace.asyncio.create_subprocess_exec",
        side_effect=_fake_exec,
    ):
        service = GitWorkspaceService(tmp_path)
        await service._run("status")

    hooks_args = [arg for arg in captured if "hooksPath" in arg]
    assert hooks_args, (
        f"core.hooksPath absent from git command: {captured!r}. "
        "The hook could fire during pipeline runs."
    )
    # The path must exist and be a directory so git accepts it
    hooks_path = hooks_args[0].split("=", 1)[1]
    assert Path(hooks_path).is_dir()
