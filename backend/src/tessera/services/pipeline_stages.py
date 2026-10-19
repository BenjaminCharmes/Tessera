"""The individual stages of a pipeline run — ticket-046.

`run_pipeline` used to hold all of this inline: some 490 lines chaining
coder → tests → security → reviewer → validator → documentation → commit,
over shared local state and event-emitting closures. Each stage now lives in
its own function, so it can be read and tested on its own.

Stages take the `Orchestrator` explicitly rather than living on it: they need
essentially all of its collaborators, and passing it in keeps the dependency
visible instead of hiding it behind a mixin.

A stage that can end the run returns a `PipelineResult`; returning `None`
means "carry on".
"""
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from tessera.models.agent import AgentRole
from tessera.models.ticket import TicketStatus, TicketType
from tessera.services.artifact_snapshot import diff_artifacts, snapshot_artifacts
from tessera.services.config_tests_touchee import (
    avertissement_config_tests,
    fichiers_de_config_touches,
)
from tessera.services.detail_du_delai import detail_du_delai, ligne_de_delai
from tessera.services.git_workspace import GitWorkspaceError, NotAGitRepository
from tessera.services import journal_en_attente
from tessera.services.pipeline_events import (
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.pipeline_outcomes import finish_security_block, finish_timeout_expired
from tessera.services.pipeline_rangement import ranger_les_bloques_livres
from tessera.services.pipeline_run import PipelineRun, emit, set_status
from tessera.services.providers.refus_garde import refus_du_tour
from tessera.services.pipeline_text import _extract_criteria, _parse_reviewer_verdict
from tessera.services.quota_exhaustion import is_quota_exhausted
from tessera.services.security_auditor import SecurityAuditResult
from tessera.services.validator_cited_files import format_cited_files_log
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator
    from tessera.services.test_runner import TestResult

_logger = get_logger(__name__)


# ------------------------------------------------------------------
# Préparation
# ------------------------------------------------------------------


async def ensure_clean_tree(
    orch: "Orchestrator", run: PipelineRun
) -> Optional[PipelineResult]:
    """Refuse to start on a tree something outside Tessera has modified.

    Every run now commits its own work, approved or not, so a dirty tree is
    no longer how a rejected run hands off for inspection: it means the tree
    changed behind the pipeline's back. The ticket must not be left in
    `todo` — `pick_next_ticket` would hand back this exact ticket on every
    remaining slot of an autonomous run, burning them all on zero progress.
    """
    if orch._git_workspace is None:
        return None
    try:
        if await orch._git_workspace.is_clean():
            return None
    except GitWorkspaceError as exc:
        _logger.warning("dirty_check_failed", extra={"error": str(exc)})
        return None

    fichiers: list[str] = []
    try:
        fichiers = await orch._git_workspace.dirty_files()
    except GitWorkspaceError:
        pass

    noms = ", ".join(fichiers)
    arret = (
        f"l'arbre contient des modifications hors pipeline : {noms}"
        if noms
        else "l'arbre contient des modifications hors pipeline"
    )

    _logger.warning(
        "dirty_working_tree_refused",
        extra={"ticket_id": run.ticket_id, "fichiers": fichiers},
    )
    await set_status(orch, run, TicketStatus.blocked)
    await emit(
        run, EventType.ERROR,
        reason="dirty_working_tree",
        fichiers=fichiers,
        arret=arret,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=0,
        approved=False,
    )


async def create_branch(
    orch: "Orchestrator", run: PipelineRun
) -> Optional[PipelineResult]:
    """Switch to the ticket's own branch; degrade without one if git is absent.

    Aligns the base ref with the remote before forking (ticket-285).
    Returns a blocked ``PipelineResult`` when the local base has diverged
    from the remote and the run cannot safely start.

    Commits any pending pipeline bookkeeping (pipeline-log, ticket files)
    before switching branches: an interrupted delivery may have left them
    modified in the working tree, causing ``git checkout`` to refuse the
    switch when the base has a different version of those files (ticket-314).
    Only Tessera's own bookkeeping paths are staged — code files are not
    touched.  ``ensure_clean_tree`` still blocks on code modifications before
    this stage is reached.

    Pending pipeline-log lines are the exception: they are set aside before
    that commit and written back into the new branch's log, so that lines
    logged after a delivery's push reach the base with the next run instead
    of being stranded on the delivered branch (ticket-331).
    """
    if orch._git_workspace is None:
        return None

    racine = orch._project_path
    lignes = await journal_en_attente.mettre_de_cote(racine) if racine else []
    try:
        return await _basculer(orch, run, racine, lignes)
    finally:
        # Réécrites même si la branche n'a pas pu être créée : aucune ligne
        # ne se perd. Sans effet si `_basculer` l'a déjà fait.
        _reecrire_journal(racine, lignes)


def _reecrire_journal(racine: Optional[Path], lignes: list[str]) -> None:
    if racine is None:
        return
    try:
        journal_en_attente.reecrire(racine, lignes)
    except OSError as exc:
        _logger.warning("pending_log_rewrite_failed", extra={"error": str(exc)})


async def _realigner_base_au_depart(orch: "Orchestrator") -> Optional[str]:
    """Fast-forward the local base onto the remote before forking (ticket-406).

    The last ticket of a queue is merged by the CIWatcher after the run is
    over, so nobody realigns the base behind it: the next run would fork from
    a base that lags the remote. A tree left on the previous ticket's branch is
    first put back on the base (ticket-457): the pending log lines were already
    set aside by the caller, so the checkout is not in their way. Does nothing
    unless a git workspace and a base branch are known. Returns the refusal
    reason, or ``None`` when the base was realigned or nothing was attempted —
    a refusal (checkout included) never stops the run.
    """
    # getattr : les doubles d'orchestrateur des tests d'étape n'ont pas de base.
    base: Optional[str] = getattr(orch, "_base_branch", None)
    if orch._git_workspace is None or base is None:
        return None
    try:
        if not await orch._sur_la_base():
            await orch._git_workspace.retourner_sur_base(base)
        return await orch._git_workspace.sync_base_depuis_distant(base)
    except GitWorkspaceError as exc:
        _logger.warning("realignement_debut_de_run_echoue", extra={"error": str(exc)})
        return str(exc)


async def _depart_sur_la_base(orch: "Orchestrator") -> bool:
    """True when the tree is on the base branch at the point of forking.

    Bookkeeping must not be committed there: a local commit would make the
    base diverge from the remote (no direct commit on develop or main).
    """
    if orch._git_workspace is None or getattr(orch, "_base_branch", None) is None:
        return False
    try:
        return await orch._sur_la_base()
    except GitWorkspaceError:
        return False


async def _basculer(
    orch: "Orchestrator",
    run: PipelineRun,
    racine: Optional[Path],
    lignes: list[str],
) -> Optional[PipelineResult]:
    assert orch._git_workspace is not None

    # Avant tout commit de tenue de livres : le journal est déjà mis de côté,
    # l'arbre est donc propre pour l'avance rapide de la base (ticket-406).
    raison_base = await _realigner_base_au_depart(orch)

    # Les tickets bloqués puis livrés à la main passent en `done` sur la base
    # réalignée, avant le commit de tenue de livres qui les emporte (ticket-482).
    lignes_rangement = await ranger_les_bloques_livres(orch, run.ticket_id)

    # Commit pending bookkeeping before the branch switch.  Failures here
    # are logged but not fatal: the following branch creation attempt may
    # still succeed, and a missing bookkeeping commit is better than a
    # blocked pipeline when git is not fully configured.
    # Pas sur la base : un commit local la ferait diverger du distant. Les
    # modifications de `tickets/` suivent alors la branche du ticket (ticket-457).
    try:
        if not await _depart_sur_la_base(orch):
            await orch._git_workspace.commit_bookkeeping()
    except GitWorkspaceError as exc:
        _logger.warning("bookkeeping_before_branch_failed", extra={"error": str(exc)})

    try:
        # Sync base_branch with remote before forking the ticket branch (ticket-285).
        # A diverged local base blocks the run immediately rather than producing
        # a PR that GitHub will immediately reject.
        # Un ticket qui dépend d'un autre ne part jamais d'une base locale
        # faute de lire le distant : elle peut précéder le merge attendu
        # (ticket-340).
        raison_blocage = await orch._git_workspace.initialiser_base_ref(
            exiger_distant=bool(run.ticket.depends_on)
        )
        if raison_blocage is not None:
            _logger.warning("base_divergee_blocage", extra={"raison": raison_blocage})
            await set_status(orch, run, TicketStatus.blocked)
            await emit(run, EventType.ERROR, reason=raison_blocage)
            return PipelineResult(
                ticket_id=run.ticket_id,
                final_status=TicketStatus.blocked,
                rounds=0,
                approved=False,
                arret=raison_blocage,
            )
        run.branch = await orch._git_workspace.create_branch(
            run.ticket_id, run.ticket.title
        )
        # Avant la ligne « branche » : le journal garde son ordre.
        _reecrire_journal(racine, lignes)
        await emit(run, EventType.BRANCH_CREATED, branch=run.branch)
        orch._log(f"[{run.ticket_id}] branche {run.branch}")
        # Journalisé ici et non plus tôt : une ligne écrite avant le commit de
        # tenue de livres partirait en commit sur la base locale.
        if raison_base is not None:
            orch._log(f"[{run.ticket_id}] base non réalignée — {raison_base}")
        for ligne in lignes_rangement:
            orch._log(ligne)
    except NotAGitRepository:
        # Un projet sans dépôt git reste utilisable : on continue sans
        # garde-fou de branche plutôt que d'interrompre le pipeline.
        _logger.warning("branch_creation_no_repo", extra={"ticket_id": run.ticket_id})
    except GitWorkspaceError as exc:
        # Any other git error on a real repository: block the run (ADR-037,
        # ticket-314).  Running a ticket on the wrong branch — or without a
        # branch at all — lets subsequent commits land on whatever ref was
        # checked out, mixing unrelated work across tickets.
        arret = str(exc)
        _logger.warning("branch_creation_failed", extra={"error": arret})
        await set_status(orch, run, TicketStatus.blocked)
        await emit(run, EventType.ERROR, reason=arret)
        return PipelineResult(
            ticket_id=run.ticket_id,
            final_status=TicketStatus.blocked,
            rounds=0,
            approved=False,
            arret=arret,
        )
    return None


def take_artifact_snapshot(orch: "Orchestrator", run: PipelineRun) -> None:
    """Take a snapshot of memory/ and tickets/ before any agent runs.

    Stored in ``run.artifact_snapshot`` and used at the end of each coder turn
    to produce the artifact diff — a textual view of what the agent wrote in
    Tessera's own directories, which are excluded from the git diff either
    because the project is in local-artifact mode (ADR-021) or because
    ``_ORCHESTRATOR_ARTIFACT_PATHS`` excludes them from the reviewed diff.

    Called once per run, before the first tour.  No-op when no project path is
    configured (tests, projects without a filesystem path).
    """
    if orch._project_path is None:
        return
    run.artifact_snapshot = snapshot_artifacts(orch._project_path)


def build_context(orch: "Orchestrator", run: PipelineRun) -> str:
    """Project context, reviewer feedback so far, and anything the user said.

    This is where the user's in-flight messages enter the run (ticket-066).
    Every stage builds its context here, so draining the mailbox at this one
    point is what makes an interjection reach *the next agent to speak*, no
    matter which one it is.

    The mailbox is drained, not read: a message injected twice would be
    repeated at every round, and the context would grow a little more each
    time.
    """
    parts = [orch._project_context]

    # Le plan précède les retours : le codeur le suit, le reviewer juge
    # l'écart (ticket-243). Il reste dans le contexte du tour, donc dans les
    # reprises : c'est court, et c'est ce qui dit où le travail doit aller.
    if run.plan:
        parts.append(f"\n\n## Plan retenu avant le code\n{run.plan}")

    if run.review_feedback:
        parts.append(
            "\n\n## Retours reviewer précédents\n"
            + "\n---\n".join(
                f"Tour {i + 1}: {fb}" for i, fb in enumerate(run.review_feedback)
            )
        )

    if messages := run.dialogue.drain():
        parts.append(
            "\n\n## Consignes de l'utilisateur, en cours de run\n"
            + "\n".join(f"- {m}" for m in messages)
        )

    # Gardé à part pour le codeur qui reprend sa session (ticket-187) : la
    # boîte aux lettres est vidée ici, une seconde construction ne retrouverait
    # plus les consignes.
    run.contexte_du_tour = "".join(parts[1:]).strip()
    return "".join(parts)


def asker_for(run: PipelineRun) -> Optional[Callable[[str], Awaitable[str]]]:
    """L'outil `ask_user` à donner à l'agent, ou rien (ticket-066).

    Un run non interactif — appel programmatique, test, run autonome — ne doit
    pas recevoir l'outil : l'agent y attendrait le délai complet d'ADR-025 à
    chaque question, sans que personne ne puisse jamais y répondre.
    """
    return run.dialogue.ask if run.dialogue.interactive else None


# ------------------------------------------------------------------
# Codeur
# ------------------------------------------------------------------


def journaliser_refus_cli(
    orch: "Orchestrator", ticket_id: str, role: AgentRole, outils: list[str]
) -> None:
    """Writes one journal line per tool the embedded CLI refused (ticket-515).

    Sans cette ligne le refus restait invisible : le tour finissait « normalement »
    alors que l'agent s'était arrêté sur un outil qu'on ne lui avait pas laissé.
    """
    for nom in outils:
        orch._log(f"[{ticket_id}] {role.value}: outil {nom} refusé par le CLI")


async def run_coder(orch: "Orchestrator", run: PipelineRun, context: str) -> None:
    """Run the coder, then capture what it actually wrote to disk."""
    # Un ticket `design` ne demande pas du code mais une décision, et
    # `ide-core/CLAUDE.md` promettait l'architecte dessus depuis le premier
    # commit sans que rien ne route par type (ticket-098). L'étape reste la
    # même — quelqu'un produit le travail — seul le rôle change. Les
    # événements portent ce rôle, pas `codeur` en dur : l'UI montrait un
    # codeur au travail quand l'architecte produisait (ticket-122).
    role = _role_qui_produit(run.ticket.type)
    codeur_cfg = orch._config_for(role)
    ticket_id = run.ticket_id

    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_STARTED,
            agent=role,
            ticket_id=ticket_id,
            data={"round": run.round_num},
        )
    )
    orch._log(f"[{ticket_id}] tour {run.round_num} — codeur démarré")

    async def _emit_token(token: str, tid: str = ticket_id) -> None:
        await run.on_event(
            OrchestratorEvent(
                type=EventType.AGENT_TOKEN,
                agent=role,
                ticket_id=tid,
                data={"token": token},
            )
        )

    async def _emit_tool(name: str, payload: dict[str, Any], tid: str = ticket_id) -> None:
        await run.on_event(
            OrchestratorEvent(
                type=EventType.AGENT_TOOL_USE,
                agent=role,
                ticket_id=tid,
                data={"tool": name, "input": payload},
            )
        )

    # Comme au niveau du provider : le paramètre n'est transmis que s'il y a
    # quelque chose à transmettre. Un run non interactif appelle donc le
    # runner exactement comme avant ce ticket.
    asker = asker_for(run)
    extra: dict[str, Any] = {"ask_user": asker} if asker is not None else {}

    # Au tour suivant, le codeur reprend sa conversation et ne reçoit que ce
    # que le tour ajoute : le ticket, les ADR et le dépôt, il les a déjà lus
    # (ticket-187). Sans session — premier tour, provider muet — l'appel
    # reste complet.
    if run.session_codeur is not None:
        extra["session"] = run.session_codeur
        context = run.contexte_du_tour
    elif run.carte_du_depot:
        # La carte précède le contexte : `adr_pertinents` découpe tout ce qui
        # suit « Décisions récentes » en ADR, et une carte placée après serait
        # avalée par le dernier d'entre eux (ticket-190). Le reviewer ne la
        # reçoit pas : il part du diff.
        context = (
            "## Fichiers du projet\n"
            "Lis ce dont tu as besoin ; ne relis pas cette carte.\n\n"
            f"{run.carte_du_depot}\n\n{context}"
        )

    # Ce qu'un rôle antérieur (le plan) aurait refusé n'est pas le tour du codeur.
    refus_du_tour(orch)
    codeur_result = await orch._runner.run(
        role=role,
        ticket=run.ticket,
        project_context=context,
        agent_config=codeur_cfg,
        stream_callback=_emit_token,
        tool_callback=_emit_tool,
        run_id=run.run_id,
        **extra,
    )
    if codeur_result.session_id is not None:
        run.session_codeur = codeur_result.session_id
    journaliser_refus_cli(orch, ticket_id, role, codeur_result.outils_refuses)
    orch.record_spend(codeur_result.cost_usd)
    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_DONE,
            agent=role,
            ticket_id=ticket_id,
            # Le coût part avec la fin de l'appel : c'est pendant le run
            # qu'on décide de l'arrêter (ticket-197).
            data={
                "content": codeur_result.content,
                "cost_usd": codeur_result.cost_usd,
                "duration_ms": codeur_result.duration_ms,
            },
        )
    )
    orch._log(
        f"[{ticket_id}] tour {run.round_num} — {role.value} terminé "
        f"({codeur_result.duration_ms}ms)"
    )

    run.refus_du_tour = refus_du_tour(orch)
    run.reviewed_code = await _capture_diff(orch, run, codeur_result.content)
    _capture_artifact_diff(orch, run)
    await set_status(orch, run, TicketStatus.in_review)


