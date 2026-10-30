"""The single reader and writer of `agents.json` — ticket-675.

Each key read by the backend is checked through its real caller in four
situations: present, absent, mistyped, and a manifest that is not valid JSON.
"""
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from tessera.services import manifeste
from tessera.services.artifacts import read_artifact_mode
from tessera.services.autonomie import NiveauAutonomie, lire_niveau
from tessera.services.captures_config import load_captures_config
from tessera.services.manifeste import (
    ecrire_clef,
    ecrire_manifeste,
    lire_booleen,
    lire_chaine,
    lire_fichier,
    lire_label_map,
    lire_liste,
    lire_manifeste,
    lire_objet,
    lire_pour_modifier,
    lire_valeur,
)
from tessera.services.online_declaration import read_online_declaration
from tessera.services.politique_run import PolitiqueRun
from tessera.services.project_loader import (
    _load_github_remote,
    load_pipeline_config,
    load_services_config,
)
from tessera.services.worktree_politique import lire_worktree


@dataclass(frozen=True)
class Cle:
    """One key of the manifest, how a caller reads it, and what it should yield."""

    nom: str
    presente: object
    lecteur: Callable[[Path], object]
    attendu: object
    defaut: object
    mal_typee: object = 42


def _worktree(p: Path) -> object:
    config = lire_worktree(p, p, "tracked")
    return config.test_command if config is not None else None


def _captures(p: Path) -> object:
    config = load_captures_config(p)
    return config.url if config is not None else None


CLES: list[Cle] = [
    Cle("github_remote", "acme/app", lambda p: _load_github_remote(p)[1], "acme/app", None),
    Cle(
        "github_sync",
        {"label_map": {"bug": "fix"}},
        lire_label_map,
        {"bug": "fix"},
        {},
        mal_typee=["x"],
    ),
    Cle("base_branch", "main", lambda p: PolitiqueRun.lire(p).base_branch, "main", None),
    Cle("autonomy", "merge", lire_niveau, NiveauAutonomie.merge, NiveauAutonomie.commit),
    Cle("git_root", "ancestor", lambda p: PolitiqueRun.lire(p).git_root, "ancestor", None),
    Cle("artifacts", "tracked", read_artifact_mode, "tracked", "local"),
    Cle(
        "captures",
        {"url": "http://localhost:5173", "ecrans": [{"nom": "home", "chemin": "/"}]},
        _captures,
        "http://localhost:5173",
        None,
    ),
    Cle("online", {"domain": "Exemple.fr"}, lambda p: read_online_declaration(p).domain,
        "exemple.fr", None),
    Cle("worktree", {"test_command": "make t"}, _worktree, "make t", None),
    Cle(
        "services",
        [{"nom": "api", "commande": "run"}],
        lambda p: [s["nom"] for s in load_services_config(p)],
        ["api"],
        [],
    ),
    Cle("pipeline", {"test_command": "pytest"},
        lambda p: load_pipeline_config(p).test_command, "pytest", None),
]


def _projet(tmp_path: Path, contenu: str | None) -> Path:
    projet = tmp_path / "projet"
    projet.mkdir()
    if contenu is not None:
        (projet / "agents.json").write_text(contenu, encoding="utf-8")
    return projet


@pytest.fixture(autouse=True)
def _journal_vierge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(manifeste, "_journalises", set())


@pytest.mark.parametrize("cle", CLES, ids=lambda c: c.nom)
def test_a_present_key_is_read(tmp_path: Path, cle: Cle) -> None:
    projet = _projet(tmp_path, json.dumps({cle.nom: cle.presente}))
    assert cle.lecteur(projet) == cle.attendu


@pytest.mark.parametrize("cle", CLES, ids=lambda c: c.nom)
def test_an_absent_key_gives_the_default(tmp_path: Path, cle: Cle) -> None:
    projet = _projet(tmp_path, json.dumps({"autre": 1}))
    assert cle.lecteur(projet) == cle.defaut


@pytest.mark.parametrize("cle", CLES, ids=lambda c: c.nom)
def test_a_mistyped_key_gives_the_default(tmp_path: Path, cle: Cle) -> None:
    projet = _projet(tmp_path, json.dumps({cle.nom: cle.mal_typee}))
    assert cle.lecteur(projet) == cle.defaut


@pytest.mark.parametrize("cle", CLES, ids=lambda c: c.nom)
def test_an_invalid_json_gives_the_default(tmp_path: Path, cle: Cle) -> None:
    projet = _projet(tmp_path, "{ pas du json")
    assert cle.lecteur(projet) == cle.defaut


@pytest.mark.parametrize("cle", CLES, ids=lambda c: c.nom)
def test_a_missing_manifest_gives_the_default(tmp_path: Path, cle: Cle) -> None:
    assert cle.lecteur(_projet(tmp_path, None)) == cle.defaut


