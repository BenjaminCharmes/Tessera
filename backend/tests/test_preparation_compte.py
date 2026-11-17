"""ticket-995: the worktree setup starts under the agent account when declared."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from tessera.config import settings
from tessera.models.worktree_config import ConfigWorktree
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.pipeline.preparation_worktree import preparation_du_run
from tessera.services.verification import chaine_python
from tests.chaine_factice import chaine_factice  # noqa: F401
from tests.doubles_compte import LanceurDouble, ProcessDouble


@pytest.fixture
def compte(monkeypatch: pytest.MonkeyPatch, chaine: Path, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr("pw"))
    python = tmp_path / "python"
    python.mkdir()
    monkeypatch.setattr(chaine_python, "CHAINE_PYTHON", python)


def _politique(compte_agent: bool) -> PolitiqueRun:
    return PolitiqueRun(worktree=ConfigWorktree(setup="node install.js", compte_agent=compte_agent))


async def test_setup_goes_through_the_account_launcher(compte: None, tmp_path: Path) -> None:
    lanceur = LanceurDouble(ProcessDouble(b"ok", b"", code=0))
    preparation = preparation_du_run(_politique(True), tmp_path, tmp_path, None, 60, lanceur=lanceur)
    assert preparation is not None
    with patch("asyncio.create_subprocess_exec") as direct:
        resultat = await preparation()
    direct.assert_not_called()
    assert resultat.arret is None
    assert lanceur.appels[0]["compte"] == "tessera-agent"
    assert lanceur.appels[0]["cwd"] == str(tmp_path.resolve())


async def test_launcher_failure_blocks_the_setup_without_fallback(
    compte: None, tmp_path: Path
) -> None:
    lanceur = LanceurDouble(refus="logon refuse")
    preparation = preparation_du_run(_politique(True), tmp_path, tmp_path, None, 60, lanceur=lanceur)
    assert preparation is not None
    with patch("asyncio.create_subprocess_exec") as direct:
        resultat = await preparation()
    direct.assert_not_called()
    assert resultat.arret is not None and "logon refuse" in resultat.arret


async def test_project_without_agent_account_starts_as_before(
    compte: None, tmp_path: Path
) -> None:
    lanceur = LanceurDouble()
    proc = MagicMock()
    proc.returncode = 0
    proc.pid = 1
    proc.communicate = AsyncMock(return_value=(b"ok", b""))
    preparation = preparation_du_run(_politique(False), tmp_path, tmp_path, None, 60, lanceur=lanceur)
    assert preparation is not None
    with patch("asyncio.create_subprocess_exec", return_value=proc) as direct:
        resultat = await preparation()
    direct.assert_called()
    assert lanceur.appels == []
    assert resultat.arret is None
