"""La porte de configuration des tests connaît tous les fichiers — ticket-748."""
from tessera.services.config_tests_touchee import (
    fichiers_de_config_touches,
    fichiers_non_nommes,
)


def _creation(chemin: str) -> str:
    """A diff that creates `chemin` with one line."""
    return (
        f"diff --git a/{chemin} b/{chemin}\nnew file mode 100644\n"
        f"--- /dev/null\n+++ b/{chemin}\n@@ -0,0 +1,1 @@\n+x = 1\n"
    )


def _modification(chemin: str) -> str:
    """A diff that changes one line of `chemin`."""
    return (
        f"diff --git a/{chemin} b/{chemin}\n--- a/{chemin}\n+++ b/{chemin}\n"
        "@@ -1,2 +1,2 @@\n-a = 1\n+a = 2\n b = 1\n"
    )


def test_a_created_pytest_ini_is_flagged_when_the_ticket_does_not_name_it() -> None:
    fichiers = fichiers_de_config_touches(_creation("backend/pytest.ini"), [])

    assert fichiers == ["backend/pytest.ini"]
    assert fichiers_non_nommes(fichiers, "Implement the feature.") == ["backend/pytest.ini"]


def test_a_modified_vite_config_is_flagged() -> None:
    diff = _modification("frontend/vite.config.ts")

    assert fichiers_de_config_touches(diff, []) == ["frontend/vite.config.ts"]


def test_every_other_config_name_is_flagged() -> None:
    noms = ["tox.ini", "setup.cfg", "mypy.ini", ".mypy.ini", ".coveragerc", "vitest.workspace.ts"]

    for nom in noms:
        assert fichiers_de_config_touches(_modification(f"backend/{nom}"), []) == [
            f"backend/{nom}"
        ], nom


def test_a_source_file_with_a_similar_name_is_not_flagged() -> None:
    diff = _modification("frontend/src/vite.configuration.ts")

    assert fichiers_de_config_touches(diff, []) == []


def test_only_the_full_path_covers_a_file() -> None:
    fichiers = ["frontend/vitest.config.ts"]

    assert fichiers_non_nommes(fichiers, "Voir frontend/src/x/vitest.config.ts") == fichiers
    assert fichiers_non_nommes(fichiers, "Voir `vitest.config.ts`") == fichiers
    assert fichiers_non_nommes(fichiers, "Voir app/frontend/vitest.config.ts") == fichiers
    assert fichiers_non_nommes(["frontend/vite.config.ts"], "Voir frontend/vite.config.ts.") == []


def test_a_root_file_is_not_covered_by_the_same_name_in_a_folder() -> None:
    assert fichiers_non_nommes(["pytest.ini"], "Voir backend/pytest.ini") == ["pytest.ini"]
    assert fichiers_non_nommes(["pytest.ini"], "Voir `pytest.ini` à la racine") == []
