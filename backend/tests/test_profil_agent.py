"""ticket-1008: the agent profile is wiped between calls, except the two caches."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.services.providers import profil_agent
from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.providers.profil_agent import nettoyage_en_echec, reinitialiser_profil
from tessera.services.providers.securite_fichiers import InfoSecurite


class Icacls:
    def __init__(self) -> None:
        self.appels: list[list[str]] = []

    async def __call__(self, args: list[str]) -> tuple[int, str]:
        self.appels.append(args)
        return 0, ""


class FauxSecurite:
    """Owner and protection per path; the account is `compte`, the backend is `backend`."""

    def __init__(self, infos: dict[Path, InfoSecurite] | None = None) -> None:
        self.infos = infos or {}
        self.lus: list[Path] = []
        self.reprises: list[Path] = []

    def sid_de(self, compte: str) -> str:
        return compte

    def lire(self, chemin: Path) -> InfoSecurite:
        self.lus.append(chemin)
        return self.infos.get(chemin, InfoSecurite("backend", False))

    def reprendre(self, chemin: Path, backend_sid: str, *, proprietaire_seul: bool) -> None:
        self.reprises.append(chemin)
        self.infos[chemin] = InfoSecurite(backend_sid, False)


def _ATTENDU(profil: Path) -> list[list[str]]:
    p = str(profil)
    return [
        [p, "/grant", "backend:(OI)(CI)F", "/L"],
        [p, "/grant", "tessera-agent:(OI)(CI)(IO)M", "/L"],
        [p, "/grant", "tessera-agent:(RX,WD,AD)", "/L"],
        [p, "/grant", "*S-1-3-4:(OI)(CI)(RC)", "/L"],
    ]


@pytest.fixture(autouse=True)
def _remise_a_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(profil_agent, "_NETTOYAGE_ECHOUE", False)
    monkeypatch.setattr(profil_agent, "compte_du_backend", lambda: "backend")


@pytest.fixture
def profil(tmp_path: Path) -> Path:
    dossier = tmp_path / "profil-agent"
    (dossier / "npm-cache" / "_cacache").mkdir(parents=True)
    (dossier / "npm-cache" / "_cacache" / "index").write_text("i")
    (dossier / "uv" / "cache").mkdir(parents=True)
    (dossier / "uv" / "cache" / "wheel").write_text("w")
    return dossier


async def test_user_files_are_removed_and_only_the_npm_cache_is_kept(profil: Path) -> None:
    (profil / ".bashrc").write_text("evil")
    (profil / ".npmrc").write_text("evil")
    (profil / "AppData" / "Roaming" / "uv").mkdir(parents=True)
    (profil / "AppData" / "Roaming" / "uv" / "uv.toml").write_text("evil")
    (profil / "uv" / "uv.toml").write_text("evil")
    icacls = Icacls()
    securite = FauxSecurite({profil: InfoSecurite("tessera-agent", False)})
    await reinitialiser_profil("tessera-agent", icacls, profil, securite=securite)
    assert sorted(p.name for p in profil.iterdir()) == ["AppData", "npm-cache"]
    assert (profil / "npm-cache" / "_cacache" / "index").read_text() == "i"
    assert not (profil / "uv").exists()
    assert icacls.appels == _ATTENDU(profil)


async def test_read_only_file_is_removed(profil: Path) -> None:
    fichier = profil / ".gitconfig"
    fichier.write_text("x")
    os.chmod(fichier, 0o400)
    await reinitialiser_profil("tessera-agent", Icacls(), profil, securite=FauxSecurite())
    assert not fichier.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="junction")
async def test_a_junction_is_removed_without_following_it(profil: Path, tmp_path: Path) -> None:
    cible = tmp_path / "cible"
    cible.mkdir()
    (cible / "precieux.txt").write_text("x")
    lien = profil / "lien"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(lien), str(cible)], check=True, capture_output=True)
    await reinitialiser_profil("tessera-agent", Icacls(), profil, securite=FauxSecurite())
    assert not lien.exists()
    assert (cible / "precieux.txt").exists()


async def test_a_failed_removal_raises_droits_refuses(profil: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (profil / "x.txt").write_text("x")

    def refuse(chemin: str) -> None:
        raise PermissionError("refusé")

    monkeypatch.setattr(os, "unlink", refuse)
    with pytest.raises(DroitsAgentRefuses):
        await reinitialiser_profil("tessera-agent", Icacls(), profil, securite=FauxSecurite())


async def test_the_account_is_dispossessed_before_the_purge(profil: Path) -> None:
    """The trap owned by the account is taken back before the first deletion."""
    piege = profil / "piege.txt"
    piege.write_text("x")
    vu: list[bool] = []

    class Espion(FauxSecurite):
        def reprendre(self, chemin: Path, backend_sid: str, *, proprietaire_seul: bool) -> None:
            vu.append(piege.exists())
            super().reprendre(chemin, backend_sid, proprietaire_seul=proprietaire_seul)

    securite = Espion({piege: InfoSecurite("tessera-agent", False)})
    await reinitialiser_profil("tessera-agent", Icacls(), profil, securite=securite)
    assert vu == [True]
    assert securite.reprises == [piege]
    assert not piege.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="junction")
async def test_an_entry_of_the_backend_is_not_taken_back_and_a_link_is_not_walked(
    profil: Path, tmp_path: Path,
) -> None:
    cible = tmp_path / "cible"
    cible.mkdir()
    (cible / "dedans").write_text("x")
    lien = profil / "lien"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(lien), str(cible)], check=True, capture_output=True)
    (profil / "propre.txt").write_text("x")
    securite = FauxSecurite()
    await reinitialiser_profil("tessera-agent", Icacls(), profil, securite=securite)
    assert lien in securite.lus
    assert not [c for c in securite.lus if lien in c.parents]
    assert securite.reprises == []
    assert (cible / "dedans").exists()


async def test_an_unreadable_entry_raises_and_lifts_the_flag(profil: Path) -> None:
    class Illisible(FauxSecurite):
        def lire(self, chemin: Path) -> InfoSecurite:
            if chemin.name == ".bashrc":
                raise PermissionError("refusé")
            return super().lire(chemin)

    (profil / ".bashrc").write_text("x")
    with pytest.raises(DroitsAgentRefuses, match="bashrc"):
        await reinitialiser_profil("tessera-agent", Icacls(), profil, securite=Illisible())
    assert nettoyage_en_echec()


async def test_without_taking_the_root_back_no_icacls_runs(profil: Path) -> None:
    icacls = Icacls()
    await reinitialiser_profil("tessera-agent", icacls, profil, securite=FauxSecurite())
    assert icacls.appels == []


async def test_an_absent_profile_raises_droits_refuses(tmp_path: Path) -> None:
    icacls = Icacls()
    with pytest.raises(DroitsAgentRefuses):
        await reinitialiser_profil("tessera-agent", icacls, tmp_path / "absent", securite=FauxSecurite())
    assert icacls.appels == []
    assert nettoyage_en_echec()


async def test_a_successful_wipe_clears_the_failure_flag(profil: Path, tmp_path: Path) -> None:
    with pytest.raises(DroitsAgentRefuses):
        await reinitialiser_profil("tessera-agent", Icacls(), tmp_path / "absent", securite=FauxSecurite())
    await reinitialiser_profil("tessera-agent", Icacls(), profil, securite=FauxSecurite())
    assert not nettoyage_en_echec()


async def test_a_failing_icacls_raises_the_flag(profil: Path) -> None:
    class Refus(Icacls):
        async def __call__(self, args: list[str]) -> tuple[int, str]:
            return 5, "refusé"

    with pytest.raises(DroitsAgentRefuses):
        await reinitialiser_profil("tessera-agent", Refus(), profil, securite=FauxSecurite({profil: InfoSecurite("tessera-agent", False)}))
    assert nettoyage_en_echec()


@pytest.mark.skipif(sys.platform != "win32", reason="extended-length paths")
async def test_a_reserved_name_and_a_very_long_path_are_removed(profil: Path) -> None:
    sep = os.sep
    prefixe = sep * 2 + "?" + sep + str(profil.resolve())
    os.makedirs(prefixe + sep + sep.join(["d" * 50] * 7))
    reserve = prefixe + sep + "x."
    with open(reserve, "w") as f:
        f.write("x")
    await reinitialiser_profil("tessera-agent", Icacls(), profil, securite=FauxSecurite())
    assert not os.path.exists(reserve)
    assert not os.path.exists(prefixe + sep + "d" * 50)


async def test_temp_and_appdata_folders_exist_after_the_reset(profil: Path) -> None:
    (profil / "AppData" / "Local" / "Temp").mkdir(parents=True)
    (profil / "AppData" / "Local" / "Temp" / "junk").write_text("x")
    await reinitialiser_profil("tessera-agent", Icacls(), profil, securite=FauxSecurite())
    assert (profil / "AppData" / "Local" / "Temp").is_dir()
    assert not (profil / "AppData" / "Local" / "Temp" / "junk").exists()
    assert (profil / "AppData" / "Roaming").is_dir()


def test_the_recreated_folders_are_the_ones_the_environment_points_to(tmp_path: Path) -> None:
    """Windows paths are split with ntpath, so the same folders come back under Linux too."""
    from tessera.services.providers.profil_agent import _recreer

    _recreer(tmp_path)
    assert (tmp_path / "AppData" / "Local" / "Temp").is_dir()
    assert (tmp_path / "AppData" / "Roaming").is_dir()