async def _capture_diff(orch: "Orchestrator", run: PipelineRun, prose: str) -> str:
    """The real diff if there is one, the coder's prose as a last resort.

    Le codeur écrit réellement sur disque : ce qui doit être relu, audité et
    validé, c'est le diff, pas la prose de l'agent.

    Sur une branche reprise (second run du même ticket), `diff_depuis_base`
    étend le diff jusqu'au point de divergence de la branche : l'audit
    sécurité, le reviewer et le validateur voient tout le travail accumulé,
    pas seulement ce que le dernier tour n'a pas encore commité (ticket-208).
    Une seule fonction calcule le diff — `reviewed_code` est posé ici et les
    trois portes le lisent, sans recalcul.
    """
    if orch._git_workspace is None:
        return prose
    try:
        diff = await orch._git_workspace.diff_depuis_base()
    except GitWorkspaceError as exc:
        _logger.warning("diff_failed", extra={"error": str(exc)})
        _logger.info("diff_empty_fallback_to_prose", extra={"ticket_id": run.ticket_id})
        return prose
    if diff.strip():
        return diff
    _logger.info("diff_empty_fallback_to_prose", extra={"ticket_id": run.ticket_id})
    return prose


def _capture_artifact_diff(orch: "Orchestrator", run: PipelineRun) -> None:
    """Compute and store the artifact diff since run start.

    Populates ``run.artifact_diff`` with the textual diff of memory/ and
    tickets/ since the snapshot taken by ``take_artifact_snapshot``.  No-op
    when no snapshot exists (no project path, or not yet taken).

    This diff is intentionally kept separate from ``run.reviewed_code`` (the
    git diff): it is passed to the reviewer and the validator but never
    committed, so it does not affect what ends up in the repository.
    """
    if orch._project_path is None or run.artifact_snapshot is None:
        return
    run.artifact_diff = diff_artifacts(run.artifact_snapshot, orch._project_path)


