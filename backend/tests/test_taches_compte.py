"""Scheduled tasks of the agent account are removed at the last call's end — ticket-1018."""
import asyncio
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers import droits_appel, profil_agent, taches_compte
from tessera.services.providers.droits_appel import clore_appel, ouvrir_appel
from tessera.services.providers.droits_worktree import DroitsAgentRefuses
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.taches_compte import noms_de_taches, retirer_les_taches, taches_du_compte

SID = "S-1-5-21-1111-2222-3333-1001"


def _tache(nom: str, compte: str, auteur: str, commentaire: bool = True) -> str:
    """One task as `/query /xml` prints it: comment, declaration, then the `<Task>` element."""
    ns = "http://schemas.microsoft.com/windows/2004/02/mit/task"
    return (
        (f"<!-- {chr(10)}{nom} -->{chr(10)}" if commentaire else "")
        + '<?xml version="1.0" encoding="UTF-16"?>' + chr(10)
        + f'<Task version="1.2" xmlns="{ns}"><RegistrationInfo><Author>{auteur}</Author><URI>{nom}</URI>'
        + f"</RegistrationInfo><Principals><Principal id=\"A\"><UserId>{compte}</UserId></Principal></Principals></Task>" + chr(10)
    )


def _sortie(*taches: str) -> str:
    return "<Tasks>" + chr(10) + "".join(taches) + "</Tasks>" + chr(10)


# Ce qu'un compte ordinaire voit : sa tâche, celle d'un éditeur, celle de l'utilisateur.
SORTIE = _sortie(
    _tache("\\Nettoyage", SID, "poste\\tessera-agent"),
    _tache("\\Adobe Acrobat Update Task", "S-1-5-4", "Editeur"),
    _tache("\\SoftLanding\\Tache", "poste\\Benjamin", "poste\\Benjamin"),
)


class Faux:
    def __init__(self, suppression: int = 0, sortie: str = SORTIE) -> None:
        self.appels: list[list[str]] = []
        self.suppression = suppression
        self.sortie = sortie

    async def __call__(self, args: list[str]) -> tuple[int, str]:
        self.appels.append(args)
        if "/delete" in args:
            return self.suppression, "refusé"
        return 0, self.sortie


@pytest.fixture(autouse=True)
def compte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(taches_compte, "sid_texte_du_compte", lambda compte: SID)


async def test_only_the_task_that_runs_as_the_account_is_deleted() -> None:
    faux = Faux()
    await retirer_les_taches(faux)
    suppressions = [a for a in faux.appels if "/delete" in a]
    assert len(suppressions) == 1
    assert suppressions[0][2:] == ["/tn", "\\Nettoyage", "/f"]


async def test_a_refused_deletion_of_a_task_the_account_did_not_author_is_logged_not_raised() -> None:
    """Windows creates tasks for the account (OneDrive) that it can neither change nor delete."""
    sortie = _sortie(_tache("\\OneDrive Startup Task", SID, "Microsoft Corporation"))
    faux = Faux(suppression=1, sortie=sortie)
    await retirer_les_taches(faux)
    assert [a for a in faux.appels if "/delete" in a]
    assert not taches_compte.taches_en_echec()


async def test_a_failed_deletion_raises() -> None:
    with pytest.raises(DroitsAgentRefuses):
        await retirer_les_taches(Faux(suppression=1))


async def test_an_empty_list_emits_no_deletion() -> None:
    faux = Faux(sortie="INFO: aucune tâche\n")
    await retirer_les_taches(faux)
    assert len(faux.appels) == 1


async def test_without_agent_user_nothing_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_user", "")
    faux = Faux()
    await retirer_les_taches(faux)
    assert faux.appels == []


def test_names_keep_only_the_tasks_of_the_account() -> None:
    assert noms_de_taches(SORTIE, "tessera-agent", SID) == ["\\Nettoyage"]


def test_a_user_id_by_name_matches_like_a_user_id_by_sid() -> None:
    sortie = _sortie(_tache("\\A", "POSTE\\tessera-agent", "x"), _tache("\\B", "autre-tessera-agent", "x"))
    assert noms_de_taches(sortie, "tessera-agent", SID) == ["\\A"]


