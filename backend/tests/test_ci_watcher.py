"""CIWatcher — tâche de fond pour la CI et le merge — ticket-306.

Couverture :
- Une seconde livraison du même projet attend la première.
- Deux projets différents ne s'attendent pas.
- CI verte → merge, ci_merge_done avec merged=True.
- CI rouge → ticket blocked, ci_merge_done avec merged=False et arret contenant le numéro de PR.
- en_attente liste le ticket pendant l'attente, plus après ci_merge_done.
- Arrêt : les tâches en cours sont annulées sans lever d'exception.
- Exception dans livraison_phase_2 → ci_merge_done(merged=False) avec message d'erreur (ticket-328).
- Exception → ticket passe en blocked (ticket-328).
- Timeout de la phase 2 → ci_merge_done(merged=False) avec 'délai dépassé' (ticket-328).
- Annulation à l'arrêt → aucun ci_merge_done émis (ticket-328).
- Merge raté → pipeline-log.md écrit, aucun fichier tickets/ déplacé (ticket-392).
- Merge raté → attendre_merge retourne False (ticket-392).
- Erreur réseau puis PR mergée → succès journalisé ; exception sans texte nommée (ticket-405).
"""
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from tessera.models.ticket import TicketStatus
from tessera.services.ci_watcher import CIWatcher, decrire_exception
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import EventType, OrchestratorEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _rien(event: OrchestratorEvent) -> None:
    """No-op event callback."""


async def _phase2_success(pr_number: int) -> Livraison:
    return Livraison(pr_number=pr_number, merged=True)


async def _phase2_red_ci(pr_number: int) -> Livraison:
    return Livraison(
        pr_number=pr_number,
        merged=False,
        arret=f"CI failing : la PR #{pr_number} reste ouverte.",
    )


def _collecteur() -> tuple[
    list[OrchestratorEvent],
    Callable[[OrchestratorEvent], Awaitable[None]],
]:
    """Returns (events_list, callback) to collect emitted events."""
    events: list[OrchestratorEvent] = []

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    return events, collect


# ---------------------------------------------------------------------------
# Sérialisation par projet
# ---------------------------------------------------------------------------


async def test_seconde_livraison_meme_projet_attend_la_premiere() -> None:
    """A second delivery for the same project waits for the first to finish."""
    watcher = CIWatcher()
    ordre: list[str] = []
    gate = asyncio.Event()

    async def phase2_sequentielle(pr_number: int) -> Livraison:
        await gate.wait()
        ordre.append(f"pr{pr_number}")
        return Livraison(pr_number=pr_number, merged=True)

    events, collect = _collecteur()

    await watcher.surveiller("proj", "ticket-001", 1, phase2_sequentielle, collect)
    await watcher.surveiller("proj", "ticket-002", 2, phase2_sequentielle, collect)

    # Pendant l'attente, les deux tickets sont inscrits.
    await asyncio.sleep(0)
    assert set(watcher.en_attente("proj")) == {"ticket-001", "ticket-002"}

    gate.set()
    await asyncio.sleep(0.05)

    # Ordre séquentiel : ticket-001 avant ticket-002.
    assert ordre == ["pr1", "pr2"]

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 2
    assert done[0].data["ticket_id"] == "ticket-001"
    assert done[1].data["ticket_id"] == "ticket-002"


async def test_deux_projets_differents_ne_s_attendent_pas() -> None:
    """Two different projects run their deliveries concurrently."""
    watcher = CIWatcher()
    en_cours: list[str] = []
    max_concurrence: list[int] = []

    def _faire_phase2(project_id: str) -> Callable[[int], Awaitable[Livraison]]:
        async def _phase2(pr_number: int) -> Livraison:
            en_cours.append(project_id)
            max_concurrence.append(len(en_cours))
            await asyncio.sleep(0.01)
            en_cours.remove(project_id)
            return Livraison(pr_number=pr_number, merged=True)

        return _phase2

    await watcher.surveiller("proj-a", "ticket-001", 1, _faire_phase2("proj-a"), _rien)
    await watcher.surveiller("proj-b", "ticket-002", 2, _faire_phase2("proj-b"), _rien)

    await asyncio.sleep(0.05)

    # Les deux ont tourné en même temps (concurrence maximale = 2).
    assert max(max_concurrence) == 2


