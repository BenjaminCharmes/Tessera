"""ticket-992: a CLI command still past 1 024 characters goes through a node relay."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tessera.services.providers.lanceur_windows import LIMITE_LIGNE
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.relais_cli import relayer_si_trop_long


def _node(dossier: Path) -> str:
    (dossier / "bin").mkdir()
    node = dossier / "bin" / "node.exe"
    node.write_bytes(b"")
    return str(dossier / "bin")


def test_short_command_is_left_alone_without_reading_the_path(tmp_path: Path) -> None:
    def jamais() -> str:
        raise AssertionError("le PATH du compte n'est lu que pour relayer")

    commande = ["claude.exe", "--print", "--model", "x"]
    assert relayer_si_trop_long(commande, tmp_path, jamais) == commande
    assert not (tmp_path / "relais.js").exists()


def test_long_command_is_relayed_through_files(tmp_path: Path) -> None:
    schema = json.dumps({"type": "object", "properties": {f"cle{i}": {"type": "string"} for i in range(60)}})
    commande = ["claude.exe", "--print", "--json-schema", schema]
    relayee = relayer_si_trop_long(commande, tmp_path, lambda: _node(tmp_path))
    assert relayee == [
        str(tmp_path / "bin" / "node.exe"), "--preserve-symlinks-main",
        str(tmp_path / "relais.js"), str(tmp_path / "relais.json"),
    ]
    assert subprocess.list2cmdline(relayee).__len__() <= LIMITE_LIGNE
    assert json.loads((tmp_path / "relais.json").read_text(encoding="utf-8")) == commande


def test_long_command_without_node_on_the_account_path_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProviderIndisponible, match="node"):
        relayer_si_trop_long(["claude.exe", "x" * 2000], tmp_path, lambda: str(tmp_path / "vide"))


@pytest.mark.skipif(shutil.which("node") is None, reason="node absent")
def test_relay_passes_arguments_stdio_and_exit_code(tmp_path: Path) -> None:
    node = shutil.which("node")
    assert node is not None
    long = "a" * 3000
    script = "process.stdout.write(String(process.argv[1].length)); process.stdin.pipe(process.stdout); process.stdin.on('end', () => process.exit(7));"
    commande = [node, "-e", script, long]
    relayee = relayer_si_trop_long(commande, tmp_path, lambda: str(Path(node).parent))
    fini = subprocess.run(relayee, input=b"|entree", capture_output=True, timeout=60)
    assert fini.stdout == b"3000|entree"
    assert fini.returncode == 7
