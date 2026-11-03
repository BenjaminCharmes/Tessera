"""Declared visual check and its trigger — ticket-617, ADR-062."""
import json
from pathlib import Path

from tessera.services.captures_config import load_captures_config
from tessera.services.controle_visuel import (
    DELAI_DEFAUT_S,
    DELAI_MAX_S,
    ControleVisuel,
    controle_du,
    lire_le_controle,
)

_CAPTURES: dict[str, object] = {
    "url": "http://localhost:{port}",
    "ecrans": [{"nom": "accueil", "chemin": "/"}],
    "largeurs": [390, 1024, 1440],
    "interface": ["app/", "components/", ".css"],
    "demarrage": {"commande": "corepack pnpm@10 exec next dev -p {port}", "delai_s": 120},
}


def _ecrire(project: Path, mode: object = "joindre", **captures: object) -> None:
    section = {**_CAPTURES, **captures}
    section = {k: v for k, v in section.items() if v is not None}
    pipeline = {} if mode is None else {"controle_visuel": mode}
    project.joinpath("agents.json").write_text(
        json.dumps({"pipeline": pipeline, "captures": section}), encoding="utf-8"
    )


def _controle(project: Path, **captures: object) -> ControleVisuel:
    _ecrire(project, **captures)
    controle = lire_le_controle(project)
    assert controle is not None
    return controle


def test_lire_le_controle_reads_mode_and_configuration(tmp_path: Path) -> None:
    controle = _controle(tmp_path)
    assert controle.mode == "joindre"
    assert controle.captures.largeurs == (390, 1024, 1440)
    assert controle.interface == ("app/", "components/", ".css")
    assert controle.demarrage.commande.endswith("-p {port}")


def test_lire_le_controle_accepts_relire(tmp_path: Path) -> None:
    _ecrire(tmp_path, mode="relire")
    controle = lire_le_controle(tmp_path)
    assert controle is not None and controle.mode == "relire"


def test_lire_le_controle_without_declared_mode_is_none(tmp_path: Path) -> None:
    _ecrire(tmp_path, mode=None)
    assert lire_le_controle(tmp_path) is None


def test_lire_le_controle_with_unknown_mode_is_none(tmp_path: Path) -> None:
    for mode in ("auto", "", 1, True, None, ["joindre"]):
        _ecrire(tmp_path, mode=mode)
        assert lire_le_controle(tmp_path) is None


def test_lire_le_controle_needs_port_in_start_command(tmp_path: Path) -> None:
    _ecrire(tmp_path, demarrage={"commande": "next dev -p 3000"})
    assert lire_le_controle(tmp_path) is None


def test_lire_le_controle_without_start_is_none(tmp_path: Path) -> None:
    for demarrage in (None, "next dev -p {port}", {"delai_s": 10}, {"commande": 3}):
        _ecrire(tmp_path, demarrage=demarrage)
        assert lire_le_controle(tmp_path) is None


def test_lire_le_controle_without_usable_captures_is_none(tmp_path: Path) -> None:
    _ecrire(tmp_path, ecrans=[])
    assert lire_le_controle(tmp_path) is None


def test_lire_le_controle_without_file_or_garbage_is_none(tmp_path: Path) -> None:
    assert lire_le_controle(tmp_path) is None
    tmp_path.joinpath("agents.json").write_text("{pas du json", encoding="utf-8")
    assert lire_le_controle(tmp_path) is None
    tmp_path.joinpath("agents.json").write_text("[]", encoding="utf-8")
    assert lire_le_controle(tmp_path) is None
    tmp_path.joinpath("agents.json").write_text(
        json.dumps({"pipeline": [], "captures": _CAPTURES}), encoding="utf-8"
    )
    assert lire_le_controle(tmp_path) is None


def test_lire_le_controle_ignores_captures_without_mode(tmp_path: Path) -> None:
    tmp_path.joinpath("agents.json").write_text(
        json.dumps({"captures": _CAPTURES}), encoding="utf-8"
    )
    assert lire_le_controle(tmp_path) is None


def test_delai_defaults_to_120_and_is_capped_at_300(tmp_path: Path) -> None:
    commande = "next dev -p {port}"
    cas: dict[str, object] = {"absent": None, "texte": "vite", "zero": 0, "vrai": True}
    for valeur in cas.values():
        brut = {"commande": commande, "delai_s": valeur}
        assert _controle(tmp_path, demarrage=brut).demarrage.delai_s == DELAI_DEFAUT_S
    assert _controle(tmp_path, demarrage={"commande": commande}).demarrage.delai_s == 120
    plafonne = _controle(tmp_path, demarrage={"commande": commande, "delai_s": 900})
    assert plafonne.demarrage.delai_s == DELAI_MAX_S
    court = _controle(tmp_path, demarrage={"commande": commande, "delai_s": 45})
    assert court.demarrage.delai_s == 45


def test_interface_has_no_default(tmp_path: Path) -> None:
    for interface in (None, [], "app/", [3, ""]):
        controle = _controle(tmp_path, interface=interface)
        assert controle.interface == ()
        assert controle_du(["app/page.tsx", "x.css"], controle) is False


def test_controle_du_matches_prefix_and_extension(tmp_path: Path) -> None:
    controle = _controle(tmp_path)
    assert controle_du(["README.md", "app/page.tsx"], controle) is True
    assert controle_du(["docs/a.md", "styles/site.css"], controle) is True
    assert controle_du(iter(["components/Nav.tsx"]), controle) is True


def test_controle_du_is_false_when_nothing_matches(tmp_path: Path) -> None:
    controle = _controle(tmp_path)
    assert controle_du([], controle) is False
    # `app/` est un préfixe de chemin : `src/app/` et `application/` n'y sont pas.
    assert controle_du(["src/app/page.tsx", "application/x.py", "a.css.map"], controle) is False


def test_manual_capture_config_is_unchanged_without_new_fields(tmp_path: Path) -> None:
    tmp_path.joinpath("agents.json").write_text(
        json.dumps({"captures": {"url": "http://localhost:5196/", "ecrans": _CAPTURES["ecrans"]}}),
        encoding="utf-8",
    )
    config = load_captures_config(tmp_path)
    assert config is not None
    assert config.url == "http://localhost:5196"
    assert lire_le_controle(tmp_path) is None