# ---------------------------------------------------------------------------
# CI verte → merge
# ---------------------------------------------------------------------------


async def test_ci_verte_emet_ci_merge_done_merged_true() -> None:
    """Green CI emits ci_merge_done with merged=True and arret=None."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    await watcher.surveiller("proj", "ticket-001", 42, _phase2_success, collect)
    await asyncio.sleep(0.05)

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 1
    assert done[0].data["merged"] is True
    assert done[0].data["arret"] is None
    assert done[0].data["pr_number"] == 42
    assert done[0].data["project_id"] == "proj"
    assert done[0].data["ticket_id"] == "ticket-001"


# ---------------------------------------------------------------------------
# CI rouge → blocked
# ---------------------------------------------------------------------------


async def test_ci_rouge_emet_ticket_blocked_et_ci_merge_done_merged_false() -> None:
    """Red CI emits ticket_status_changed(blocked) then ci_merge_done(merged=False)."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    await watcher.surveiller("proj", "ticket-001", 7, _phase2_red_ci, collect)
    await asyncio.sleep(0.05)

    status_events = [e for e in events if e.type is EventType.TICKET_STATUS_CHANGED]
    assert len(status_events) == 1
    assert status_events[0].data["status"] == TicketStatus.blocked.value

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 1
    assert done[0].data["merged"] is False
    # L'arret contient le numéro de la PR.
    assert "7" in done[0].data["arret"]
    assert done[0].data["pr_number"] == 7


# ---------------------------------------------------------------------------
# en_attente
# ---------------------------------------------------------------------------


async def test_en_attente_liste_le_ticket_pendant_l_attente_puis_plus_apres() -> None:
    """en_attente lists the ticket during the wait, then removes it after ci_merge_done."""
    watcher = CIWatcher()
    gate = asyncio.Event()

    async def phase2_bloquante(pr_number: int) -> Livraison:
        await gate.wait()
        return Livraison(pr_number=pr_number, merged=True)

    await watcher.surveiller("proj", "ticket-001", 1, phase2_bloquante, _rien)
    await asyncio.sleep(0)

    # Pendant l'attente : listé.
    assert "ticket-001" in watcher.en_attente("proj")

    gate.set()
    await asyncio.sleep(0.05)

    # Après ci_merge_done : retiré.
    assert "ticket-001" not in watcher.en_attente("proj")


async def test_en_attente_projet_inconnu_retourne_tuple_vide() -> None:
    watcher = CIWatcher()
    assert watcher.en_attente("projet-inconnu") == ()


# ---------------------------------------------------------------------------
# Arrêt
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# attendre_merge — ticket-307
# ---------------------------------------------------------------------------


async def test_attendre_merge_retourne_immediatement_si_deja_fini() -> None:
    """attendre_merge returns immediately when the ticket is no longer waiting."""
    watcher = CIWatcher()
    # Le ticket n'est pas dans _en_attente → retour immédiat.
    await watcher.attendre_merge("proj", "ticket-001")  # no hang


async def test_attendre_merge_non_inscrit_sans_pr_retourne_true() -> None:
    """Without a PR number there is nothing to wait for: True, as before."""
    assert await CIWatcher().attendre_merge("proj", "ticket-001") is True


async def test_attendre_merge_non_inscrit_pr_ouverte_ne_retourne_pas_true() -> None:
    """An unregistered ticket whose PR is still open is not merged."""
    watcher = CIWatcher()
    merge = await watcher.attendre_merge(
        "proj", "ticket-001", pr_number=14, etat_pr=_lecture_pr("open")
    )
    assert merge is False


