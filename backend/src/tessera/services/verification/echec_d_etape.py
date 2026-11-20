"""Results of a test step that could not run: launch failure, missing tool."""
import shlex
import time

from tessera.services.verification.lancement_compte import EchecLancementCompte
from tessera.services.verification.resultat_de_test import EtapeTest, TestResult
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def echec_de_lancement(
    exc: Exception, cmd: str, args: list[str], start: float
) -> TestResult:
    """Build the result of a step that could not run at all."""
    duration_ms = int((time.monotonic() - start) * 1000)
    if isinstance(exc, EchecLancementCompte):
        # Panne d'environnement, pas un test rouge ; aucun repli sous le compte
        # du backend (ticket-934, ADR-085).
        _logger.warning("test_runner_compte_agent_echec", extra={"error": str(exc)})
        return TestResult(
            passed=False,
            demarree=False,
            total=0,
            failed=0,
            output_summary=(
                f"La commande de test n'a pas démarré sous le compte dédié : {exc}. "
                "Panne d'environnement, ce n'est pas un test en échec."
            ),
            errors=[str(exc)],
            duration_ms=duration_ms,
        )
    if isinstance(exc, FileNotFoundError):
        # Pas un test rouge : la commande n'a pas démarré. Le dire
        # explicitement évite au codeur de corriger du code qui n'est pas
        # en cause (ticket-157).
        _logger.warning(
            "test_runner_commande_introuvable", extra={"cmd": cmd, "error": str(exc)}
        )
        return TestResult(
            passed=False,
            demarree=False,
            total=0,
            failed=0,
            output_summary=(
                f"La commande de test n'a pas démarré : « {shlex.join(args)} » — "
                "exécutable introuvable. Ce n'est pas un test en échec."
            ),
            errors=[str(exc)],
            duration_ms=duration_ms,
        )
    _logger.warning("test_runner_exec_failed", extra={"error": str(exc)})
    return TestResult(
        passed=False,
        total=0,
        failed=0,
        output_summary=f"Erreur d'exécution : {exc}",
        errors=[str(exc)],
        duration_ms=duration_ms,
    )


def marquer_panne_d_environnement(
    result: TestResult, etape: EtapeTest, outil: str
) -> None:
    """Turn a red step into an environment failure: the tool, not the code, is missing.

    Le détail de l'échec reste : c'est la sortie qui prouve le diagnostic
    (ticket-496).
    """
    _logger.warning(
        "test_runner_outil_introuvable", extra={"outil": outil, "etape": etape.commande}
    )
    result.demarree = False
    result.output_summary = (
        f"étape `{etape.commande}` — panne d'environnement : outil `{outil}` "
        "introuvable. Réinstaller les dépendances du projet. "
        "Ce n'est pas un test en échec."
    )
    result.errors = [result.output_summary]
