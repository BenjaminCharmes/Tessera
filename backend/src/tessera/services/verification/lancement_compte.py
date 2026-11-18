"""Start a run's processes under the dedicated account — ticket-934, ADR-085.

Quand le projet a déclaré `worktree.compte_agent` et que `AGENT_USER` est
renseigné, la commande de test et l'app du contrôle visuel partent par le
`LanceurAgent` du CLI (ADR-083), jamais sous le compte du backend. Tout échec
est un `EchecLancementCompte` : aucun repli (ADR-037).

Le lanceur Windows place chaque processus dans un job `KILL_ON_JOB_CLOSE`
(ticket-943) ; `clore()` le ferme et retire le droit d'écriture du compte sur
le worktree. La lecture des tubes comme l'attente sont bornées par l'appelant
(`wait_for`, minuteur d'étape).
"""
import asyncio
import ntpath
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from anyio import EndOfStream
from anyio.abc import ByteReceiveStream, Process

from tessera.config import settings
from tessera.services.providers.droits_appel import clore_appel, ouvrir_appel
from tessera.services.providers.env_agent import env_du_profil
from tessera.services.providers.lanceur_agent import LanceurAgent
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.path_compte import ChaineAbsente, path_du_compte, resoudre_executable
from tessera.services.providers.process_agent import ProcessAgent
from tessera.services.providers.transport_agent import fabriquer_lanceur
from tessera.services.verification.env_du_code_de_projet import est_un_nom_de_secret
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Les seuls noms repris du backend : de quoi trouver les outils. Le dossier
#: temporaire vient du profil du compte (ticket-988) ; le reste de
#: l'environnement du backend n'atteint pas le compte.
_NOMS_REPRIS = frozenset({"pathext", "systemroot", "windir", "comspec"})

#: Les noms que le profil du compte fixe et qu'aucun `extra` ne remplace.
_DU_PROFIL = frozenset(env_du_profil("x"))


class EchecLancementCompte(ProviderIndisponible):
    """The command could not start under the dedicated account."""


def compte_declare() -> bool:
    """True when ``AGENT_USER`` is set."""
    return bool(settings.agent_user)


def env_du_compte(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build the environment from nothing: the allow-list, then ``extra``, no secret."""
    if any(nom.lower() == "path" for nom in (extra or {})):
        raise EchecLancementCompte("`worktree.env` ne peut pas porter PATH : il vient de la chaîne d'outils (ADR-086)")
    base = {nom: val for nom, val in os.environ.items() if nom.lower() in _NOMS_REPRIS}
    base.update(env_du_profil(settings.agent_user or ""))
    try:
        base["PATH"] = path_du_compte()
    except ChaineAbsente as exc:
        raise EchecLancementCompte(str(exc)) from exc
    # Un `extra` déclaré ne ramène pas le dossier temporaire chez l'utilisateur.
    base.update({k: v for k, v in (extra or {}).items() if k not in _DU_PROFIL})
    # Repasse par le filtre des secrets : un `extra` déclaré ne les réintroduit pas.
    return {nom: val for nom, val in base.items() if not est_un_nom_de_secret(nom)}


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

    def __init__(self, processus: Process, racine_droits: Path | None = None) -> None:
        self._processus = processus
        self._racine_droits = racine_droits

    async def clore(self) -> None:
        """Ends the call: closes the process's job, withdraws the write right (ticket-943).

        Idempotent. Un refus lève `DroitsAgentRefuses` : le run passe en `blocked`.
        """
        racine, self._racine_droits = self._racine_droits, None
        if isinstance(self._processus, ProcessAgent):
            await self._processus.aclose()
        await clore_appel(racine)

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
    racine_droits = await ouvrir_appel(dossier)
    try:
        return await _lancer_les_formes(lance, args, dossier, env, racine_droits)
    except BaseException:
        await clore_appel(racine_droits)
        raise


async def _lancer_les_formes(
    lance: LanceurAgent, args: Sequence[str], dossier: Path,
    env: Mapping[str, str] | None, racine_droits: Path | None,
) -> ProcessusDuCompte:
    compte = settings.agent_user or ""
    mot_de_passe = settings.agent_logon_password.get_secret_value()
    environnement = env_du_compte(env)
    commande = _commande_resolue(args, environnement)
    try:
        _logger.info("processus_lance_sous_compte", extra={"compte": compte})
        processus = await lance.lancer(
            commande, compte=compte, mot_de_passe=mot_de_passe,
            env=environnement, cwd=str(dossier), avec_stderr=True,
        )
    except (ProviderIndisponible, OSError) as exc:
        raise EchecLancementCompte(str(exc)) from exc
    return ProcessusDuCompte(processus, racine_droits)


def _commande_resolue(args: Sequence[str], env: Mapping[str, str]) -> list[str]:
    """Replace a bare program name by its file in the account's ``PATH`` (ticket-986).

    Un nom nu serait cherché par Windows dans le PATH du backend : `node` y
    désigne celui du profil, que le compte ne peut pas exécuter. Introuvable
    dans le PATH du compte, il ne part pas (ADR-037, ADR-086). Un chemin qui
    porte un dossier passe tel quel.
    """
    if not args:
        raise EchecLancementCompte("commande vide")
    nom = args[0]
    if ntpath.dirname(nom) or os.path.dirname(nom):
        return list(args)
    chemin = next((val for cle, val in env.items() if cle.lower() == "path"), "")
    trouve = resoudre_executable(nom, chemin)
    if trouve is None:
        raise EchecLancementCompte(
            f"`{nom}` introuvable dans le PATH du compte agent (chaîne d'outils, ADR-086)"
        )
    return [trouve, *args[1:]]
