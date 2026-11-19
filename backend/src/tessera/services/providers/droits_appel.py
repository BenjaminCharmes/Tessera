"""The write right of the agent account lasts one call — ticket-943.

ADR-083. Le compte n'a le droit d'écrire dans un worktree que pendant un appel
d'agent, une commande de test ou l'app du contrôle visuel. À la fin du dernier
appel en cours, tout processus restant du compte est arrêté (journalisé), puis
son droit est retiré ; le suivant le repose. Un échec est une
`DroitsAgentRefuses` : le run passe en `blocked` (ADR-037).
"""
import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.config import settings
from tessera.services.providers.droits_worktree import DroitsAgentRefuses, Icacls, _icacls_reel, poser_ecriture, retirer_ecriture
from tessera.services.providers.processus_compte import ProcessusIllisibles, processus_du_compte, processus_existe, sid_du_compte
from tessera.services.providers.profil_agent import reinitialiser_profil
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Processus du compte : couples (pid, nom d'image).
Enumerer = Callable[[str], Awaitable[list[tuple[int, str]]]]
#: Arrête un processus par son pid.
Tuer = Callable[[int], Awaitable[None]]

_ACTIFS: dict[Path, int] = {}
_VERROU = asyncio.Condition()
#: Appels en attente d'une autre racine, dans l'ordre d'arrivée.
_FILE: deque[object] = deque()
#: Au-delà, l'attente est journalisée (secondes).
_ATTENTE_JOURNALISEE_S = 5.0


async def _executer(*args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    sortie, _ = await proc.communicate()
    return proc.returncode or 0, sortie.decode(errors="replace")


async def _enumerer_reel(compte: str) -> list[tuple[int, str]]:
    """The account's processes by token SID: in milliseconds, without resolving any account name (ticket-991)."""
    sid = await asyncio.to_thread(sid_du_compte, compte)
    return await asyncio.to_thread(processus_du_compte, sid)


async def _tuer_reel(pid: int, existe: Callable[[int], bool] = processus_existe) -> None:
    code, sortie = await _executer("taskkill", "/F", "/T", "/PID", str(pid))
    if code != 0:
        if not await asyncio.to_thread(existe, pid):
            _logger.info("processus_deja_disparu", extra={"pid": pid})
            return
        raise DroitsAgentRefuses(f"taskkill a échoué sur {pid} (code {code}) : {sortie.strip()}")


def racine_du_worktree(cwd: str | Path) -> Path | None:
    """The run worktree of `cwd`: its ancestor that is a direct child of `<worktrees>/<project>/`.

    No `.git` lookup: a folder an agent creates cannot move the root (ticket-1015).
    `None` when `cwd` is not at least two levels below a worktrees folder.
    """
    chemin = Path(cwd).resolve()
    for dossier in (settings.ide_worktrees_dir, settings.ide_worktrees_dir_agent):
        base = Path(dossier).resolve()
        if chemin.is_relative_to(base):
            parties = chemin.relative_to(base).parts
            if len(parties) >= 2:
                return base / parties[0] / parties[1]
    return None


_REPARSE_POINT = 0x400


def _verifier_git_sans_lien(racine: Path) -> None:
    """Refuse a `.git` of the root that is a reparse point (junction) or a symlink."""
    git = racine / ".git"
    try:
        etat = git.lstat()
    except FileNotFoundError:
        return
    if getattr(etat, "st_file_attributes", 0) & _REPARSE_POINT or git.is_symlink():
        raise DroitsAgentRefuses(f"{git} est un lien : aucun droit posé")


async def arreter_les_restants(compte: str, enumerer: Enumerer, tuer: Tuer) -> None:
    """Stop every process still owned by `compte`; log each image name."""
    illisibles: ProcessusIllisibles | None = None
    try:
        trouves = await enumerer(compte)
    except ProcessusIllisibles as exc:
        trouves, illisibles = exc.trouves, exc
    for pid, image in trouves:
        _logger.warning("processus_du_compte_restant", extra={"pid": pid, "image": image})
        await tuer(pid)
    if illisibles is not None:
        raise illisibles


def _peut_passer(racine: Path, jeton: object) -> bool:
    """Whether a call on `racine` may start now: same root as the active ones, or nobody active and first in line."""
    if settings.agent_calls_parallel or racine in _ACTIFS:
        return True
    return not _ACTIFS and _FILE[0] is jeton


async def _attendre_son_tour(racine: Path, jeton: object) -> None:
    """Wait (lock held on entry) until `_peut_passer`; log the wait once past a few seconds."""
    journalise = False
    while not _peut_passer(racine, jeton):
        try:
            await asyncio.wait_for(_VERROU.wait(), _ATTENTE_JOURNALISEE_S)
        except TimeoutError:
            if not journalise:
                journalise = True
                _logger.warning("appel_agent_en_attente", extra={"racine": str(racine), "actifs": len(_ACTIFS)})


async def ouvrir_appel(cwd: str | Path, icacls: Icacls = _icacls_reel) -> Path | None:
    """Give the account its write right on the worktree of `cwd`; returns its root.

    One worktree at a time carries calls under the account: a call on another
    root waits, in arrival order, for the active ones to end (several calls on
    the same root overlap). `AGENT_CALLS_PARALLEL=true` lifts the wait. A test
    command or the visual-check app counts as a call: the app holds the account
    for as long as it runs.
    `None` sans `AGENT_USER` : rien n'est posé, rien ne sera retiré.
    """
    compte = settings.agent_user
    if not compte:
        return None
    # Échec fermé : jamais de droit sur un dossier qui n'est pas un worktree de
    # run, le checkout de l'utilisateur en tête (ticket-999, ADR-056).
    racine = racine_du_worktree(cwd)
    if racine is None:
        raise DroitsAgentRefuses(f"{cwd} n'est pas sous le dossier des worktrees : aucun droit posé")
    _verifier_git_sans_lien(racine)
    jeton = object()
    async with _VERROU:
        _FILE.append(jeton)
        try:
            await _attendre_son_tour(racine, jeton)
            if _ACTIFS.get(racine, 0) == 0:
                await poser_ecriture(racine, compte, icacls)
            _ACTIFS[racine] = _ACTIFS.get(racine, 0) + 1
        finally:
            # Annulé ou refusé pendant l'attente : la place se libère, aucun compteur posé.
            _FILE.remove(jeton)
            _VERROU.notify_all()
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
        try:
            await _clore_sous_verrou(racine, compte, icacls, enumerer, tuer)
        finally:
            _VERROU.notify_all()


async def _clore_sous_verrou(
    racine: Path, compte: str, icacls: Icacls, enumerer: Enumerer, tuer: Tuer,
) -> None:
    """Body of `clore_appel`, the condition lock held."""
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
            # Processus arrêtés : plus rien ne tient un fichier du profil (ticket-1008).
            await reinitialiser_profil(compte, icacls)
        except DroitsAgentRefuses as exc:
            erreur = exc
    await retirer_ecriture(racine, compte, icacls)
    if erreur is not None:
        raise erreur
