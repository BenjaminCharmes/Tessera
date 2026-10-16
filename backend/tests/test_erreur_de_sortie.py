"""Tests for the error line surfaced in a failed step's detail (ticket-473)."""

from tessera.services.erreur_de_sortie import (
    detail_avec_erreur,
    premiere_ligne_d_erreur,
)
from tessera.services.test_runner import EtapeTest, _parse_failed_step

_CONSEIL = "corepack"
_CONSEIL_BIN = "node_modules/.bin"

_SORTIE_WINDOWS = "\n".join(
    [
        "> souhaito@0.1.0 check:build",
        "> node scripts/check-build.mjs",
        "'pnpm' n'est pas reconnu en tant que commande interne ou externe,",
        "un programme exécutable ou un fichier de commandes.",
        " ELIFECYCLE  Command failed with exit code 1.",
    ]
)

_SORTIE_UNIX = "\n".join(
    [
        "> node scripts/check-build.mjs",
        "sh: 1: pnpm: command not found",
        " ELIFECYCLE  Command failed with exit code 127.",
    ]
)


def test_windows_missing_command_leads_the_detail() -> None:
    resultat = _parse_failed_step(EtapeTest("pnpm run check:build", 1), _SORTIE_WINDOWS, 0, True)

    assert resultat.failure_details.startswith("'pnpm' n'est pas reconnu")
    assert _CONSEIL in resultat.failure_details
    assert _CONSEIL_BIN in resultat.failure_details
    assert "ELIFECYCLE" in resultat.failure_details


def test_unix_command_not_found_is_handled_the_same_way() -> None:
    resultat = _parse_failed_step(EtapeTest("pnpm run check:build", 127), _SORTIE_UNIX, 0, True)

    assert resultat.failure_details.startswith("sh: 1: pnpm: command not found")
    assert _CONSEIL in resultat.failure_details
    assert _CONSEIL_BIN in resultat.failure_details


def test_pytest_output_keeps_its_structured_extraction() -> None:
    sortie = "\n".join(
        [
            "=========================== short test summary info ===========================",
            "FAILED tests/test_a.py::test_x - AssertionError: boom",
            "========================= 1 failed, 2 passed in 0.12s =========================",
        ]
    )

    resultat = _parse_failed_step(EtapeTest("pytest", 1), sortie, 0, False)

    assert resultat.failure_details == "FAILED tests/test_a.py::test_x - AssertionError: boom"
    assert _CONSEIL not in resultat.failure_details


def test_error_without_missing_command_gets_no_corepack_hint() -> None:
    detail = detail_avec_erreur("src/a.ts(3,1): error TS2322: bad type", "queue")

    assert detail.startswith("src/a.ts(3,1): error TS2322")
    assert _CONSEIL not in detail


def test_cannot_find_module_is_an_error_line() -> None:
    assert premiere_ligne_d_erreur("ok\nCannot find module 'x'\nsuite") == "Cannot find module 'x'"


def test_output_without_error_line_is_unchanged() -> None:
    assert premiere_ligne_d_erreur("ligne 1\nligne 2") == ""
    assert detail_avec_erreur("ligne 1\nligne 2", "queue") == "queue"
