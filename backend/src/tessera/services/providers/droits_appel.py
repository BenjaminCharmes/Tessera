"""The write right of the agent account lasts one call — ticket-943.

ADR-083. Le compte n'a le droit d'écrire dans un worktree que pendant un appel
d'agent, une commande de test ou l'app du contrôle visuel. À la fin du dernier
appel en cours, tout processus restant du compte est arrêté (journalisé), puis
son droit est retiré ; le suivant le repose. Un échec est une
`DroitsAgentRefuses` : le run passe en `blocked` (ADR-037).
"""
import asyncio
import csv
import io
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.config import settings
from tessera.services.providers.droits_worktree import DroitsAgentRefuses, Icacls, _icacls_reel, poser_ecriture, retirer_ecriture
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Processus du compte : couples (pid, nom d'image).
Enumerer = Callable[[str], Awaitable[list[tuple[int, str]]]]
#: Arrête un processus par son pid.
Tuer = Callable[[int], Awaitable[None]]

_COLONNE_UTILISATEUR = 6
_ACTIFS: dict[Path, int] = {}
_VERROU = asyncio.Lock()


def processus_du_compte(csv_tasklist: str, compte: str) -> list[tuple[int, str]]:
    """Parse `tasklist /V /FO CSV /NH`; keep the rows whose user is `compte`."""
    voulu = compte.lower().split("\\")[-1]
    trouves: list[tuple[int, str]] = []
    for ligne in csv.reader(io.StringIO(csv_tasklist)):
        if len(ligne) <= _COLONNE_UTILISATEUR or not ligne[1].isdigit():
            continue
        if ligne[_COLONNE_UTILISATEUR].lower().split("\\")[-1] == voulu:
            trouves.append((int(ligne[1]), ligne[0]))
    return trouves


async def _executer(*args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    sortie, _ = await proc.communicate()
    return proc.returncode or 0, sortie.decode(errors="replace")


async def _enumerer_reel(compte: str) -> list[tuple[int, str]]:
    code, sortie = await _executer("tasklist", "/V", "/FO", "CSV", "/NH")
    if code != 0:
        raise DroitsAgentRefuses(f"tasklist a échoué (code {code})")
    return processus_du_compte(sortie, compte)


async def _tuer_reel(pid: int) -> None:
    code, sortie = await _executer("taskkill", "/F", "/T", "/PID", str(pid))
    if code != 0:
        raise DroitsAgentRefuses(f"taskkill a échoué sur {pid} (code {code}) : {sortie.strip()}")


def racine_du_worktree(cwd: str | Path) -> Path | None:
    """The nearest folder, from `cwd` upwards, that holds a `.git`."""
    chemin = Path(cwd).resolve()
    for dossier in (chemin, *chemin.parents):
        if (dossier / ".git").exists():
            return dossier
    return None


async def arreter_les_restants(compte: str, enumerer: Enumerer, tuer: Tuer) -> None:
    """Stop every process still owned by `compte`; log each image name."""
    for pid, image in await enumerer(compte):
        _logger.warning("processus_du_compte_restant", extra={"pid": pid, "image": image})
        await tuer(pid)


async def ouvrir_appel(cwd: str | Path, icacls: Icacls = _icacls_reel) -> Path | None:
    """Give the account its write right on the worktree of `cwd`; returns its root.

    `None` sans `AGENT_USER` ou hors d'un dépôt : rien n'est posé, rien ne sera retiré.
    """
    compte = settings.agent_user
    racine = racine_du_worktree(cwd) if compte else None
    if not compte or racine is None:
        return None
    async with _VERROU:
        if _ACTIFS.get(racine, 0) == 0:
            await poser_ecriture(racine, compte, icacls)
        _ACTIFS[racine] = _ACTIFS.get(racine, 0) + 1
    return racine


async def clore_appel(
    racine: Path | None, icacls: Icacls = _icacls_reel,
    enumerer: Enumerer = _enumerer_reel, tuer: Tuer = _tuer_reel,
) -> None:
    """End a call: at the last one, stop the account's leftovers, then withdraw its right."""
    compte = settings.agent_user
    if racine is None or not compte:
        return
    async with _VERROU:
        restant = _ACTIFS.get(racine, 1) - 1
        if restant > 0:
            _ACTIFS[racine] = restant
            return
        _ACTIFS.pop(racine, None)
        erreur: DroitsAgentRefuses | None = None
        # Un appel en cours sur un autre worktree, sous le même compte : rien n'est
        # tué (le job de chaque appel a déjà fermé le sien).
        if not _ACTIFS:
            try:
                await arreter_les_restants(compte, enumerer, tuer)
            except DroitsAgentRefuses as exc:
                erreur = exc
        await retirer_ecriture(racine, compte, icacls)
        if erreur is not None:
            raise erreur
