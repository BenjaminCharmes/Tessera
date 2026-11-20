"""The rights of the agent account on a run worktree — ticket-895, ticket-1027.

ADR-083, ADR-091. The CLI runs under `AGENT_USER`; the worktree belongs to the
backend's account. Rules set with `icacls`, never `F` (it includes deleting
children): modify on the worktree for the length of a call, read-only `.git`,
write and delete (fine-grained rights, reading kept) refused on each existing
file that `motif_de_protection` designates (policy files, test script).
Without `AGENT_USER`, nothing is set.
"""
import asyncio
import getpass
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.config import settings
from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.providers.chemins_proteges import motif_de_protection
from tessera.services.providers.script_verification import script_de_verification
from tessera.services.providers.securite_fichiers import SecuriteFichiers, securite_par_defaut
from tessera.services.worktrees.run_worktree import RunWorktree
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Runs `icacls` with these arguments; returns (exit code, output).
Icacls = Callable[[list[str]], Awaitable[tuple[int, str]]]

# Dossiers volumineux sans fichier de politique : on ne les parcourt pas.
_SANS_POLITIQUE = {".git", "node_modules", ".venv"}


class DroitsAgentRefuses(GitWorkspaceError):
    """`icacls` failed: the worktree is not safe to hand to the agent account (ADR-037)."""


async def _icacls_reel(args: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "icacls", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    sortie, _ = await proc.communicate()
    return proc.returncode or 0, sortie.decode(errors="replace")


async def _lancer(lanceur: Icacls, args: list[str]) -> None:
    code, sortie = await lanceur(args)
    if code != 0:
        raise DroitsAgentRefuses(f"icacls a échoué (code {code}) sur {args[0]} : {sortie.strip()}")


#: Écrire, ajouter, changer attributs et attributs étendus, supprimer : les droits
#: précis. Les droits simples `W` et `D` d'icacls portent aussi SYNCHRONIZE, et
#: les refuser interdit d'ouvrir le fichier, même en lecture (ticket-994).
_REFUS_ECRITURE = "(WD,AD,WEA,WA,DE)"


def fichiers_proteges(wt: RunWorktree, script: Path | None) -> list[Path]:
    """Existing files of the worktree that `motif_de_protection` designates."""
    trouves: list[Path] = []
    for dossier, sous_dossiers, fichiers in os.walk(wt.racine):
        sous_dossiers[:] = [d for d in sous_dossiers if d not in _SANS_POLITIQUE]
        for nom in fichiers:
            chemin = Path(dossier) / nom
            if motif_de_protection(str(chemin), wt.projet, wt.racine, script) is not None:
                trouves.append(chemin)
    return trouves


#: OWNER RIGHTS (S-1-3-4) : le propriétaire d'un fichier ne garde que la lecture
#: des droits, donc ni WRITE_DAC ni WRITE_OWNER sur ce que l'agent crée.
OWNER_RIGHTS = "*S-1-3-4:(OI)(CI)(RC)"


#: Fichiers protégés par racine de worktree, notés quand le refus est posé (une
#: fois par run) : la reprise d'un fichier du compte l'efface, on le refuse de nouveau.
_REFUSES: dict[Path, list[Path]] = {}

#: Racines dont la base est posée, par (chemin résolu, st_ctime_ns) : un worktree
#: recréé au même chemin a une autre date de création et repasse par la base.
_BASES: set[tuple[Path, int]] = set()


async def _refuser(fichier: Path, compte: str, lanceur: Icacls) -> None:
    await _lancer(lanceur, [str(fichier), "/deny", f"{compte}:{_REFUS_ECRITURE}", "/L"])


def compte_du_backend() -> str:
    """Name of the account the backend runs under."""
    return getpass.getuser()


async def _proteger_git(git: Path, compte: str, lanceur: Icacls) -> None:
    droit = "(OI)(CI)RX" if git.is_dir() else "RX"
    await _lancer(lanceur, [str(git), "/inheritance:d", "/L"])
    await _lancer(lanceur, [str(git), "/remove:g", compte, "/L"])
    await _lancer(lanceur, [str(git), "/grant:r", f"{compte}:{droit}", "/L"])


def _cle_base(racine: Path) -> tuple[Path, int]:
    return racine.resolve(), racine.stat().st_ctime_ns


async def poser_base(
    racine: Path, compte: str, lanceur: Icacls = _icacls_reel, backend: str | None = None
) -> None:
    """Set once per root what gives `compte` no write right: backend control, OWNER RIGHTS, read-only `.git`.

    L'ACE du backend d'abord : il est propriétaire de la racine et n'y a que
    « modifier » par héritage. OWNER RIGHTS posée en premier lui retirait
    WRITE_DAC, et son propre `/grant` suivant était refusé (preuve du 19/11).
    Idempotente : mémorisée par (chemin résolu, st_ctime_ns de la racine).
    """
    cle = _cle_base(racine)
    if cle in _BASES:
        return
    await _lancer(lanceur, [str(racine), "/grant", f"{backend or compte_du_backend()}:(OI)(CI)F", "/L"])
    await _lancer(lanceur, [str(racine), "/grant", OWNER_RIGHTS, "/L"])
    git = racine / ".git"
    if git.exists():
        await _proteger_git(git, compte, lanceur)
    _BASES.add(cle)


async def poser_ecriture(racine: Path, compte: str, lanceur: Icacls = _icacls_reel) -> None:
    """Give `compte` modify on `racine` (before each call): the only right that lasts one call."""
    await _lancer(lanceur, [str(racine), "/grant", f"{compte}:(OI)(CI)M", "/L"])


async def retirer_ecriture(
    racine: Path, compte: str, lanceur: Icacls = _icacls_reel, backend: str | None = None,
    securite: SecuriteFichiers | None = None,
) -> None:
    """Withdraw the grant of `compte`, then take back what it owns (ticket-943, ticket-1027).

    Le `/remove:g` passe d'abord : le droit est retiré même si la reprise échoue.
    La reprise est ciblée (`reprise_ciblee`) ; le `.git` de la racine reste en
    lecture seule, sans y toucher. Le refus d'écriture d'un fichier protégé que
    la reprise a remis à l'héritage est reposé (fail closed).
    """
    # Import local : `reprise_ciblee` importe `DroitsAgentRefuses` de ce module.
    from tessera.services.providers.reprise_ciblee import reprendre_arbre

    await _lancer(lanceur, [str(racine), "/remove:g", compte, "/L"])
    reprises = await reprendre_arbre(
        racine, compte, backend or compte_du_backend(), securite or securite_par_defaut(), {racine / ".git"}
    )
    for fichier in _REFUSES.get(racine.resolve(), []):
        if fichier in reprises:
            await _refuser(fichier, compte, lanceur)


async def accorder_droits_agent(
    wt: RunWorktree,
    commande_de_tests: str | None,
    lanceur: Icacls = _icacls_reel,
) -> None:
    """Set the rules on `wt` when `AGENT_USER` is set; otherwise do nothing."""
    compte = settings.agent_user
    if not compte:
        return
    await poser_base(wt.racine, compte, lanceur)
    await poser_ecriture(wt.racine, compte, lanceur)
    script = script_de_verification(wt.projet, commande_de_tests)
    proteges = fichiers_proteges(wt, script)
    _REFUSES[wt.racine.resolve()] = proteges
    for fichier in proteges:
        await _refuser(fichier, compte, lanceur)
    _logger.info("droits_agent_poses", extra={"racine": str(wt.racine)})
