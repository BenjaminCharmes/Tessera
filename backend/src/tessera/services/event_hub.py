"""Fan-out of pipeline events to every observer — ticket-127.

`pipeline_stream.emetteur()` writes to one socket and one only: a run is
therefore observable from the tab that launched it, and from nowhere else.
The hub makes the emission plural, so that the same run can feed the panel of
its project, a supervision view, and any other client at once.

## Ce qu'une file pleine a le droit de perdre

Un client lent ne doit ni ralentir un run — le pipeline publie depuis la
boucle qui fait tourner les agents — ni faire disparaître un verdict. D'où une
règle asymétrique : les événements de **texte** (`agent_token`,
`agent_tool_use`) se jettent, les **transitions** jamais. Perdre du texte
dégrade l'affichage ; perdre une transition le rend faux — un run resterait
« en cours » à l'écran alors qu'il est commité depuis dix minutes.
"""
from collections import deque
from typing import Optional

import asyncio

from tessera.services.journal_du_texte import JOURNAL_DU_TEXTE
from tessera.services.pipeline_events import EventType, OrchestratorEvent

#: Les seuls types qu'une file saturée a le droit de jeter. Tout le reste
#: décrit un changement d'état, et se perdrait silencieusement.
JETABLES: frozenset[EventType] = frozenset(
    {
        EventType.AGENT_TOKEN,
        EventType.AGENT_TOOL_USE,
        EventType.SERVICE_OUTPUT,
    }
)

#: Assez pour absorber une rafale de tokens sans garder en mémoire le flux
#: entier d'un agent bavard.
TAILLE_PAR_DEFAUT = 512


class Abonnement:
    """La file d'un observateur, et ce qu'elle accepte de perdre."""

    def __init__(self, taille: int, hub: "EventHub") -> None:
        self._file: deque[OrchestratorEvent] = deque()
        self._taille = taille
        self._hub = hub
        self._reveil = asyncio.Event()
        self._ferme = False
        #: Combien d'événements de texte cette file a jetés. Exposé pour que
        #: l'UI puisse dire « flux tronqué » plutôt que de mentir par omission.
        self.perdus = 0

    def deposer(self, event: OrchestratorEvent) -> None:
        if self._ferme:
            return
        if len(self._file) >= self._taille:
            if event.type in JETABLES:
                self.perdus += 1
                return
            # Une transition ne se jette pas : on fait de la place en
            # sacrifiant le plus vieux texte. S'il n'y en a aucun, la file
            # grandit — quelques transitions de plus coûtent moins cher
            # qu'un état faux à l'écran.
            if self._evincer_le_plus_vieux_texte():
                self.perdus += 1
        self._file.append(event)
        self._reveil.set()

    def _evincer_le_plus_vieux_texte(self) -> bool:
        for index, candidat in enumerate(self._file):
            if candidat.type in JETABLES:
                del self._file[index]
                return True
        return False

    async def recevoir(self) -> OrchestratorEvent:
        """Wait for the next event of this subscription."""
        while not self._file:
            self._reveil.clear()
            await self._reveil.wait()
        return self._file.popleft()

    def vider(self) -> list[OrchestratorEvent]:
        """Take everything queued so far, without waiting."""
        recus = list(self._file)
        self._file.clear()
        return recus

    def fermer(self) -> None:
        self._ferme = True
        self._file.clear()
        self._hub.retirer(self)


class EventHub:
    """Publish/subscribe en mémoire du process.

    Même nature et même durée de vie que `RunLock` : un backend local n'a pas
    de second process à prévenir.
    """

    def __init__(self) -> None:
        self._abonnes: list[Abonnement] = []

    def subscribe(self, taille: Optional[int] = None) -> Abonnement:
        abonnement = Abonnement(taille or TAILLE_PAR_DEFAUT, self)
        self._abonnes.append(abonnement)
        return abonnement

    def retirer(self, abonnement: Abonnement) -> None:
        # Sans retrait, chaque onglet fermé laisserait une file qui grossit
        # jusqu'à l'arrêt du backend.
        if abonnement in self._abonnes:
            self._abonnes.remove(abonnement)

    async def publish(self, event: OrchestratorEvent) -> None:
        """Hand the event to every subscriber, without ever blocking.

        `async` sans `await` : la signature doit rester celle d'un
        `EventCallback` pour que le hub se branche là où le pipeline attend
        un émetteur.
        """
        # Retenir ici, et non dans la file d'un observateur : une file saturée
        # jette le texte, et le journal perdrait ce qu'il existe pour garder
        # (ticket-185).
        JOURNAL_DU_TEXTE.retenir(event)
        for abonnement in list(self._abonnes):
            abonnement.deposer(event)

    @property
    def nombre_d_abonnes(self) -> int:
        return len(self._abonnes)


#: L'instance que les routeurs partagent, pour la même raison que `RUN_LOCK` :
#: deux hubs seraient deux publics, et l'un des deux ne verrait rien.
EVENT_HUB = EventHub()
