"""Start a run's processes under the dedicated account — ticket-934, ADR-085.

Quand le projet a déclaré `worktree.compte_agent` et que `AGENT_USER` est
renseigné, la commande de test et l'app du contrôle visuel partent par le
`LanceurAgent` du CLI (ADR-083), jamais sous le compte du backend. Tout échec
est un `EchecLancementCompte` : aucun repli (ADR-037).

Le lanceur Windows ne crée pas de job : `kill()` ne coupe que le processus
direct, et la lecture des tubes comme l'attente sont bornées par l'appelant
(`wait_for`, minuteur d'étape).
"""
import asyncio
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from anyio import EndOfStream
from anyio.abc import ByteReceiveStream, Process

from tessera.config import settings
from tessera.services.noyau.lancement import essais_de_commande
from tessera.services.providers.lanceur_agent import LanceurAgent
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.transport_agent import fabriquer_lanceur
from tessera.services.verification.env_du_code_de_projet import env_du_code_de_projet
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Les seuls noms repris du backend : de quoi trouver les outils et un dossier
#: temporaire. Le reste de l'environnement du backend n'atteint pas le compte.
_NOMS_REPRIS = frozenset(
    {"path", "pathext", "systemroot", "windir", "comspec", "temp", "tmp"}
)


class EchecLancementCompte(ProviderIndisponible):
    """The command could not start under the dedicated account."""


def compte_declare() -> bool:
    """True when ``AGENT_USER`` is set."""
    return bool(settings.agent_user)


def env_du_compte(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build the environment from nothing: the allow-list, then ``extra``, no secret."""
    base = {nom: val for nom, val in os.environ.items() if nom.lower() in _NOMS_REPRIS}
    base.update(extra or {})
    # Repasse par le filtre des secrets : un `extra` déclaré ne les réintroduit pas.
    sans_secret = env_du_code_de_projet(base)
    return {nom: sans_secret[nom] for nom in base if nom in sans_secret}


async def _lire(flux: ByteReceiveStream | None) -> bytes:
    """Read a pipe to its end."""
    if flux is None:
        return b""
    morceaux: list[bytes] = []
    while True:
        try:
            morceaux.append(await flux.receive())
        except EndOfStream:
            return b"".join(morceaux)


class ProcessusDuCompte:
    """The surface of an asyncio process, over a process started under the account."""

    def __init__(self, processus: Process) -> None:
        self._processus = processus

    @property
    def pid(self) -> int:
        return self._processus.pid

    @property
    def returncode(self) -> int | None:
        return self._processus.returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        """Close stdin, read both pipes to their end, then wait for the exit."""
        if self._processus.stdin is not None:
            await self._processus.stdin.aclose()
        sortie, erreur = await asyncio.gather(
            _lire(self._processus.stdout), _lire(self._processus.stderr)
        )
        await self._processus.wait()
        return sortie, erreur

    async def wait(self) -> int:
        return await self._processus.wait()

    def kill(self) -> None:
        self._processus.kill()

    def terminate(self) -> None:
        self._processus.terminate()


async def lancer_sous_compte(
    args: Sequence[str],
    dossier: Path,
    env: Mapping[str, str] | None = None,
    lanceur: LanceurAgent | None = None,
) -> ProcessusDuCompte:
    """Start ``args`` in ``dossier`` under ``AGENT_USER``; never under the backend's."""
    compte = settings.agent_user
    mot_de_passe = settings.agent_logon_password.get_secret_value()
    if not compte:
        raise EchecLancementCompte("AGENT_USER absent : rien ne démarre sous le compte du backend")
    if not mot_de_passe:
        raise EchecLancementCompte("AGENT_LOGON_PASSWORD absent : le processus ne peut pas démarrer")
    try:
        lance = lanceur or fabriquer_lanceur()
    except ProviderIndisponible as exc:
        raise EchecLancementCompte(str(exc)) from exc
    derniere: Exception | None = None
    # Les formes de `essais_de_commande` (`npm`, puis `npm.cmd`) : le lanceur ne
    # distingue pas « introuvable » d'un logon refusé, on tente donc chacune.
    for tentative in essais_de_commande(list(args)):
        try:
            _logger.info("processus_lance_sous_compte", extra={"compte": compte})
            processus = await lance.lancer(
                tentative, compte=compte, mot_de_passe=mot_de_passe,
                env=env_du_compte(env), cwd=str(dossier), avec_stderr=True,
            )
        except (ProviderIndisponible, OSError) as exc:
            derniere = exc
            continue
        return ProcessusDuCompte(processus)
    raise EchecLancementCompte(str(derniere or "commande vide")) from derniere
