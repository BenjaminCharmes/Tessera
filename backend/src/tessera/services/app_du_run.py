"""Start and stop the app of a run, from its worktree — ticket-618, ADR-062.

Le démarrage ne passe par aucun shell (ADR-027, ADR-031) et le processus part
dans les groupes d'ADR-042 : à l'arrêt, c'est son arbre qui meurt. Rien ne tue
jamais un processus qui n'a pas été lancé ici.
"""
import asyncio
import os
import shlex
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit

from tessera.services.captures import app_repond
from tessera.services.captures_config import ConfigCaptures
from tessera.services.controle_visuel import JETON_PORT, Demarrage
from tessera.services.groupe_de_processus import (
    creer_groupe,
    fermer_le_groupe,
    rattacher_au_groupe,
    tuer_l_arbre,
)
from tessera.services.lancement import essais_de_commande, options_de_lancement
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_DELAI_D_ARRET_S = 5.0
_PAUSE_SONDE_S = 0.5


class DemarrageEchoue(Exception):
    """The app did not start, died while starting, or did not answer in time."""


class AppLancee(Protocol):
    """A process started for the run: it can say it ended, and be stopped."""

    @property
    def code_de_sortie(self) -> int | None: ...

    async def arreter(self) -> None: ...


#: Lance les arguments depuis ce dossier ; un exécuteur factice le remplace en test.
Demarreur = Callable[[list[str], Path], Awaitable[AppLancee]]
Sonde = Callable[[str], Awaitable[bool]]


@dataclass
class _Processus:
    """The default `AppLancee`: an asyncio process and its job group."""

    processus: Any
    groupe: Any

    @property
    def code_de_sortie(self) -> int | None:
        code = self.processus.returncode
        return code if isinstance(code, int) else None

    async def arreter(self) -> None:
        if self.code_de_sortie is not None:
            fermer_le_groupe(self.groupe)
            return
        try:
            fermer_le_groupe(self.groupe)
            await tuer_l_arbre(self.processus.pid)
            self.processus.terminate()
            await asyncio.wait_for(self.processus.wait(), timeout=_DELAI_D_ARRET_S)
        except asyncio.TimeoutError:
            self.processus.kill()
            await self.processus.wait()
        except ProcessLookupError:
            return  # déjà mort : rien à arrêter
        except Exception as exc:  # noqa: BLE001 — un arrêt raté ne casse pas le run
            _logger.warning("arret_app_du_run_echoue", extra={"erreur": str(exc)})


async def demarrer_processus(args: list[str], cwd: Path) -> AppLancee:
    """Start `args` in `cwd` without a shell, in its own group."""
    derniere: FileNotFoundError | None = None
    for tentative in essais_de_commande(args):
        try:
            processus = await asyncio.create_subprocess_exec(
                *tentative,
                cwd=str(cwd),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                **options_de_lancement(os.name),
            )
        except FileNotFoundError as exc:
            derniere = exc
            continue
        groupe = creer_groupe()
        if groupe is not None:
            rattacher_au_groupe(groupe, processus.pid)
        return _Processus(processus, groupe)
    raise DemarrageEchoue(f"Commande introuvable : {args[0]}") from derniere


def port_libre() -> int:
    """Ask the system for a free local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as prise:
        prise.bind(("127.0.0.1", 0))
        return int(prise.getsockname()[1])


def commande_du_run(demarrage: Demarrage, port: int) -> list[str]:
    """Split the declared command, with `{port}` replaced by the chosen port."""
    try:
        args = shlex.split(demarrage.commande.replace(JETON_PORT, str(port)))
    except ValueError as exc:
        raise DemarrageEchoue(f"Commande de démarrage illisible : {exc}") from exc
    if not args:
        raise DemarrageEchoue("Commande de démarrage vide.")
    return args


def config_sur_le_port(config: ConfigCaptures, port: int) -> ConfigCaptures:
    """The capture configuration pointed at the run's own port, host kept."""
    parties = urlsplit(config.url)
    hote = parties.hostname or "localhost"
    url = urlunsplit((parties.scheme, f"{hote}:{port}", parties.path, "", ""))
    return replace(config, url=url.rstrip("/"))


async def attendre_que_l_app_reponde(
    app: AppLancee, url: str, delai_s: float, sonde: Sonde = app_repond,
    pause_s: float = _PAUSE_SONDE_S,
) -> None:
    """Wait until `url` answers ; fail on an early exit or after `delai_s`."""
    echeance = asyncio.get_running_loop().time() + delai_s
    while True:
        code = app.code_de_sortie
        if code is not None:
            raise DemarrageEchoue(f"L'app s'est arrêtée au démarrage (code {code}).")
        if await sonde(url):
            return
        if asyncio.get_running_loop().time() >= echeance:
            raise DemarrageEchoue(f"L'app n'a pas répondu en {int(delai_s)} s.")
        await asyncio.sleep(pause_s)
