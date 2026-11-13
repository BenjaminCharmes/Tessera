"""The agent account writes in a worktree only during a call — ticket-943."""
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers import droits_appel
from tessera.services.providers.droits_appel import clore_appel, ouvrir_appel, processus_du_compte
from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.verification.groupe_d_etape import GroupeDEtape
from tessera.services.verification.lancement_compte import ProcessusDuCompte

COMPTE = "tessera-agent"


class Icacls:
    def __init__(self, code: int = 0, echec_sur: str | None = None) -> None:
        self.appels: list[list[str]] = []
        self.code = code
        self.echec_sur = echec_sur

    async def __call__(self, args: list[str]) -> tuple[int, str]:
        self.appels.append(args)
        if self.echec_sur is not None and self.echec_sur in args:
            return 5, "refusé"
        return self.code, ""


class Processus:
    def __init__(self, restants: list[tuple[int, str]]) -> None:
        self.restants = restants
        self.tues: list[int] = []

    async def enumerer(self, compte: str) -> list[tuple[int, str]]:
        return self.restants

    async def tuer(self, pid: int) -> None:
        self.tues.append(pid)


@pytest.fixture(autouse=True)
def compte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    droits_appel._ACTIFS.clear()


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "backend").mkdir()
    return tmp_path


async def test_right_is_withdrawn_after_a_call_and_set_again_before_the_next(worktree: Path) -> None:
    icacls, procs = Icacls(), Processus([])
    racine = await ouvrir_appel(worktree / "backend", icacls)
    assert racine == worktree.resolve()
    assert [str(worktree.resolve()), "/grant", f"{COMPTE}:(OI)(CI)M"] in icacls.appels
    icacls.appels.clear()
    await clore_appel(racine, icacls, procs.enumerer, procs.tuer)
    assert icacls.appels == [
        [str(worktree.resolve() / ".git"), "/remove:g", COMPTE],
        [str(worktree.resolve()), "/remove:g", COMPTE],
    ]
    icacls.appels.clear()
    await ouvrir_appel(worktree, icacls)
    assert [str(worktree.resolve()), "/grant", f"{COMPTE}:(OI)(CI)M"] in icacls.appels


async def test_overlapping_calls_withdraw_the_right_once_at_the_last(worktree: Path) -> None:
    icacls, procs = Icacls(), Processus([])
    premier = await ouvrir_appel(worktree, icacls)
    second = await ouvrir_appel(worktree, icacls)
    icacls.appels.clear()
    await clore_appel(premier, icacls, procs.enumerer, procs.tuer)
    assert icacls.appels == []
    await clore_appel(second, icacls, procs.enumerer, procs.tuer)
    assert len(icacls.appels) == 2


async def test_a_failed_withdrawal_raises_so_the_run_is_blocked(worktree: Path) -> None:
    racine = await ouvrir_appel(worktree, Icacls())
    with pytest.raises(DroitsAgentRefuses):
        await clore_appel(racine, Icacls(code=5), Processus([]).enumerer, Processus([]).tuer)


async def test_leftover_processes_of_the_account_are_stopped_at_the_end(worktree: Path) -> None:
    icacls, procs = Icacls(), Processus([(11, "node.exe"), (12, "python.exe")])
    racine = await ouvrir_appel(worktree, icacls)
    await clore_appel(racine, icacls, procs.enumerer, procs.tuer)
    assert procs.tues == [11, 12]


async def test_a_failed_stop_still_withdraws_the_right_then_raises(worktree: Path) -> None:
    icacls = Icacls()

    async def tuer(pid: int) -> None:
        raise DroitsAgentRefuses("taskkill refusé")

    racine = await ouvrir_appel(worktree, icacls)
    icacls.appels.clear()
    with pytest.raises(DroitsAgentRefuses):
        await clore_appel(racine, icacls, Processus([(11, "node.exe")]).enumerer, tuer)
    assert len(icacls.appels) == 2


async def test_without_agent_user_nothing_is_set_or_removed(
    worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    icacls = Icacls()
    assert await ouvrir_appel(worktree, icacls) is None
    await clore_appel(worktree, icacls)
    assert icacls.appels == []


async def test_folder_outside_a_repository_gets_no_right(tmp_path: Path) -> None:
    icacls = Icacls()
    sans_depot = tmp_path / "x"
    sans_depot.mkdir()
    if droits_appel.racine_du_worktree(sans_depot) is None:
        assert await ouvrir_appel(sans_depot, icacls) is None
        assert icacls.appels == []


def test_tasklist_rows_are_filtered_on_the_account() -> None:
    csv_texte = (
        '"node.exe","101","Services","0","50 K","Unknown","PC\\tessera-agent","0:00:01","N/A"\n'
        '"code.exe","102","Console","1","50 K","Running","PC\\benjamin","0:00:01","N/A"\n'
        'INFO: ligne ignorée\n'
    )
    assert processus_du_compte(csv_texte, COMPTE) == [(101, "node.exe")]


async def test_step_group_ends_the_call_of_its_process() -> None:
    class Compte(ProcessusDuCompte):
        clos = 0

        async def clore(self) -> None:
            Compte.clos += 1

    groupe = GroupeDEtape()
    groupe.rattacher(1, Compte(None))  # type: ignore[arg-type]
    await groupe.fermer_et_clore()
    assert Compte.clos == 1
