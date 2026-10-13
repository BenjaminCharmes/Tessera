"""Ce que la machine sait de ses processus — ticket-416.

`psutil` serait l'outil évident, mais il n'est pas une dépendance du projet et
Smart App Control bloque déjà certaines DLL sur la machine de dev : on s'appuie
sur ce que l'OS fournit (`netstat`/PowerShell sous Windows, `ss`/`ps` ailleurs).
Tout passe par `SondeSysteme`, pour que les tests utilisent un faux.

Une sonde qui échoue rend un résultat **vide**, jamais une exception : un
inventaire incomplet vaut mieux qu'une vue qui ne s'affiche pas.
"""
import asyncio
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_DELAI_S = 15.0
_OCTETS_PAR_MO = 1024 * 1024

_POWERSHELL = (
    "Get-CimInstance Win32_Process | Where-Object { $_.CreationDate } | "
    "ForEach-Object { '{0},{1},{2},{3}' -f $_.ProcessId, $_.ParentProcessId, "
    "$_.WorkingSetSize, $_.CreationDate.ToUniversalTime().ToString('o') }"
)
_PORT_NETSTAT = re.compile(r":(\d+)$")
_PID_SS = re.compile(r"pid=(\d+)")


@dataclass(frozen=True)
class InfoProcessus:
    """Un processus vu par la sonde."""

    ppid: int
    memoire_mo: float
    demarre_a: datetime | None


class SondeSysteme(Protocol):
    """Ce dont l'inventaire a besoin, et rien de plus."""

    async def ecouteurs(self) -> dict[int, int]:
        """Port TCP en écoute -> pid qui l'écoute."""
        ...

    async def processus(self) -> dict[int, InfoProcessus]:
        """Tous les processus : de quoi remonter les arbres et sommer la RSS."""
        ...


def _executer(commande: list[str]) -> str:
    try:
        resultat = subprocess.run(
            commande,
            capture_output=True,
            text=True,
            # `netstat` écrit dans la page de code OEM : sans `replace`, un
            # accent illisible fait échouer la lecture et la sortie est `None`.
            errors="replace",
            timeout=_DELAI_S,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _logger.warning("sonde_en_echec", extra={"commande": commande[0], "erreur": str(exc)})
        return ""
    return resultat.stdout or ""


def lire_netstat(sortie: str) -> dict[int, int]:
    """Parse `netstat -ano`: only TCP lines in LISTENING state."""
    ports: dict[int, int] = {}
    for ligne in sortie.splitlines():
        champs = ligne.split()
        if len(champs) < 5 or champs[0] != "TCP" or champs[3] != "LISTENING":
            continue
        port = _PORT_NETSTAT.search(champs[1])
        if port and champs[4].isdigit():
            ports.setdefault(int(port.group(1)), int(champs[4]))
    return ports


def lire_ss(sortie: str) -> dict[int, int]:
    """Parse `ss -ltnpH`: the local address is the 4th column."""
    ports: dict[int, int] = {}
    for ligne in sortie.splitlines():
        champs = ligne.split()
        if len(champs) < 4:
            continue
        port = _PORT_NETSTAT.search(champs[3])
        pid = _PID_SS.search(ligne)
        if port and pid:
            ports.setdefault(int(port.group(1)), int(pid.group(1)))
    return ports


def lire_powershell(sortie: str) -> dict[int, InfoProcessus]:
    """Parse `pid,ppid,working_set_bytes,iso_creation_date` lines."""
    processus: dict[int, InfoProcessus] = {}
    for ligne in sortie.splitlines():
        champs = ligne.strip().split(",")
        if len(champs) != 4 or not all(c.isdigit() for c in champs[:3]):
            continue
        try:
            demarre_a: datetime | None = datetime.fromisoformat(champs[3])
        except ValueError:
            demarre_a = None
        processus[int(champs[0])] = InfoProcessus(
            ppid=int(champs[1]),
            memoire_mo=int(champs[2]) / _OCTETS_PAR_MO,
            demarre_a=demarre_a,
        )
    return processus


def lire_ps(sortie: str) -> dict[int, InfoProcessus]:
    """Parse `ps -eo pid=,ppid=,rss=,lstart=` (RSS in KiB, local time)."""
    processus: dict[int, InfoProcessus] = {}
    for ligne in sortie.splitlines():
        champs = ligne.split(None, 3)
        if len(champs) != 4 or not all(c.isdigit() for c in champs[:3]):
            continue
        try:
            demarre_a: datetime | None = datetime.strptime(
                champs[3].strip(), "%a %b %d %H:%M:%S %Y"
            ).astimezone()
        except ValueError:
            demarre_a = None
        processus[int(champs[0])] = InfoProcessus(
            ppid=int(champs[1]),
            memoire_mo=int(champs[2]) / 1024,
            demarre_a=demarre_a,
        )
    return processus


class SondeReelle:
    """La sonde de la machine : Windows d'un côté, le reste de l'autre."""

    async def ecouteurs(self) -> dict[int, int]:
        if os.name == "nt":
            sortie = await asyncio.to_thread(_executer, ["netstat", "-ano"])
            return lire_netstat(sortie)
        return lire_ss(await asyncio.to_thread(_executer, ["ss", "-ltnpH"]))

    async def processus(self) -> dict[int, InfoProcessus]:
        if os.name == "nt":
            sortie = await asyncio.to_thread(
                _executer, ["powershell", "-NoProfile", "-Command", _POWERSHELL]
            )
            return lire_powershell(sortie)
        sortie = await asyncio.to_thread(
            _executer, ["ps", "-eo", "pid=,ppid=,rss=,lstart="]
        )
        return lire_ps(sortie)