def _role_qui_produit(type_de_ticket: "TicketType") -> AgentRole:
    """Qui tient l'étape « quelqu'un produit le travail », selon le ticket.

    Un ticket `design` appelle une décision d'architecture, pas du code. Le
    reste du pipeline est inchangé : le même reviewer relit, le même commit
    conclut.
    """
    if type_de_ticket is TicketType.design:
        return AgentRole.architect
    return AgentRole.codeur


# ------------------------------------------------------------------
# Testeur
# ------------------------------------------------------------------


def _noter_le_delai(orch: "Orchestrator", run: PipelineRun, result: "TestResult") -> None:
    """Log a timeout with its step durations and hand the same list to the coder.

    Le résumé du résultat porte déjà la liste des étapes (``TestRunnerService``) :
    ``test_context`` la reprend une seule fois. Le codeur ne la lit que par
    ``verifier_travail_repris``, qui la copie dans ses retours (ticket-514).
    """
    orch._log(f"[{run.ticket_id}] testeur: {ligne_de_delai(result)}")
    if detail_du_delai(result):
        run.test_context = f"\n\n## Résultats des tests ⏱\n{result.output_summary}\n"


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

    from tessera.services.test_runner import TestCommandNotFound

    try:
        async def _on_attente() -> None:
            orch._log(f"[{run.ticket_id}] testeur: en attente d'un créneau de test")

        result = await orch._test_runner.run_tests(
            orch._project_path,
            test_command=orch._test_command,
            en_attente=_on_attente,
        )

        # Un timeout ne dit rien sur le code : relancer une fois sans repasser
        # par le codeur est moins coûteux qu'un tour complet (ticket-349).
        if result.expiree:
            orch._log(
                f"[{run.ticket_id}] testeur: délai dépassé, suite relancée"
            )
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


