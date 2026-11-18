"""The testeur's journal line names the failing test files — ticket-1006."""
from tessera.services.verification.ligne_des_echecs import fichiers_en_echec, ligne_du_testeur
from tessera.services.verification.resultat_de_test import TestResult


def _rouge(details: str, resume: str = "failed") -> TestResult:
    return TestResult(
        passed=False, total=10, failed=3, output_summary=resume, failure_details=details
    )


def test_pytest_names_each_file_once() -> None:
    details = (
        "FAILED tests/test_a.py::test_un - assert 1 == 2\n"
        "FAILED tests/test_a.py::test_deux - assert 1 == 3\n"
        "FAILED tests/test_b.py::test_trois - boom\n"
    )

    ligne = ligne_du_testeur(_rouge(details))

    assert ligne.count("tests/test_a.py") == 1
    assert ligne.count("tests/test_b.py") == 1
    assert "+" not in ligne.split("fichiers en échec")[1]


def test_vitest_names_five_files_and_counts_the_rest() -> None:
    details = "\n".join(f" FAIL  src/f{i}.test.ts > cas" for i in range(7))

    ligne = ligne_du_testeur(_rouge(details))

    assert len(fichiers_en_echec(_rouge(details))) == 7
    assert "src/f4.test.ts" in ligne
    assert "src/f5.test.ts" not in ligne
    assert ligne.endswith("+2")


def test_line_is_unchanged_without_a_readable_file() -> None:
    result = _rouge("src/x.ts(1,1): error TS2322", resume="tsc: 1 error")

    assert ligne_du_testeur(result) == "tsc: 1 error"


def test_line_is_unchanged_when_tests_pass() -> None:
    result = TestResult(passed=True, total=1, failed=0, output_summary="1 passed")

    assert ligne_du_testeur(result) == "1 passed"
