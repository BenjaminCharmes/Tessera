"""A folder cited in a criterion is joined as the list of its files (ticket-509)."""

from pathlib import Path

import pytest

from tessera.services.validator_cited_dirs import (
    FOLDER_MAX_ENTRIES,
    list_folder_files,
    looks_like_folder,
    render_folder_entry,
    resolve_folder,
)
from tessera.services.validator_cited_files import (
    CITED_FILES_MAX_CHARS,
    build_cited_files_section,
    extract_file_refs,
    format_cited_files_log,
)


def _maquette(root: Path, count: int = 3) -> None:
    folder = root / "design" / "maquette"
    folder.mkdir(parents=True)
    for i in range(count):
        (folder / f"ecran-{i:03d}.html").write_text("<p>x</p>", encoding="utf-8")
    (folder / "sous-dossier").mkdir()
    (folder / "sous-dossier" / "profond.html").write_text("x", encoding="utf-8")


def test_a_cited_folder_gets_a_section_listing_its_files(tmp_path: Path) -> None:
    _maquette(tmp_path)

    section, report = build_cited_files_section(["design/maquette/"], tmp_path)

    assert "### design/maquette/" in section
    assert "design/maquette/ecran-000.html" in section
    assert "design/maquette/ecran-002.html" in section
    assert "profond.html" not in section
    assert report.joined == ["design/maquette/"]
    assert report.absent == []


@pytest.mark.parametrize("ref", ["design/maquette", "design/maquette/"])
def test_a_folder_is_recognised_with_or_without_trailing_slash(
    tmp_path: Path, ref: str
) -> None:
    _maquette(tmp_path)

    refs = extract_file_refs([f"la maquette existe dans `{ref}`"])
    section, report = build_cited_files_section(refs, tmp_path)

    assert refs == [ref]
    assert report.joined == [ref]
    assert "design/maquette/ecran-001.html" in section


def test_a_url_route_or_a_dotted_identifier_is_not_a_folder() -> None:
    refs = extract_file_refs(["`/api/v1/runs`, `https://x.test/a` et `BRAND.name`"])

    assert refs == []
    assert not looks_like_folder("a b/c")


def test_the_list_is_bounded_in_number_of_entries(tmp_path: Path) -> None:
    folder = tmp_path / "many"
    folder.mkdir()
    for i in range(FOLDER_MAX_ENTRIES + 20):
        (folder / f"f{i:04d}.txt").write_text("", encoding="utf-8")

    section, report = build_cited_files_section(["many/"], tmp_path)

    assert "many/f0099.txt" in section
    assert "many/f0100.txt" not in section
    assert report.folders == {"many/": FOLDER_MAX_ENTRIES + 20}
    assert report.truncated == ["many/"]


def test_the_list_counts_in_the_cited_files_budget(tmp_path: Path) -> None:
    folder = tmp_path / "lourd"
    folder.mkdir()
    for i in range(FOLDER_MAX_ENTRIES):
        (folder / f"fichier-{i:03d}.txt").write_text("", encoding="utf-8")
    # Un fichier long laisse 100 caractères au dossier : sa liste est coupée.
    (tmp_path / "big.test.ts").write_text(
        "x" * (CITED_FILES_MAX_CHARS - 150), encoding="utf-8"
    )
    (tmp_path / "late.test.ts").write_text("late", encoding="utf-8")

    section, report = build_cited_files_section(
        ["big.test.ts", "lourd/", "late.test.ts"], tmp_path
    )

    assert "lourd/fichier-099.txt" not in section
    assert report.truncated == ["lourd/"]
    assert report.omitted == ["late.test.ts"]


def test_render_cuts_the_names_at_the_remaining_budget() -> None:
    files = [f"d/{i:03d}.txt" for i in range(50)]

    entry, cut = render_folder_entry("d/", files, budget=40)

    assert cut
    assert "d/049.txt" not in entry
    assert "50 fichiers au total" in entry


def test_log_line_marks_the_entry_as_a_folder_with_its_file_count(
    tmp_path: Path,
) -> None:
    _maquette(tmp_path, count=9)
    (tmp_path / "a.test.ts").write_text("a", encoding="utf-8")

    _, report = build_cited_files_section(
        ["design/maquette/", "a.test.ts"], tmp_path
    )

    assert format_cited_files_log(report) == (
        "validateur: fichiers cités joints : "
        "design/maquette/ (dossier, 9 fichiers), a.test.ts"
    )


@pytest.mark.parametrize("ref", ["design/absent/", "design/absent"])
def test_a_cited_folder_that_does_not_exist_is_reported_absent(
    tmp_path: Path, ref: str
) -> None:
    section, report = build_cited_files_section([ref], tmp_path)

    assert report.absent == [ref]
    assert report.joined == []
    assert "absent du dépôt" in section
    assert "absents : " + ref in format_cited_files_log(report)


def test_a_trailing_slash_never_matches_a_file_of_that_name(tmp_path: Path) -> None:
    (tmp_path / "notes").write_text("x", encoding="utf-8")

    _, report = build_cited_files_section(["docs/notes/"], tmp_path)

    assert report.absent == ["docs/notes/"]


def test_resolve_folder_stays_inside_the_root(tmp_path: Path) -> None:
    (tmp_path / "in").mkdir()
    outside = tmp_path.parent / "outside-509"
    outside.mkdir(exist_ok=True)

    assert resolve_folder("in/", tmp_path) == tmp_path / "in"
    assert resolve_folder("../outside-509/", tmp_path) is None
    assert resolve_folder(str(outside), tmp_path) is None


def test_list_folder_files_is_sorted_and_skips_subfolders(tmp_path: Path) -> None:
    _maquette(tmp_path, count=2)

    files = list_folder_files("design/maquette", tmp_path / "design" / "maquette")

    assert files == ["design/maquette/ecran-000.html", "design/maquette/ecran-001.html"]
