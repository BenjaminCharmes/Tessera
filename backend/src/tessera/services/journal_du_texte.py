"""Ce qu'un observateur tardif a manqué — ticket-185.

ADR-041 sépare deux flux : les transitions partent à tous, le texte n'est
poussé qu'aux clients abonnés. Un observateur qui arrive en cours de route
reçoit donc l'état du run et plus rien de ce qui a été écrit avant lui — un
rechargement de page vidait le panneau d'un agent qui travaillait.

Le journal garde ce texte le temps du run et le rejoue à l'abonnement. C'est
un tampon de lecture, pas un historique : rien n'est persisté, et l'historique
d'un travail vit dans ses commits et sa pull request.
"""
from collections import deque

from tessera.services.pipeline_events import EventType, OrchestratorEvent

#: Ce qui se garde : exactement ce que le hub s'autorise à jeter, donc ce
#: qu'un client risque de ne jamais voir.
RETENUS: frozenset[EventType] = frozenset(
    {EventType.AGENT_TOKEN, EventType.AGENT_TOOL_USE}
)

#: Le plafond se compte en caractères et non en événements : un token vaut
#: trois lettres, une sortie d'outil quelques milliers. Compter les événements
#: donnerait un tampon dont la taille varierait d'un facteur mille.
CARACTERES_GARDES = 40_000


def _poids(event: OrchestratorEvent) -> int:
    """Ce que cet événement pèse dans le plafond."""
    return sum(len(v) for v in event.data.values() if isinstance(v, str))


class JournalDuTexte:
    """Le texte récent de chaque run vivant, en mémoire du process.

    Même nature et même durée de vie que `RunLock` et `EventHub` : un backend
    local n'a pas de second process à prévenir.
    """

    def __init__(self, caracteres: int = CARACTERES_GARDES) -> None:
        self._caracteres = caracteres
        self._par_run: dict[str, deque[OrchestratorEvent]] = {}
        self._poids: dict[str, int] = {}

    def retenir(self, event: OrchestratorEvent) -> None:
        """Garde un événement de texte, et oublie le run qui se ferme.

        Appelé à la **publication** et non depuis la file d'un observateur :
        une file saturée jette le texte, et le journal perdrait précisément ce
        qu'il existe pour garder.
        """
        run_id = event.run_id
        if run_id is None:
            return
        if event.type is EventType.RUN_CLOSED:
            self.oublier(run_id)
            return
        if event.type not in RETENUS:
            return

        file = self._par_run.setdefault(run_id, deque())
        file.append(event)
        self._poids[run_id] = self._poids.get(run_id, 0) + _poids(event)
        # Toujours garder le dernier : une sortie d'outil plus grosse que le
        # plafond viderait sinon le tampon qu'elle vient de remplir, et
        # l'observateur retrouverait un panneau vide.
        while len(file) > 1 and self._poids[run_id] > self._caracteres:
            self._poids[run_id] -= _poids(file.popleft())

    def relire(self, run_id: str) -> list[OrchestratorEvent]:
        """Ce qu'il reste du texte de ce run, dans l'ordre où il a été écrit."""
        return list(self._par_run.get(run_id, ()))

    def oublier(self, run_id: str) -> None:
        """Libère ce qu'un run terminé occupait.

        Sans ça, un backend qui tourne une journée garde le texte de tous les
        runs de la journée.
        """
        self._par_run.pop(run_id, None)
        self._poids.pop(run_id, None)

    @property
    def runs_suivis(self) -> int:
        return len(self._par_run)


#: L'instance que le hub alimente et que le routeur relit, pour la même raison
#: qu'`EVENT_HUB` : deux journaux seraient deux mémoires, et le lecteur
#: tomberait sur la vide.
JOURNAL_DU_TEXTE = JournalDuTexte()
