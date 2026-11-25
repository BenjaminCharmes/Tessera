"""The profile of the agent account is wiped between calls — ticket-1008.

ADR-087. `~/.bashrc`, `~/.npmrc`, `uv.toml` ou un `.pth` écrits par un appel ne
doivent pas survivre jusqu'au suivant. Tout le dossier de profil est supprimé,
sauf `npm-cache` ; le dossier est recréé et le compte retrouve
`M` dessus. Aucun lien (jonction, lien symbolique) n'est suivi : il se retire
lui-même. npm vérifie l'intégrité de ce qu'il sort de son cache, donc il
survit ; uv ne revérifie pas un paquet décompressé, son cache part (ticket-1019,
ADR-088). Un échec est une `DroitsAgentRefuses` (ADR-037). Avant la purge, le dossier
revient au backend par reprise ciblée (`reprendre_arbre`, ADR-091) : le compte,
propriétaire de ce qu'il crée, ne peut pas piéger la purge (ticket-1014, ticket-1028).
"""
import asyncio
import ntpath
import os
import stat
from pathlib import Path

from tessera.services.providers.droits_worktree import OWNER_RIGHTS, DroitsAgentRefuses, Icacls, _icacls_reel, _lancer, compte_du_backend
from tessera.services.providers.env_agent import CACHE_NPM, PROFIL_AGENT, env_du_profil
from tessera.services.providers.reprise_ciblee import reprendre_arbre
from tessera.services.providers.securite_fichiers import SecuriteFichiers, securite_par_defaut
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

DOSSIER_PROFIL = Path(PROFIL_AGENT)
#: Attribut Windows d'un lien (jonction, lien symbolique) ; `stat` ne le porte que sous Windows.
_REPARSE_POINT = 0x400
#: Chemins relatifs qui survivent au nettoyage.
_GARDES: tuple[tuple[str, ...], ...] = (
    (CACHE_NPM,),
)


def _est_un_lien(chemin: Path) -> bool:
    """Whether `chemin` is a symlink or a junction (never followed)."""
    attributs = getattr(os.lstat(chemin), "st_file_attributes", 0)
    return chemin.is_symlink() or bool(attributs & _REPARSE_POINT)


def _retirer(chemin: Path) -> None:
    """Remove a file, a link, or a real folder with its content."""
    if _est_un_lien(chemin):
        # Un lien vers un dossier se retire par `rmdir`, jamais en le parcourant.
        if chemin.is_dir():
            os.rmdir(chemin)
        else:
            os.unlink(chemin)
    elif chemin.is_dir():
        for enfant in list(chemin.iterdir()):
            _retirer(enfant)
        os.rmdir(chemin)
    else:
        os.chmod(chemin, stat.S_IWRITE)
        os.unlink(chemin)


def _purger(dossier: Path, gardes: tuple[tuple[str, ...], ...]) -> None:
    """Remove everything under `dossier` except the kept relative paths."""
    for enfant in list(dossier.iterdir()):
        suite = [g[1:] for g in gardes if g[0] == enfant.name]
        # Un lien ne se garde jamais, même sous le nom d'un cache.
        if not suite or _est_un_lien(enfant):
            _retirer(enfant)
        elif all(suite) and enfant.is_dir():
            # Un garde plus profond (`a\b`) : on descend, le reste part.
            _purger(enfant, tuple(suite))
        # Sinon le chemin entier est gardé (`suite` contient ()).


def _vider(profil: Path) -> None:
    try:
        _purger(_prefixe_long(profil), _GARDES)
    except OSError as exc:
        raise DroitsAgentRefuses(f"profil de l'agent non nettoyé ({profil}) : {exc}") from exc


def _recreer(profil: Path) -> None:
    """Recreate the folders that `TEMP`, `APPDATA` and `LOCALAPPDATA` point to, from `env_du_profil`."""
    env = env_du_profil("")
    try:
        for cle in ("TEMP", "APPDATA", "LOCALAPPDATA"):
            # Chemins Windows, lus aussi sous Linux (CI) : `ntpath`, jamais `Path`.
            relatif = ntpath.relpath(env[cle], PROFIL_AGENT).split("\\")
            profil.joinpath(*relatif).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DroitsAgentRefuses(f"profil de l'agent non recréé ({profil}) : {exc}") from exc


