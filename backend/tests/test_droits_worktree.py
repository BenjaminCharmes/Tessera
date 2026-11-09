"""The agent account gets exactly what a run needs on its worktree — ticket-895."""
import json
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers.droits_worktree import DroitsAgentRefuses, accorder_droits_agent
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
    assert appels[1:4] == [
        [git, "/inheritance:d"],
        [git, "/remove:g", COMPTE],
        [git, "/grant:r", f"{COMPTE}:(OI)(CI)RX"],
    ]
    refuses = {Path(a[0]).name for a in appels[4:] if a[1:] == ["/deny", f"{COMPTE}:(W,D)"]}
    assert refuses == {"agents.json", "CLAUDE.md", "verif.py"}
    assert len(appels) == 4 + 3


async def test_no_call_grants_full_control(wt: RunWorktree, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    icacls = Enregistreur()
    await accorder_droits_agent(wt, "python scripts/verif.py", icacls)
    for appel in icacls.appels:
        assert all(not arg.endswith(":F") and "(F)" not in arg for arg in appel)


async def test_icacls_failure_raises(wt: RunWorktree, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    with pytest.raises(DroitsAgentRefuses):
        await accorder_droits_agent(wt, None, Enregistreur(code=5))
