"""ticket-991: the agent account's processes are listed by token SID, without tasklist."""
import os
from pathlib import Path

import pytest

from tessera.services.providers import processus_compte
from tessera.services.providers.processus_compte import processus_par_sid

SRC = Path(__file__).resolve().parents[1] / "src" / "tessera" / "services" / "providers"


def test_only_processes_whose_token_carries_the_sid_are_kept() -> None:
    sids = {10: b"agent", 11: b"moi", 12: None, 13: b"agent"}
    images = {10: "node.exe", 13: "conhost.exe"}
    trouves = processus_par_sid(
        b"agent", pids=lambda: [0, 10, 11, 12, 13], sid_de=sids.get, image_de=images.get,
    )
    assert trouves == [(10, "node.exe"), (13, "conhost.exe")]


def test_a_process_without_readable_image_keeps_a_placeholder_name() -> None:
    trouves = processus_par_sid(
        b"agent", pids=lambda: [7], sid_de=lambda _pid: b"agent", image_de=lambda _pid: None,
    )
    assert trouves == [(7, "?")]


def test_listing_never_goes_through_tasklist() -> None:
    # `tasklist /V` prenait 87 s par appel sur le poste (ticket-991).
    for nom in ("processus_compte.py", "droits_appel.py"):
        assert "tasklist" not in (SRC / nom).read_text(encoding="utf-8")


@pytest.mark.skipif(os.name != "nt", reason="API Windows")
def test_the_current_process_is_found_under_its_own_account() -> None:
    compte = os.environ["USERNAME"]
    sid = processus_compte.sid_du_compte(compte)
    assert os.getpid() in [pid for pid, _ in processus_compte.processus_du_compte(sid)]


def test_an_unreadable_new_process_is_refused_after_the_readable_ones_are_listed() -> None:
    from tessera.services.providers.droits_worktree import DroitsAgentRefuses
    from tessera.services.providers.processus_compte import ILLISIBLE, ProcessusIllisibles

    sids = {10: b"agent", 11: ILLISIBLE, 12: ILLISIBLE}
    with pytest.raises(DroitsAgentRefuses) as exc:
        processus_par_sid(
            b"agent", pids=lambda: [10, 11, 12], sid_de=sids.get, image_de=lambda _p: "x.exe",
            avant=frozenset({12}),
        )
    assert isinstance(exc.value, ProcessusIllisibles)
    assert exc.value.trouves == [(10, "x.exe")]


def test_a_full_pid_buffer_is_listed_again_with_a_larger_one() -> None:
    from tessera.services.providers.processus_compte import _pids

    capacites: list[int] = []

    def lire(capacite: int) -> tuple[list[int], bool]:
        capacites.append(capacite)
        return list(range(capacite)), len(capacites) == 1

    assert len(_pids(lire)) == capacites[1] == 2 * capacites[0]


def test_taskkill_on_a_vanished_pid_is_a_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from tessera.services.providers import droits_appel

    async def echec(*_args: str) -> tuple[int, str]:
        return 128, "not found"

    monkeypatch.setattr(droits_appel, "_executer", echec)
    asyncio.run(droits_appel._tuer_reel(42, existe=lambda _pid: False))
    with pytest.raises(droits_appel.DroitsAgentRefuses):
        asyncio.run(droits_appel._tuer_reel(42, existe=lambda _pid: True))


@pytest.mark.skipif(os.name != "nt", reason="API Windows")
def test_a_real_listing_with_a_snapshot_refuses_nothing_on_a_healthy_machine() -> None:
    sid = processus_compte.sid_du_compte(os.environ["USERNAME"])
    avant = processus_compte.instantane_pids()
    assert os.getpid() in [pid for pid, _ in processus_compte.processus_du_compte(sid, avant)]
