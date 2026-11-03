"""Largeurs et thèmes de capture configurables — ticket-616.

Un projet qui ne déclare rien garde 390 et 1440, clair et sombre. Une valeur
invalide ne lève rien : elle retombe sur ces défauts.
"""
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services import captures
from tessera.services.captures_config import (
    LARGEURS,
    THEMES,
    ConfigCaptures,
    Ecran,
    load_captures_config,
)

_BASE: dict[str, object] = {
    "url": "http://localhost:5196",
    "ecrans": [{"nom": "accueil", "chemin": "/"}],
}


def _lire(project: Path, **extra: object) -> ConfigCaptures:
    section = {**_BASE, **extra}
    project.joinpath("agents.json").write_text(
        json.dumps({"captures": section}), encoding="utf-8"
    )
    config = load_captures_config(project)
    assert config is not None
    return config


@pytest.fixture
def projet(tmp_path: Path) -> Path:
    dossier = tmp_path / "workspace" / "mon-projet"
    dossier.mkdir(parents=True)
    (dossier / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    return dossier


def test_defaults_give_the_same_four_names_per_screen(projet: Path) -> None:
    config = _lire(projet)

    assert config.largeurs == LARGEURS == (390, 1440)
    assert config.themes == THEMES == ("clair", "sombre")
    assert captures.noms_attendus(config) == [
        "accueil-390-clair.png",
        "accueil-390-sombre.png",
        "accueil-1440-clair.png",
        "accueil-1440-sombre.png",
    ]


def test_declared_widths_are_expected_for_each_theme(projet: Path) -> None:
    config = _lire(projet, largeurs=[390, 1024, 1440])

    noms = captures.noms_attendus(config)

    assert len(noms) == 6
    assert "accueil-1024-clair.png" in noms
    assert "accueil-1024-sombre.png" in noms


def test_declared_themes_restrict_the_names(projet: Path) -> None:
    config = _lire(projet, themes=["sombre"])

    assert captures.noms_attendus(config) == [
        "accueil-390-sombre.png",
        "accueil-1440-sombre.png",
    ]


@pytest.mark.parametrize(
    "largeurs",
    [
        [199, 390],
        [390, 3001],
        [390, 390],
        [],
        "1024",
        [390.5],
        [True],
        ["1024"],
        None,
    ],
)
def test_invalid_widths_fall_back_to_defaults(
    projet: Path, largeurs: object
) -> None:
    assert _lire(projet, largeurs=largeurs).largeurs == LARGEURS


@pytest.mark.parametrize(
    "themes",
    [["clair", "neon"], ["clair", "clair"], [], "clair", [1], None],
)
def test_invalid_themes_fall_back_to_defaults(projet: Path, themes: object) -> None:
    assert _lire(projet, themes=themes).themes == THEMES


def test_bounds_are_inclusive(projet: Path) -> None:
    assert _lire(projet, largeurs=[200, 3000]).largeurs == (200, 3000)


def test_payload_sent_to_the_script_carries_the_declared_values() -> None:
    config = ConfigCaptures(
        url="http://localhost:5196",
        ecrans=(Ecran(nom="accueil", chemin="/"),),
        largeurs=(1024,),
        themes=("clair",),
    )

    charge = json.loads(captures._charge(config, None))

    assert charge["largeurs"] == [1024]
    assert charge["themes"] == ["clair"]


@pytest.mark.parametrize(
    "nom",
    ["x-1024-clair.png", "x-390-sombre.png", "ecran-fin-768-clair.png"],
)
def test_pattern_accepts_any_integer_width(nom: str) -> None:
    assert captures.MOTIF_FICHIER.fullmatch(nom)


@pytest.mark.parametrize(
    "nom",
    ["../x.png", "x-abc-clair.png", "x-1024-neon.png", "x-1024-clair.txt", "x--clair.png"],
)
def test_pattern_refuses_malformed_names(nom: str) -> None:
    assert captures.MOTIF_FICHIER.fullmatch(nom) is None


@pytest.fixture
def client(projet: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "ide_workspace_dir", projet.parent)
    monkeypatch.setattr(settings, "ide_state_dir", projet.parent.parent / "etat")
    with TestClient(app) as c:
        yield c


def test_route_serves_a_custom_width_and_still_refuses_traversal(
    projet: Path, client: TestClient
) -> None:
    dossier = captures.dossier_des_captures("mon-projet")
    dossier.mkdir(parents=True)
    (dossier / "accueil-1024-clair.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    base = "/api/v1/projects/mon-projet/captures"

    assert client.get(f"{base}/accueil-1024-clair.png").status_code == 200
    assert client.get(f"{base}/..%2Fx.png").status_code == 404
    assert client.get(f"{base}/accueil-1025-clair.png").status_code == 404
    assert client.get(f"{base}/accueil-1024-clair.txt").status_code == 404
