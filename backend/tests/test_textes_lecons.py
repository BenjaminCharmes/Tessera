"""`_resoudre_lecons`: the base file plus the run's own additions (ticket-907)."""

from tessera.services.git_workspace.textes import _resoudre_lecons

_PROPOSEES = [f"- leçon {i}" for i in range(11)]
_ANCETRE = "# L\n\n## En vigueur\n\n## Proposées\n\n" + "\n".join(_PROPOSEES) + "\n"
_BASE = "# L\n\n## En vigueur\n\n" + "\n".join(_PROPOSEES) + "\n\n## Proposées\n"


def test_the_base_wins_and_only_the_branch_addition_comes_back() -> None:
    branche = _ANCETRE + "- nouvelle\n"
    assert _resoudre_lecons(_ANCETRE, _BASE, branche) == _BASE + "- nouvelle\n"


def test_an_ancestor_line_removed_by_the_branch_refuses() -> None:
    branche = _ANCETRE.replace("- leçon 3\n", "")
    assert _resoudre_lecons(_ANCETRE, _BASE, branche) is None


def test_an_ancestor_line_modified_by_the_branch_refuses() -> None:
    assert _resoudre_lecons(_ANCETRE, _BASE, _ANCETRE.replace("leçon 3", "autre")) is None


def test_an_addition_already_in_the_base_is_not_duplicated() -> None:
    base = _BASE + "- nouvelle\n"
    assert _resoudre_lecons(_ANCETRE, base, _ANCETRE + "- nouvelle\n") == base


def test_a_base_without_proposees_refuses() -> None:
    assert _resoudre_lecons(_ANCETRE, "# L\n\n## En vigueur\n", _ANCETRE + "- x\n") is None


def test_additions_land_before_the_next_section() -> None:
    base = "## Proposées\n\n- a\n\n## Autre\n\n- z\n"
    resultat = _resoudre_lecons("## Proposées\n\n- a\n", base, "## Proposées\n\n- a\n- b\n")
    assert resultat == "## Proposées\n\n- a\n- b\n\n## Autre\n\n- z\n"


def test_crlf_in_the_branch_does_not_look_like_a_removal() -> None:
    branche = (_ANCETRE + "- nouvelle\n").replace("\n", "\r\n")
    assert _resoudre_lecons(_ANCETRE, _BASE, branche) == _BASE + "- nouvelle\n"


def test_an_absent_ancestor_accepts_every_branch_line_not_in_the_base() -> None:
    assert _resoudre_lecons("", _BASE, _BASE + "- x\n") == _BASE + "- x\n"
