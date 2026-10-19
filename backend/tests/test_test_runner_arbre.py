"""Ticket-507: an expired test step ends with its whole process tree."""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera.services import groupe_d_etape
from tessera.services.groupe_d_etape import GroupeDEtape
from tessera.services.test_runner import TestRunnerService

# Le parent lance un petit-enfant de longue durée qui hérite de stdout, note
# son pid, puis dort : seul le groupe peut les atteindre tous les deux.
_PARENT = (
    "import subprocess, sys, time; "
    "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'], "
    "stdout=sys.stdout, stderr=sys.stderr); "
    "open('pid.txt', 'w').write(str(p.pid)); "
    "time.sleep(600)"
)


def _est_vivant(pid: int) -> bool:
    if os.name == "nt":
        sortie = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        return str(pid) in sortie
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@pytest.fixture
def projet(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    return tmp_path


class TestExpirationTueLArbre:
    async def test_the_grandchild_dies_with_the_expired_step(self, projet: Path) -> None:
        commande = f'"{sys.executable}" -c "{_PARENT}"'
        debut = time.monotonic()

        result = await TestRunnerService().run_tests(
            projet, test_command=commande, timeout=3
        )

        assert result.expiree is True
        assert time.monotonic() - debut < 30
        pid = int((projet / "pid.txt").read_text(encoding="utf-8"))
        # Laisse à l'OS le temps de réaper un processus tué.
        for _ in range(20):
            if not _est_vivant(pid):
                break
            await asyncio.sleep(0.25)
        assert not _est_vivant(pid)

    async def test_a_wait_that_never_returns_still_gives_expiree(
        self, projet: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(groupe_d_etape, "DELAI_ATTENTE_FIN_S", 0.2)

        async def jamais() -> int:
            await asyncio.Event().wait()
            return 0

        proc = MagicMock()
        proc.kill = MagicMock()
        proc.wait = jamais
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await asyncio.wait_for(
                TestRunnerService().run_tests(projet, test_command="x", timeout=1),
                timeout=10,
            )

        assert result.expiree is True
        proc.kill.assert_called_once()

    async def test_without_a_group_the_step_runs_normally(self, projet: Path) -> None:
        commande = f'"{sys.executable}" -c "print(\'5 passed in 0.1s\')"'

        with patch(
            "tessera.services.groupe_de_processus.creer_groupe", return_value=None
        ) as creer:
            result = await TestRunnerService().run_tests(projet, test_command=commande)

        creer.assert_called()
        assert result.passed is True
        assert result.etapes[0].code == 0
        assert "5 passed" in result.output_summary

    async def test_without_a_group_an_expired_step_still_returns(
        self, projet: Path
    ) -> None:
        commande = f'"{sys.executable}" -c "import time; time.sleep(600)"'

        with patch("tessera.services.groupe_de_processus.creer_groupe", return_value=None):
            result = await TestRunnerService().run_tests(
                projet, test_command=commande, timeout=2
            )

        assert result.expiree is True


class TestGroupeDEtape:
    def test_each_step_gets_its_own_group_closed_once(self) -> None:
        with (
            patch(
                "tessera.services.groupe_de_processus.creer_groupe", return_value=object()
            ),
            patch(
                "tessera.services.groupe_de_processus.fermer_le_groupe",
                return_value=True,
            ) as fermer,
        ):
            groupe = GroupeDEtape()
            groupe.fermer()
            groupe.fermer()

        fermer.assert_called_once()

    def test_a_pid_that_is_not_an_int_is_not_attached(self) -> None:
        with patch(
            "tessera.services.groupe_de_processus.creer_groupe", return_value=object()
        ):
            assert GroupeDEtape().rattacher(MagicMock()) is False

    def test_an_ungrouped_step_reports_no_tree_closed(self) -> None:
        with patch("tessera.services.groupe_de_processus.creer_groupe", return_value=None):
            assert GroupeDEtape().fermer() is False


class TestCommandeQuiFinitDansLeDelai:
    async def test_exit_code_and_output_are_kept(self, projet: Path) -> None:
        commande = (
            f'"{sys.executable}" -c "import sys; print(\'1 failed, 2 passed in 0.1s\'); '
            'sys.exit(3)"'
        )

        result = await TestRunnerService().run_tests(projet, test_command=commande)

        assert result.passed is False
        assert result.expiree is False
        assert result.etapes[0].code == 3
        assert "1 failed, 2 passed" in result.output_summary