async def test_attendre_merge_non_inscrit_pr_mergee_retourne_true() -> None:
    """An unregistered ticket whose PR is merged counts as merged."""
    watcher = CIWatcher()
    merge = await watcher.attendre_merge(
        "proj", "ticket-001", pr_number=14, etat_pr=_lecture_pr("merged")
    )
    assert merge is True


async def test_attendre_merge_non_inscrit_sans_lecteur_echoue_ferme() -> None:
    """No way to read the PR: fails closed, it is not merged."""
    merge = await CIWatcher().attendre_merge("proj", "ticket-001", pr_number=14)
    assert merge is False


async def test_attendre_merge_non_inscrit_lecture_en_erreur_echoue_ferme() -> None:
    """A reader that raises is not a proof of merge."""

    async def lire(pr_number: int) -> str:
        raise httpx.ReadTimeout("")

    merge = await CIWatcher().attendre_merge(
        "proj", "ticket-001", pr_number=14, etat_pr=lire
    )
    assert merge is False


async def test_surveiller_purge_le_resultat_d_une_surveillance_precedente() -> None:
    """A stale merged result is never read back as the new PR's outcome."""
    watcher = CIWatcher()
    gate = asyncio.Event()

    async def phase2_bloquante(pr_number: int) -> Livraison:
        await gate.wait()
        return Livraison(pr_number=pr_number, merged=False, arret="CI rouge")

    watcher._resultats_merge["proj:ticket-001"] = True
    await watcher.surveiller("proj", "ticket-001", 2, phase2_bloquante, _rien)
    gate.set()
    await asyncio.sleep(0.05)

    assert await watcher.attendre_merge("proj", "ticket-001") is False


async def test_attendre_merge_suspend_jusqu_a_la_fin() -> None:
    """attendre_merge suspends the caller until ci_merge_done is emitted."""
    watcher = CIWatcher()
    gate = asyncio.Event()
    termine: list[bool] = []

    async def phase2_bloquante(pr_number: int) -> Livraison:
        await gate.wait()
        return Livraison(pr_number=pr_number, merged=True)

    await watcher.surveiller("proj", "ticket-001", 1, phase2_bloquante, _rien)
    await asyncio.sleep(0)

    assert "ticket-001" in watcher.en_attente("proj")

    async def _attendre() -> None:
        await watcher.attendre_merge("proj", "ticket-001")
        termine.append(True)

    tache = asyncio.create_task(_attendre())
    await asyncio.sleep(0)

    # Pas encore terminé.
    assert termine == []

    gate.set()
    await asyncio.sleep(0.05)

    # Terminé après que la gate a été levée.
    assert termine == [True]
    await tache


async def test_attendre_merge_deux_appelants() -> None:
    """Multiple waiters on the same ticket are all unblocked."""
    watcher = CIWatcher()
    gate = asyncio.Event()
    termines: list[int] = []

    async def phase2_bloquante(pr_number: int) -> Livraison:
        await gate.wait()
        return Livraison(pr_number=pr_number, merged=True)

    await watcher.surveiller("proj", "ticket-001", 1, phase2_bloquante, _rien)
    await asyncio.sleep(0)

    async def _attendre(n: int) -> None:
        await watcher.attendre_merge("proj", "ticket-001")
        termines.append(n)

    t1 = asyncio.create_task(_attendre(1))
    t2 = asyncio.create_task(_attendre(2))
    await asyncio.sleep(0)

    assert termines == []

    gate.set()
    await asyncio.sleep(0.05)

    assert sorted(termines) == [1, 2]
    await t1
    await t2


async def test_arret_annule_les_taches_sans_lever() -> None:
    """arreter() cancels running tasks without raising any exception."""
    watcher = CIWatcher()
    started = asyncio.Event()

    async def phase2_infinie(pr_number: int) -> Livraison:
        started.set()
        await asyncio.sleep(3600)
        return Livraison(pr_number=pr_number, merged=True)

    await watcher.surveiller("proj", "ticket-001", 1, phase2_infinie, _rien)
    await started.wait()

    # Ne doit pas lever d'exception.
    await watcher.arreter()

    # Après l'arrêt, plus de tâches actives.
    assert len(watcher._taches) == 0


