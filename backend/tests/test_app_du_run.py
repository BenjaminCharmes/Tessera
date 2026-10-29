"""Starting and stopping the app of a run — ticket-618, ADR-062."""
import asyncio
import sys
from pathlib import Path

import pytest

from tessera.services.app_du_run import (
    DemarrageEchoue,
    attendre_que_l_app_reponde,
    commande_du_run,
    config_sur_le_port,
    demarrer_processus,
    port_libre,
)
from tessera.services.captures_config import ConfigCaptures, Ecran
from tessera.services.controle_visuel import Demarrage


class _App:
    def __init__(self, code: int | None = None) -> None:
        self.code = code

    @property
    def code_de_sortie(self) -> int | None:
        return self.code

    async def arreter(self) -> None:
        self.code = 0


def test_port_libre_gives_a_usable_port() -> None:
    port = port_libre()
    assert 1024 <= port <= 65535


def test_commande_du_run_replaces_the_port_and_splits_without_a_shell() -> None:
    demarrage = Demarrage("pnpm exec next dev -p {port}")
    assert commande_du_run(demarrage, 5444) == ["pnpm", "exec", "next", "dev", "-p", "5444"]


def test_commande_du_run_refuses_an_unreadable_command() -> None:
    with pytest.raises(DemarrageEchoue):
        commande_du_run(Demarrage('node "{port}'), 5444)


def test_config_sur_le_port_keeps_the_host_and_changes_the_port() -> None:
    config = ConfigCaptures(url="http://localhost:{port}", ecrans=(Ecran("a", "/"),))
    assert config_sur_le_port(config, 5444).url == "http://localhost:5444"
    fixe = ConfigCaptures(url="http://127.0.0.1:5196", ecrans=(Ecran("a", "/"),))
    assert config_sur_le_port(fixe, 5444).url == "http://127.0.0.1:5444"


async def test_wait_returns_as_soon_as_the_app_answers() -> None:
    appels: list[str] = []

    async def sonde(url: str) -> bool:
        appels.append(url)
        return len(appels) == 2

    await attendre_que_l_app_reponde(_App(), "http://localhost:1", 5, sonde, pause_s=0)
    assert appels == ["http://localhost:1"] * 2


async def test_wait_fails_when_the_process_ended_early() -> None:
    async def sonde(_url: str) -> bool:
        raise AssertionError("an ended process must not be probed")

    with pytest.raises(DemarrageEchoue, match="code 3"):
        await attendre_que_l_app_reponde(_App(code=3), "http://x:1", 5, sonde, pause_s=0)


async def test_wait_fails_after_the_delay() -> None:
    async def sonde(_url: str) -> bool:
        return False

    with pytest.raises(DemarrageEchoue, match="0 s"):
        await attendre_que_l_app_reponde(_App(), "http://x:1", 0, sonde, pause_s=0)


async def test_a_real_process_starts_in_the_given_folder_and_is_stopped(tmp_path: Path) -> None:
    code = "import os, time; open('cwd.txt', 'w').write(os.getcwd()); time.sleep(60)"
    app = await demarrer_processus([sys.executable, "-c", code], tmp_path)
    try:
        assert app.code_de_sortie is None
        for _ in range(50):
            if (tmp_path / "cwd.txt").is_file() and (tmp_path / "cwd.txt").read_text():
                break
            await asyncio.sleep(0.1)
        assert Path((tmp_path / "cwd.txt").read_text()).resolve() == tmp_path.resolve()
    finally:
        await app.arreter()
    assert app.code_de_sortie is not None


async def test_an_unknown_program_is_a_failed_start(tmp_path: Path) -> None:
    with pytest.raises(DemarrageEchoue, match="introuvable"):
        await demarrer_processus(["programme-qui-n-existe-pas-618"], tmp_path)
