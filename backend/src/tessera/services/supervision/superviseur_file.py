"""The supervisor reopens a queue cut by the infrastructure — ticket-858, ADR-080.

No model. A queue stops with a line « file interrompue : … » in the pipeline
log. This module classifies the cause from that line: a network, git or sleep
cut (`infrastructure`) is a mishap, a verdict (« non approuvé ») is a quality
decision, a missing ticket is a ticket to fix. Only `infrastructure`, and only
when the project declared `relance_file` (ticket-852), reopens the remaining
tickets, through the entry that starts a queue (ADR-041).

One relaunch per cause and per queue: a reopened queue cut again by the same
cause goes to « À toi », never to a third attempt (ADR-078). The daily spend
and the real quota are read first, as between two tickets of an autonomous run
(ADR-020); an unknown quota never blocks. Nothing here starts a queue nobody
had opened: the caller names the interrupted queue and what it still held.
"""
import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.services.livraison.controle_tete import decrire_exception
from tessera.services.supervision.superviseur_actions import Action, Decision, Verdict
from tessera.services.supervision.superviseur_pr import cause_de_l_arret
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

Cause = Literal["infrastructure", "verdict", "introuvable", "inconnue"]

#: Rouvre une file : (projet, tickets restants) -> identifiant du nouveau run.
Rouvrir = Callable[[str, list[str]], Awaitable[str]]

_MARQUE = "file interrompue :"
_LIGNE = re.compile(r"^- .*?\[(?P<projet>[^\]]+)\]\s*file interrompue\s*:\s*(?P<raison>.*)$")
# Une décision de qualité se lit avant tout : « non approuvé » ne se relance jamais.
_MARQUES_VERDICT = ("non approuvé", "non approuve", "not approved", "unapproved")
_MARQUES_INTROUVABLE = ("introuvable", "not found")
# L'argent et l'arrêt demandé ne sont pas des pannes : ils restent à l'humain.
_MARQUES_HUMAINES = ("plafond", "budget", "quota", "arrêt demandé", "arret demande")


@dataclass(frozen=True)
class FileCoupee:
    """A queue that stopped early: its run, the log line, the tickets it had left."""

    project_id: str
    run_id: str
    ligne: str
    restants: tuple[str, ...]


def raison_de_l_interruption(ligne: str) -> str:
    """The reason carried by a `file interrompue : …` log line, or the whole line."""
    trouve = _LIGNE.match(ligne.strip())
    if trouve is not None:
        return trouve.group("raison").strip()
    avant, marque, apres = ligne.partition(_MARQUE)
    return apres.strip() if marque else avant.strip()


def classer_interruption(ligne: str) -> Cause:
    """Classify why a queue stopped, from its pipeline log line.

    Fail closed: a line that names a verdict, a missing ticket, money or a
    requested stop is never `infrastructure`, even if it also names a network.
    """
    texte = raison_de_l_interruption(ligne).casefold()
    if any(marque in texte for marque in _MARQUES_VERDICT):
        return "verdict"
    if any(marque in texte for marque in _MARQUES_INTROUVABLE):
        return "introuvable"
    if any(marque in texte for marque in _MARQUES_HUMAINES):
        return "inconnue"
    if cause_de_l_arret(texte) == "infrastructure":
        return "infrastructure"
    return "inconnue"


def interruptions_du_journal(journal: str, project_id: str) -> list[str]:
    """The `file interrompue` lines of `project_id` in a pipeline log, oldest first."""
    lignes = (_LIGNE.match(brut.strip()) for brut in journal.splitlines())
    return [m.group(0) for m in lignes if m is not None and m.group("projet") == project_id]


def _decision(coupee: FileCoupee, verdict: Verdict, raison: str) -> Decision:
    return Decision(Action.RELANCER_FILE, f"{coupee.project_id} file {coupee.run_id}", verdict, raison)


