"""The watcher updates a conflicting PR once and follows its new head — ticket-733.

Couverture :
- phase 2 `conflicting` → mise à jour, `pushed_sha` noté avant l'attente de la CI,
  phase 2 relancée sur la nouvelle tête, PR mergée ;
- refus de la mise à jour, tête changée avant elle, écriture impossible, délai
  dépassé : ticket `blocked`, rien de mergé ;
- un second `conflicting` n'appelle pas une seconde mise à jour ;
- sans `mise_a_jour`, le comportement et le texte de l'arrêt sont ceux d'avant ;
- reprise après redémarrage sur la tête mise à jour ;
- `mise_a_jour_de` : branche lue chez GitHub, tête suivie, refus rendu en arrêt.
"""
import asyncio
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.models.ticket import TicketStatus
from tessera.services.livraison import mise_a_jour_pr
from tessera.services.livraison.ci_watcher import CIWatcher, ControleTete
from tessera.services.database_runs import create_run
from tessera.services.github.github_service import PrOuverte
from tessera.services.livraison.livraison import Livraison
from tessera.services.livraison.mise_a_jour_branche import MiseAJour
from tessera.services.livraison.mise_a_jour_pr import MiseAJourPr, TeteAttendue, mise_a_jour_de
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.livraison.sha_approbation import noter_poussee, sha_pousse_du_ticket
from tessera.services.livraison.surveillance_run import controle_tete_de

_A = "a" * 40
_B = "b" * 40
_C = "c" * 40
_ARRET_CONFLIT = "PR #7 en conflit avec main : à rebaser. La PR reste ouverte."


def _conflit() -> Livraison:
    return Livraison(pr_number=7, arret=_ARRET_CONFLIT, a_mettre_a_jour=True)


def _merge() -> Livraison:
    return Livraison(pr_number=7, merged=True)


class _Phase2:
    """Phase 2 rejouée : une livraison par appel, et ce que la base disait alors."""

    def __init__(self, *livraisons: Livraison, tete: TeteAttendue | None = None) -> None:
        self._livraisons = list(livraisons)
        self._tete = tete
        self.appels = 0
        self.sha_attendus: list[str | None] = []
        self.sha_en_base: list[str | None] = []

    async def __call__(self, pr_number: int) -> Livraison:
        self.appels += 1
        if self._tete is not None:
            self.sha_attendus.append(self._tete.sha)
        self.sha_en_base.append(await sha_pousse_du_ticket(settings.ide_db_path, "proj", "ticket-001"))
        return self._livraisons.pop(0)


class _Tete:
    """La tête que GitHub montre, et ce qu'elle devient après une mise à jour."""

    def __init__(self, valeur: str) -> None:
        self.valeur = valeur

    async def lire(self, pr_number: int) -> str | None:
        return self.valeur

    def controle(self, pushed: str | None = _A) -> ControleTete:
        return ControleTete(pushed_sha=pushed, lire_tete=self.lire, intervalle_s=0.0)


class _MiseAJour:
    def __init__(self, resultat: MiseAJour, tete: _Tete | None = None) -> None:
        self.resultat = resultat
        self.tete = tete
        self.appels: list[str] = []

    async def __call__(self, attendue: str) -> MiseAJour:
        self.appels.append(attendue)
        if self.tete is not None and self.resultat.sha is not None:
            self.tete.valeur = self.resultat.sha
        return self.resultat


class _Lente:
    async def __call__(self, attendue: str) -> MiseAJour:
        await asyncio.sleep(30)
        return MiseAJour(sha=_B, arret=None)


async def _run_pousse(sha: str | None = _A) -> None:
    run_id = await create_run(settings.ide_db_path, "proj", "ticket-001")
    if sha is not None:
        await noter_poussee(settings.ide_db_path, run_id, sha)


async def _surveiller(
    phase2: _Phase2,
    tete: _Tete,
    mise_a_jour: MiseAJourPr | None,
    watcher: CIWatcher | None = None,
    log: Path | None = None,
) -> tuple[bool, list[OrchestratorEvent]]:
    watcher = watcher or CIWatcher()
    events: list[OrchestratorEvent] = []

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    await watcher.surveiller(
        "proj", "ticket-001", 7, phase2, collect,
        pipeline_log_path=log, controle_tete=tete.controle(),
        mise_a_jour=mise_a_jour,
    )
    merge = await asyncio.wait_for(watcher.attendre_merge("proj", "ticket-001"), 5.0)
    return merge, events