def nettoyage_en_echec() -> bool:
    """Whether the last profile wipe failed (ticket-1014): the next call is refused."""
    return _NETTOYAGE_ECHOUE


#: Tant que le dernier nettoyage a échoué, `ouvrir_appel` refuse : un profil
#: piégé ne sert jamais à un autre run. Remis à zéro par un nettoyage réussi.
_NETTOYAGE_ECHOUE = False


_PREFIXE_LONG = "\\\\?\\"


def _prefixe_long(chemin: Path) -> Path:
    """The extended-length form of `chemin` under Windows (reserved names, over 260 characters); unchanged elsewhere."""
    if os.name != "nt":
        return chemin
    absolu = os.path.abspath(chemin)
    return chemin if absolu.startswith(_PREFIXE_LONG) else Path(_PREFIXE_LONG + absolu)


async def _reprendre_la_main(
    dossier: Path, compte: str, backend: str, securite: SecuriteFichiers,
) -> bool:
    """Take back what the account owns under `dossier`; `True` when the root itself had to be taken back.

    Le compte n'a que `RC` (OWNER RIGHTS) sur la racine : il n'en change ni le
    propriétaire ni la DACL. Une racine à son nom ou à DACL protégée est donc
    l'indice d'une altération, reprise puis redonnée. Les autres entrées passent
    par `reprendre_arbre` (aucun lien suivi, refus nommant le chemin).
    """
    await reprendre_arbre(dossier, compte, backend, securite)
    racine = await asyncio.to_thread(_racine_a_reprendre, dossier, compte, backend, securite)
    return racine


def _racine_a_reprendre(dossier: Path, compte: str, backend: str, securite: SecuriteFichiers) -> bool:
    try:
        info = securite.lire(dossier)
        if info.proprietaire_sid != securite.sid_de(compte) and not info.dacl_protegee:
            return False
        securite.reprendre(dossier, securite.sid_de(backend), proprietaire_seul=False)
    except OSError as exc:
        raise DroitsAgentRefuses(f"racine du profil non reprise ({dossier}) : {type(exc).__name__}") from exc
    return True


async def _redonner_au_compte(dossier: Path, compte: str, icacls: Icacls, backend: str) -> None:
    """Lay the rights again: backend first (OWNER RIGHTS would take its WRITE_DAC), then the account, then OWNER RIGHTS.

    Le compte ne porte `M` que sur le contenu ; sur le dossier lui-même, lecture
    et création, sans `DELETE` : il ne peut pas le déplacer.
    """
    cible = str(dossier)
    await _lancer(icacls, [cible, "/grant", f"{backend}:(OI)(CI)F", "/L"])
    await _lancer(icacls, [cible, "/grant", f"{compte}:(OI)(CI)(IO)M", "/L"])
    await _lancer(icacls, [cible, "/grant", f"{compte}:(RX,WD,AD)", "/L"])
    await _lancer(icacls, [cible, "/grant", OWNER_RIGHTS, "/L"])


async def reinitialiser_profil(
    compte: str, icacls: Icacls = _icacls_reel, profil: Path | None = None, backend: str | None = None,
    securite: SecuriteFichiers | None = None,
) -> None:
    """Take the agent profile back, wipe it except the npm cache, recreate it, give `compte` its rights.

    La racine garde sa DACL : les quatre droits ne se reposent que si elle a été reprise.

    Un dossier absent est une `DroitsAgentRefuses` : l'appel suivant partirait
    avec un `HOME` qui n'existe pas. Tout échec lève le drapeau
    `nettoyage_en_echec`, qu'un nettoyage réussi remet à zéro.
    """
    global _NETTOYAGE_ECHOUE
    dossier = profil or DOSSIER_PROFIL
    try:
        if not dossier.is_dir():
            raise DroitsAgentRefuses(f"profil de l'agent absent ({dossier}) : agent setup à relancer")
        proprietaire = backend or compte_du_backend()
        racine_reprise = await _reprendre_la_main(dossier, compte, proprietaire, securite or securite_par_defaut())
        await asyncio.to_thread(_vider, dossier)
        await asyncio.to_thread(_recreer, dossier)
        if racine_reprise:
            await _redonner_au_compte(dossier, compte, icacls, proprietaire)
    except DroitsAgentRefuses:
        _NETTOYAGE_ECHOUE = True
        raise
    _NETTOYAGE_ECHOUE = False
