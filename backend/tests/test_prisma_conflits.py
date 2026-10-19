"""Pure merges for Prisma schemas and migration folders — ticket-484."""
import pytest

from tessera.services.prisma_conflits import fusionner_ajouts, planifier_renumerotation

_ANCETRE = """generator client {
  provider = "prisma-client-js"
}

model User {
  id Int @id
}
"""


def _avec(*blocs: str) -> str:
    return _ANCETRE + "".join("\n" + bloc for bloc in blocs)


_ORDER = "model Order {\n  id Int @id\n}\n"
_WISH = "model Wish {\n  id Int @id\n  label String\n}\n"


def _accolades_equilibrees(texte: str) -> bool:
    return texte.count("{") == texte.count("}")


# --- fusionner_ajouts -------------------------------------------------------


def test_two_models_added_at_the_same_place_are_both_kept() -> None:
    resultat = fusionner_ajouts(_avec(_ORDER), _avec(_WISH), _ANCETRE)

    assert resultat is not None
    assert "model Order {" in resultat
    assert "model Wish {" in resultat
    assert "model User {" in resultat
    assert "<<<<<<<" not in resultat and ">>>>>>>" not in resultat
    assert _accolades_equilibrees(resultat)


def test_base_blocks_come_before_ticket_blocks_each_closed_on_its_own() -> None:
    resultat = fusionner_ajouts(_avec(_ORDER), _avec(_WISH), _ANCETRE)

    assert resultat is not None
    assert resultat.index("model Order") < resultat.index("model Wish")
    assert "}\nmodel" not in resultat
    assert resultat.endswith("}\n")


def test_enum_and_type_additions_are_kept() -> None:
    enum = "enum Role {\n  ADMIN\n  USER\n}\n"
    type_ = "type Address {\n  street String\n}\n"

    resultat = fusionner_ajouts(_avec(enum), _avec(type_), _ANCETRE)

    assert resultat is not None
    assert "enum Role {" in resultat and "type Address {" in resultat


def test_the_same_block_added_identically_on_both_sides_is_kept_once() -> None:
    resultat = fusionner_ajouts(_avec(_ORDER), _avec(_ORDER, _WISH), _ANCETRE)

    assert resultat is not None
    assert resultat.count("model Order {") == 1
    assert resultat.count("model Wish {") == 1


def test_ticket_adding_nothing_gives_the_base_back() -> None:
    assert fusionner_ajouts(_avec(_ORDER), _ANCETRE, _ANCETRE) == _avec(_ORDER)


def test_an_existing_block_edited_by_the_ticket_is_refused() -> None:
    edite = _ANCETRE.replace("id Int @id", "id Int @id\n  name String")

    assert fusionner_ajouts(_avec(_ORDER), edite, _ANCETRE) is None


def test_an_existing_block_edited_by_the_base_is_refused() -> None:
    edite = _ANCETRE.replace("id Int @id", "id Int @id\n  name String")

    assert fusionner_ajouts(edite, _avec(_WISH), _ANCETRE) is None


def test_an_existing_block_removed_is_refused() -> None:
    sans_user = _ANCETRE.split("model User")[0]

    assert fusionner_ajouts(_avec(_ORDER), sans_user, _ANCETRE) is None


def test_same_name_with_different_content_is_refused() -> None:
    autre = "model Order {\n  id Int @id\n  total Int\n}\n"

    assert fusionner_ajouts(_avec(_ORDER), _avec(autre), _ANCETRE) is None


def test_a_new_generator_is_not_an_addable_block() -> None:
    generateur = 'generator docs {\n  provider = "docs"\n}\n'

    assert fusionner_ajouts(_avec(_ORDER), _avec(generateur), _ANCETRE) is None


def test_a_line_outside_any_block_that_differs_is_refused() -> None:
    assert fusionner_ajouts(_avec(_ORDER), _avec(_WISH) + "stray\n", _ANCETRE) is None


def test_an_unclosed_block_is_refused() -> None:
    casse = _ANCETRE + "\nmodel Broken {\n  id Int\n"

    assert fusionner_ajouts(casse, _avec(_WISH), _ANCETRE) is None


