"""A fake shared toolchain, so account-environment tests do not need the real one."""
from pathlib import Path

import pytest

from tessera.services.providers import path_compte


@pytest.fixture(name="chaine")
def chaine_factice(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> Path:
    racine = tmp_path_factory.mktemp("toolchain")
    (racine / "node").mkdir()
    (racine / "node" / "node.exe").write_bytes(b"")
    monkeypatch.setattr(path_compte, "TOOLCHAIN", racine)
    return racine
