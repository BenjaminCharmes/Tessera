"""Les services qu'un projet a lancés — ticket-137.

ADR-042 : le backend lance lui-même les commandes déclarées, sans shell et
sans agent, et les processus sont ses **enfants** — ils meurent avec lui.
C'est ce qui rend inutile toute reprise après redémarrage : il n'y a jamais
de processus orphelin à retrouver.

Ce registre est en mémoire du process, comme `RunLock` et `RunRegistry`
(ADR-038, ADR-041). La différence tient en une phrase : un run se termine
tout seul, un serveur non. Rien ici n'attend la fin de quoi que ce soit.
"""
import asyncio
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Les opérateurs qu'un shell interpréterait et que `create_subprocess_exec`
#: ne fait pas. Cherchés **après** découpage, et seulement comme token entier :
#: `python -c "import time; time.sleep(30)"` est légitime, et une recherche
#: naïve dans la chaîne entière le refuserait — elle l'a fait.
OPERATEURS_DE_SHELL = frozenset({"&&", "||", "|", ";", ">", ">>", "<", "&"})

#: Combien de temps on laisse un service s'arrêter poliment avant de le tuer.
DELAI_D_ARRET_S = 5.0


class CommandeInvalide(Exception):
    """La commande déclarée ne peut pas être lancée telle quelle."""


@dataclass
class Service:
    """Un processus lancé pour un projet."""

    nom: str
    project_id: str
    pid: int
    demarre_a: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    processus: Any = None

    @property
    def en_cours(self) -> bool:
        return self.processus is not None and self.processus.returncode is None

    def en_dict(self) -> dict[str, Any]:
        return {
            "nom": self.nom,
            "project_id": self.project_id,
            "pid": self.pid,
            "demarre_a": self.demarre_a.isoformat(),
            "en_cours": self.en_cours,
            "code_de_sortie": (
                self.processus.returncode if self.processus is not None else None
            ),
        }


def verifier_la_commande(commande: str) -> list[str]:
    """Découpe la commande, en refusant ce qui exige un shell.

    `create_subprocess_exec` ne passe par aucun shell : un `&&` arriverait
    tel quel en argument du premier programme. Refuser tôt vaut mieux que de
    lancer la moitié de ce qui était écrit.

    Le contrôle porte sur les **tokens**, jamais sur la chaîne brute : un
    point-virgule dans `python -c "import time; time.sleep(30)"` appartient au
    code Python, pas au shell.
    """
    if not commande.strip():
        raise CommandeInvalide("commande vide")
    args = shlex.split(commande)
    if not args:
        raise CommandeInvalide("commande vide")
    for token in args:
        if token in OPERATEURS_DE_SHELL:
            raise CommandeInvalide(
                f"« {token} » demande un shell, et l'IDE n'en utilise pas : "
                "déclare un service par commande dans `services`."
            )
    return args


def resoudre_le_cwd(racine: Path, cwd: Optional[str]) -> Path:
    """Le dossier de travail, refusé s'il sort de la racine du projet.

    Même frontière qu'ADR-031 : ce que l'IDE lance ne travaille pas chez le
    voisin. Six dépôts clients côte à côte, et un `cwd` mal écrit démarre un
    serveur dans le mauvais.
    """
    racine_reelle = racine.resolve()
    cible = (racine_reelle / (cwd or ".")).resolve()
    if cible != racine_reelle and racine_reelle not in cible.parents:
        raise CommandeInvalide(
            f"`cwd` sort de la racine du projet : {cwd!r}"
        )
    return cible


class ProcessRegistry:
    """Les services vivants, par projet."""

    def __init__(self) -> None:
        self._services: dict[str, list[Service]] = {}

    def services_de(self, project_id: str) -> list[Service]:
        return [s for s in self._services.get(project_id, []) if s.en_cours]

    def instantane(self) -> list[dict[str, Any]]:
        return [
            service.en_dict()
            for services in self._services.values()
            for service in services
            if service.en_cours
        ]

    async def demarrer(
        self,
        project_id: str,
        nom: str,
        commande: str,
        racine: Path,
        cwd: Optional[str] = None,
        sur_ligne: Any = None,
    ) -> Service:
        """Lance une commande déclarée, sans shell, sous la racine du projet."""
        args = verifier_la_commande(commande)
        dossier = resoudre_le_cwd(racine, cwd)

        processus = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(dossier),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        service = Service(
            nom=nom, project_id=project_id, pid=processus.pid, processus=processus
        )
        self._services.setdefault(project_id, []).append(service)

        if sur_ligne is not None:
            # La lecture tourne à côté : sans elle, le tube se remplit et le
            # service se bloque sur son propre `print` au bout de quelques
            # kilo-octets.
            asyncio.create_task(self._lire(service, sur_ligne))
        return service

    async def _lire(self, service: Service, sur_ligne: Any) -> None:
        flux = service.processus.stdout if service.processus else None
        if flux is None:
            return
        try:
            while True:
                ligne = await flux.readline()
                if not ligne:
                    break
                await sur_ligne(service, ligne.decode("utf-8", "replace").rstrip())
        except Exception as exc:  # noqa: BLE001 — lire ne doit rien casser
            _logger.warning("lecture_service_interrompue", extra={"erreur": str(exc)})

    async def arreter(self, project_id: str) -> int:
        """Arrête les services d'un projet, et les retire."""
        services = self._services.pop(project_id, [])
        for service in services:
            await self._terminer(service)
        return len(services)

    async def tout_arreter(self) -> int:
        """Arrête tout ce qui tourne — appelé quand le backend s'éteint."""
        total = 0
        for project_id in list(self._services):
            total += await self.arreter(project_id)
        return total

    async def _terminer(self, service: Service) -> None:
        processus = service.processus
        if processus is None or processus.returncode is not None:
            return
        try:
            processus.terminate()
            await asyncio.wait_for(processus.wait(), timeout=DELAI_D_ARRET_S)
        except asyncio.TimeoutError:
            # Un service qui ignore `terminate` garderait son port : le tuer
            # est moins grave que de le laisser derrière soi.
            processus.kill()
            await processus.wait()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("arret_service_echoue", extra={"erreur": str(exc)})


#: L'instance que les routeurs partagent, comme `RUN_LOCK` et `EVENT_HUB`.
PROCESS_REGISTRY = ProcessRegistry()