# ---------------------------------------------------------------------------
# Erreur dans livraison_phase_2 — ticket-328
# ---------------------------------------------------------------------------


async def test_exception_emet_ci_merge_done_avec_arret() -> None:
    """An exception in livraison_phase_2 emits ci_merge_done(merged=False) with the message."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    async def phase2_qui_explose(pr_number: int) -> Livraison:
        raise RuntimeError("connexion refusée")

    await watcher.surveiller("proj", "ticket-001", 7, phase2_qui_explose, collect)
    await asyncio.sleep(0.05)

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 1
    assert done[0].data["merged"] is False
    assert "connexion refusée" in done[0].data["arret"]
    assert done[0].data["pr_number"] == 7
    assert done[0].data["ticket_id"] == "ticket-001"


async def test_exception_passe_le_ticket_en_blocked() -> None:
    """An exception in livraison_phase_2 transitions the ticket to blocked."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    async def phase2_qui_explose(pr_number: int) -> Livraison:
        raise RuntimeError("boom")

    await watcher.surveiller("proj", "ticket-001", 7, phase2_qui_explose, collect)
    await asyncio.sleep(0.05)

    status_events = [e for e in events if e.type is EventType.TICKET_STATUS_CHANGED]
    assert len(status_events) == 1
    assert status_events[0].data["status"] == TicketStatus.blocked.value

    # L'ordre doit être : blocked d'abord, puis ci_merge_done.
    types = [e.type for e in events]
    assert types.index(EventType.TICKET_STATUS_CHANGED) < types.index(EventType.CI_MERGE_DONE)


async def test_timeout_emet_ci_merge_done_avec_arret_delai_depasse() -> None:
    """Phase 2 timeout emits ci_merge_done(merged=False) with 'délai dépassé'."""
    watcher = CIWatcher(timeout_phase2_s=0.02)  # délai très court pour le test
    events, collect = _collecteur()

    async def phase2_infinie(pr_number: int) -> Livraison:
        await asyncio.sleep(3600)
        return Livraison(pr_number=pr_number, merged=True)

    await watcher.surveiller("proj", "ticket-001", 5, phase2_infinie, collect)
    await asyncio.sleep(0.15)

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 1
    assert done[0].data["merged"] is False
    assert "délai" in done[0].data["arret"]
    assert done[0].data["pr_number"] == 5


async def test_arret_backend_n_emet_pas_de_ci_merge_done() -> None:
    """Backend shutdown (arreter) does not emit a false ci_merge_done."""
    watcher = CIWatcher()
    events, collect = _collecteur()
    started = asyncio.Event()

    async def phase2_infinie(pr_number: int) -> Livraison:
        started.set()
        await asyncio.sleep(3600)
        return Livraison(pr_number=pr_number, merged=True)

    await watcher.surveiller("proj", "ticket-001", 1, phase2_infinie, collect)
    await started.wait()

    await watcher.arreter()

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert done == [], "un arrêt propre ne doit pas émettre ci_merge_done"


# ---------------------------------------------------------------------------
# Merge raté → pipeline log sans déplacement de fichier — ticket-392
# ---------------------------------------------------------------------------


