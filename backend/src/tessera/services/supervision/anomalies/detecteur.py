"""The anomaly detector: a witness that watches live runs — ticket-839 (ADR-078).

Une tâche de fond relit, toutes les 5 minutes et en lecture seule, chaque run
vivant. Elle **dit** ; elle n'agit jamais : ni arrêt, ni relance, ni
modification d'un run, ni LLM, ni `git`, ni `gh`, ni écriture dans un dépôt.
Son échec se journalise et n'atteint aucun run (ADR-037) : c'est un témoin, il
échoue muet.
"""
import asyncio
import contextlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tessera.models.agent import AgentRole
from tessera.services.noyau.event_hub import EventHub
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.run_executor import emetteur
from tessera.services.pipeline.run_registry import RunActif, RunRegistry
from tessera.services.supervision.anomalies import lecture_evenements, lecture_historique
from tessera.services.supervision.anomalies.etapes import ETAPES_SILENCIEUSES, etapes_depuis
from tessera.services.supervision.anomalies.modeles import Anomalie, Etape
from tessera.services.supervision.anomalies.regles_directes import outil_repete, silence, tours_de_revue
from tessera.services.supervision.anomalies.regles_historiques import blocages_identiques, cout_budget, cout_median, etape_longue, mediane_si_assez
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Combien d'appels d'outils récents la règle `outil_repete` relit.
APPELS_RELUS = 40


def _horloge_utc() -> datetime:
    return datetime.now(UTC)


