"""The agent desktop and the account's entry on the station — ticket-1023 (ADR-089)."""
from pathlib import Path
from typing import Any

import pytest

from tessera.services.providers import station_agent
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.station_agent import BureauAgent, EntreesStation, ouvrir_bureau


class FauxUser32:
    """Records the closings; the station handle is 7, the desktop handle 9."""

    def __init__(self) -> None:
        self.ferme: list[str] = []

    def CreateWindowStationW(self, *args: Any) -> int:  # noqa: N802
        return 7

    def CloseDesktop(self, handle: Any) -> bool:  # noqa: N802
        self.ferme.append("bureau")
        return True

    def CloseWindowStation(self, handle: Any) -> bool:  # noqa: N802
        self.ferme.append("station")
        return True


@pytest.fixture
def entrees(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replaces the Win32 steps; returns the journal of the account's entry (set / revoke)."""
    journal: list[str] = []
    u32 = FauxUser32()
    monkeypatch.setattr(station_agent, "_ENTREES", EntreesStation())
    monkeypatch.setattr(station_agent, "_dlls", lambda: (u32, object(), object()))
    monkeypatch.setattr(station_agent, "_sid_du_processus", lambda pid: b"backend")
    monkeypatch.setattr(station_agent, "_creer_bureau", lambda *a: 9)
    monkeypatch.setattr(station_agent, "_nom", lambda u, h: "Station" if h == 7 else "Bureau")
    monkeypatch.setattr(
        station_agent, "_entree_du_compte",
        lambda adv, station, sid, mode: journal.append("pose" if mode == station_agent._SET_ACCESS else "retrait"),
    )
    return journal


def test_a_desktop_is_named_station_then_desktop(entrees: list[str]) -> None:
    bureau = ouvrir_bureau(b"agent")
    assert bureau.nom == "Station\\Bureau"
    assert entrees == ["pose"]


def test_the_entry_is_removed_only_when_the_last_desktop_closes(entrees: list[str]) -> None:
    premier, second = ouvrir_bureau(b"agent"), ouvrir_bureau(b"agent")
    premier.fermer()
    assert "retrait" not in entrees
    second.fermer()
    assert entrees.count("retrait") == 1


def test_a_second_close_does_nothing(entrees: list[str]) -> None:
    bureau = ouvrir_bureau(b"agent")
    bureau.fermer()
    bureau.fermer()
    assert entrees.count("retrait") == 1


def test_an_unreadable_backend_sid_refuses_to_open(
    entrees: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(station_agent, "_sid_du_processus", lambda pid: None)
    with pytest.raises(ProviderIndisponible, match="SID du backend"):
        ouvrir_bureau(b"agent")
    assert entrees == []


def test_a_failed_desktop_gives_back_the_entry(
    entrees: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def echec(*args: Any) -> int:
        raise ProviderIndisponible("bureau impossible")

    monkeypatch.setattr(station_agent, "_creer_bureau", echec)
    with pytest.raises(ProviderIndisponible):
        ouvrir_bureau(b"agent")
    assert entrees == ["pose", "retrait"]


def test_the_registry_counts_open_desktops() -> None:
    registre, retraits = EntreesStation(), []
    registre.ouvrir(lambda: None)
    registre.ouvrir(lambda: None)
    registre.fermer(lambda: retraits.append(1))
    assert retraits == []
    registre.fermer(lambda: retraits.append(1))
    assert retraits == [1]


def test_bureau_agent_closes_once() -> None:
    appels: list[int] = []
    bureau = BureauAgent("W\\D", lambda: appels.append(1))
    bureau.fermer()
    bureau.fermer()
    assert appels == [1]


def test_the_module_does_not_import_pywin32() -> None:
    source = Path(station_agent.__file__).read_text(encoding="utf-8")
    assert "import win32" not in source and "import pywintypes" not in source
    assert "from win32" not in source
    assert len(source.splitlines()) <= 200


class FauxStation:
    """Records whether the switch lock is held at each station call."""

    def __init__(self) -> None:
        self.verrou_pris: list[bool] = []
        self.bascules: list[int] = []

    def GetProcessWindowStation(self) -> int:  # noqa: N802
        self.verrou_pris.append(station_agent._VERROU_STATION.locked())
        return 1

    def SetProcessWindowStation(self, handle: Any) -> bool:  # noqa: N802
        self.verrou_pris.append(station_agent._VERROU_STATION.locked())
        self.bascules.append(handle.value)
        return True

    def CreateDesktopW(self, *args: Any) -> int:  # noqa: N802
        self.verrou_pris.append(station_agent._VERROU_STATION.locked())
        return 9


def test_the_station_switch_is_made_under_the_lock_and_put_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    u32 = FauxStation()
    monkeypatch.setattr(station_agent, "_descripteur", lambda adv, sids: (None, station_agent._Attributs()))
    assert station_agent._creer_bureau(u32, object(), 7, [b"a"]) == 9
    assert all(u32.verrou_pris) and len(u32.verrou_pris) == 4
    assert u32.bascules == [7, 1]
    assert not station_agent._VERROU_STATION.locked()