def test_a_b_c_authorship_is_told_apart() -> None:
    sortie = _sortie(
        _tache("\\A", SID, "poste\\tessera-agent"),
        _tache("\\B", "S-1-5-21-9-9-9-1002", "poste\\tessera-agent"),
        _tache("\\C", SID, "Autre"),
    )
    assert taches_du_compte(sortie, "tessera-agent", SID) == {"\\A": True, "\\C": False}


def test_the_name_falls_back_to_the_comment() -> None:
    sortie = _sortie(_tache("\\A", SID, "x").replace("<URI>\\A</URI>", ""))
    assert noms_de_taches(sortie, "tessera-agent", SID) == ["\\A"]


@pytest.mark.parametrize("mauvais", ["<!ENTITY x 'y'>", "<!DOCTYPE Task>"])
async def test_a_hostile_fragment_raises_and_flags(mauvais: str) -> None:
    sortie = _sortie(_tache("\\A", SID, "x").replace("<RegistrationInfo>", mauvais + "<RegistrationInfo>"))
    with pytest.raises(DroitsAgentRefuses):
        await retirer_les_taches(Faux(sortie=sortie))
    assert taches_compte.taches_en_echec()


async def test_an_unparsable_fragment_raises_and_flags() -> None:
    sortie = _sortie(_tache("\\A", SID, "x").replace("</Principals>", ""))
    with pytest.raises(DroitsAgentRefuses):
        await retirer_les_taches(Faux(sortie=sortie))
    assert taches_compte.taches_en_echec()


def test_declarations_without_any_task_are_refused() -> None:
    with pytest.raises(DroitsAgentRefuses):
        taches_du_compte('<Tasks><?xml version="1.0"?></Tasks>', "tessera-agent", SID)


def test_a_binary_sid_is_written_in_text_form() -> None:
    binaire = bytes([1, 2]) + (5).to_bytes(6, "big") + (21).to_bytes(4, "little") + (1001).to_bytes(4, "little")
    assert taches_compte._sid_texte(binaire) == "S-1-5-21-1001"


async def test_the_listing_is_asked_in_xml() -> None:
    faux = Faux()
    await retirer_les_taches(faux)
    assert faux.appels[0][1:] == ["/query", "/xml"]


async def test_close_removes_tasks_only_at_the_last_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "profil-vide").mkdir()
    monkeypatch.setattr(profil_agent, "DOSSIER_PROFIL", tmp_path / "profil-vide")
    monkeypatch.setattr(profil_agent, "_NETTOYAGE_ECHOUE", False)
    droits_appel._ACTIFS.clear()
    droits_appel._FILE.clear()
    monkeypatch.setattr(droits_appel, "_VERROU", asyncio.Condition())
    dossier = tmp_path / "worktrees"
    monkeypatch.setattr(settings, "ide_worktrees_dir", dossier)
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", dossier)
    (dossier / "p" / "t-1" / ".git").mkdir(parents=True)
    appels: list[int] = []

    async def espion() -> None:
        appels.append(1)

    async def icacls(args: list[str]) -> tuple[int, str]:
        return 0, ""

    async def rien(compte: str) -> list[tuple[int, str]]:
        return []

    async def ne_tue_rien(pid: int) -> None:
        return None

    monkeypatch.setattr(droits_appel, "retirer_les_taches", espion)
    racine = await ouvrir_appel(dossier / "p" / "t-1", icacls)
    await ouvrir_appel(dossier / "p" / "t-1", icacls)
    await clore_appel(racine, icacls, rien, ne_tue_rien)
    assert appels == []
    await clore_appel(racine, icacls, rien, ne_tue_rien)
    assert appels == [1]


async def test_a_launch_failure_is_a_refusal() -> None:
    async def echoue(args: list[str]) -> tuple[int, str]:
        raise ProviderIndisponible("AGENT_LOGON_PASSWORD absent")

    with pytest.raises(DroitsAgentRefuses):
        await retirer_les_taches(echoue)


