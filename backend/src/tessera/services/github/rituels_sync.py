"""Ritual state shared between PCs through a file on a GitHub branch — ticket-905.

`rituels-etat.json` on the `etat-rituels` branch holds only the ids and the two
dates of each ritual. State only moves forward: per id, the latest `fait_le`
and the latest `reporte_jusqua` win. Without token, network or rights, the
local state stands and the answer says `locale`.
"""
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, ValidationError

from tessera.config import _REPO_ROOT, settings
from tessera.services.github.github_contents import ConflitContenu, ErreurContenu, FichierDistant, GitHubContents
from tessera.services.noyau.git_commande import build_command
from tessera.services.projets import rituels as local
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

BRANCHE = "etat-rituels"
CHEMIN = "rituels-etat.json"
INTERVALLE_S = 60.0

Synchro = Literal["github", "locale"]
Etats = dict[str, tuple[datetime | None, datetime | None]]


class EtatRituel(BaseModel):
    fait_le: datetime | None = None
    reporte_jusqua: datetime | None = None


class EtatDistant(BaseModel):
    version: Literal[1] = 1
    rituels: dict[str, EtatRituel] = {}


class Distant(Protocol):
    async def lire_fichier(self, chemin: str, branche: str) -> FichierDistant | None: ...
    async def ecrire_fichier(
        self, chemin: str, branche: str, contenu: str, message: str, sha: str | None
    ) -> None: ...
    async def creer_branche(self, branche: str) -> None: ...


_URL_GITHUB = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$"
)
# Mémoire de l'origin : lu une seule fois, `None` compris.
_origin: tuple[str | None] | None = None
_avertis: set[str] = set()


def depot_de_l_url(url: str) -> str | None:
    """`owner/repo` of a GitHub HTTPS or SSH URL, None for any other form."""
    trouve = _URL_GITHUB.match(url.strip())
    return f"{trouve.group(1)}/{trouve.group(2)}" if trouve else None


def lire_origin() -> str | None:
    """URL of `origin` in the Tessera repository; None when git or the remote is missing."""
    try:
        sortie = subprocess.run(
            build_command(("remote", "get-url", "origin")),
            cwd=_REPO_ROOT, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return sortie.stdout.strip() if sortie.returncode == 0 else None


def _depot() -> str | None:
    """The configured repository, else the one of `origin`, read once."""
    global _origin
    if settings.github_repo:
        return settings.github_repo
    if _origin is None:
        url = lire_origin()
        _origin = (depot_de_l_url(url) if url else None,)
    return _origin[0]


def _avertir_une_fois(raison: str) -> None:
    if raison not in _avertis:
        _avertis.add(raison)
        _logger.warning("rituels_synchro_inactive", extra={"raison": raison})


def creer_service() -> Distant | None:
    """The GitHub client, or None without token or repository (warned once)."""
    if not settings.github_token:
        _avertir_une_fois("sans_jeton")
        return None
    depot = _depot()
    if depot is None:
        _avertir_une_fois("sans_depot")
        return None
    return GitHubContents(settings.github_token, depot)


def _plus_recent(a: datetime | None, b: datetime | None) -> datetime | None:
    if a is None or b is None:
        return a or b
    return max(a, b)


def fusionner(a: Etats, b: Etats) -> Etats:
    """Per id, the latest `fait_le` and the latest `reporte_jusqua` of both sides."""
    fusion: Etats = {}
    for identifiant in a.keys() | b.keys():
        fa, ra = a.get(identifiant, (None, None))
        fb, rb = b.get(identifiant, (None, None))
        fusion[identifiant] = (_plus_recent(fa, fb), _plus_recent(ra, rb))
    return fusion


def _lire(fichier: FichierDistant | None) -> Etats:
    if fichier is None:
        return {}
    etat = EtatDistant.model_validate_json(fichier.contenu)
    return {i: (e.fait_le, e.reporte_jusqua) for i, e in etat.rituels.items()}


def _serialiser(etats: Etats) -> str:
    etat = EtatDistant(
        rituels={i: EtatRituel(fait_le=f, reporte_jusqua=r) for i, (f, r) in etats.items()}
    )
    return json.dumps(etat.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


async def _tirer_et_fusionner(db_path: Path | str, svc: Distant) -> Etats:
    distant = _lire(await svc.lire_fichier(CHEMIN, BRANCHE))
    fusion = fusionner(await local.lire_etats(db_path), distant)
    await local.ecrire_etats(db_path, fusion)
    return fusion


async def _pousser(db_path: Path | str, svc: Distant) -> None:
    """Merge then PUT; a stale `sha` rereads, remerges and retries once."""
    await svc.creer_branche(BRANCHE)
    for tentative in (1, 2):
        fichier = await svc.lire_fichier(CHEMIN, BRANCHE)
        fusion = fusionner(await local.lire_etats(db_path), _lire(fichier))
        try:
            await svc.ecrire_fichier(
                CHEMIN, BRANCHE, _serialiser(fusion), "chore: ritual state",
                fichier.sha if fichier else None,
            )
        except ConflitContenu:
            if tentative == 2:
                raise
            continue
        await local.ecrire_etats(db_path, fusion)
        return


_ERREURS = (httpx.HTTPError, ErreurContenu, ConflitContenu, ValidationError, ValueError, TypeError)
# Mémoire de la dernière lecture : (instant, base, résultat).
_memo: tuple[float, str, Synchro] | None = None


def reinitialiser() -> None:
    """Forget the last pull (tests, and after a push)."""
    global _memo
    _memo = None


def oublier_depot() -> None:
    """Forget the origin read and the warnings already given (tests)."""
    global _origin
    _origin = None
    _avertis.clear()


async def tirer(db_path: Path | str) -> Synchro:
    """Merge the remote state into the local one, at most once a minute."""
    global _memo
    maintenant = time.monotonic()
    if _memo and _memo[1] == str(db_path) and maintenant - _memo[0] < INTERVALLE_S:
        return _memo[2]
    svc = creer_service()
    resultat: Synchro = "locale"
    if svc is not None:
        try:
            await _tirer_et_fusionner(db_path, svc)
            resultat = "github"
        except _ERREURS as exc:
            _logger.warning("rituels_synchro_lecture_echec", extra={"erreur": type(exc).__name__})
    _memo = (maintenant, str(db_path), resultat)
    return resultat


async def pousser(db_path: Path | str) -> Synchro:
    """Push the merged state after a `fait` or `reporter`; never raises."""
    svc = creer_service()
    if svc is None:
        return "locale"
    try:
        await _pousser(db_path, svc)
    except _ERREURS as exc:
        _logger.warning("rituels_synchro_ecriture_echec", extra={"erreur": type(exc).__name__})
        return "locale"
    reinitialiser()
    return "github"
