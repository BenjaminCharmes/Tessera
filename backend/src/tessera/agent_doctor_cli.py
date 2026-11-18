"""Check the shared toolchain by launching it as the agent account (ADR-086, ticket-983).

``python -m tessera.agent_doctor_cli``, run by ``scripts/tessera.ps1 agent
doctor``. ``Get-Command`` runs under the user's account and says nothing of
what the agent account can execute; this runs ``node``, ``uv`` and ``python``
under ``AGENT_USER`` with the account's own ``PATH``, plus ``npm config get
cache``, which must stay in the agent's profile (ticket-988). One line per tool, exit
code 1 at the first failure, and no secret is ever printed. It repairs
nothing: a failure points at ``agent setup``. An agent never runs it (the vault
guard refuses the command).
"""
import asyncio
import ntpath
import sys
from collections.abc import Sequence
from pathlib import Path

from tessera.config import settings
from tessera.services.providers.env_agent import profil_de
from tessera.services.providers.lanceur_agent import LanceurAgent
from tessera.services.verification.lancement_compte import EchecLancementCompte, compte_declare, lancer_sous_compte

#: Les vérifications, dans l'ordre : aucun `python.exe` n'est sur le PATH du
#: compte (ticket-986), Python se lance donc par `uv run`.
OUTILS: tuple[tuple[str, ...], ...] = (
    ("node", "--version"),
    ("uv", "--version"),
    ("uv", "run", "--no-project", "python", "--version"),
    ("npm", "config", "get", "cache"),
)
DELAI_S = 20.0
_CONSEIL = "lancer `agent setup`"


def _cause(message: str) -> str:
    """Name the likely cause of a launch failure, without echoing the raw text."""
    bas = message.lower()
    if "eperm" in bas or "operation not permitted" in bas or "accès refusé" in bas or "access is denied" in bas:
        return "EPERM (droit d'exécution refusé au compte)"
    if "logon" in bas or "1326" in bas or "mot de passe" in bas or "password" in bas:
        return "logon refusé ou mot de passe absent"
    if "introuvable" in bas or "not found" in bas or "no such file" in bas or "chaîne d'outils" in bas:
        return "introuvable sur le PATH du compte"
    return "échec de lancement"


def _cache_npm_hors_profil(sortie: bytes) -> str | None:
    """Return a failure when npm's cache is not under the agent's own profile (ticket-988)."""
    valeur = sortie.decode("utf-8", errors="replace").strip().splitlines()
    cache = valeur[-1].strip() if valeur else ""
    profil = ntpath.normcase(ntpath.normpath(profil_de(settings.agent_user or "")))
    norme = ntpath.normcase(ntpath.normpath(cache)) if cache else ""
    if norme == profil or norme.startswith(profil + "\\"):
        return None
    return "cache npm hors du profil de l'agent"


async def _verifier(commande: Sequence[str], dossier: Path, lanceur: LanceurAgent | None, delai_s: float) -> str | None:
    """Run the command under the account; return None on success, else the cause."""
    processus = None
    try:
        processus = await lancer_sous_compte(list(commande), dossier, None, lanceur)
        sortie, _ = await asyncio.wait_for(processus.communicate(), timeout=delai_s)
        if processus.returncode != 0:
            return f"code de sortie {processus.returncode}"
        if commande[:3] == ("npm", "config", "get"):
            return _cache_npm_hors_profil(sortie)
        return None
    except TimeoutError:
        return f"délai de {delai_s:g} s dépassé"
    except (EchecLancementCompte, OSError) as exc:
        return _cause(str(exc))
    finally:
        if processus is not None:
            await processus.clore()


def _libelle(commande: Sequence[str]) -> str:
    """Name a check on its output line."""
    if commande[0] == "npm":
        return "npm cache"
    return "python (uv run)" if "python" in commande else commande[0]


async def verifier_outils(
    dossier: Path, lanceur: LanceurAgent | None = None,
    outils: Sequence[tuple[str, ...]] = OUTILS, delai_s: float = DELAI_S,
) -> int:
    """Check each command in turn, print one line each, and stop at the first failure."""
    if not compte_declare():
        sys.stdout.write(f"AGENT_USER absent : {_CONSEIL}" + chr(10))
        return 1
    for commande in outils:
        libelle = _libelle(commande)
        echec = await _verifier(commande, dossier, lanceur, delai_s)
        if echec is not None:
            sys.stdout.write(f"{libelle} : ÉCHEC, {echec} ; {_CONSEIL}" + chr(10))
            return 1
        sys.stdout.write(f"{libelle} : ok" + chr(10))
    return 0


def main() -> int:
    """Entry point: check the tools from the current folder."""
    return asyncio.run(verifier_outils(Path.cwd()))


if __name__ == "__main__":
    sys.exit(main())
