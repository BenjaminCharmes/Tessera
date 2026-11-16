"""Check the shared toolchain by launching it as the agent account (ADR-086, ticket-983).

``python -m tessera.agent_doctor_cli``, run by ``scripts/tessera.ps1 agent
doctor``. ``Get-Command`` runs under the user's account and says nothing of
what the agent account can execute; this runs ``node``, ``uv`` and ``python``
under ``AGENT_USER`` with the account's own ``PATH``. One line per tool, exit
code 1 at the first failure, and no secret is ever printed. It repairs
nothing: a failure points at ``agent setup``. An agent never runs it (the vault
guard refuses the command).
"""
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from tessera.services.providers.lanceur_agent import LanceurAgent
from tessera.services.verification.lancement_compte import (
    EchecLancementCompte,
    compte_declare,
    lancer_sous_compte,
)

#: Les outils vérifiés, dans l'ordre ; chacun répond à `--version`.
OUTILS: tuple[str, ...] = ("node", "uv", "python")
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


async def _verifier(outil: str, dossier: Path, lanceur: LanceurAgent | None, delai_s: float) -> str | None:
    """Run ``outil --version`` under the account; return None on success, else the cause."""
    processus = None
    try:
        processus = await lancer_sous_compte([outil, "--version"], dossier, None, lanceur)
        await asyncio.wait_for(processus.communicate(), timeout=delai_s)
        if processus.returncode != 0:
            return f"code de sortie {processus.returncode}"
        return None
    except TimeoutError:
        return f"délai de {delai_s:g} s dépassé"
    except EchecLancementCompte as exc:
        return _cause(str(exc))
    except OSError as exc:
        return _cause(str(exc))
    finally:
        if processus is not None:
            await processus.clore()


async def verifier_outils(
    dossier: Path, lanceur: LanceurAgent | None = None,
    outils: Sequence[str] = OUTILS, delai_s: float = DELAI_S,
) -> int:
    """Check each tool in turn, print one line each, and stop at the first failure."""
    if not compte_declare():
        sys.stdout.write(f"AGENT_USER absent : {_CONSEIL}\n")
        return 1
    for outil in outils:
        echec = await _verifier(outil, dossier, lanceur, delai_s)
        if echec is not None:
            sys.stdout.write(f"{outil} : ÉCHEC, {echec} ; {_CONSEIL}\n")
            return 1
        sys.stdout.write(f"{outil} : ok\n")
    return 0


def main() -> int:
    """Entry point: check the tools from the current folder."""
    return asyncio.run(verifier_outils(Path.cwd()))


if __name__ == "__main__":
    sys.exit(main())
