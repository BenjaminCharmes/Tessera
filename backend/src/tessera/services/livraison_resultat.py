"""Le résultat d'une livraison, sorti de `livraison.py` (ticket-659).

Un fichier de données pur : le service qui enchaîne les étapes le réimporte, et
reste ainsi sous le plafond du cliquet de longueur.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Livraison:
    """Ce que la livraison a fait, et pourquoi elle s'est arrêtée."""

    etapes: tuple[str, ...] = ()
    #: Durée en millisecondes de chaque étape, dans le même ordre que `etapes`.
    #: `tuple[float, ...]` est JSON-sérialisable (devient une liste). (ticket-288)
    durees_ms: tuple[float, ...] = ()
    #: `None` quand la livraison est allée aussi loin que le projet l'autorise.
    arret: str | None = None
    conflits: tuple[str, ...] = ()
    pr_number: int | None = None
    merged: bool = False
    #: Vrai quand la phase 1 a levé **après** l'ouverture de la PR : `arret`
    #: porte alors une cause, mais la PR est bien ouverte et doit passer à la
    #: phase 2. Les autres arrêts avec PR (conflit résolu, ADR-033) restent
    #: sans surveillance. (ticket-415)
    pr_orpheline: bool = False
    #: Tête de la branche telle qu'elle est partie sur le distant : c'est elle
    #: que le watcher compare à la tête de la PR avant de merger (ticket-492).
    pushed_sha: str | None = None
    #: Vrai quand la branche ne porte plus le commit que le reviewer a lu :
    #: rien n'est poussé, le ticket est bloqué (ticket-492).
    branche_modifiee: bool = False
    #: Vrai quand la CI a rendu `conflicting` en phase 2 : le watcher peut
    #: mettre la PR à jour, une fois, avant de bloquer le ticket (ticket-733).
    #: Le texte de `arret` ne change pas.
    a_mettre_a_jour: bool = False
    #: Vrai quand le projet déclare le niveau `commit` : l'arrêt est voulu, le
    #: ticket reste `done` (ticket-741).
    arret_voulu: bool = False

    @property
    def bloque_le_ticket(self) -> bool:
        """Whether the ticket must read `blocked` after this delivery (ticket-741).

        Vrai pour une branche modifiée depuis l'approbation, et pour tout arrêt
        de phase 1 qui n'a pas ouvert de PR, sauf l'arrêt voulu du niveau
        `commit`. Une PR ouverte, même orpheline, reste suivie par le watcher.
        """
        if self.branche_modifiee:
            return True
        return (
            self.arret is not None and self.pr_number is None and not self.arret_voulu
        )
