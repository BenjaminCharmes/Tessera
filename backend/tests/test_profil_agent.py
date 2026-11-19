"""ticket-1008: the agent profile is wiped between calls, except the two caches."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.providers.profil_agent import reinitialiser_profil


class Icacls:
    def __init__(self) -> None:
        self.appels: list[list[str]] = []

    async def __call__(self, args: list[str]) -> tuple[int, str]:
        self.appels.append(args)
        return 0, ""


@pytest.fixture
def profil(tmp_path: Path) -> Path:
    dossier = tmp_path / "profil-agent"
    (dossier / "npm-cache" / "_cacache").mkdir(parents=True)
    (dossier / "npm-cache" / "_cacache" / "index").write_text("i")
    (dossier / "uv" / "cache").mkdir(parents=True)
    (dossier / "uv" / "cache" / "wheel").write_text("w")
    return dossier


async def test_user_files_are_removed_and_both_caches_kept(profil: Path) -> None:
    (profil / ".bashrc").write_text("evil")
    (profil / ".npmrc").write_text("evil")
    (profil / "AppData" / "Roaming" / "uv").mkdir(parents=True)
    (profil / "AppData" / "Roaming" / "uv" / "uv.toml").write_text("evil")
    (profil / "uv" / "uv.toml").write_text("evil")
    icacls = Icacls()
    await reinitialiser_profil("tessera-agent", icacls, profil)
    assert sorted(p.name for p in profil.iterdir()) == ["AppData", "npm-cache", "uv"]
    assert [p.name for p in (profil / "uv").iterdir()] == ["cache"]
    assert (profil / "npm-cache" / "_cacache" / "index").read_text() == "i"
    assert (profil / "uv" / "cache" / "wheel").read_text() == "w"
    assert icacls.appels == [[str(profil), "/grant", "tessera-agent:(OI)(CI)M", "/L"]]


async def test_read_only_file_is_removed(profil: Path) -> None:
    fichier = profil / ".gitconfig"
    fichier.write_text("x")
    os.chmod(fichier, 0o400)
    await reinitialiser_profil("tessera-agent", Icacls(), profil)
    assert not fichier.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="junction")
async def test_a_junction_is_removed_without_following_it(profil: Path, tmp_path: Path) -> None:
    cible = tmp_path / "cible"
    cible.mkdir()
    (cible / "precieux.txt").write_text("x")
    lien = profil / "lien"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(lien), str(cible)], check=True, capture_output=True)
    await reinitialiser_profil("tessera-agent", Icacls(), profil)
    assert not lien.exists()
    assert (cible / "precieux.txt").exists()


async def test_a_failed_removal_raises_droits_refuses(profil: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (profil / "x.txt").write_text("x")

    def refuse(chemin: str) -> None:
        raise PermissionError("refusé")

    monkeypatch.setattr(os, "unlink", refuse)
    with pytest.raises(DroitsAgentRefuses):
        await reinitialiser_profil("tessera-agent", Icacls(), profil)


async def test_an_absent_folder_is_left_alone(tmp_path: Path) -> None:
    icacls = Icacls()
    await reinitialiser_profil("tessera-agent", icacls, tmp_path / "absent")
    assert icacls.appels == []
    assert not (tmp_path / "absent").exists()


async def test_temp_and_appdata_folders_exist_after_the_reset(profil: Path) -> None:
    (profil / "AppData" / "Local" / "Temp").mkdir(parents=True)
    (profil / "AppData" / "Local" / "Temp" / "junk").write_text("x")
    await reinitialiser_profil("tessera-agent", Icacls(), profil)
    assert (profil / "AppData" / "Local" / "Temp").is_dir()
    assert not (profil / "AppData" / "Local" / "Temp" / "junk").exists()
    assert (profil / "AppData" / "Roaming").is_dir()
