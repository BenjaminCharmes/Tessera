"""The testeur runs every step of an `&&` chain — ticket-337.

Lancée sans shell, `a && b` ne faisait tourner que `a` quand `a` est un
exécutable natif : `&&` et la suite devenaient ses arguments, et le testeur
annonçait vert ce qu'il n'avait pas lancé. Avec `npm` en tête, `npm.cmd`
passait par cmd.exe, qui enchaînait — par chance, et seulement sous Windows.
"""
import sys
from pathlib import Path

from tessera.services.test_runner import TestRunnerService

PY = f'"{sys.executable}" -c'


def _sortie(code: int) -> str:
    return f'{PY} "import sys; sys.exit({code})"'


async def test_a_failing_later_step_fails_the_run(tmp_path: Path) -> None:
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_sortie(0)} && {_sortie(4)}"
    )

    assert result.passed is False
    assert result.demarree is True
    assert [e.code for e in result.etapes] == [0, 4]


async def test_the_chain_stops_at_the_first_failure(tmp_path: Path) -> None:
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_sortie(2)} && {_sortie(0)}"
    )

    assert result.passed is False
    assert [e.code for e in result.etapes] == [2]


async def test_every_step_green_is_green_and_each_step_is_recorded(tmp_path: Path) -> None:
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_sortie(0)} && {_sortie(0)}"
    )

    assert result.passed is True
    assert len(result.etapes) == 2
    assert all(e.code == 0 for e in result.etapes)
    assert "sys.exit(0)" in result.etapes[1].commande


async def test_an_unsupported_operator_does_not_start(tmp_path: Path) -> None:
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_sortie(0)} | {_sortie(0)}"
    )

    assert result.passed is False
    assert result.demarree is False
    assert "|" in result.output_summary
