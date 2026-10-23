"""Ticket-571: a test step is cut at its deadline even when the event loop is blocked."""

import asyncio
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tessera.services import pipeline_stages
from tessera.services.detail_du_delai import ligne_de_delai
from tessera.services.groupe_d_etape import GroupeDEtape
from tessera.services.minuteur_d_etape import MARGE_S
from tessera.services.test_runner import TestResult, TestRunnerService

# La commande note son pid puis dort : seul un arrêt venu de l'extérieur de la
# boucle peut l'atteindre pendant que celle-ci est bloquée.
_DORMEUR = "import os, time; open('pid.txt', 'w').write(str(os.getpid())); time.sleep(600)"


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


def _mort_dans(pid: int, secondes: float) -> bool:
    """Poll synchronously: the loop is not ours to yield to in these tests."""
    fin = time.monotonic() + secondes
    while time.monotonic() < fin:
        if not _est_vivant(pid):
            return True
        time.sleep(0.1)
    return not _est_vivant(pid)


@pytest.fixture
def projet(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    return tmp_path


async def _attendre_le_pid(tache: "asyncio.Task[TestResult]", fichier: Path) -> int:
    for _ in range(100):
        if tache.done():
            raise AssertionError("the step ended before the loop was blocked")
        if fichier.exists() and fichier.read_text(encoding="utf-8").strip():
            return int(fichier.read_text(encoding="utf-8"))
        await asyncio.sleep(0.1)
    raise AssertionError("the step never wrote its pid")


class TestBoucleBloquee:
    async def test_the_command_is_dead_by_the_deadline_plus_two_seconds(
        self, projet: Path
    ) -> None:
        timeout = 2
        commande = f'"{sys.executable}" -c "{_DORMEUR}"'
        tache = asyncio.create_task(
            TestRunnerService().run_tests(projet, test_command=commande, timeout=timeout)
        )
        pid = await _attendre_le_pid(tache, projet / "pid.txt")

        # Appel synchrone : la boucle, donc le `wait_for`, ne tourne plus.
        time.sleep(timeout + 2.5)

        # Vérifié avant tout `await` : seul le minuteur a pu tuer le processus.
        assert _mort_dans(pid, 1.0)
        result = await asyncio.wait_for(tache, timeout=30)
        assert result.expiree is True
        assert result.duration_ms <= (timeout + 2) * 1000
        assert result.etape_coupee is not None
        assert result.etape_coupee.duree_ms <= (timeout + 2) * 1000


class TestMinuteurAnnule:
    async def test_the_timer_is_cancelled_when_the_command_ends_in_time(
        self, projet: Path
    ) -> None:
        commande = f'"{sys.executable}" -c "print(\'5 passed in 0.1s\')"'

        with patch("tessera.services.minuteur_d_etape.threading.Timer") as timer:
            result = await TestRunnerService().run_tests(projet, test_command=commande)

        assert result.passed is True
        assert result.expiree is False
        timer.return_value.start.assert_called_once()
        timer.return_value.cancel.assert_called_once()
        delai = timer.call_args.args[0]
        assert 120.0 <= delai <= 120.0 + MARGE_S


class TestJournalDuDelai:
    async def test_the_log_line_gives_the_real_duration_close_to_the_limit(
        self, projet: Path
    ) -> None:
        timeout = 2
        commande = f'"{sys.executable}" -c "import time; time.sleep(600)"'
        result = await TestRunnerService().run_tests(
            projet, test_command=commande, timeout=timeout
        )
        orch, run = MagicMock(), MagicMock()
        run.ticket_id = "ticket-000"

        pipeline_stages._noter_le_delai(orch, run, result)

        ligne = orch._log.call_args.args[0]
        trouve = re.search(r"durée réelle (\d+) s", ligne)
        assert trouve is not None, ligne
        reelle = int(trouve.group(1))
        assert timeout <= reelle <= timeout + 3

    def test_a_late_cut_shows_in_the_header(self) -> None:
        result = TestResult(
            passed=False,
            expiree=True,
            total=0,
            failed=0,
            output_summary="t",
            duration_ms=2_597_000,
            delai_s=1500.0,
        )

        assert ligne_de_delai(result) == "délai dépassé (1500 s, durée réelle 2597 s)"


class TestTerminerSync:
    def test_an_ungrouped_step_is_killed_without_the_event_loop(self) -> None:
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(600)"],
            start_new_session=os.name != "nt",
        )
        try:
            with patch(
                "tessera.services.groupe_de_processus.creer_groupe", return_value=None
            ):
                GroupeDEtape().terminer_sync(proc.pid)

            assert proc.wait(timeout=10) != 0
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)

    def test_a_pid_that_is_not_an_int_is_ignored(self) -> None:
        with patch("tessera.services.groupe_de_processus.creer_groupe", return_value=None):
            GroupeDEtape().terminer_sync(MagicMock())
