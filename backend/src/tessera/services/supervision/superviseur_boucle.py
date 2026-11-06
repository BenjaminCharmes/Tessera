"""The supervisor's background task: events and a 15-minute sweep — ticket-859, ADR-080.

Same shape as the anomaly detector's task (ADR-078), offset from it. It starts
with the backend only if a project declared the `superviseur` role active (off
by default), hooks `RUN_REGISTRY.sur_fermeture`, and sweeps every 15 minutes.

Each pass asks `collecter` what could be done, then, for each candidate:
- a key (`action:projet/cible:sha`) already done is never tried again, in memory
  and in `ide_state_dir`; two failures in a row on a key end the attempts with
  an `a_toi` verdict;
- once the day's spend of the `superviseur` role reaches `budget_jour_usd`, only
  the actions that call no model go on; the others wait for the next day;
- each decision other than `rien` is announced once, as `superviseur_action`.

The task never interrupts a run (`intervenir` waits for the project) and its
failure reaches no run (ADR-037): every error is logged and swallowed. A close
that comes while a pass is running (the pass's own interventions close a
`supervision` run) starts nothing: the pass is single, and the next sweep
catches up.
"""
import asyncio
from collections.abc import Collection

from tessera.services.noyau.event_hub import EventHub
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.run_registry import RunRegistry
from tessera.services.providers.enregistrant import activer_enregistrement
from tessera.services.supervision.superviseur_actions import RAISON_MAX, Decision
from tessera.services.supervision.superviseur_boucle_etat import EtatIdempotence
from tessera.services.supervision.superviseur_boucle_ports import Candidat, Collecter, DepenseDuJour, ProjetsSupervises, ProjetSupervise
from tessera.utils.exceptions import decrire_exception
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

INTERVALLE_S = 900.0
#: Le détecteur passe toutes les 300 s à t=0 : à t=150 s, jamais en même temps.
DECALAGE_S = 150.0
ECHECS_MAX = 2


