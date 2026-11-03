"""Extraction des ports déclarés par un projet — ticket-416."""
import json
from pathlib import Path

from tessera.services.ports_declares import (
    port_de_vite_config,
    ports_d_une_commande,
    ports_du_projet,
)


def test_port_extracted_from_command_with_space() -> None:
    assert ports_d_une_commande("uvicorn app:app --port 8026") == [8026]


def test_port_extracted_from_command_with_equals() -> None:
    assert ports_d_une_commande("uvicorn app:app --port=8026 --reload") == [8026]


def test_command_without_port_gives_nothing() -> None:
    assert ports_d_une_commande("npm.cmd run dev") == []


def test_port_extracted_from_vite_config() -> None:
    texte = "export default { server: { host: true, port: 5196 } }"

    assert port_de_vite_config(texte) == [5196]


def test_vite_config_without_port_gives_nothing() -> None:
    assert port_de_vite_config("export default {}") == []


def test_project_ports_come_from_manifest_and_vite_config(tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "vite.config.ts").write_text(
        "export default { server: { port: 5196 } }", encoding="utf-8"
    )
    (tmp_path / "agents.json").write_text(
        json.dumps(
            {"services": [{"nom": "api", "commande": "uvicorn x:app --port 8026"}]}
        ),
        encoding="utf-8",
    )

    assert ports_du_projet(tmp_path) == {8026: "api", 5196: "frontend"}


def test_service_cwd_outside_project_is_ignored(tmp_path: Path) -> None:
    projet = tmp_path / "projet"
    projet.mkdir()
    ailleurs = tmp_path / "ailleurs"
    ailleurs.mkdir()
    (ailleurs / "vite.config.ts").write_text("port: 9999", encoding="utf-8")
    (projet / "agents.json").write_text(
        json.dumps(
            {"services": [{"nom": "front", "commande": "npm", "cwd": "../ailleurs"}]}
        ),
        encoding="utf-8",
    )

    assert ports_du_projet(projet) == {}
