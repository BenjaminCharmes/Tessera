"""The targeted take-back reprises only what the account owns — ticket-1027."""
import sys
from pathlib import Path

import pytest

from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.providers.reprise_ciblee import reprendre_arbre
from tessera.services.providers.securite_fichiers import SecuriteNulle, securite_par_defaut
from tests.faux_securite import BACKEND_SID, COMPTE_SID, FauxSecurite


@pytest.fixture
def arbre(tmp_path: Path) -> Path:
    racine = tmp_path / "wt"
    (racine / "src").mkdir(parents=True)
    (racine / ".git").mkdir()
    (racine / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    for nom in ("src/a.py", "src/b.py", "src/c.py"):
        (racine / nom).write_text("", encoding="utf-8")
    return racine


async def reprendre(racine: Path, faux: FauxSecurite) -> list[Path]:
    return await reprendre_arbre(racine, "compte", "backend", faux, {racine / ".git"})


async def test_account_and_protected_entries_are_taken_back_backend_ones_are_not(arbre: Path) -> None:
    faux = FauxSecurite()
    faux.poser(arbre / "src" / "a.py", COMPTE_SID)
    faux.poser(arbre / "src" / "b.py", BACKEND_SID, protegee=True)
    reprises = await reprendre(arbre, faux)
    assert sorted(p.name for p in reprises) == ["a.py", "b.py"]
    assert {p for p, _ in faux.reprises} == {arbre / "src" / "a.py", arbre / "src" / "b.py"}
    assert (arbre / "src" / "c.py") not in {p for p, _ in faux.reprises}
    assert faux.infos[arbre / "src" / "b.py"].dacl_protegee is False


async def test_the_root_git_is_never_read_nor_taken_back(arbre: Path) -> None:
    faux = FauxSecurite()
    faux.poser(arbre / ".git" / "HEAD", COMPTE_SID)
    await reprendre(arbre, faux)
    assert not any(".git" in p.parts for p in faux.lues)
    assert faux.reprises == []


async def test_a_vanished_entry_is_ignored(arbre: Path) -> None:
    faux = FauxSecurite()
    faux.disparues.add(arbre / "src" / "a.py")
    assert await reprendre(arbre, faux) == []


async def test_an_unreadable_entry_raises_naming_the_path_only(arbre: Path) -> None:
    faux = FauxSecurite()
    faux.illisibles.add(arbre / "src" / "b.py")
    with pytest.raises(DroitsAgentRefuses) as exc:
        await reprendre(arbre, faux)
    assert str(arbre / "src" / "b.py") in str(exc.value)


async def test_an_entry_still_owned_by_the_account_after_the_take_back_raises(arbre: Path) -> None:
    faux = FauxSecurite()
    faux.poser(arbre / "src" / "a.py", COMPTE_SID)
    faux.reprise_sans_effet.add(arbre / "src" / "a.py")
    with pytest.raises(DroitsAgentRefuses):
        await reprendre(arbre, faux)


async def test_an_entry_that_cannot_be_taken_back_raises(arbre: Path) -> None:
    class Refuse(FauxSecurite):
        def reprendre(self, chemin: Path, backend_sid: str, *, proprietaire_seul: bool) -> None:
            raise PermissionError(chemin)

    faux = Refuse()
    faux.poser(arbre / "src" / "a.py", COMPTE_SID)
    with pytest.raises(DroitsAgentRefuses):
        await reprendre(arbre, faux)


def _lien_vers(cible: Path, lien: Path) -> None:
    try:
        lien.symlink_to(cible, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not available here")


async def test_a_link_of_the_account_is_never_walked_and_only_changes_owner(arbre: Path, tmp_path: Path) -> None:
    cible = tmp_path / "cible"
    cible.mkdir()
    (cible / "secret.txt").write_text("", encoding="utf-8")
    lien = arbre / "lien"
    _lien_vers(cible, lien)
    faux = FauxSecurite()
    faux.poser(lien, COMPTE_SID)
    faux.poser(cible / "secret.txt", COMPTE_SID)
    await reprendre(arbre, faux)
    assert (lien, True) in faux.reprises
    assert not any(p.is_relative_to(cible) for p in faux.lues + [p for p, _ in faux.reprises])
    assert faux.infos[cible / "secret.txt"].proprietaire_sid == COMPTE_SID


async def test_a_link_with_a_protected_dacl_raises(arbre: Path, tmp_path: Path) -> None:
    cible = tmp_path / "cible"
    cible.mkdir()
    lien = arbre / "lien"
    _lien_vers(cible, lien)
    faux = FauxSecurite()
    faux.poser(lien, BACKEND_SID, protegee=True)
    with pytest.raises(DroitsAgentRefuses):
        await reprendre(arbre, faux)


def test_the_default_security_is_null_outside_windows() -> None:
    if sys.platform == "win32":
        pytest.skip("the real implementation is used on Windows")
    assert isinstance(securite_par_defaut(), SecuriteNulle)


@pytest.mark.skipif(sys.platform != "win32", reason="real ACLs need Windows")
async def test_real_security_reads_the_backend_as_owner_of_its_own_files(tmp_path: Path) -> None:
    import getpass

    securite = securite_par_defaut()
    fichier = tmp_path / "f.txt"
    fichier.write_text("x", encoding="utf-8")
    info = securite.lire(fichier)
    assert info.dacl_protegee is False
    moi = securite.sid_de(getpass.getuser())
    # Propriétaire : le compte, ou le groupe Administrateurs d'un jeton élevé.
    assert info.proprietaire_sid in (moi, "S-1-5-32-544")
    # Reprise réelle d'un fichier que l'on possède : handle, propriétaire, DACL à l'héritage.
    moi_nom = getpass.getuser()
    await reprendre_arbre(tmp_path, moi_nom, moi_nom, securite)
    apres = securite.lire(fichier)
    assert apres.dacl_protegee is False


@pytest.mark.skipif(sys.platform != "win32", reason="real ACLs need Windows")
async def test_real_security_reads_an_entry_beyond_260_characters(tmp_path: Path) -> None:
    import getpass

    from tessera.services.providers.securite_fichiers import chemin_long

    profond = tmp_path
    while len(str(profond)) < 300:
        profond = profond / ("d" * 40)
    Path(chemin_long(profond)).mkdir(parents=True)
    fichier = profond / "f.txt"
    Path(chemin_long(fichier)).write_text("x", encoding="utf-8")
    securite = securite_par_defaut()
    # Lue, et non prise pour une entrée disparue.
    assert securite.lire(fichier).dacl_protegee is False
    moi = getpass.getuser()
    assert fichier in await reprendre_arbre(tmp_path, moi, moi, securite)
