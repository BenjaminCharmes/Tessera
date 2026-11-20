"""A parent link only counts when the parent was born before its child — ticket-1012."""
import os

import pytest

from tessera.services.providers.parentes_processus import liens_vivants, naissances, parents_toolhelp


def test_a_link_to_a_reused_parent_pid_is_dropped() -> None:
    # csrss (1784) garde le PID de son parent mort (1768), réattribué plus tard à un autre processus.
    assert liens_vivants({1784: 1768, 1768: 900}, {1784: 100, 1768: 200, 900: 50}) == {1768: 900}


def test_a_link_to_an_older_parent_is_kept() -> None:
    assert liens_vivants({11: 10}, {11: 200, 10: 100}) == {11: 10}
    assert liens_vivants({11: 10}, {11: 100, 10: 100}) == {11: 10}


def test_a_link_without_both_birth_dates_is_kept() -> None:
    # Échec fermé : sans date, le lien reste suspect.
    assert liens_vivants({11: 10, 21: 20}, {11: 200, 20: 300}) == {11: 10, 21: 20}
    assert liens_vivants({11: 10}, {11: 0, 10: 500}) == {11: 10}


def test_the_parent_map_drops_reused_pids() -> None:
    parents = parents_toolhelp(lire=lambda: {1784: 1768, 12: 4}, dates=lambda: {1784: 100, 1768: 200, 12: 9, 4: 1})
    assert parents == {12: 4}


@pytest.mark.skipif(os.name != "nt", reason="API Windows")
def test_real_birth_dates_put_this_process_after_its_parent() -> None:
    dates = naissances()
    assert 0 < dates[os.getppid()] <= dates[os.getpid()]
