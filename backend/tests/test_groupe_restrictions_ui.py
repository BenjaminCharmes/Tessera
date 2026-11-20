"""The job of an agent call limits the user interface — ticket-1024 (ADR-089)."""
from typing import Any

import pytest

from tessera.services.noyau import groupe_de_processus as groupe

JOB = 4242
KILL_ON_JOB_CLOSE = 0x2000
HUIT_DRAPEAUX = 0xFF


class FauxKernel:
    """Records each SetInformationJobObject call; the UI one can be made to fail."""

    def __init__(self, ui_ok: bool = True) -> None:
        self.ui_ok = ui_ok
        self.poses: list[tuple[int, int]] = []
        self.fermes: list[Any] = []

    def CreateJobObjectW(self, *args: Any) -> int:  # noqa: N802
        return JOB

    def SetInformationJobObject(self, job: Any, classe: int, ref: Any, taille: int) -> bool:  # noqa: N802
        objet = ref._obj
        if classe == 4:
            self.poses.append((classe, int(objet.UIRestrictionsClass)))
            return self.ui_ok
        self.poses.append((classe, int(objet.BasicLimitInformation.LimitFlags)))
        return True

    def CloseHandle(self, poignee: Any) -> bool:  # noqa: N802
        self.fermes.append(poignee)
        return True


@pytest.fixture
def noyau(monkeypatch: pytest.MonkeyPatch) -> FauxKernel:
    faux = FauxKernel()
    monkeypatch.setattr(groupe, "_kernel32", lambda: faux)
    monkeypatch.setattr(groupe, "groupe_disponible", lambda: True)
    monkeypatch.setattr(groupe, "_derniere_erreur", lambda: 5)
    return faux


def test_ui_restrictions_set_class_4_with_the_eight_flags(noyau: FauxKernel) -> None:
    assert groupe.creer_groupe(restrictions_ui=True) == JOB
    assert noyau.poses == [(9, KILL_ON_JOB_CLOSE), (4, HUIT_DRAPEAUX)]
    assert noyau.fermes == []


def test_default_group_has_no_ui_restrictions(noyau: FauxKernel) -> None:
    assert groupe.creer_groupe() == JOB
    assert noyau.poses == [(9, KILL_ON_JOB_CLOSE)]


def test_a_failed_ui_restriction_closes_the_job_and_raises(noyau: FauxKernel) -> None:
    noyau.ui_ok = False
    with pytest.raises(OSError):
        groupe.creer_groupe(restrictions_ui=True)
    assert noyau.fermes == [JOB]
