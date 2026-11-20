"""The launcher gives the call its own desktop and closes it with the job — ticket-1023 (ADR-089)."""
import io
from types import SimpleNamespace
from typing import Any

import anyio
import pytest

from tessera.services.providers import lanceur_windows
from tessera.services.providers.lanceur_windows import LanceurWindows
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.station_agent import BureauAgent


class FauxKernel:
    """Both DLLs: every call succeeds; the desktop of the start is recorded."""

    def __init__(self, logon_ok: bool = True) -> None:
        self.logon_ok = logon_ok
        self.desktops: list[str] = []

    def CreateProcessWithLogonW(self, *args: Any) -> bool:  # noqa: N802
        self.desktops.append(args[9]._obj.lpDesktop)
        return self.logon_ok

    def __getattr__(self, nom: str) -> Any:
        return lambda *a, **k: 1


class Fixture:
    def __init__(self) -> None:
        self.evenements: list[str] = []
        self.noyau = FauxKernel()

    def ouvreur(self, sid: bytes) -> BureauAgent:
        self.evenements.append(f"ouvre:{sid.decode()}")
        return BureauAgent("Station\\Bureau", lambda: self.evenements.append("ferme-bureau"))


@pytest.fixture
def faux(monkeypatch: pytest.MonkeyPatch) -> Fixture:
    f = Fixture()
    monkeypatch.setattr(lanceur_windows, "_CTYPES", SimpleNamespace(
        WinDLL=lambda *a, **k: f.noyau, get_last_error=lambda: 0))
    monkeypatch.setattr(lanceur_windows, "creer_groupe", lambda: object())
    monkeypatch.setattr(lanceur_windows, "fermer_le_groupe",
                        lambda g: f.evenements.append("ferme-job") or True)
    monkeypatch.setattr(lanceur_windows, "_fichier", lambda h, m: io.BytesIO())
    return f


def _lanceur(f: Fixture) -> LanceurWindows:
    return LanceurWindows(f.ouvreur, lambda compte: compte.encode())


def _lancer(lanceur: LanceurWindows) -> Any:
    return lanceur._lancer(["cmd"], "agent", "mdp", {}, None, True)


def test_the_process_starts_on_the_desktop_and_it_closes_with_the_job(faux: Fixture) -> None:
    proc = _lancer(_lanceur(faux))
    assert faux.noyau.desktops == ["Station\\Bureau"]
    assert faux.evenements == ["ouvre:agent"]
    anyio.run(proc.aclose)
    assert faux.evenements == ["ouvre:agent", "ferme-job", "ferme-bureau"]


def test_a_failed_desktop_raises_and_starts_nothing(faux: Fixture) -> None:
    def refuse(sid: bytes) -> BureauAgent:
        raise ProviderIndisponible("station de l'agent : refusée")

    with pytest.raises(ProviderIndisponible, match="station"):
        _lancer(LanceurWindows(refuse, lambda compte: b"sid"))
    assert faux.noyau.desktops == []
    assert faux.evenements == ["ferme-job"]


def test_a_refused_logon_closes_the_desktop(faux: Fixture) -> None:
    faux.noyau.logon_ok = False
    with pytest.raises(ProviderIndisponible):
        _lancer(_lanceur(faux))
    assert "ferme-bureau" in faux.evenements
