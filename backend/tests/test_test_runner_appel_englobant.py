"""ticket-1022: one call spans all the steps of a test command under the agent account."""
import asyncio
from functools import partial
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from tessera.config import settings
from tessera.services.providers import droits_appel, droits_worktree, profil_agent
from tessera.services.verification import lancement_compte, test_runner
from tessera.services.verification.test_runner import TestRunnerService
from tests.chaine_factice import chaine_factice  # noqa: F401
from tests.doubles_compte import LanceurDouble, ProcessDouble
from tests.faux_securite import FauxSecurite
from tests.test_droits_appel import COMPTE, Icacls, Processus


@pytest.fixture
def icacls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, chaine: Path) -> Icacls:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    monkeypatch.setattr(settings, "agent_logon_password", SecretStr("pw"))
    (tmp_path / "profil-vide").mkdir()
    monkeypatch.setattr(profil_agent, "DOSSIER_PROFIL", tmp_path / "profil-vide")
    monkeypatch.setattr(profil_agent, "_NETTOYAGE_ECHOUE", False)
    # Les tâches planifiées du compte (ticket-1018) partent d'un vrai lanceur : hors sujet ici.
    async def aucune_tache() -> None:
        return None

    monkeypatch.setattr(droits_appel, "retirer_les_taches", aucune_tache)
    monkeypatch.setattr(droits_worktree, "securite_par_defaut", lambda: FauxSecurite())
    droits_appel._ACTIFS.clear()
    droits_appel._FILE.clear()
    monkeypatch.setattr(droits_appel, "_VERROU", asyncio.Condition())
    faux, procs = Icacls(), Processus([])
    ouvrir = partial(droits_appel.ouvrir_appel, icacls=faux)
    clore = partial(droits_appel.clore_appel, icacls=faux, enumerer=procs.enumerer, tuer=procs.tuer)
    for module in (test_runner, lancement_compte):
        monkeypatch.setattr(module, "ouvrir_appel", ouvrir)
        monkeypatch.setattr(module, "clore_appel", clore)
    return faux


@pytest.fixture
def worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dossier = tmp_path / "worktrees"
    monkeypatch.setattr(settings, "ide_worktrees_dir", dossier)
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", dossier)
    arbre = dossier / "projet" / "ticket-1"
    (arbre / ".git").mkdir(parents=True)
    (arbre / "backend").mkdir()
    return arbre


class IcaclsDate(Icacls):
    """Notes how many steps had started when each call came in."""

    def __init__(self, lanceur: LanceurDouble) -> None:
        super().__init__()
        self.lanceur = lanceur
        self.etapes_lancees: list[int] = []

    async def __call__(self, args: list[str]) -> tuple[int, str]:
        self.etapes_lancees.append(len(self.lanceur.appels))
        return await super().__call__(args)


async def test_the_grant_is_withdrawn_once_after_the_last_step(
    icacls: Icacls, worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lanceur = LanceurDouble(ProcessDouble(b"ok", b"", code=0))
    datee = IcaclsDate(lanceur)
    procs = Processus([])
    monkeypatch.setattr(
        test_runner, "ouvrir_appel", partial(droits_appel.ouvrir_appel, icacls=datee))
    clore = partial(droits_appel.clore_appel, icacls=datee, enumerer=procs.enumerer, tuer=procs.tuer)
    for module in (test_runner, lancement_compte):
        monkeypatch.setattr(module, "clore_appel", clore)
    monkeypatch.setattr(lancement_compte, "ouvrir_appel", partial(droits_appel.ouvrir_appel, icacls=datee))
    runner = TestRunnerService(compte_agent=True, lanceur=lanceur)
    result = await runner.run_tests(worktree / "backend", test_command="node a.js && node b.js && node c.js")
    assert [e.code for e in result.etapes] == [0, 0, 0]
    apres = [
        n for n, a in zip(datee.etapes_lancees, datee.appels, strict=True) if "/remove:g" in a and a[0] == str(worktree.resolve()) and n == 3
    ]
    assert len(apres) == 1
    assert sum("/remove:g" in a and a[0] == str(worktree.resolve()) for a in datee.appels) == 1
    assert droits_appel._ACTIFS == {}


async def test_a_raising_step_still_closes_the_enclosing_call(
    icacls: Icacls, worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = TestRunnerService(compte_agent=True, lanceur=LanceurDouble())
    monkeypatch.setattr(runner, "_executer", AsyncMock(side_effect=RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        await runner.run_tests(worktree / "backend", test_command="node a.js && node b.js")
    assert droits_appel._ACTIFS == {}


async def test_without_the_account_no_call_is_opened(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    ouvrir = AsyncMock(return_value=None)
    monkeypatch.setattr(test_runner, "ouvrir_appel", ouvrir)
    proc = AsyncMock()
    proc.returncode = 0
    proc.pid = 1
    proc.communicate = AsyncMock(return_value=(b"1 passed", b""))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=proc))
    await TestRunnerService(compte_agent=True).run_tests(tmp_path, test_command="pytest")
    ouvrir.assert_not_called()
