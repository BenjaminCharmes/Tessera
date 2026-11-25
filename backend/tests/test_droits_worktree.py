"""The agent account gets exactly what a run needs on its worktree — ticket-895, ticket-1027."""
import getpass
import json
import sys
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers import droits_worktree
from tessera.services.providers.droits_worktree import DroitsAgentRefuses, accorder_droits_agent, poser_base, poser_ecriture, retirer_ecriture
from tessera.services.worktrees.run_worktree import RunWorktree
from tests.faux_securite import COMPTE_SID, FauxSecurite

COMPTE = "tessera-agent"


@pytest.fixture
def faux() -> FauxSecurite:
    return FauxSecurite()


@pytest.fixture
def wt(tmp_path: Path) -> RunWorktree:
    racine = tmp_path / "wt"
    projet = racine / "app"
    (racine / ".git").mkdir(parents=True)
    (projet / "scripts").mkdir(parents=True)
    (projet / "src").mkdir()
    (projet / "agents.json").write_text(
        json.dumps({"pipeline": {"test_command": "python scripts/verif.py"}}), encoding="utf-8"
    )
    (projet / "CLAUDE.md").write_text("# App\n", encoding="utf-8")
    (projet / "scripts" / "verif.py").write_text("", encoding="utf-8")
    (projet / "src" / "a.py").write_text("", encoding="utf-8")
    return RunWorktree(racine=racine, projet=projet, branche="ticket-1-x")


class Enregistreur:
    def __init__(self, code: int = 0) -> None:
        self.appels: list[list[str]] = []
        self.code = code

    async def __call__(self, args: list[str]) -> tuple[int, str]:
        self.appels.append(args)
        return self.code, "refusé"