# ------------------------------------------------------------------
# Sécurité
# ------------------------------------------------------------------


def _quota_epuise(orch: "Orchestrator", exc: BaseException) -> bool:
    """True when ``exc`` is an exhausted quota, read with the last snapshot.

    Such an exception must reach `run_pipeline`, which ends the run as a quota
    stop (ticket-498) ; any other failure keeps the closed-fail verdict.
    """
    # `getattr` : les doubles d'orchestrateur des tests d'étape n'ont pas de quota.
    tracker = getattr(orch, "quota", None)
    return is_quota_exhausted(exc, tracker.snapshot if tracker is not None else None)


async def run_security_audit(
    orch: "Orchestrator", run: PipelineRun
) -> Optional[PipelineResult]:
    """Audit the diff. A CRITICAL/HIGH verdict ends the run before the reviewer.

    Échoue fermé : une exception de l'auditeur sautait l'audit et le diff
    arrivait au reviewer comme s'il était propre (ticket-122).
    """
    if not (orch._security_auditor and orch._project_path):
        return None

    await emit(run, EventType.SECURITY_AUDIT_STARTED, round=run.round_num)
    t0 = time.monotonic()
    try:
        audit = await orch._security_auditor.audit(
            code_diff=run.reviewed_code, project_path=orch._project_path
        )
    except Exception as exc:
        if _quota_epuise(orch, exc):
            raise
        _logger.warning("security_auditor_failed", extra={"error": str(exc)})
        reason = f"Audit sécurité en panne : {exc}"
        audit = SecurityAuditResult(
            issues=[], verdict="BLOCK", summary=reason, reason=reason
        )
    audit_ms = int((time.monotonic() - t0) * 1000)

    if audit.fallback_reason:
        await emit(
            run, EventType.SECURITY_AUDIT_FALLBACK, reason=audit.fallback_reason
        )
    await emit(
        run,
        EventType.SECURITY_AUDIT_DONE,
        verdict=audit.verdict,
        issues_count=len(audit.issues),
        has_critical=audit.has_critical,
        has_high=audit.has_high,
        summary=audit.summary,
        reason=audit.reason,
    )
    orch._log(
        f"[{run.ticket_id}] securite: {audit.verdict} — {audit.summary[:80]} ({audit_ms}ms)"
    )

    if audit.verdict == "BLOCK":
        return await finish_security_block(orch, run, audit.summary)

    # PASS — les MEDIUM/LOW remontent au reviewer comme avertissements.
    if audit.issues:
        warnings = "\n".join(
            f"- [{i.severity}] {i.type} @ {i.location}: {i.description}"
            for i in audit.issues
        )
        run.security_context = f"\n\n## Audit sécurité (avertissements)\n{warnings}"
    return None


