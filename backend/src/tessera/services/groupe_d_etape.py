"""A process group per test step, closed when the step ends — ticket-507.

`proc.kill()` ne termine que le processus direct. Sous Windows, ses
descendants (`corepack`, puis `prisma`) survivaient et gardaient les tubes
stdout/stderr ouverts : `proc.wait()` ne revenait jamais, et une file est
restée figée soixante-dix minutes malgré `test_timeout_s`.

Le groupe est celui des services (`groupe_de_processus`) : un job Windows hérité
par toute la descendance, un groupe de processus sous Unix. Il est propre à
l'étape — jamais le job du backend, tué à sa fermeture seulement.
"""
import asyncio
import os

from tessera.services import groupe_de_processus
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Temps laissé au processus pour se terminer une fois son arbre tué. Passé ce
#: délai l'étape rend quand même son résultat : aucune attente non bornée ne
#: doit survivre à un timeout.
DELAI_ATTENTE_FIN_S = 5.0

_SIGKILL = 9


class GroupeDEtape:
    """Groups one step's processes so that closing it ends them all."""

    def __init__(self) -> None:
        self._groupe = groupe_de_processus.creer_groupe()
        self._rattache = False
        if self._groupe is None and groupe_de_processus.groupe_disponible():
            _logger.warning("etape_sans_groupe")

    def rattacher(self, pid: object) -> bool:
        """Put the process in the group; ``False`` leaves the step ungrouped."""
        if self._groupe is None or not isinstance(pid, int):
            return False
        self._rattache = groupe_de_processus.rattacher_au_groupe(self._groupe, pid)
        return self._rattache

    def fermer(self) -> bool:
        """Close the group, once; ``True`` when that ended a grouped tree."""
        groupe, self._groupe = self._groupe, None
        if groupe is None:
            return False
        ferme = groupe_de_processus.fermer_le_groupe(groupe)
        return ferme and self._rattache

    async def terminer(self, proc: asyncio.subprocess.Process) -> None:
        """Kill the step's whole tree, then wait for its end for a bounded time."""
        if not self.fermer():
            await _tuer_sans_groupe(proc.pid)
        try:
            proc.kill()
            await asyncio.wait_for(proc.wait(), timeout=DELAI_ATTENTE_FIN_S)
        except Exception as exc:  # noqa: BLE001 — le résultat d'expiration prime
            _logger.warning("etape_fin_non_attendue", extra={"erreur": str(exc)})


async def _tuer_sans_groupe(pid: object) -> None:
    """Best-effort tree kill when the step has no group to close."""
    if not isinstance(pid, int):
        return
    if os.name == "nt":
        await groupe_de_processus.tuer_l_arbre(pid)
        return
    # `getattr` : ces appels n'existent pas sous Windows (mypy y analyse).
    killpg = getattr(os, "killpg", None)
    getpgid = getattr(os, "getpgid", None)
    if killpg is None or getpgid is None:
        return
    try:
        # Lancée avec `start_new_session`, l'étape est chef de son groupe ;
        # jamais le nôtre, qui tuerait le backend.
        if getpgid(pid) != getpgid(0):
            killpg(pid, _SIGKILL)
    except OSError as exc:
        _logger.warning("arbre_non_tue", extra={"pid": pid, "erreur": str(exc)})
