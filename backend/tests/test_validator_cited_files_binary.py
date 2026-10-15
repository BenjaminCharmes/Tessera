"""A cited binary file is attested by its size, not read as text (ticket-462)."""

from pathlib import Path

from tessera.services.validator_binary import is_binary_file
from tessera.services.validator_cited_files import build_cited_files_section

_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + bytes(range(256)) * 4


def test_png_is_attested_with_its_size_and_without_its_bytes(tmp_path: Path) -> None:
    (tmp_path / "hero-couple.png").write_bytes(_PNG_BYTES)

    section, report = build_cited_files_section(["hero-couple.png"], tmp_path)

    assert "### hero-couple.png" in section
    assert f"fichier binaire présent, {len(_PNG_BYTES)} octets" in section
    assert "�" not in section
    assert "IHDR" not in section
    assert "```" not in section


def test_binary_without_known_extension_is_detected_by_nul_byte(
    tmp_path: Path,
) -> None:
    payload = b"\x00\x01\x02" + b"abc" * 100
    (tmp_path / "blob.dat").write_bytes(payload)

    section, report = build_cited_files_section(["blob.dat"], tmp_path)

    assert f"fichier binaire présent, {len(payload)} octets" in section
    assert report.joined == ["blob.dat"]


def test_text_file_is_still_joined_in_full(tmp_path: Path) -> None:
    content = "line one\nline two with é\n"
    (tmp_path / "notes.txt").write_text(content, encoding="utf-8")

    section, report = build_cited_files_section(["notes.txt"], tmp_path)

    assert content in section
    assert "fichier binaire" not in section
    assert report.joined == ["notes.txt"]
    assert report.truncated == []


def test_binary_file_is_joined_not_truncated(tmp_path: Path) -> None:
    (tmp_path / "logo.png").write_bytes(_PNG_BYTES * 20)

    _, report = build_cited_files_section(["logo.png"], tmp_path)

    assert report.joined == ["logo.png"]
    assert report.truncated == []
    assert report.absent == []


def test_is_binary_file_extension_is_case_insensitive(tmp_path: Path) -> None:
    upper = tmp_path / "PHOTO.PNG"
    upper.write_bytes(b"plain ascii")
    plain = tmp_path / "readme.md"
    plain.write_text("hello", encoding="utf-8")

    assert is_binary_file(upper)
    assert not is_binary_file(plain)