class DetecteurDAnomalies:
    """Watch the live runs of a registry and report each anomaly once."""

    def __init__(
        self,
        registre: RunRegistry,
        hub: EventHub,
        db_path: Path | str,
        reglages: Any,
        horloge: Callable[[], datetime] = _horloge_utc,
    ) -> None:
        self._registre = registre
        self._hub = hub
        self._db_path = db_path
        self._reglages = reglages
        self._horloge = horloge
        self._derniere_passe: datetime | None = None

    # -- une passe ---------------------------------------------------------

    async def passe(self) -> list[Anomalie]:
        """One pass over the live runs; returns what it reported."""
        maintenant = self._horloge()
        self._signaler_le_retard(maintenant)
        signalees: list[Anomalie] = []
        for run in self._registre.vivants():
            try:
                signalees.extend(await self._passe_du_run(run, maintenant))
            except Exception:  # noqa: BLE001 — un témoin échoue muet, et le dit dans le log
                _logger.warning(
                    "anomalie_passe_en_echec", extra={"run": run.run_id}, exc_info=True
                )
        return signalees

    def _signaler_le_retard(self, maintenant: datetime) -> None:
        """Log a pass that comes much later than expected (the machine slept)."""
        precedente, self._derniere_passe = self._derniere_passe, maintenant
        if precedente is None:
            return
        ecart = (maintenant - precedente).total_seconds()
        if ecart > 2 * self._reglages.anomalie_intervalle_s:
            # Une machine qui dort voit tous les runs « silencieux » : c'est
            # vrai, ils n'ont pas avancé. Le log dit comment lire l'alerte.
            _logger.warning("anomalie_passe_tardive", extra={"ecart_s": ecart})

    async def _passe_du_run(self, run: RunActif, maintenant: datetime) -> list[Anomalie]:
        candidates = await self._constats(run, maintenant)
        signalees: list[Anomalie] = []
        for anomalie in candidates:
            if anomalie.cle in run.anomalies_vues:
                continue
            await self._signaler(run, anomalie)
            signalees.append(anomalie)
        return signalees

    # -- les règles --------------------------------------------------------

    async def _constats(self, run: RunActif, maintenant: datetime) -> list[Anomalie]:
        r = self._reglages
        ticket = run.ticket_id or ""
        constats: list[Anomalie | None] = []
        ouvertes: list[Etape] = []
        medianes_armees: set[str] = set()

        if ticket and run.db_run_id:
            base = self._db_path
            appels = await lecture_evenements.derniers_appels_d_outils(
                base, run.db_run_id, ticket, APPELS_RELUS
            )
            constats.append(outil_repete(appels, r.anomalie_outil_repete))

            evenements = await lecture_evenements.evenements_de_etapes(base, run.db_run_id, ticket)
            ouvertes = [e for e in etapes_depuis(evenements) if e.fin is None and not e.abandonnee]
            for etape in ouvertes:
                passees = await lecture_historique.durees_passees(
                    base, run.project_id, etape.nom, r.anomalie_fenetre
                )
                if mediane_si_assez(passees, r.anomalie_echantillon_min) is not None:
                    medianes_armees.add(etape.nom)
                constats.append(
                    etape_longue(
                        etape, maintenant, passees, ticket_id=ticket,
                        plancher_s=r.anomalie_plancher_etape_s,
                        facteur=r.anomalie_facteur_median, minimum=r.anomalie_echantillon_min,
                    )
                )
            constats.extend(await self._constats_de_cout(run, ticket))
            constats.append(await self._constat_de_blocages(run, ticket))

        constats.append(self._constat_de_silence(run, maintenant, ticket, ouvertes, medianes_armees))
        if ticket:
            constats.append(tours_de_revue(run.tour, ticket, r.anomalie_tours))
        if run.mode == "autonomous":
            constats.append(
                cout_budget(
                    run.cout_usd, r.run_max_budget_usd, ticket_id=ticket or run.mode,
                    run_id=run.run_id, part=r.anomalie_part_budget,
                )
            )
        return [c for c in constats if c is not None]

    def _constat_de_silence(
        self, run: RunActif, maintenant: datetime, ticket: str,
        ouvertes: list[Etape], medianes_armees: set[str],
    ) -> Anomalie | None:
        # Le silence est voulu pendant une question (ADR-025), une attente
        # extérieure, et une étape silencieuse dont la médiane dit sa durée :
        # là seule `etape_longue` parle. Sans médiane, `silence` est le seul filet.
        etape_silencieuse_armee = any(
            e.nom in ETAPES_SILENCIEUSES and e.nom in medianes_armees for e in ouvertes
        )
        exempte = (
            run.question is not None or run.attente_exterieure or etape_silencieuse_armee
        )
        return silence(
            run.dernier_evenement_a, maintenant, ticket_id=ticket or run.mode,
            seuil_s=self._reglages.anomalie_silence_s, exempte=exempte,
        )

    async def _constats_de_cout(self, run: RunActif, ticket: str) -> list[Anomalie | None]:
        r = self._reglages
        ligne = await lecture_historique.ligne_ouverte_du_ticket(
            self._db_path, run.project_id, ticket
        )
        if ligne is None:
            return []
        cout = await lecture_historique.cout_du_ticket(self._db_path, ligne.id)
        passes = await lecture_historique.couts_passes(
            self._db_path, run.project_id, r.anomalie_fenetre
        )
        return [
            cout_median(
                cout, passes, ticket_id=ticket, ligne_id=ligne.id,
                plancher_usd=r.anomalie_plancher_cout_usd,
                facteur=r.anomalie_facteur_median, minimum=r.anomalie_echantillon_min,
            )
        ]

    async def _constat_de_blocages(self, run: RunActif, ticket: str) -> Anomalie | None:
        derniers = await lecture_historique.derniers_runs_finis(
            self._db_path, run.project_id, ticket, 2
        )
        return blocages_identiques(derniers)

    # -- le signalement ----------------------------------------------------

    async def _signaler(self, run: RunActif, anomalie: Anomalie) -> None:
        """Emit the anomaly, then remember it: a failed emission is retried next pass."""
        try:
            agent: AgentRole | None = AgentRole(anomalie.agent) if anomalie.agent else None
        except ValueError:
            agent = None
        envoyer = emetteur(self._hub, run, run.db_run_id)
        donnees = anomalie.model_dump()
        await envoyer(
            OrchestratorEvent(
                type=EventType.RUN_ANOMALY, agent=agent, ticket_id=anomalie.ticket_id,
                data=donnees,
            )
        )
        # Après l'émission, jamais avant : une clé notée trop tôt ne serait
        # jamais dite si l'émission échouait.
        run.ajouter_anomalie(donnees)
        run.anomalies_vues.add(anomalie.cle)
        # Ni `input` d'outil ni message : la règle, le ticket et les mesures suffisent.
        _logger.warning(
            "anomalie_de_run",
            extra={
                "regle": anomalie.regle, "ticket": anomalie.ticket_id, "run": run.run_id,
                "mesure": anomalie.mesure, "seuil": anomalie.seuil, "unite": anomalie.unite,
            },
        )

    # -- la boucle ---------------------------------------------------------

    async def boucle(self) -> None:
        """Pass, then sleep `anomalie_intervalle_s`, until cancelled."""
        if not self._reglages.anomalies_actives:
            return
        while True:
            try:
                await self.passe()
            except Exception:  # noqa: BLE001 — la boucle d'un témoin ne s'arrête jamais seule
                _logger.warning("anomalie_passe_en_echec", exc_info=True)
            await asyncio.sleep(self._reglages.anomalie_intervalle_s)


async def arreter_le_detecteur(tache: "asyncio.Task[None] | None") -> None:
    """Cancel the detector task and wait for it, without ever raising."""
    if tache is None:
        return
    tache.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await tache
