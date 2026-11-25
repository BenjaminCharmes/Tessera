"""A cancelled call never leaves the account's write right behind (ticket-1017)."""
import asyncio
from pathlib import Path

import pytest
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport

from tessera.config import settings
from tessera.services.providers import droits_appel, droits_worktree, profil_agent
from tessera.services.providers.droits_appel import clore_appel, ouvrir_appel
from tessera.services.providers.lanceur_agent import LanceurAgent
from tessera.services.providers.process_agent import ProcessAgent
from tessera.services.providers.transport_agent import TransportCompteAgent
from tests.faux_securite import FauxSecurite

COMPTE = "tessera-agent"


@pytest.fixture(autouse=True)
def cadre(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(settings, "agent_user", COMPTE)
    (tmp_path / "profil-vide").mkdir()
    monkeypatch.setattr(profil_agent, "DOSSIER_PROFIL", tmp_path / "profil-vide")
    monkeypatch.setattr(profil_agent, "_NETTOYAGE_ECHOUE", False)
    monkeypatch.setattr(droits_worktree, "securite_par_defaut", lambda: FauxSecurite())
    droits_appel._ACTIFS.clear()
    droits_appel._FILE.clear()
    monkeypatch.setattr(droits_appel, "_VERROU", asyncio.Condition())

    async def aucune_tache() -> None:
        return None

    monkeypatch.setattr(droits_appel, "retirer_les_taches", aucune_tache)
    dossier = tmp_path / "worktrees"
    monkeypatch.setattr(settings, "ide_worktrees_dir", dossier)
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", dossier)
    arbre = dossier / "projet" / "ticket-1"
    (arbre / ".git").mkdir(parents=True)
    return arbre


async def _aucun_processus(compte: str) -> list[tuple[int, str]]:
    return []


async def _ne_tue_rien(pid: int) -> None:
    return None


async def test_a_call_cancelled_during_the_close_still_withdraws_the_right(cadre: Path) -> None:
    attente, entre = asyncio.Event(), asyncio.Event()
    retraits: list[list[str]] = []

    async def icacls(args: list[str]) -> tuple[int, str]:
        if "/remove:g" in args:
            retraits.append(args)
        if "profil-vide" in args[0] or ("/remove:g" in args and args[0] == str(cadre.resolve())):
            entre.set()
            await attente.wait()
        return 0, ""

    racine = await ouvrir_appel(cadre, icacls)
    tache = asyncio.ensure_future(clore_appel(racine, icacls, _aucun_processus, _ne_tue_rien))
    await entre.wait()
    tache.cancel()
    attente.set()
    with pytest.raises(asyncio.CancelledError):
        await tache
    assert any(str(cadre.resolve()) == a[0] for a in retraits)
    assert racine not in droits_appel._ACTIFS


async def test_a_cancel_right_after_the_right_is_set_leaves_no_counter(
    cadre: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    emis: list[list[str]] = []

    async def icacls(args: list[str]) -> tuple[int, str]:
        emis.append(args)
        return 0, ""

    async def pose_puis_annulation(*_: object) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(droits_appel, "poser_ecriture", pose_puis_annulation)
    with pytest.raises(asyncio.CancelledError):
        await ouvrir_appel(cadre, icacls)
    assert droits_appel._ACTIFS == {}
    assert [str(cadre.resolve()), "/remove:g", COMPTE, "/L"] in emis


class _ProcessSuivi(ProcessAgent):
    def __init__(self) -> None:
        self.ferme = False

    async def aclose(self) -> None:
        self.ferme = True


async def test_the_process_is_closed_even_when_the_parent_close_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def echec(self: SubprocessCLITransport) -> None:
        raise RuntimeError("close failed")

    monkeypatch.setattr(SubprocessCLITransport, "close", echec)
    lanceur: LanceurAgent = object.__new__(LanceurAgent)
    transport = TransportCompteAgent(
        "p", ClaudeAgentOptions(), lanceur=lanceur, compte=COMPTE, mot_de_passe="x",
    )
    processus = _ProcessSuivi()
    transport._process = processus
    with pytest.raises(RuntimeError):
        await transport.close()
    assert processus.ferme