def _fin(events: list[OrchestratorEvent]) -> dict[str, object]:
    fins = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(fins) == 1
    return fins[0].data


def _bloque(events: list[OrchestratorEvent]) -> bool:
    statuts = [e.data["status"] for e in events if e.type is EventType.TICKET_STATUS_CHANGED]
    return statuts == [TicketStatus.blocked.value]


async def test_a_conflicting_pr_is_updated_noted_then_merged_on_the_new_head() -> None:
    await _run_pousse()
    tete = _Tete(_A)
    suivie = TeteAttendue(_A)
    phase2 = _Phase2(_conflit(), _merge(), tete=suivie)
    maj = _MiseAJour(MiseAJour(sha=_B, arret=None, base="main"), tete)

    async def mise_a_jour(attendue: str) -> MiseAJour:
        resultat = await maj(attendue)
        suivie.sha = resultat.sha
        return resultat

    merge, events = await _surveiller(phase2, tete, mise_a_jour)

    assert merge is True
    assert maj.appels == [_A]
    assert phase2.appels == 2
    # La phase 2 repart sur la nouvelle tête, déjà notée en base.
    assert phase2.sha_attendus == [_A, _B]
    assert phase2.sha_en_base == [_A, _B]
    assert _fin(events)["merged"] is True
    assert await sha_pousse_du_ticket(settings.ide_db_path, "proj", "ticket-001") == _B


async def test_the_journal_names_the_base_and_both_heads(tmp_path: Path) -> None:
    await _run_pousse()
    tete = _Tete(_A)
    maj = _MiseAJour(MiseAJour(sha=_B, arret=None, base="main"), tete)
    log = tmp_path / "memory" / "pipeline-log.md"

    await _surveiller(_Phase2(_conflit(), _merge()), tete, maj, log=log)

    ligne = [x for x in log.read_text(encoding="utf-8").splitlines() if "mise à jour" in x]
    assert len(ligne) == 1
    assert "[ticket-001] PR #7 mise à jour avec main : aaaaaaa → bbbbbbb" in ligne[0]


async def test_a_refused_update_blocks_the_ticket_and_leaves_the_pr_open() -> None:
    await _run_pousse()
    tete = _Tete(_A)
    maj = _MiseAJour(MiseAJour(sha=None, arret="Conflit hors des journaux : app.py"))

    merge, events = await _surveiller(_Phase2(_conflit()), tete, maj)

    assert merge is False
    assert _bloque(events)
    fin = _fin(events)
    assert fin["merged"] is False
    assert str(fin["arret"]).startswith("mise à jour refusée : Conflit hors des journaux")
    assert await sha_pousse_du_ticket(settings.ide_db_path, "proj", "ticket-001") == _A


async def test_a_head_that_is_no_longer_the_pushed_one_is_never_updated() -> None:
    await _run_pousse()
    tete = _Tete(_A)
    maj = _MiseAJour(MiseAJour(sha=_B, arret=None))

    class _PhaseQuiPousse(_Phase2):
        async def __call__(self, pr_number: int) -> Livraison:
            tete.valeur = _C  # un push étranger pendant l'attente de la CI
            return await super().__call__(pr_number)

    merge, events = await _surveiller(_PhaseQuiPousse(_conflit()), tete, maj)

    assert merge is False
    assert maj.appels == []
    assert "n'est plus le commit poussé" in str(_fin(events)["arret"])
    assert await sha_pousse_du_ticket(settings.ide_db_path, "proj", "ticket-001") == _A


async def test_a_second_conflict_does_not_trigger_a_second_update() -> None:
    await _run_pousse()
    tete = _Tete(_A)
    maj = _MiseAJour(MiseAJour(sha=_B, arret=None), tete)
    phase2 = _Phase2(_conflit(), _conflit())

    merge, events = await _surveiller(phase2, tete, maj)

    assert merge is False
    assert len(maj.appels) == 1
    assert phase2.appels == 2
    assert _bloque(events)
    assert str(_fin(events)["arret"]) == _ARRET_CONFLIT


async def test_a_pushed_sha_that_cannot_be_written_blocks_before_any_ci_wait() -> None:
    await _run_pousse(sha=None)  # aucun run du ticket ne porte de pushed_sha
    tete = _Tete(_A)
    maj = _MiseAJour(MiseAJour(sha=_B, arret=None), tete)
    phase2 = _Phase2(_conflit(), _merge())

    merge, events = await _surveiller(phase2, tete, maj)

    assert merge is False
    assert phase2.appels == 1
    assert _bloque(events)
    assert "non enregistrée" in str(_fin(events)["arret"])


