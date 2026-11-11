"""The result types of a test run — moved out of `test_runner.py` (ticket-934)."""
from dataclasses import dataclass, field


class TestCommandNotFound(Exception):
    # Not a pytest test class despite the "Test" prefix — see TestResult.
    __test__ = False


@dataclass
class TestResult:
    # Tells pytest not to try collecting this as a test class just because
    # its name starts with "Test" (it is a result dataclass, and pytest
    # warns on every run otherwise).
    __test__ = False

    passed: bool
    total: int
    failed: int
    output_summary: str
    errors: list[str] = field(default_factory=list)
    #: Détail structuré des échecs : section « short test summary info » de
    #: pytest ou lignes FAIL/× de vitest, suivi du bloc FAILURES/ERRORS,
    #: tronqué à 8 000 caractères. Vide quand les tests passent (ticket-393).
    failure_details: str = ""
    duration_ms: int = 0
    #: La commande a-t-elle seulement démarré ? Faux quand l'exécutable est
    #: introuvable — ce qui n'est pas la même chose que des tests rouges, et
    #: ne demande pas la même chose au codeur. Deux tours de revue ont été
    #: dépensés à corriger du code qui n'était pas en cause (ticket-157).
    demarree: bool = True
    #: Le délai global a-t-il été dépassé avant la fin de la commande ?
    #: Distinct d'un test rouge : aucun test n'a été exécuté jusqu'au bout,
    #: donc rien ne dit que le code est en cause. Relancer sans repasser par
    #: le codeur est la bonne réponse (ticket-349).
    expiree: bool = False
    #: Chaque étape lancée et son code de sortie, dans l'ordre : ce que le
    #: validateur lit pour juger « typecheck, lint et build passent »
    #: (ticket-337).
    etapes: list["EtapeTest"] = field(default_factory=list)
    #: Quand ``expiree`` : l'étape en cours à la coupure et ce qu'elle avait
    #: déjà consommé. Elle n'est pas dans ``etapes``, qui ne garde que les
    #: étapes terminées avec un code de sortie (ticket-514).
    etape_coupee: "EtapeCoupee | None" = None
    #: Le délai global, en secondes, qui a expiré (0 tant qu'il n'a pas expiré).
    delai_s: float = 0.0


@dataclass
class EtapeTest:
    """One step of the test command, as it was launched."""

    commande: str
    code: int
    #: Durée de l'étape, du lancement à la fin du processus (ticket-514).
    duree_ms: int = 0


@dataclass
class EtapeCoupee:
    """The step that was running when the global timeout expired."""

    commande: str
    duree_ms: int
