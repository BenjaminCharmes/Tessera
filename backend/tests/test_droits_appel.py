"""The agent account writes in a worktree only during a call — ticket-943."""
import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers import droits_appel, droits_worktree, profil_agent
from tessera.services.providers.droits_appel import clore_appel, ouvrir_appel
from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.verification.groupe_d_etape import GroupeDEtape
from tessera.services.verification.lancement_compte import ProcessusDuCompte
from tests.faux_securite import FauxSecurite

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
def compte(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    # Jamais le vrai profil de l'agent (ticket-1008) ; un profil absent refuse (ticket-1014).
    (tmp_path / "profil-vide").mkdir()
    monkeypatch.setattr(profil_agent, "DOSSIER_PROFIL", tmp_path / "profil-vide")
    monkeypatch.setattr(profil_agent, "_NETTOYAGE_ECHOUE", False)
    monkeypatch.setattr(droits_worktree, "securite_par_defaut", lambda: FauxSecurite())
    droits_appel._ACTIFS.clear()
    droits_appel._FILE.clear()
    # Une condition se lie à la boucle de son premier `wait` : une neuve par test.
    monkeypatch.setattr(droits_appel, "_VERROU", asyncio.Condition())

    async def aucune_tache() -> None:
        return None

    monkeypatch.setattr(droits_appel, "retirer_les_taches", aucune_tache)


@pytest.fixture
def worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dossier = tmp_path / "worktrees"
    monkeypatch.setattr(settings, "ide_worktrees_dir", dossier)
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", dossier)
    arbre = dossier / "projet" / "ticket-1"
    (arbre / ".git").mkdir(parents=True)
    (arbre / "backend").mkdir()
    return arbre


async def test_a_checkout_outside_the_worktrees_folder_is_refused_without_icacls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_worktrees_dir", tmp_path / "worktrees")
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", tmp_path / "worktrees")
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    icacls = Icacls()
    with pytest.raises(DroitsAgentRefuses):
        await ouvrir_appel(checkout, icacls)
    assert icacls.appels == []
    assert droits_appel._ACTIFS == {}


async def test_right_is_withdrawn_after_a_call_and_set_again_before_the_next(worktree: Path) -> None:
    icacls, procs = Icacls(), Processus([])
    racine = await ouvrir_appel(worktree / "backend", icacls)
    assert racine == worktree.resolve()
    assert [str(worktree.resolve()), "/grant", f"{COMPTE}:(OI)(CI)M", "/L"] in icacls.appels
    icacls.appels.clear()
    await clore_appel(racine, icacls, procs.enumerer, procs.tuer)
    racine_s = str(worktree.resolve())
    # Les appels du profil (ticket-1014) sont testés dans test_profil_agent.
    assert [a for a in icacls.appels if "profil-vide" not in a[0]] == [[racine_s, "/remove:g", COMPTE, "/L"]]
    icacls.appels.clear()
    await ouvrir_appel(worktree, icacls)
    assert [str(worktree.resolve()), "/grant", f"{COMPTE}:(OI)(CI)M", "/L"] in icacls.appels


async def test_overlapping_calls_withdraw_the_right_once_at_the_last(worktree: Path) -> None:
    icacls, procs = Icacls(), Processus([])
    premier = await ouvrir_appel(worktree, icacls)
    second = await ouvrir_appel(worktree, icacls)
    icacls.appels.clear()
    await clore_appel(premier, icacls, procs.enumerer, procs.tuer)
    assert icacls.appels == []
    await clore_appel(second, icacls, procs.enumerer, procs.tuer)
    sur_racine = [a for a in icacls.appels if "profil-vide" not in a[0]]
    assert sum(1 for a in sur_racine if "/remove:g" in a) == 1
    assert not any("/setowner" in a or "/reset" in a for a in sur_racine)


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
    assert [str(worktree.resolve()), "/remove:g", COMPTE, "/L"] in icacls.appels


async def test_without_agent_user_nothing_is_set_or_removed(
    worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    icacls = Icacls()
    assert await ouvrir_appel(worktree, icacls) is None
    await clore_appel(worktree, icacls)
    assert icacls.appels == []


async def test_folder_outside_the_worktrees_gets_no_right(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ide_worktrees_dir", tmp_path / "worktrees")
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", tmp_path / "worktrees")
    sans_depot = tmp_path / "x"
    sans_depot.mkdir()
    icacls = Icacls()
    with pytest.raises(DroitsAgentRefuses):
        await ouvrir_appel(sans_depot, icacls)
    assert icacls.appels == []


def test_root_is_the_run_worktree_even_with_a_git_in_a_subfolder(worktree: Path) -> None:
    sous = worktree / "sous"
    (sous / ".git").mkdir(parents=True)
    assert droits_appel.racine_du_worktree(sous) == worktree.resolve()
    assert droits_appel.racine_du_worktree(worktree) == worktree.resolve()


def test_a_project_folder_alone_is_not_a_root(worktree: Path) -> None:
    assert droits_appel.racine_du_worktree(worktree.parent) is None


@pytest.mark.skipif(sys.platform != "win32", reason="junctions are a Windows feature")
async def test_a_junction_git_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dossier = tmp_path / "worktrees"
    monkeypatch.setattr(settings, "ide_worktrees_dir", dossier)
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", dossier)
    arbre = dossier / "projet" / "ticket-1"
    arbre.mkdir(parents=True)
    cible = tmp_path / "cible"
    cible.mkdir()
    subprocess.run(["cmd", "/c", "mklink", "/J", str(arbre / ".git"), str(cible)], check=True, capture_output=True)
    icacls = Icacls()
    with pytest.raises(DroitsAgentRefuses):
        await ouvrir_appel(arbre, icacls)
    assert icacls.appels == []


async def test_every_icacls_call_carries_l(worktree: Path) -> None:
    icacls = Icacls()
    racine = await ouvrir_appel(worktree, icacls)
    await clore_appel(racine, icacls, Processus([]).enumerer, Processus([]).tuer)
    assert icacls.appels
    assert all("/L" in a for a in icacls.appels)


async def test_step_group_ends_the_call_of_its_process() -> None:
    class Compte(ProcessusDuCompte):
        clos = 0

        async def clore(self) -> None:
            Compte.clos += 1

    groupe = GroupeDEtape()
    groupe.rattacher(1, Compte(None))  # type: ignore[arg-type]
    await groupe.fermer_et_clore()
    assert Compte.clos == 1


@pytest.fixture
def deux_worktrees(worktree: Path) -> tuple[Path, Path]:
    autre = worktree.parent / "ticket-2"
    (autre / ".git").mkdir(parents=True)
    return worktree, autre


async def _laisser_tourner() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_a_call_on_another_root_waits_for_the_first_to_close(deux_worktrees: tuple[Path, Path]) -> None:
    premier, second = deux_worktrees
    icacls, processus = Icacls(), Processus([])
    racine = await ouvrir_appel(premier, icacls)
    tache = asyncio.create_task(ouvrir_appel(second, icacls))
    await _laisser_tourner()
    assert not tache.done()
    await clore_appel(racine, icacls, processus.enumerer, processus.tuer)
    assert await asyncio.wait_for(tache, 1) == second.resolve()


async def test_a_call_on_the_same_root_passes(worktree: Path) -> None:
    icacls = Icacls()
    await ouvrir_appel(worktree, icacls)
    await asyncio.wait_for(ouvrir_appel(worktree, icacls), 1)
    assert droits_appel._ACTIFS[worktree.resolve()] == 2


async def test_parallel_setting_lets_both_roots_through(
    deux_worktrees: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_calls_parallel", True)
    icacls = Icacls()
    await ouvrir_appel(deux_worktrees[0], icacls)
    await asyncio.wait_for(ouvrir_appel(deux_worktrees[1], icacls), 1)
    assert len(droits_appel._ACTIFS) == 2


async def test_cancel_while_waiting_leaves_no_counter(deux_worktrees: tuple[Path, Path]) -> None:
    icacls = Icacls()
    await ouvrir_appel(deux_worktrees[0], icacls)
    tache = asyncio.create_task(ouvrir_appel(deux_worktrees[1], icacls))
    await _laisser_tourner()
    tache.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tache
    assert list(droits_appel._ACTIFS) == [deux_worktrees[0].resolve()]
    assert not droits_appel._FILE


async def test_waiters_are_served_in_arrival_order(deux_worktrees: tuple[Path, Path]) -> None:
    premier, second = deux_worktrees
    troisieme = premier.parent / "ticket-3"
    (troisieme / ".git").mkdir(parents=True)
    icacls, processus = Icacls(), Processus([])
    racine = await ouvrir_appel(premier, icacls)
    t2 = asyncio.create_task(ouvrir_appel(second, icacls))
    await _laisser_tourner()
    t3 = asyncio.create_task(ouvrir_appel(troisieme, icacls))
    await _laisser_tourner()
    await clore_appel(racine, icacls, processus.enumerer, processus.tuer)
    await _laisser_tourner()
    assert t2.done() and not t3.done()
    await clore_appel(await t2, icacls, processus.enumerer, processus.tuer)
    assert await asyncio.wait_for(t3, 1) == troisieme.resolve()


async def test_without_agent_user_there_is_no_wait(
    deux_worktrees: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    assert await asyncio.wait_for(ouvrir_appel(deux_worktrees[0]), 1) is None
    assert await asyncio.wait_for(ouvrir_appel(deux_worktrees[1]), 1) is None


async def test_profile_is_reset_at_the_last_call_only(worktree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profil = tmp_path / "profil"
    profil.mkdir()
    (profil / ".bashrc").write_text("x")
    monkeypatch.setattr(profil_agent, "DOSSIER_PROFIL", profil)
    icacls, procs = Icacls(), Processus([])
    premier = await ouvrir_appel(worktree, icacls)
    second = await ouvrir_appel(worktree, icacls)
    await clore_appel(premier, icacls, procs.enumerer, procs.tuer)
    assert (profil / ".bashrc").exists()
    await clore_appel(second, icacls, procs.enumerer, procs.tuer)
    assert not (profil / ".bashrc").exists()
    assert [str(profil), "/grant", f"{COMPTE}:(OI)(CI)(IO)M", "/L"] in icacls.appels


async def test_profile_is_not_reset_while_another_worktree_is_active(
    worktree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profil = tmp_path / "profil"
    profil.mkdir()
    (profil / ".npmrc").write_text("x")
    monkeypatch.setattr(profil_agent, "DOSSIER_PROFIL", profil)
    monkeypatch.setattr(settings, "agent_calls_parallel", True)
    autre = worktree.parent / "ticket-2"
    (autre / ".git").mkdir(parents=True)
    icacls, procs = Icacls(), Processus([])
    a = await ouvrir_appel(worktree, icacls)
    b = await ouvrir_appel(autre, icacls)
    await clore_appel(a, icacls, procs.enumerer, procs.tuer)
    assert (profil / ".npmrc").exists()
    await clore_appel(b, icacls, procs.enumerer, procs.tuer)
    assert not (profil / ".npmrc").exists()


async def test_profile_is_untouched_without_agent_user(worktree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profil = tmp_path / "profil"
    profil.mkdir()
    (profil / ".bashrc").write_text("x")
    monkeypatch.setattr(profil_agent, "DOSSIER_PROFIL", profil)
    monkeypatch.setattr(settings, "agent_user", "")
    racine = await ouvrir_appel(worktree, Icacls())
    await clore_appel(racine, Icacls())
    assert (profil / ".bashrc").exists()


async def test_a_failed_wipe_refuses_the_next_call_until_one_succeeds(
    worktree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profil = tmp_path / "profil-vide"
    icacls, procs = Icacls(), Processus([])
    racine = await ouvrir_appel(worktree, icacls)
    profil.rmdir()
    with pytest.raises(DroitsAgentRefuses):
        await clore_appel(racine, icacls, procs.enumerer, procs.tuer)
    with pytest.raises(DroitsAgentRefuses):
        await ouvrir_appel(worktree, icacls)
    # Le dossier revenu, l'ouverture suivante retente le nettoyage elle-même : pas de redémarrage.
    profil.mkdir()
    (profil / ".bashrc").write_text("x")
    assert await ouvrir_appel(worktree, icacls) is not None
    assert not (profil / ".bashrc").exists()