async def test_phase2_echouee_ne_deplace_pas_les_fichiers_tickets(
    tmp_path: Path,
) -> None:
    """A failed phase 2 must not move or modify any file under tickets/."""
    import frontmatter as _fm

    # Créer une fiche dans tickets/todo/.
    tickets_dir = tmp_path / "tickets" / "todo"
    tickets_dir.mkdir(parents=True)
    ticket_file = tickets_dir / "ticket-007-fix-bug.md"
    post = _fm.Post(
        "",
        id="ticket-007",
        title="Fix bug",
        type="feat",
        status="in_progress",
        priority="medium",
        agent="codeur",
        depends_on=[],
    )
    original_content = _fm.dumps(post)
    ticket_file.write_text(original_content, encoding="utf-8")

    log_path = tmp_path / "memory" / "pipeline-log.md"
    watcher = CIWatcher()

    await watcher.surveiller(
        "proj", "ticket-007", 10, _phase2_red_ci, _rien,
        pipeline_log_path=log_path,
    )
    await asyncio.sleep(0.1)

    # Aucun fichier ne doit avoir été déplacé ni créé dans tickets/.
    all_ticket_files = list((tmp_path / "tickets").rglob("*.md"))
    assert all_ticket_files == [ticket_file], (
        f"Aucune fiche ne doit être déplacée, got: {all_ticket_files}"
    )
    # Le contenu de la fiche ne doit pas avoir changé.
    assert ticket_file.read_text(encoding="utf-8") == original_content, (
        "Le contenu de la fiche ne doit pas avoir été modifié."
    )


async def test_phase2_echouee_emet_blocked_et_ecrit_log(
    tmp_path: Path,
) -> None:
    """A failed phase 2 emits ticket_status_changed(blocked) and writes to pipeline-log.md."""
    log_path = tmp_path / "memory" / "pipeline-log.md"
    watcher = CIWatcher()
    events, collect = _collecteur()

    await watcher.surveiller(
        "proj", "ticket-007", 10, _phase2_red_ci, collect,
        pipeline_log_path=log_path,
    )
    await asyncio.sleep(0.1)

    # L'événement ticket_status_changed(blocked) doit être émis.
    status_events = [e for e in events if e.type is EventType.TICKET_STATUS_CHANGED]
    assert len(status_events) == 1
    assert status_events[0].data["status"] == TicketStatus.blocked.value

    # Le pipeline-log.md doit être écrit avec la ligne de blocage.
    assert log_path.exists(), "pipeline-log.md doit avoir été créé"
    log_content = log_path.read_text(encoding="utf-8")
    assert "PR #10 non mergée" in log_content, (
        f"Le log doit mentionner 'PR #10 non mergée', got:\n{log_content}"
    )
    assert "ticket-007" in log_content


# ---------------------------------------------------------------------------
# Merge réussi → ligne « mergée » dans le pipeline log — ticket-458
# ---------------------------------------------------------------------------


async def test_merge_reussi_ecrit_la_ligne_mergee_au_journal(tmp_path: Path) -> None:
    """A successful merge writes `[project] ticket PR #N mergée (CI verte)`."""
    log_path = tmp_path / "memory" / "pipeline-log.md"
    watcher = CIWatcher()

    await watcher.surveiller(
        "proj", "ticket-001", 42, _phase2_success, _rien,
        pipeline_log_path=log_path,
    )
    await asyncio.sleep(0.1)

    lignes = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lignes) == 1
    assert lignes[0].endswith("[proj] ticket-001 PR #42 mergée (CI verte)")


async def test_echec_n_ecrit_pas_la_ligne_mergee(tmp_path: Path) -> None:
    """A failed merge writes the blocking line, never the success line."""
    log_path = tmp_path / "memory" / "pipeline-log.md"
    watcher = CIWatcher()

    await watcher.surveiller(
        "proj", "ticket-007", 10, _phase2_red_ci, _rien,
        pipeline_log_path=log_path,
    )
    await asyncio.sleep(0.1)

    contenu = log_path.read_text(encoding="utf-8")
    assert "non mergée" in contenu
    assert "mergée (CI verte)" not in contenu


async def test_phase2_echouee_attendre_merge_retourne_false() -> None:
    """attendre_merge returns False after a failed phase 2."""
    watcher = CIWatcher()

    await watcher.surveiller("proj", "ticket-007", 10, _phase2_red_ci, _rien)
    await asyncio.sleep(0.1)

    result = await watcher.attendre_merge("proj", "ticket-007")
    assert result is False, (
        f"attendre_merge doit retourner False après un échec de phase 2, got: {result}"
    )