class SuperviseurFile:
    """Reopens an interrupted queue once per cause, when the infrastructure cut it."""

    def __init__(
        self,
        config: ConfigSuperviseur,
        rouvrir: Rouvrir,
        projet_occupe: Callable[[str], bool],
        depense_jour_usd: Callable[[], Awaitable[float]],
        quota_bas: Callable[[], Awaitable[bool]],
    ) -> None:
        self._config = config
        self._rouvrir = rouvrir
        self._projet_occupe = projet_occupe
        self._depense_jour = depense_jour_usd
        self._quota_bas = quota_bas
        self._traitees: set[str] = set()
        self._racine: dict[str, str] = {}
        self._relances: set[tuple[str, Cause]] = set()

    async def relancer(self, coupee: FileCoupee) -> Decision:
        """Decide for one interrupted queue and, when `agir`, reopen what it still held."""
        refus = self._refus_sans_lecture(coupee)
        if refus is not None:
            return refus
        racine = self._racine.get(coupee.run_id, coupee.run_id)
        if (racine, "infrastructure") in self._relances:
            return _decision(coupee, "a_toi", "deux interruptions de suite par l'infrastructure : pas de troisième relance")
        refus = await self._refus_de_ressources(coupee)
        if refus is not None:
            return refus
        return await self._rouvrir_la_file(coupee, racine)

    def _refus_sans_lecture(self, coupee: FileCoupee) -> Decision | None:
        """`rien` for what is never relaunched or already handled, `None` when it may be."""
        cause = classer_interruption(coupee.ligne)
        if cause != "infrastructure":
            return _decision(coupee, "rien", f"cause « {cause} » : une file ne se relance que sur une coupure d'infrastructure")
        if not self._config.relance_file:
            return _decision(coupee, "rien", "relance_file non déclaré : la file reste interrompue")
        if coupee.run_id in self._traitees:
            return _decision(coupee, "rien", "cette interruption a déjà été traitée")
        if not coupee.restants:
            return _decision(coupee, "rien", "aucun ticket restant dans la file")
        if self._projet_occupe(coupee.project_id):
            return _decision(coupee, "rien", "une autre file tient déjà le projet")
        return None

    async def _refus_de_ressources(self, coupee: FileCoupee) -> Decision | None:
        """`a_toi` when the daily budget is spent, `rien` while the quota is low."""
        try:
            depense = await self._depense_jour()
        except Exception as exc:  # noqa: BLE001 — une dépense illisible : rien ne repart
            return _decision(coupee, "a_toi", f"dépense du jour illisible ({decrire_exception(exc)})")
        plafond = self._config.budget_jour_usd
        if depense >= plafond:
            return _decision(coupee, "a_toi", f"budget du jour atteint ({depense:.2f} $ / {plafond:.2f} $)")
        if await self._quota_est_bas():
            return _decision(coupee, "rien", "quota d'abonnement bas : la relance attend")
        return None

    async def _quota_est_bas(self) -> bool:
        try:
            return await self._quota_bas()
        except Exception:  # noqa: BLE001 — un quota inconnu ne bloque jamais (ADR-020)
            _logger.warning("superviseur_file_quota_inconnu")
            return False

    async def _rouvrir_la_file(self, coupee: FileCoupee, racine: str) -> Decision:
        restants = list(coupee.restants)
        try:
            nouveau = await self._rouvrir(coupee.project_id, restants)
        except Exception as exc:  # noqa: BLE001 — rien n'a démarré : pas de relance notée
            _logger.warning("superviseur_file_echec", extra={"project": coupee.project_id})
            return _decision(coupee, "a_toi", f"réouverture impossible ({decrire_exception(exc)})")
        self._traitees.add(coupee.run_id)
        self._relances.add((racine, "infrastructure"))
        self._racine[nouveau] = racine
        return _decision(coupee, "agir", f"file rouverte avec {len(restants)} ticket(s) : {', '.join(restants)}")


def tickets_restants(ticket_ids: Sequence[str], termines: Sequence[str]) -> tuple[str, ...]:
    """The tickets of a queue that were not finished, in their queued order."""
    faits = set(termines)
    return tuple(ticket for ticket in ticket_ids if ticket not in faits)
