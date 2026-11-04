"""A diff cut into sections, delivered lines only — ticket-757."""
from tessera.services.documentation_diff import sections_du_diff

_DIFF = (
    "diff --git a/x.py b/x.py\n"
    "index 1..2 100644\n"
    "--- a/x.py\n"
    "+++ b/x.py\n"
    "@@ -1,2 +1,2 @@\n"
    " garde\n"
    "-ancien\n"
    "+nouveau\n"
    "@@ -9,1 +9,2 @@\n"
    "+++i\n"
    "--- tiret\n"
    "\\ No newline at end of file\n"
    "diff --git a/y.py b/y.py\n"
    "--- a/y.py\n"
    "+++ b/y.py\n"
    "@@ -1 +1 @@\n"
    "+autre\n"
)


def test_a_diff_is_cut_into_one_section_per_hunk() -> None:
    sections = sections_du_diff(_DIFF)

    assert [s.livrees for s in sections] == [["garde", "nouveau"], ["++i"], ["autre"]]


def test_removed_lines_are_not_delivered_but_stay_in_the_section() -> None:
    premiere = sections_du_diff(_DIFF)[0]

    assert "-ancien" in premiere.lignes
    assert "ancien" not in premiere.livrees
    assert premiere.avec_marqueurs == [" garde", "+nouveau"]


def test_file_headers_are_not_content_but_hunk_lines_are() -> None:
    lignes = [ligne for s in sections_du_diff(_DIFF) for ligne in s.lignes]

    assert not any(ligne.startswith("+++ b/") for ligne in lignes)
    assert "+++i" in lignes
    assert "--- tiret" in lignes


def test_a_diff_without_hunk_marker_is_one_section() -> None:
    sections = sections_du_diff("diff --git a/x b/x\n+un\n+deux\n")

    assert [s.livrees for s in sections] == [["un", "deux"]]