@pytest.mark.parametrize("cle", CLES, ids=lambda c: c.nom)
def test_a_manifest_that_is_not_an_object_gives_the_default(tmp_path: Path, cle: Cle) -> None:
    assert cle.lecteur(_projet(tmp_path, "[1, 2]")) == cle.defaut


def test_every_documented_key_is_covered() -> None:
    assert {c.nom for c in CLES} == {
        "github_remote", "github_sync", "base_branch", "autonomy", "git_root",
        "artifacts", "captures", "online", "worktree", "services", "pipeline",
    }


def test_typed_readers_return_none_or_false_on_a_wrong_type(tmp_path: Path) -> None:
    projet = _projet(tmp_path, json.dumps({"a": 1, "b": "x", "c": True, "d": {"k": 1}, "e": [1]}))
    assert lire_chaine(projet, "a") is None and lire_chaine(projet, "b") == "x"
    assert lire_booleen(projet, "c") is True and lire_booleen(projet, "b") is False
    assert lire_objet(projet, "d") == {"k": 1} and lire_objet(projet, "e") is None
    assert lire_liste(projet, "e") == [1] and lire_liste(projet, "d") is None
    assert lire_valeur(projet, "absent") is None
    assert lire_manifeste(projet)["a"] == 1


def test_an_unreadable_manifest_is_logged_once(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    projet = _projet(tmp_path, "{ pas du json")
    with caplog.at_level(logging.WARNING):
        for _ in range(3):
            lire_manifeste(projet)
            lire_chaine(projet, "git_root")
    assert [r.message for r in caplog.records].count("agents_json_illisible") == 1


def test_a_manifest_that_reads_fine_again_is_logged_when_it_breaks_again(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    projet = _projet(tmp_path, "{ pas du json")
    chemin = projet / "agents.json"
    with caplog.at_level(logging.WARNING):
        lire_fichier(chemin)
        chemin.write_text("{}", encoding="utf-8")
        lire_fichier(chemin)
        chemin.write_text("{ encore cassé", encoding="utf-8")
        lire_fichier(chemin)
    assert [r.message for r in caplog.records].count("agents_json_illisible") == 2


def test_a_missing_manifest_is_not_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        lire_manifeste(_projet(tmp_path, None))
    assert caplog.records == []


def test_ecrire_clef_keeps_the_keys_it_does_not_know(tmp_path: Path) -> None:
    contenu = {"agents": [{"role": "codeur"}], "inconnue": {"x": [1, 2]}, "autonomy": "pr"}
    projet = _projet(tmp_path, json.dumps(contenu))
    ecrire_clef(projet, "github_remote", "acme/app")
    ecrit = json.loads((projet / "agents.json").read_text(encoding="utf-8"))
    assert ecrit == {**contenu, "github_remote": "acme/app"}
    assert (projet / "agents.json").read_text(encoding="utf-8").endswith("}\n")


def test_ecrire_clef_creates_a_missing_manifest(tmp_path: Path) -> None:
    projet = _projet(tmp_path, None)
    ecrire_clef(projet, "artifacts", "local")
    assert lire_chaine(projet, "artifacts") == "local"


def test_ecrire_clef_can_drop_an_obsolete_key(tmp_path: Path) -> None:
    projet = _projet(tmp_path, json.dumps({"vibe_artifacts": "tracked", "x": 1}))
    ecrire_clef(projet, "artifacts", "local", retirer=("vibe_artifacts",))
    assert lire_manifeste(projet) == {"x": 1, "artifacts": "local"}


def test_ecrire_clef_leaves_no_temporary_file(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "{}")
    ecrire_clef(projet, "a", 1)
    assert sorted(p.name for p in projet.iterdir()) == ["agents.json"]


def test_ecrire_manifeste_replaces_the_whole_content(tmp_path: Path) -> None:
    projet = _projet(tmp_path, json.dumps({"ancien": 1}))
    ecrire_manifeste(projet, {"nouveau": 2})
    assert lire_manifeste(projet) == {"nouveau": 2}


def test_lire_pour_modifier_refuses_to_guess(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        lire_pour_modifier(_projet(tmp_path, None))
    projet = tmp_path / "autre"
    projet.mkdir()
    (projet / "agents.json").write_text("{ cassé", encoding="utf-8")
    with pytest.raises(ValueError):
        lire_pour_modifier(projet)
    (projet / "agents.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        lire_pour_modifier(projet)


def test_lire_pour_modifier_returns_the_whole_manifest(tmp_path: Path) -> None:
    projet = _projet(tmp_path, json.dumps({"a": 1}))
    assert lire_pour_modifier(projet) == {"a": 1}
