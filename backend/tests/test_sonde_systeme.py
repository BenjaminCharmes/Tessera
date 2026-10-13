"""La lecture de ce que `netstat`, `ss`, PowerShell et `ps` rendent — ticket-416."""
import asyncio

from tessera.services.sonde_systeme import (
    SondeReelle,
    lire_netstat,
    lire_powershell,
    lire_ps,
    lire_ss,
)

_NETSTAT = """
Connexions actives

  Proto  Adresse locale         Adresse distante       État            PID
  TCP    0.0.0.0:8025           0.0.0.0:0              LISTENING       1234
  TCP    [::]:5195              [::]:0                 LISTENING       5678
  TCP    127.0.0.1:50000        127.0.0.1:8025         ESTABLISHED     999
  UDP    0.0.0.0:5353           *:*                                    42
"""

_SS = (
    'LISTEN 0 128 0.0.0.0:8025 0.0.0.0:* users:(("python",pid=1234,fd=3))\n'
    "LISTEN 0 128 [::]:22 [::]:*\n"
)


def test_netstat_keeps_only_listening_tcp() -> None:
    assert lire_netstat(_NETSTAT) == {8025: 1234, 5195: 5678}


def test_ss_reads_port_and_pid() -> None:
    assert lire_ss(_SS) == {8025: 1234}


def test_powershell_lines_give_memory_parent_and_start() -> None:
    sortie = "1234,10,104857600,2026-10-13T08:00:00.0000000Z\nbruit\n"

    procs = lire_powershell(sortie)

    assert list(procs) == [1234]
    assert procs[1234].ppid == 10
    assert procs[1234].memoire_mo == 100.0
    assert procs[1234].demarre_a is not None


def test_ps_lines_give_memory_in_mb_and_start() -> None:
    sortie = "  321   1  2048 Tue Oct 13 08:00:00 2026\n"

    procs = lire_ps(sortie)

    assert procs[321].ppid == 1
    assert procs[321].memoire_mo == 2.0
    assert procs[321].demarre_a is not None


def test_real_probe_never_raises() -> None:
    sonde = SondeReelle()

    ecouteurs = asyncio.run(sonde.ecouteurs())
    procs = asyncio.run(sonde.processus())

    assert isinstance(ecouteurs, dict)
    assert isinstance(procs, dict)