# ------------------------------------------------------------------
# Reviewer et validateur
# ------------------------------------------------------------------


def _avertissement_config_tests(orch: "Orchestrator", run: PipelineRun) -> str:
    """Warning opening the reviewer's message when the diff touches test config.

    Returns an empty string when it does not. The line in the pipeline log
    names the files, so the signal outlives the reviewer's answer (ticket-490).
    """
    chemin = orch._project_path
    racines = [chemin.resolve(), *chemin.resolve().parents] if chemin else []
    fichiers = fichiers_de_config_touches(run.reviewed_code, racines)
    if fichiers:
        orch._log(
            f"[{run.ticket_id}] configuration des tests modifiée : "
            + ", ".join(fichiers)
        )
    return avertissement_config_tests(fichiers)


async def run_review(
    orch: "Orchestrator", run: PipelineRun, context: str
) -> tuple[bool, str, str]:
    """Review the diff. Returns (approved, reason, raw verdict text)."""
    reviewer_cfg = orch._config_for(AgentRole.reviewer)
    ticket_id = run.ticket_id

    review_context = (
        _avertissement_config_tests(orch, run)
        + context
        + f"\n\n## Code produit par le codeur (tour {run.round_num})\n{run.reviewed_code}"
        + run.artifact_diff
        + run.refus_du_tour
        + run.test_context
        + run.security_context
    )

    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_STARTED,
            agent=AgentRole.reviewer,
            ticket_id=ticket_id,
            data={"round": run.round_num},
        )
    )
    orch._log(f"[{ticket_id}] tour {run.round_num} — reviewer démarré")

    reviewer_result = await orch._runner.run(
        role=AgentRole.reviewer,
        ticket=run.ticket,
        project_context=review_context,
        agent_config=reviewer_cfg,
        run_id=run.run_id,
    )
    orch.record_spend(reviewer_result.cost_usd)
    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_DONE,
            agent=AgentRole.reviewer,
            ticket_id=ticket_id,
            data={
                "content": reviewer_result.content,
                "cost_usd": reviewer_result.cost_usd,
                "duration_ms": reviewer_result.duration_ms,
            },
        )
    )
    orch._log(
        f"[{ticket_id}] tour {run.round_num} — reviewer terminé ({reviewer_result.duration_ms}ms)"
    )

    approved, reason = _parse_reviewer_verdict(reviewer_result.content)
    return approved, reason, reviewer_result.content