def test_braces_in_strings_and_comments_do_not_move_block_boundaries() -> None:
    piege = 'model Note {\n  id Int @id // closes } early?\n  txt String @default("}")\n}\n'

    resultat = fusionner_ajouts(_avec(piege), _avec(_WISH), _ANCETRE)

    assert resultat is not None
    assert "model Note {" in resultat and "model Wish {" in resultat


def test_a_comment_stuck_to_a_new_block_travels_with_it() -> None:
    commente = "// Wishes belong to a list\n" + _WISH

    resultat = fusionner_ajouts(_avec(_ORDER), _avec(commente), _ANCETRE)

    assert resultat is not None
    assert "// Wishes belong to a list\nmodel Wish {" in resultat


def test_crlf_base_keeps_its_line_endings() -> None:
    base = _avec(_ORDER).replace("\n", "\r\n")

    resultat = fusionner_ajouts(base, _avec(_WISH), _ANCETRE)

    assert resultat is not None
    assert "\r\n" in resultat
    assert "\n" not in resultat.replace("\r\n", "")


# --- planifier_renumerotation -----------------------------------------------

_MIG = "prisma/migrations/"


def test_a_colliding_ticket_migration_moves_to_the_next_free_number() -> None:
    base = {_MIG + "0005_y"}
    presents = {_MIG + "0005_y", _MIG + "0005_x"}

    assert planifier_renumerotation(base, presents) == [
        (_MIG + "0005_x", _MIG + "0006_x")
    ]


def test_no_collision_means_no_rename() -> None:
    base = {_MIG + "0005_y"}

    assert planifier_renumerotation(base, base | {_MIG + "0006_x"}) == []
    assert planifier_renumerotation(base, base) == []
    assert planifier_renumerotation(set(), set()) == []


def test_ticket_migrations_keep_their_order_when_the_first_collides() -> None:
    base = {_MIG + "0005_y"}
    presents = base | {_MIG + "0005_x", _MIG + "0006_z"}

    assert planifier_renumerotation(base, presents) == [
        (_MIG + "0005_x", _MIG + "0007_x"),
        (_MIG + "0006_z", _MIG + "0008_z"),
    ]


def test_a_migration_before_the_collision_stays_where_it_is() -> None:
    base = {_MIG + "0004_a", _MIG + "0005_y"}
    presents = base | {_MIG + "0003_w", _MIG + "0005_x"}

    assert planifier_renumerotation(base, presents) == [
        (_MIG + "0005_x", _MIG + "0006_x")
    ]


def test_timestamp_prefixes_are_never_renamed() -> None:
    base = {_MIG + "20261015093000_y"}
    presents = base | {_MIG + "20261015093000_x"}

    assert planifier_renumerotation(base, presents) == []


def test_a_counter_never_collides_with_a_timestamp() -> None:
    base = {_MIG + "20261015093000_y"}

    assert planifier_renumerotation(base, base | {_MIG + "0005_x"}) == []


def test_the_zero_padding_width_is_kept() -> None:
    base = {_MIG + "009_y"}
    presents = base | {_MIG + "009_x"}

    assert planifier_renumerotation(base, presents) == [
        (_MIG + "009_x", _MIG + "010_x")
    ]


def test_folders_outside_prisma_migrations_are_ignored() -> None:
    base = {"db/migrations/0005_y", "docs"}
    presents = base | {"db/migrations/0005_x"}

    assert planifier_renumerotation(base, presents) == []


def test_each_prisma_folder_is_numbered_on_its_own() -> None:
    base = {"api/prisma/migrations/0001_a", "web/prisma/migrations/0001_b"}
    presents = base | {"api/prisma/migrations/0001_c"}

    assert planifier_renumerotation(base, presents) == [
        ("api/prisma/migrations/0001_c", "api/prisma/migrations/0002_c")
    ]


@pytest.mark.parametrize("nom", ["init", "_x", "migration_lock"])
def test_a_folder_without_a_counter_prefix_is_left_alone(nom: str) -> None:
    base = {_MIG + "0005_y"}

    assert planifier_renumerotation(base, base | {_MIG + nom}) == []
