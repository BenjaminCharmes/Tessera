"""Deterministic rules for the trivial blocks of a rebase conflict — ticket-548."""
import pytest

from tessera.services.regles_conflit import (
    Resolution,
    resoudre_bloc,
    resoudre_fichier,
)


def test_identical_sides_resolve_to_that_text() -> None:
    assert resoudre_bloc("a\n", "b\n", "b\n") == Resolution("b\n", "identiques")


def test_a_trailing_whitespace_difference_keeps_the_upstream_side() -> None:
    resolution = resoudre_bloc("x = 1\n", "x = 2\n", "x = 2  \r\n")

    assert resolution == Resolution("x = 2\n", "espacement")


def test_an_indentation_difference_is_not_a_spacing_difference() -> None:
    assert resoudre_bloc("", "if x:\n    a\n", "if x:\n  a\n") is None


def test_only_the_ticket_changed_keeps_the_ticket_side() -> None:
    assert resoudre_bloc("v0\n", "v0\n", "v1\n") == Resolution("v1\n", "cote-unique")


def test_only_upstream_changed_keeps_the_upstream_side() -> None:
    assert resoudre_bloc("v0\n", "v1\n", "v0\n") == Resolution("v1\n", "cote-unique")


def test_python_imports_added_on_both_sides_are_unioned_upstream_first() -> None:
    resolution = resoudre_bloc("", "import os\n", "from pathlib import Path\n")

    assert resolution == Resolution("import os\nfrom pathlib import Path\n", "imports")


def test_typescript_imports_added_on_both_sides_are_unioned() -> None:
    notre = "import { a } from './a'\n"
    leur = "import type { B } from \"./b\";\nimport './side-effect'\n"

    resolution = resoudre_bloc("", notre, leur)

    assert resolution == Resolution(notre + leur, "imports")


def test_an_import_added_on_both_sides_is_kept_once() -> None:
    base = "import os\n"
    resolution = resoudre_bloc(base, base + "import re\n", base + "import re\nimport sys\n")

    assert resolution == Resolution("import os\nimport re\nimport sys\n", "imports")


def test_a_block_mixing_an_import_and_another_line_is_not_settled_by_imports() -> None:
    assert resoudre_bloc("", "import os\nVALEUR = 1\n", "import re\n") is None


def test_an_import_removed_on_one_side_is_not_brought_back() -> None:
    base = "import os\nimport re\n"

    assert resoudre_bloc(base, "import os\nimport sys\n", base + "import json\n") is None


def test_both_sides_changing_the_same_line_differently_gives_none() -> None:
    assert resoudre_bloc("v0\n", "v1\n", "v2\n") is None


def _marque(base: str, notre: str, leur: str) -> str:
    return (
        f"<<<<<<< HEAD\n{notre}||||||| base\n{base}=======\n{leur}>>>>>>> ticket\n"
    )


def test_a_file_with_two_settled_blocks_is_rewritten_without_markers() -> None:
    texte = (
        "debut\n"
        + _marque("", "import os\n", "import re\n")
        + "milieu\n"
        + _marque("v0\n", "v0\n", "v1\n")
        + "fin\n"
    )

    assert resoudre_fichier(texte) == (
        "debut\nimport os\nimport re\nmilieu\nv1\nfin\n",
        ("imports", "cote-unique"),
    )


def test_one_block_without_a_rule_gives_none_for_the_whole_file() -> None:
    texte = _marque("", "import os\n", "import re\n") + _marque("v0\n", "v1\n", "v2\n")

    assert resoudre_fichier(texte) is None


@pytest.mark.parametrize(
    "texte",
    ["sans marqueur\n", "<<<<<<< HEAD\na\n||||||| base\n=======\nb\n"],
    ids=["no-block", "unclosed-block"],
)
def test_a_file_without_a_closed_block_gives_none(texte: str) -> None:
    assert resoudre_fichier(texte) is None


def test_crlf_line_endings_survive_a_settled_file() -> None:
    bloc = _marque("v0\n", "v0\n", "v1\n").replace("\n", "\r\n")
    texte = "a\r\n" + bloc + "z\r\n"

    resolu = resoudre_fichier(texte)

    assert resolu is not None
    assert resolu[0] == "a\r\nv1\r\nz\r\n"