async def test_empty_agent_user_never_calls_icacls(
    wt: RunWorktree, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    icacls = Enregistreur()
    await accorder_droits_agent(wt, "python scripts/verif.py", icacls)
    assert icacls.appels == []


async def test_rights_are_set_in_order(wt: RunWorktree, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    icacls = Enregistreur()
    await accorder_droits_agent(wt, "python scripts/verif.py", icacls)
    appels = icacls.appels
    dossier_git = str(wt.racine / ".git")
    # Le backend d'abord : propriétaire de la racine, il perdrait WRITE_DAC dès l'ACE OWNER RIGHTS.
    assert appels[0] == [str(wt.racine), "/grant", f"{getpass.getuser()}:(OI)(CI)F", "/L"]
    assert appels[1] == [str(wt.racine), "/grant", "*S-1-3-4:(OI)(CI)(RC)", "/L"]
    assert appels[2:5] == [
        [dossier_git, "/inheritance:d", "/L"],
        [dossier_git, "/remove:g", COMPTE, "/L"],
        [dossier_git, "/grant:r", f"{COMPTE}:(OI)(CI)RX", "/L"],
    ]
    assert appels[5] == [str(wt.racine), "/grant", f"{COMPTE}:(OI)(CI)M", "/L"]
    refuses = {Path(a[0]).name for a in appels[6:] if a[1:3] == ["/deny", f"{COMPTE}:(WD,AD,WEA,WA,DE)"]}
    assert refuses == {"agents.json", "CLAUDE.md", "verif.py"}
    assert all("/L" in a for a in appels)
    assert len(appels) == 6 + 3


async def test_write_grant_is_a_single_icacls_call(wt: RunWorktree) -> None:
    icacls = Enregistreur()
    await poser_ecriture(wt.racine, COMPTE, icacls)
    assert icacls.appels == [[str(wt.racine), "/grant", f"{COMPTE}:(OI)(CI)M", "/L"]]


async def test_base_is_set_once_per_root_and_again_for_a_recreated_worktree(wt: RunWorktree) -> None:
    icacls = Enregistreur()
    await poser_base(wt.racine, COMPTE, icacls)
    n = len(icacls.appels)
    assert n == 5
    await poser_base(wt.racine, COMPTE, icacls)
    assert len(icacls.appels) == n
    # Même chemin, autre création : la clé mémorisée n'est plus la bonne.
    chemin, ctime = droits_worktree._cle_base(wt.racine)
    droits_worktree._BASES.discard((chemin, ctime))
    droits_worktree._BASES.add((chemin, ctime - 1))
    await poser_base(wt.racine, COMPTE, icacls)
    assert len(icacls.appels) == 2 * n


async def test_base_gives_the_account_no_modify_right(wt: RunWorktree) -> None:
    icacls = Enregistreur()
    await poser_base(wt.racine, COMPTE, icacls)
    for appel in icacls.appels:
        assert not any(arg.startswith(f"{COMPTE}:") and "M" in arg.split(":")[1] for arg in appel)


async def test_agent_account_never_gets_full_control(wt: RunWorktree, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    icacls = Enregistreur()
    await accorder_droits_agent(wt, "python scripts/verif.py", icacls)
    for appel in icacls.appels:
        assert not any(arg.startswith(f"{COMPTE}:") and arg.endswith("F") for arg in appel)


async def test_icacls_failure_raises(wt: RunWorktree, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    with pytest.raises(DroitsAgentRefuses):
        await accorder_droits_agent(wt, None, Enregistreur(code=5))


async def test_protected_files_stay_readable(wt: RunWorktree, monkeypatch: pytest.MonkeyPatch) -> None:
    # ticket-994 : les droits simples W et D d'icacls portent SYNCHRONIZE ; les
    # refuser interdit toute ouverture du fichier, lecture comprise (un test de
    # Serpent lisait .github/workflows/ci.yml et recevait EPERM).
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    icacls = Enregistreur()
    await accorder_droits_agent(wt, "python scripts/verif.py", icacls)
    refus = [a[2] for a in icacls.appels if a[1:2] == ["/deny"]]
    assert refus
    for droit in refus:
        drapeaux = droit.split(":", 1)[1].strip("()").split(",")
        assert "W" not in drapeaux and "D" not in drapeaux and "F" not in drapeaux and "M" not in drapeaux
        assert {"WD", "AD", "DE"} <= set(drapeaux)


async def test_closing_removes_the_grant_without_setowner_nor_reset(wt: RunWorktree, faux: FauxSecurite) -> None:
    icacls = Enregistreur()
    await retirer_ecriture(wt.racine, COMPTE, icacls, "backend", faux)
    assert icacls.appels == [[str(wt.racine), "/remove:g", COMPTE, "/L"]]


async def test_the_grant_is_removed_first_and_stays_so_when_the_take_back_fails(
    wt: RunWorktree, faux: FauxSecurite
) -> None:
    sale = wt.racine / "app" / "src" / "a.py"
    faux.poser(sale, COMPTE_SID)
    faux.reprise_sans_effet.add(sale)
    icacls = Enregistreur()
    with pytest.raises(DroitsAgentRefuses):
        await retirer_ecriture(wt.racine, COMPTE, icacls, "backend", faux)
    assert icacls.appels == [[str(wt.racine), "/remove:g", COMPTE, "/L"]]


async def test_a_taken_back_protected_file_gets_its_denial_again(
    wt: RunWorktree, monkeypatch: pytest.MonkeyPatch, faux: FauxSecurite
) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    await accorder_droits_agent(wt, "python scripts/verif.py", Enregistreur())
    repris = wt.projet / "CLAUDE.md"
    faux.poser(repris, COMPTE_SID)
    icacls = Enregistreur()
    await retirer_ecriture(wt.racine, COMPTE, icacls, "backend", faux)
    refus = [a for a in icacls.appels if a[1] == "/deny"]
    assert [Path(a[0]) for a in refus] == [repris]
    assert refus[0][2] == f"{COMPTE}:(WD,AD,WEA,WA,DE)"


async def test_a_failed_denial_after_a_take_back_raises(
    wt: RunWorktree, monkeypatch: pytest.MonkeyPatch, faux: FauxSecurite
) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    await accorder_droits_agent(wt, "python scripts/verif.py", Enregistreur())
    faux.poser(wt.projet / "CLAUDE.md", COMPTE_SID)

    async def echec_sur_deny(args: list[str]) -> tuple[int, str]:
        return (5, "refusé") if "/deny" in args else (0, "")

    with pytest.raises(DroitsAgentRefuses):
        await retirer_ecriture(wt.racine, COMPTE, echec_sur_deny, "backend", faux)


@pytest.mark.skipif(sys.platform != "win32", reason="real ACLs need Windows")
async def test_a_protected_file_keeps_its_denial_after_a_real_closing(tmp_path: Path) -> None:
    guests = "*S-1-5-32-546"
    racine = tmp_path / "wt"
    (racine / "app").mkdir(parents=True)
    protege = racine / "app" / "agents.json"
    protege.write_text("{}", encoding="utf-8")
    droits_worktree._REFUSES[racine.resolve()] = [protege]
    await droits_worktree._refuser(protege, guests, droits_worktree._icacls_reel)
    await retirer_ecriture(racine, guests, droits_worktree._icacls_reel, "backend", FauxSecurite())
    code, sortie = await droits_worktree._icacls_reel([str(protege)])
    assert code == 0
    assert "(DENY)" in sortie