# ---------------------------------------------------------------------------
# Erreur réseau pendant la phase 2 — ticket-405
# ---------------------------------------------------------------------------


async def _phase2_read_timeout(pr_number: int) -> Livraison:
    raise httpx.ReadTimeout("")


def _lecture_pr(etat: str) -> Callable[[int], Awaitable[str]]:
    async def lire(pr_number: int) -> str:
        return etat

    return lire


async def test_read_timeout_puis_pr_mergee_est_un_succes(tmp_path: Path) -> None:
    """A ReadTimeout followed by a merged PR is merged=True, and the log says so."""
    log_path = tmp_path / "memory" / "pipeline-log.md"
    watcher = CIWatcher()
    events, collect = _collecteur()

    await watcher.surveiller(
        "proj", "ticket-006", 8, _phase2_read_timeout, collect,
        pipeline_log_path=log_path, etat_pr=_lecture_pr("merged"),
    )
    await asyncio.sleep(0.1)

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 1
    assert done[0].data["merged"] is True
    assert done[0].data["arret"] is None
    assert [e for e in events if e.type is EventType.TICKET_STATUS_CHANGED] == []
    contenu = log_path.read_text(encoding="utf-8")
    assert "mergée malgré une erreur réseau" in contenu
    assert "PR #8" in contenu
    assert "ReadTimeout" in contenu
    assert await watcher.attendre_merge("proj", "ticket-006") is True


async def test_read_timeout_pr_encore_ouverte_reste_un_echec() -> None:
    """A network error on a PR that is still open stays a failure."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    await watcher.surveiller(
        "proj", "ticket-006", 8, _phase2_read_timeout, collect,
        etat_pr=_lecture_pr("open"),
    )
    await asyncio.sleep(0.05)

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 1
    assert done[0].data["merged"] is False
    assert "ReadTimeout" in done[0].data["arret"]


async def test_read_timeout_relecture_impossible_reste_un_echec() -> None:
    """If the PR cannot be re-read either, the delivery is reported failed."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    async def lecture_en_panne(pr_number: int) -> str:
        raise httpx.ConnectError("")

    await watcher.surveiller(
        "proj", "ticket-006", 8, _phase2_read_timeout, collect,
        etat_pr=lecture_en_panne,
    )
    await asyncio.sleep(0.05)

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 1
    assert done[0].data["merged"] is False


async def test_erreur_reseau_sans_relecture_reste_un_echec() -> None:
    """Without `etat_pr`, a network error is a failure, as before."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    await watcher.surveiller("proj", "ticket-006", 8, _phase2_read_timeout, collect)
    await asyncio.sleep(0.05)

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert done[0].data["merged"] is False


async def test_exception_a_message_vide_nomme_son_type_dans_le_journal(
    tmp_path: Path,
) -> None:
    """A failure by an exception with empty text still names its type in the log."""
    log_path = tmp_path / "memory" / "pipeline-log.md"
    watcher = CIWatcher()
    events, collect = _collecteur()

    await watcher.surveiller(
        "proj", "ticket-006", 8, _phase2_read_timeout, collect,
        pipeline_log_path=log_path,
    )
    await asyncio.sleep(0.1)

    contenu = log_path.read_text(encoding="utf-8")
    assert "erreur inattendue : ReadTimeout" in contenu
    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert "ReadTimeout" in done[0].data["arret"]


async def test_exception_non_reseau_a_message_vide_nomme_son_type() -> None:
    """Any exception, not only network ones, is named in the failure message."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    async def phase2_vide(pr_number: int) -> Livraison:
        raise RuntimeError()

    await watcher.surveiller("proj", "ticket-006", 8, phase2_vide, collect)
    await asyncio.sleep(0.05)

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert done[0].data["arret"] == "erreur inattendue : RuntimeError"


def test_decrire_exception_garde_le_texte_quand_il_existe() -> None:
    assert decrire_exception(RuntimeError("boom")) == "RuntimeError: boom"
    assert decrire_exception(RuntimeError()) == "RuntimeError"