class SuperviseurBoucle:
    """Runs the supervisor's candidates on run closings and on a fixed sweep."""

    def __init__(
        self,
        registre: RunRegistry,
        hub: EventHub,
        projets: ProjetsSupervises,
        collecter: Collecter,
        depense_jour: DepenseDuJour,
        etat: EtatIdempotence,
        *,
        intervalle_s: float = INTERVALLE_S,
        decalage_s: float = DECALAGE_S,
    ) -> None:
        self._registre = registre
        self._hub = hub
        self._projets = projets
        self._collecter = collecter
        self._depense_jour = depense_jour
        self._etat = etat
        self._intervalle_s = intervalle_s
        self._decalage_s = decalage_s
        self._verrou = asyncio.Lock()
        self._taches: set[asyncio.Task[list[Decision]]] = set()
        self._accroche = False

    # -- le démarrage ------------------------------------------------------

    def demarrer(self) -> bool:
        """Hook the run closings if a project declares the role active; `False` otherwise."""
        if not self._projets_actifs():
            return False
        if not self._accroche:
            self._registre.sur_fermeture(self._sur_fermeture)
            self._accroche = True
        return True

    def _projets_actifs(self) -> list[ProjetSupervise]:
        try:
            return self._projets()
        except Exception:  # noqa: BLE001 — une lecture qui échoue n'active rien
            _logger.warning("superviseur_projets_illisibles", exc_info=True)
            return []

    def _sur_fermeture(self, project_id: str) -> None:
        if self._verrou.locked():
            return
        try:
            tache = asyncio.get_running_loop().create_task(self.passe({project_id}))
        except RuntimeError:
            return  # aucune boucle d'événements : rien à lancer
        self._taches.add(tache)
        tache.add_done_callback(self._taches.discard)

    async def attendre(self) -> None:
        """Wait for the passes the closings started, never raising."""
        if self._taches:
            await asyncio.gather(*self._taches, return_exceptions=True)

    async def boucle(self) -> None:
        """Sweep after the offset, then every `intervalle_s`, until cancelled."""
        if not self.demarrer():
            return
        await asyncio.sleep(self._decalage_s)
        while True:
            await self.passe()
            await asyncio.sleep(self._intervalle_s)

    # -- une passe ---------------------------------------------------------

    async def passe(self, projets: Collection[str] | None = None) -> list[Decision]:
        """One pass over the active projects (or only `projets`); never raises, never doubles."""
        if self._verrou.locked():
            return []
        async with self._verrou:
            try:
                return await self._balayer(projets)
            except Exception:  # noqa: BLE001 — l'échec du superviseur n'atteint aucun run (ADR-037)
                _logger.warning("superviseur_passe_en_echec", exc_info=True)
                return []

    async def _balayer(self, projets: Collection[str] | None) -> list[Decision]:
        # Les appels du modèle s'enregistrent sous ce run fictif : c'est ce que lit la dépense du jour.
        activer_enregistrement("superviseur", "superviseur")
        decisions: list[Decision] = []
        for projet in self._projets_actifs():
            if projets is None or projet.project_id in projets:
                decisions.extend(await self._projet(projet))
        return decisions

    async def _projet(self, projet: ProjetSupervise) -> list[Decision]:
        try:
            candidats = await self._collecter(projet.project_id, projet.path)
        except Exception as exc:  # noqa: BLE001 — rien à faire sur ce projet cette fois
            _logger.warning("superviseur_collecte_en_echec", extra={"project": projet.project_id, "erreur": decrire_exception(exc)})
            return []
        decisions: list[Decision] = []
        budget_permet: bool | None = None
        for candidat in candidats:
            if self._etat.deja_faite(candidat.cle):
                continue
            if not candidat.sans_modele:
                if budget_permet is None:
                    budget_permet = await self._budget_permet(projet)
                if not budget_permet:
                    continue
            decisions.extend(await self._un(candidat))
        return decisions

    async def _budget_permet(self, projet: ProjetSupervise) -> bool:
        """Whether the day's spend is under the project's budget; unreadable reads as spent."""
        try:
            depense = await self._depense_jour()
        except Exception as exc:  # noqa: BLE001 — une dépense illisible : pas d'appel de modèle
            _logger.warning("superviseur_depense_illisible", extra={"erreur": decrire_exception(exc)})
            return False
        plafond = projet.config.budget_jour_usd
        if depense >= plafond:
            _logger.info("superviseur_budget_du_jour_atteint", extra={"project": projet.project_id, "depense": depense})
        return depense < plafond

    # -- une action --------------------------------------------------------

    async def _un(self, candidat: Candidat) -> list[Decision]:
        try:
            decisions = await candidat.executer()
        except Exception as exc:  # noqa: BLE001 — un échec se compte, il ne se propage pas
            return await self._echec(candidat, decrire_exception(exc))
        retenues = [d for d in decisions if d.verdict != "rien"]
        if retenues:
            self._etat.marquer_faite(candidat.cle)
            for decision in retenues:
                await self._annoncer(candidat.project_id, decision)
            return retenues
        if decisions and not candidat.sans_modele:
            return await self._echec(candidat, decisions[0].raison)
        return []  # rien à faire (ou rien à juger) : ni fait, ni échec

    async def _echec(self, candidat: Candidat, raison: str) -> list[Decision]:
        """Count a failure; the second in a row hands the key to « À toi » for good."""
        echecs = self._etat.noter_echec(candidat.cle)
        _logger.warning("superviseur_action_en_echec", extra={"cle": candidat.cle, "echecs": echecs, "raison": raison[:200]})
        if echecs < ECHECS_MAX:
            return []
        texte = f"{ECHECS_MAX} échecs de suite : {' '.join(raison.split())}"
        decision = Decision(candidat.action, candidat.cible, "a_toi", texte[:RAISON_MAX])
        self._etat.marquer_faite(candidat.cle)
        await self._annoncer(candidat.project_id, decision)
        return [decision]

    async def _annoncer(self, project_id: str, decision: Decision) -> None:
        """Publish `superviseur_action` (bell, history); a failed publish is logged, never raised."""
        evenement = OrchestratorEvent(
            type=EventType.SUPERVISEUR_ACTION,
            ticket_id=decision.cible,
            project_id=project_id,
            data={
                "action": decision.action.value, "cible": decision.cible,
                "verdict": decision.verdict, "raison": decision.raison,
            },
        )
        try:
            await self._hub.publish(evenement)
        except Exception:  # noqa: BLE001 — l'annonce n'est pas l'action
            _logger.warning("superviseur_annonce_en_echec", exc_info=True)
