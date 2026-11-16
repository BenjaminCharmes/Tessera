"""The worktree setup of an agent-account project builds its venv on the shared Python — ticket-984."""
import shlex
import sys
from pathlib import Path

import pytest

from tessera.models.worktree_config import ConfigWorktree
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.pipeline.preparation_worktree import preparation_du_run
from tessera.services.verification import chaine_python
from tessera.services.verification.chaine_python import ChaineAbsente, env_du_setup, fusionner_env, verifier_chaine

_CLES = {"UV_PYTHON_INSTALL_DIR", "UV_PYTHON_PREFERENCE"}


def test_agent_account_setup_carries_both_variables() -> None:
    env = env_du_setup(ConfigWorktree(compte_agent=True))
    assert set(env) == _CLES
    assert env["UV_PYTHON_PREFERENCE"] == "only-managed"
    assert env["UV_PYTHON_INSTALL_DIR"].endswith(r"toolchain\python")


def test_setup_without_agent_account_carries_neither() -> None:
    assert env_du_setup(ConfigWorktree()) == {}
    assert fusionner_env(ConfigWorktree(), None) is None
    assert fusionner_env(ConfigWorktree(), {"CI": "1"}) == {"CI": "1"}


def test_declared_env_is_kept_next_to_the_uv_variables() -> None:
    env = fusionner_env(ConfigWorktree(compte_agent=True), {"CI": "1"})
    assert env is not None and env["CI"] == "1" and _CLES <= set(env)


def test_missing_toolchain_fails_closed_naming_agent_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chaine_python, "CHAINE_PYTHON", tmp_path / "absent")
    with pytest.raises(ChaineAbsente, match="agent setup"):
        verifier_chaine(ConfigWorktree(compte_agent=True))
    verifier_chaine(ConfigWorktree())


async def test_setup_without_toolchain_is_refused_before_launching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chaine_python, "CHAINE_PYTHON", tmp_path / "absent")
    politique = PolitiqueRun(worktree=ConfigWorktree(setup="uv sync", compte_agent=True))
    preparation = preparation_du_run(politique, tmp_path, tmp_path, None, None)
    assert preparation is not None
    arret = (await preparation()).arret
    assert arret is not None and "agent setup" in arret


async def test_venv_home_made_by_the_setup_is_under_the_toolchain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chaine = tmp_path / "toolchain" / "python"
    chaine.mkdir(parents=True)
    monkeypatch.setattr(chaine_python, "CHAINE_PYTHON", chaine)
    script = tmp_path / "faux_uv.py"
    # Fait comme `uv venv` : `home` vient de UV_PYTHON_INSTALL_DIR.
    script.write_text(
        "import os, pathlib\n"
        "home = pathlib.Path(os.environ['UV_PYTHON_INSTALL_DIR']) / 'cpython-3.12'\n"
        "venv = pathlib.Path('.venv'); venv.mkdir()\n"
        "(venv / 'pyvenv.cfg').write_text(f'home = {home}\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    wt = tmp_path / "wt"
    wt.mkdir()
    commande = f"{shlex.quote(Path(sys.executable).as_posix())} {shlex.quote(script.as_posix())}"
    politique = PolitiqueRun(worktree=ConfigWorktree(setup=commande, compte_agent=True))
    preparation = preparation_du_run(politique, wt, tmp_path, None, 60)
    assert preparation is not None
    assert (await preparation()).arret is None
    cfg = (wt / ".venv" / "pyvenv.cfg").read_text(encoding="utf-8")
    home = Path(cfg.split("=", 1)[1].strip())
    assert home.is_relative_to(chaine)
