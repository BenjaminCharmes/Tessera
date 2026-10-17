"""A dotted identifier in a criterion is not a cited file (ticket-475)."""

from tessera.services.validator_cited_files import extract_file_refs
from tessera.services.validator_file_extensions import looks_like_file


def test_dotted_identifiers_are_not_extracted() -> None:
    refs = extract_file_refs(
        ["`BRAND.name` et `BRAND.domain` viennent de `settings.github_token`"]
    )

    assert refs == []


def test_plain_and_nested_files_are_still_extracted() -> None:
    refs = extract_file_refs(
        ["`brand.ts`, `src/lib/brand.ts` et `prisma/schema.prisma`"]
    )

    assert refs == ["brand.ts", "src/lib/brand.ts", "prisma/schema.prisma"]


def test_a_token_with_a_slash_is_a_file_whatever_its_extension() -> None:
    refs = extract_file_refs(["`docs/notes.unknownext`"])

    assert refs == ["docs/notes.unknownext"]


def test_a_known_extension_is_matched_case_insensitively_with_line_suffix() -> None:
    refs = extract_file_refs(["`README.MD` et `brand.ts:12`", "`user.email`"])

    assert refs == ["README.MD", "brand.ts"]


def test_looks_like_file_rejects_a_token_without_extension() -> None:
    assert not looks_like_file("Makefile")
    assert not looks_like_file("user.email")
    assert looks_like_file(".env")
