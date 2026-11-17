"""Stage — the project's test suite (ticket-688, split from `pipeline_stages`)."""
from typing import TYPE_CHECKING

from tessera.services.noyau.diff_changements import lire_diff
from tessera.services.noyau.pipeline_events import EventType, PipelineResult
from tessera.services.pipeline.pipeline_outcomes import finish_timeout_expired
from tessera.services.pipeline.pipeline_run import PipelineRun, emit
from tessera.services.verification.detail_du_delai import detail_du_delai, ligne_de_delai
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.pipeline.orchestrator import Orchestrator
    from tessera.services.verification.test_runner import TestResult

_logger = get_logger(__name__)


def _noter_le_delai(orch: "Orchestrator", run: PipelineRun, result: "TestResult") -> None:
    """Log a timeout with its step durations and hand the same list to the coder.

    Le résumé du résultat porte déjà la liste des étapes (``TestRunnerService``) :
    ``test_context`` la reprend une seule fois. Le codeur ne la lit que par
    ``verifier_travail_repris``, qui la copie dans ses retours (ticket-514).
    """
    orch._log(f"[{run.ticket_id}] testeur: {ligne_de_delai(result)}")
    if detail_du_delai(result):
        run.test_context = f"\n\n## Résultats des tests ⏱\n{result.output_summary}\n"


async def _diff_du_run(orch: "Orchestrator") -> list[str] | None:
    """The files the run changed; None when unreadable, so no test is run again.

    Distinct de `fichiers_du_diff`, qui rend `[]` d'un diff illisible : lu comme
    « rien n'a changé », il ouvrirait la relance (ticket-971, ADR-037).
    """
    lire = getattr(orch._git_workspace, "diff_depuis_base", None)
    try:
        diff = await lire() if lire is not None else None
    except Exception as exc:  # noqa: BLE001 — un diff illisible ne bloque pas le testeur
        _logger.warning("diff_du_testeur_illisible", extra={"error": str(exc)})
        return None
    if not isinstance(diff, str):
        return None
    return [fichier.chemin for fichier in lire_diff(diff)]


async def run_tests(
    orch: "Orchestrator", run: PipelineRun, *, reprise: bool = False
) -> "bool | PipelineResult":
    """Lance la suite de tests du projet.

    ``reprise`` marque le contrôle d'un travail repris avant le codeur
    (ticket-497) : il faut alors une preuve, pas une absence d'échec. Un délai
    dépassé deux fois, une commande introuvable ou une panne du lanceur rendent
    ``False`` — jamais ``True``, qui ferait passer une panne pour un vert — et
    ne terminent pas le run : le codeur reprend, comme si les tests étaient
    rouges.

    Rend ``False`` quand les tests sont rouges (le codeur reprend).
    Rend ``True`` quand les tests passent, ou quand il n'y a pas de testeur.
    Rend un ``PipelineResult`` (blocked) quand le délai expire deux fois de
    suite : aucun code n'est en cause, et il serait inutile d'invoquer le
    codeur (ticket-349).

    Rend ``True`` quand il n'y a pas de testeur, ou pas de commande détectée :
    l'absence de test n'est pas un échec de test.
    """
    if not (orch._test_runner and orch._project_path):
        return True

    from tessera.services.verification.test_runner import TestCommandNotFound

    try:
        async def _on_attente() -> None:
            orch._log(f"[{run.ticket_id}] testeur: en attente d'un créneau de test")

        await emit(run, EventType.TEST_STARTED)
        result = await orch._test_runner.run_tests(
            orch._project_path,
            test_command=orch._test_command,
            en_attente=_on_attente,
            fichiers_du_diff=await _diff_du_run(orch),
        )

        # Un timeout ne dit rien sur le code : relancer une fois sans repasser
        # par le codeur est moins coûteux qu'un tour complet (ticket-349).
        if result.expiree:
            orch._log(f"[{run.ticket_id}] testeur: délai dépassé, suite relancée")
            _noter_le_delai(orch, run, result)
            result = await orch._test_runner.run_tests(
                orch._project_path, test_command=orch._test_command
            )
            if result.expiree:
                _noter_le_delai(orch, run, result)
                if reprise:
                    return False
                return await finish_timeout_expired(orch, run)

        run.test_result = result
        if result.instables_relances:
            orch._log(
                f"[{run.ticket_id}] testeur: tests_instables_relances "
                f"{result.instables_relances} ({result.instables_relances_ms} ms)"
            )
        await emit(
            run,
            EventType.TEST_RESULT,
            passed=result.passed,
            total=result.total,
            failed=result.failed,
            output_summary=result.output_summary,
            errors=result.errors,
            failure_details=result.failure_details,
            duration_ms=result.duration_ms,
        )
        badge = "✅" if result.passed else "❌"
        if result.failure_details:
            details = f"\nDétail des échecs:\n{result.failure_details}"
        elif result.errors:
            details = "\nErreurs:\n" + "\n".join(result.errors)
        else:
            details = ""
        run.test_context = (
            f"\n\n## Résultats des tests {badge}\n{result.output_summary}\n{details}"
        )
        orch._log(f"[{run.ticket_id}] testeur: {result.output_summary}")
        return bool(result.passed)
    except TestCommandNotFound:
        orch._log(f"[{run.ticket_id}] testeur: commande non détectée, ignoré")
    except Exception as exc:
        # Le lanceur lui-même a échoué : on ne transforme pas sa panne en
        # échec du ticket, sinon une commande mal configurée bloquerait tout.
        _logger.warning("test_runner_failed", extra={"error": str(exc)})
    return not reprise
