"""The agent account gets exactly what a run needs on its worktree — ticket-895."""
import getpass
import json
import sys
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers import droits_worktree
from tessera.services.providers.droits_worktree import DroitsAgentRefuses, accorder_droits_agent, retirer_ecriture
from tessera.services.worktrees.run_worktree import RunWorktree

COMPTE = "tessera-agent"


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
    assert appels[0] == [str(wt.racine), "/grant", f"{COMPTE}:(OI)(CI)M"]
    git = str(wt.racine / ".git")
    assert appels[1] == [str(wt.racine), "/grant", "*S-1-3-4:(OI)(CI)(RC)"]
    assert appels[2] == [str(wt.racine), "/grant", f"{getpass.getuser()}:(OI)(CI)F"]
    assert appels[3:6] == [
        [git, "/inheritance:d"],
        [git, "/remove:g", COMPTE],
        [git, "/grant:r", f"{COMPTE}:(OI)(CI)RX"],
    ]
    refuses = {Path(a[0]).name for a in appels[6:] if a[1:] == ["/deny", f"{COMPTE}:(WD,AD,WEA,WA,DE)"]}
    assert refuses == {"agents.json", "CLAUDE.md", "verif.py"}
    assert len(appels) == 6 + 3


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


class EchecSurDeny(Enregistreur):
    async def __call__(self, args: list[str]) -> tuple[int, str]:
        await super().__call__(args)
        return (5, "refusé") if "/deny" in args else (0, "")


async def test_closing_lays_the_denials_again_after_the_reset(
    wt: RunWorktree, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    await accorder_droits_agent(wt, "python scripts/verif.py", Enregistreur())
    icacls = Enregistreur()
    await retirer_ecriture(wt.racine, COMPTE, icacls)
    noms = [a[1] for a in icacls.appels]
    dernier_reset = max(i for i, n in enumerate(noms) if n == "/reset")
    refuses = {Path(a[0]).name for a in icacls.appels[dernier_reset:] if a[1] == "/deny"}
    assert refuses == {"agents.json", "CLAUDE.md", "verif.py"}
    assert all(a[2] == f"{COMPTE}:(WD,AD,WEA,WA,DE)" for a in icacls.appels if a[1] == "/deny")


async def test_a_failed_denial_at_closing_raises(
    wt: RunWorktree, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    await accorder_droits_agent(wt, "python scripts/verif.py", Enregistreur())
    with pytest.raises(DroitsAgentRefuses):
        await retirer_ecriture(wt.racine, COMPTE, EchecSurDeny())


@pytest.mark.skipif(sys.platform != "win32", reason="real ACLs need Windows")
async def test_a_protected_file_keeps_its_denial_after_a_real_closing(tmp_path: Path) -> None:
    guests = "*S-1-5-32-546"
    racine = tmp_path / "wt"
    (racine / "app").mkdir(parents=True)
    protege = racine / "app" / "agents.json"
    protege.write_text("{}", encoding="utf-8")
    droits_worktree._REFUSES[racine.resolve()] = [protege]
    await droits_worktree._refuser(protege, guests, droits_worktree._icacls_reel)
    await retirer_ecriture(racine, guests)
    code, sortie = await droits_worktree._icacls_reel([str(protege)])
    assert code == 0
    assert "(DENY)" in sortie
