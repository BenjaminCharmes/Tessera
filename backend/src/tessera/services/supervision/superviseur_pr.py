"""The supervisor hands an unwatched approved PR back to the watcher — ticket-857, ADR-080.

No model. A delivery cut by the infrastructure (network, git, sleep) leaves an
approved run's PR open and held by nobody. This module spots it and gives it
back to `CIWatcher` through the same `surveiller` entry the pipeline uses: the
watcher then runs its usual checks and is the only one to merge, bound to
`pushed_sha` (ADR-039). Nothing here merges, pushes or re-reads the PR's code.

Never handed back: a run that is not approved (ADR-030), a red CI (ADR-051), a
conflict-resolver PR (ADR-033). A head that is no longer `pushed_sha` goes to
« À toi ». One hand-over per `(PR, sha)`.
"""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from tessera.services.livraison.controle_tete import decrire_exception
from tessera.services.livraison.livraison_resultat import Livraison
from tessera.services.noyau.pipeline_events import EventCallback
from tessera.services.supervision.superviseur_actions import Action, Decision, Verdict
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Confie une PR au watcher : (projet, ticket, numéro de PR, callback d'événements).
Surveiller = Callable[[str, str, int, EventCallback], Awaitable[None]]

# Une CI rouge se lit d'abord : une ligne qui nomme les deux reste une CI rouge.
_MARQUES_CI_ROUGE = ("ci rouge", "ci en échec", "ci en echec", "ci failed")
_MARQUES_INFRASTRUCTURE = (
    "gitcommanderror", "transporterror", "connecterror", "connecttimeout",
    "readtimeout", "connectionerror", "réseau", "reseau", "network", "veille",
    "coupure",
)


class _Surveillance(Protocol):
    """What the supervisor reads of the watcher."""

    def en_attente(self, project_id: str) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class RunLivre:
    """An approved-or-not run and what its delivery left behind."""

    project_id: str
    ticket_id: str
    approuve: bool
    livraison: Livraison
    resolveur_conflit: bool = False


def cause_de_l_arret(arret: str | None) -> str:
    """Classify a delivery stop line: `ci_rouge`, `infrastructure` or `autre`."""
    if arret is None:
        return "autre"
    texte = arret.casefold()
    if any(marque in texte for marque in _MARQUES_CI_ROUGE):
        return "ci_rouge"
    if any(marque in texte for marque in _MARQUES_INFRASTRUCTURE):
        return "infrastructure"
    return "autre"


def _decision(run: RunLivre, verdict: Verdict, raison: str) -> Decision:
    pr = run.livraison.pr_number
    return Decision(Action.RECONFIER_PR, f"{run.ticket_id} PR #{pr}", verdict, raison)


def _a_ignorer(run: RunLivre) -> str | None:
    """Why the run is never handed back, or `None` when it may be."""
    if not run.approuve:
        return "run non approuvé : une PR non approuvée ne se livre jamais"
    if run.resolveur_conflit:
        return "PR d'une résolution de conflit : elle ne se merge jamais seule"
    if run.livraison.pr_number is None:
        return "aucune PR ouverte par ce run"
    cause = cause_de_l_arret(run.livraison.arret)
    if cause == "ci_rouge":
        return "CI rouge : la PR reste bloquée, sans relance"
    if cause != "infrastructure":
        return "l'arrêt de la livraison n'est pas une coupure d'infrastructure"
    return None


def _cle(run: RunLivre, sha: str) -> str:
    return f"{Action.RECONFIER_PR.value}:{run.project_id}:{run.livraison.pr_number}:{sha}"


class SuperviseurPr:
    """Hands back to the watcher the PRs it does not hold, once per `(PR, sha)`."""

    def __init__(
        self,
        surveillance: _Surveillance,
        surveiller: Surveiller,
        etat_pr: Callable[[str, int], Awaitable[str]],
        lire_tete: Callable[[str, int], Awaitable[str | None]],
    ) -> None:
        self._surveillance = surveillance
        self._surveiller = surveiller
        self._etat_pr = etat_pr
        self._lire_tete = lire_tete
        self._confiees: set[str] = set()

    async def reconfier(self, run: RunLivre, on_event: EventCallback) -> Decision:
        """Decide for one run and, when `agir`, give its PR back to the watcher."""
        raison = _a_ignorer(run)
        if raison is not None:
            return _decision(run, "rien", raison)
        if run.ticket_id in self._surveillance.en_attente(run.project_id):
            return _decision(run, "rien", "la PR est déjà surveillée")
        pr, pushed = run.livraison.pr_number, run.livraison.pushed_sha
        if pr is None:
            return _decision(run, "rien", "aucune PR ouverte par ce run")
        if pushed is not None and _cle(run, pushed) in self._confiees:
            return _decision(run, "rien", "PR déjà redonnée au watcher pour ce commit")
        garde = await self._garde(run, pr, pushed)
        if garde is not None:
            return garde
        # `_garde` a refusé un commit poussé inconnu : `pushed` est un SHA ici.
        return await self._confier(run, pr, pushed or "", on_event)

    async def _garde(self, run: RunLivre, pr: int, pushed: str | None) -> Decision | None:
        """`rien` when the PR is not open, `a_toi` when its head is not `pushed_sha`."""
        try:
            if await self._etat_pr(run.project_id, pr) != "open":
                return _decision(run, "rien", "la PR n'est plus ouverte")
            if pushed is None:
                return _decision(run, "a_toi", "commit poussé inconnu : la PR n'est pas redonnée")
            tete = await self._lire_tete(run.project_id, pr)
        except Exception as exc:  # noqa: BLE001 — une lecture qui échoue : rien n'est confié
            return _decision(run, "a_toi", f"PR illisible ({decrire_exception(exc)})")
        if tete != pushed:
            lue = tete[:7] if tete else "inconnue"
            return _decision(
                run, "a_toi", f"la tête de la PR ({lue}) n'est plus le commit poussé ({pushed[:7]})"
            )
        return None

    async def _confier(
        self, run: RunLivre, pr: int, pushed: str, on_event: EventCallback
    ) -> Decision:
        try:
            await self._surveiller(run.project_id, run.ticket_id, pr, on_event)
        except Exception as exc:  # noqa: BLE001 — le watcher n'a rien reçu : pas de clé
            _logger.warning(
                "superviseur_pr_echec",
                extra={"project": run.project_id, "ticket": run.ticket_id, "pr": pr},
            )
            return _decision(run, "a_toi", f"remise au watcher impossible ({decrire_exception(exc)})")
        self._confiees.add(_cle(run, pushed))
        return _decision(run, "agir", f"PR redonnée au watcher, tête {pushed[:7]}")


def reperer(runs: list[RunLivre]) -> list[RunLivre]:
    """The runs a hand-back is worth considering for: approved, PR open, infrastructure stop."""
    return [run for run in runs if _a_ignorer(run) is None]