async def run_validation(
    orch: "Orchestrator", run: PipelineRun
) -> tuple[bool, str]:
    """Check the ticket's acceptance criteria independently of the reviewer.

    Returns ``(True, "")`` when the validator is absent or approves,
    ``(False, feedback)`` when it refuses or is unavailable.
    """
    if orch._validator is None:
        return True, ""
    await emit(run, EventType.VALIDATION_STARTED)
    t0 = time.monotonic()
    # Transmis seulement quand il y a un refus : un validateur qui ne connaît
    # pas ce paramètre est appelé comme avant ticket-476.
    extra = {"refus": run.refus_du_tour} if run.refus_du_tour else {}
    try:
        validation = await orch._validator.validate(
            criteria=_extract_criteria(run.ticket.body),
            code_produced=run.reviewed_code + run.artifact_diff,
            test_result=run.test_result,
            project_root=orch._project_path,
            ticket_type=run.ticket.type,
            **extra,
        )
    except Exception as exc:
        if _quota_epuise(orch, exc):
            raise
        # Échoue fermé, comme l'audit : une validation qui n'a pas eu lieu
        # n'approuve rien (ticket-122).
        _logger.warning("validator_failed", extra={"error": str(exc)})
        return False, f"Validation en panne : {exc}"
    validation_ms = int((time.monotonic() - t0) * 1000)

    await emit(
        run,
        EventType.VALIDATION_DONE,
        verdict=validation.verdict,
        # Le frontend lit `approved` pour afficher le statut ; le fallback sur
        # `verdict` existe côté frontend, mais le champ explicite est plus fiable
        # (ticket-279).
        approved=(validation.verdict == "APPROVED"),
        all_passed=validation.all_passed,
        feedback=validation.feedback,
        criteria=[
            {"criterion": c.criterion, "passed": c.passed, "note": c.note}
            for c in validation.criteria
        ],
    )
    if validation.cited_files is not None:
        cited_line = format_cited_files_log(validation.cited_files)
        if cited_line:
            orch._log(f"[{run.ticket_id}] {cited_line}")
    orch._log(
        f"[{run.ticket_id}] validateur: {validation.verdict} — "
        f"{validation.feedback[:80]} ({validation_ms}ms)"
    )
    if validation.verdict == "CHANGES_REQUESTED":
        return False, validation.feedback
    return True, ""