async def test_close_withdraws_the_right_when_the_task_launch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "profil-vide").mkdir()
    monkeypatch.setattr(profil_agent, "DOSSIER_PROFIL", tmp_path / "profil-vide")
    monkeypatch.setattr(profil_agent, "_NETTOYAGE_ECHOUE", False)
    droits_appel._ACTIFS.clear()
    droits_appel._FILE.clear()
    monkeypatch.setattr(droits_appel, "_VERROU", asyncio.Condition())
    dossier = tmp_path / "worktrees"
    monkeypatch.setattr(settings, "ide_worktrees_dir", dossier)
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", dossier)
    (dossier / "p" / "t-1" / ".git").mkdir(parents=True)
    appels: list[list[str]] = []

    async def icacls(args: list[str]) -> tuple[int, str]:
        appels.append(args)
        return 0, ""

    async def echoue(args: list[str]) -> tuple[int, str]:
        raise OSError("pas de lanceur")

    async def taches() -> None:
        await retirer_les_taches(echoue)

    async def rien(compte: str) -> list[tuple[int, str]]:
        return []

    async def ne_tue_rien(pid: int) -> None:
        return None

    monkeypatch.setattr(droits_appel, "retirer_les_taches", taches)
    racine = await ouvrir_appel(dossier / "p" / "t-1", icacls)
    avant = len(appels)
    with pytest.raises(DroitsAgentRefuses):
        await clore_appel(racine, icacls, rien, ne_tue_rien)
    assert len(appels) > avant


@pytest.fixture(autouse=True)
def drapeau_remis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(taches_compte, "_TACHES_ECHOUEES", False)


def _cadre(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "profil-vide").mkdir()
    monkeypatch.setattr(profil_agent, "DOSSIER_PROFIL", tmp_path / "profil-vide")
    monkeypatch.setattr(profil_agent, "_NETTOYAGE_ECHOUE", False)
    droits_appel._ACTIFS.clear()
    droits_appel._FILE.clear()
    monkeypatch.setattr(droits_appel, "_VERROU", asyncio.Condition())
    dossier = tmp_path / "worktrees"
    monkeypatch.setattr(settings, "ide_worktrees_dir", dossier)
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", dossier)
    (dossier / "p" / "t-1" / ".git").mkdir(parents=True)
    return dossier / "p" / "t-1"


async def _icacls(args: list[str]) -> tuple[int, str]:
    return 0, ""


async def test_a_task_failure_does_not_skip_the_stop_nor_the_wipe_and_refuses_the_next_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arbre = _cadre(tmp_path, monkeypatch)
    vus: list[str] = []

    async def echoue(args: list[str]) -> tuple[int, str]:
        raise OSError("pas de lanceur")

    async def restants(compte: str) -> list[tuple[int, str]]:
        vus.append("enumere")
        return []

    async def ne_tue_rien(pid: int) -> None:
        return None

    async def profil(compte: str, icacls: object = None) -> None:
        vus.append("profil")

    monkeypatch.setattr(taches_compte, "_lanceur_reel", echoue)
    monkeypatch.setattr(droits_appel, "reinitialiser_profil", profil)
    racine = await ouvrir_appel(arbre, _icacls)
    with pytest.raises(DroitsAgentRefuses):
        await clore_appel(racine, _icacls, restants, ne_tue_rien)
    assert vus == ["enumere", "profil"]
    assert taches_compte.taches_en_echec()
    with pytest.raises(DroitsAgentRefuses):
        await ouvrir_appel(arbre, _icacls)


async def test_refused_deletion_of_c_is_logged_and_that_of_a_raises() -> None:
    c = _tache("\\C", SID, "Autre")
    a = _tache("\\A", SID, "poste\\tessera-agent")
    await retirer_les_taches(Faux(suppression=1, sortie=_sortie(c)))
    assert not taches_compte.taches_en_echec()
    faux = Faux(suppression=1, sortie=_sortie(c, a))
    with pytest.raises(DroitsAgentRefuses, match="A"):
        await retirer_les_taches(faux)
    assert taches_compte.taches_en_echec()
    assert [x[3] for x in faux.appels if "/delete" in x] == ["\\C", "\\A"]