async def test_without_an_update_the_behaviour_and_the_stop_line_are_unchanged() -> None:
    await _run_pousse()
    tete = _Tete(_A)
    phase2 = _Phase2(_conflit())

    merge, events = await _surveiller(phase2, tete, None)

    assert merge is False
    assert phase2.appels == 1
    assert _bloque(events)
    assert _fin(events)["arret"] == _ARRET_CONFLIT


async def test_an_update_that_exceeds_its_bound_blocks_and_names_the_delay() -> None:
    await _run_pousse()
    tete = _Tete(_A)
    watcher = CIWatcher(timeout_mise_a_jour_s=0.05)

    merge, events = await _surveiller(_Phase2(_conflit()), tete, _Lente(), watcher)

    assert merge is False
    assert _bloque(events)
    assert "délai dépassé (0.05 s)" in str(_fin(events)["arret"])
    assert str(_fin(events)["arret"]).startswith("mise à jour refusée : ")


async def test_a_restart_resumes_on_the_updated_head_and_merges() -> None:
    await _run_pousse()
    tete = _Tete(_A)
    maj = _MiseAJour(MiseAJour(sha=_B, arret=None), tete)
    await _surveiller(_Phase2(_conflit(), _merge()), tete, maj)

    # Le backend redémarre : la reprise relit `pushed_sha` en base.
    controle = await controle_tete_de("proj", "ticket-001", tete.lire)
    assert controle.pushed_sha == _B
    phase2 = _Phase2(_merge())
    events: list[OrchestratorEvent] = []

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    watcher = CIWatcher()
    await watcher.surveiller("proj", "ticket-001", 7, phase2, collect, controle_tete=controle)

    assert await asyncio.wait_for(watcher.attendre_merge("proj", "ticket-001"), 5.0) is True
    assert phase2.appels == 1
    assert await sha_pousse_du_ticket(settings.ide_db_path, "proj", "ticket-001") == _B


class _Github:
    def __init__(self, prs: list[PrOuverte] | Exception) -> None:
        self.prs = prs

    async def prs_ouvertes(self) -> list[PrOuverte]:
        if isinstance(self.prs, Exception):
            raise self.prs
        return self.prs


def _fabrique(github: _Github, tete: TeteAttendue) -> MiseAJourPr:
    return mise_a_jour_de(
        depot=Path("depot"), base="main", pr_number=7,
        prs_ouvertes=github.prs_ouvertes, tete=tete,
    )


async def test_the_update_of_a_pr_uses_its_github_branch_and_the_policy_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    appels: list[tuple[Path, str, str, str]] = []

    async def faux(depot: Path, branche: str, base: str, attendue: str) -> MiseAJour:
        appels.append((depot, branche, base, attendue))
        return MiseAJour(sha=_B, arret=None, base=base)

    monkeypatch.setattr(mise_a_jour_pr, "mettre_a_jour_branche", faux)
    tete = TeteAttendue(_A)
    github = _Github([PrOuverte(number=3, branche="autre", base="main"),
                      PrOuverte(number=7, branche="ticket-001-x", base="main")])

    resultat = await _fabrique(github, tete)(_A)

    assert resultat.sha == _B
    assert appels == [(Path("depot"), "ticket-001-x", "main", _A)]
    assert tete.sha == _B


@pytest.mark.parametrize("prs", [[], RuntimeError("GitHub injoignable")])
async def test_a_pr_without_a_readable_branch_is_not_updated(
    prs: list[PrOuverte] | Exception,
) -> None:
    tete = TeteAttendue(_A)

    resultat = await _fabrique(_Github(prs), tete)(_A)

    assert resultat.sha is None
    assert "introuvable" in str(resultat.arret)
    assert tete.sha == _A


async def test_a_refused_update_keeps_the_followed_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def faux(*_args: object, **_kw: object) -> MiseAJour:
        return MiseAJour(sha=None, arret="Push refusé")

    monkeypatch.setattr(mise_a_jour_pr, "mettre_a_jour_branche", faux)
    tete = TeteAttendue(_A)
    github = _Github([PrOuverte(number=7, branche="b", base="main")])

    resultat = await _fabrique(github, tete)(_A)

    assert resultat.arret == "Push refusé"
    assert tete.sha == _A
