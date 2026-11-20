"""The supervisor gives an unwatched approved PR back to the watcher, and never merges (ticket-857)."""
import ast
from pathlib import Path

from tessera.services.livraison.livraison_resultat import Livraison
from tessera.services.noyau.pipeline_events import OrchestratorEvent
from tessera.services.supervision import superviseur_pr
from tessera.services.supervision.superviseur_actions import Action
from tessera.services.supervision.superviseur_pr import RunLivre, SuperviseurPr, cause_de_l_arret, reperer

PUSHED = "a" * 40
AUTRE = "b" * 40
COUPURE = "GitCommandError: git push a échoué (réseau coupé)"


class _Watcher:
    def __init__(self, en_attente: tuple[str, ...] = ()) -> None:
        self._en_attente = en_attente
        self.confiees: list[tuple[str, str, int]] = []

    def en_attente(self, project_id: str) -> tuple[str, ...]:
        return self._en_attente

    async def surveiller(
        self, project_id: str, ticket_id: str, pr: int, on_event: object
    ) -> None:
        self.confiees.append((project_id, ticket_id, pr))


async def _ignorer(evenement: OrchestratorEvent) -> None:
    return None


def _run(
    *, arret: str | None = COUPURE, approuve: bool = True, resolveur: bool = False,
    pushed: str | None = PUSHED, pr: int | None = 913,
) -> RunLivre:
    livraison = Livraison(arret=arret, pr_number=pr, pushed_sha=pushed, pr_orpheline=True)
    return RunLivre("demo", "ticket-776", approuve, livraison, resolveur)


def _superviseur(
    watcher: _Watcher, *, tete: str | None = PUSHED, etat: str = "open"
) -> SuperviseurPr:
    async def etat_pr(project_id: str, pr: int) -> str:
        return etat

    async def lire_tete(project_id: str, pr: int) -> str | None:
        return tete

    return SuperviseurPr(watcher, watcher.surveiller, etat_pr, lire_tete)


async def test_unwatched_approved_pr_is_handed_to_the_watcher() -> None:
    watcher = _Watcher()
    decision = await _superviseur(watcher).reconfier(_run(), _ignorer)

    assert decision.verdict == "agir"
    assert decision.action is Action.RECONFIER_PR
    assert watcher.confiees == [("demo", "ticket-776", 913)]


async def test_already_watched_pr_is_left_alone() -> None:
    watcher = _Watcher(en_attente=("ticket-776",))
    decision = await _superviseur(watcher).reconfier(_run(), _ignorer)

    assert decision.verdict == "rien"
    assert watcher.confiees == []


async def test_head_moved_since_pushed_sha_goes_to_a_toi() -> None:
    watcher = _Watcher()
    decision = await _superviseur(watcher, tete=AUTRE).reconfier(_run(), _ignorer)

    assert decision.verdict == "a_toi"
    assert watcher.confiees == []


async def test_unknown_pushed_sha_or_unreadable_head_goes_to_a_toi() -> None:
    watcher = _Watcher()
    sans_sha = await _superviseur(watcher).reconfier(_run(pushed=None), _ignorer)
    sans_tete = await _superviseur(watcher, tete=None).reconfier(_run(), _ignorer)

    assert (sans_sha.verdict, sans_tete.verdict) == ("a_toi", "a_toi")
    assert watcher.confiees == []


async def test_closed_pr_is_not_handed_back() -> None:
    watcher = _Watcher()
    decision = await _superviseur(watcher, etat="merged").reconfier(_run(), _ignorer)

    assert decision.verdict == "rien"
    assert watcher.confiees == []


async def test_red_ci_is_never_handed_back() -> None:
    watcher = _Watcher()
    rouge = _run(arret="CI rouge : la PR #913 reste ouverte.")
    decision = await _superviseur(watcher).reconfier(rouge, _ignorer)

    assert decision.verdict == "rien"
    assert watcher.confiees == []


async def test_unapproved_run_is_never_handed_back() -> None:
    watcher = _Watcher()
    decision = await _superviseur(watcher).reconfier(_run(approuve=False), _ignorer)

    assert decision.verdict == "rien"
    assert watcher.confiees == []


async def test_conflict_resolver_pr_is_never_handed_back() -> None:
    watcher = _Watcher()
    decision = await _superviseur(watcher).reconfier(_run(resolveur=True), _ignorer)

    assert decision.verdict == "rien"
    assert watcher.confiees == []


async def test_same_pr_and_sha_is_handed_once() -> None:
    watcher = _Watcher()
    superviseur = _superviseur(watcher)

    premiere = await superviseur.reconfier(_run(), _ignorer)
    seconde = await superviseur.reconfier(_run(), _ignorer)

    assert (premiere.verdict, seconde.verdict) == ("agir", "rien")
    assert len(watcher.confiees) == 1


async def test_a_new_sha_on_the_same_pr_is_handed_again() -> None:
    watcher = _Watcher()
    await _superviseur(watcher).reconfier(_run(), _ignorer)
    suivant = _superviseur(watcher, tete=AUTRE)
    await suivant.reconfier(_run(pushed=AUTRE), _ignorer)
    await suivant.reconfier(_run(pushed=AUTRE), _ignorer)

    assert len(watcher.confiees) == 2


async def test_failed_hand_over_is_not_recorded_and_goes_to_a_toi() -> None:
    appels: list[int] = []

    async def une_panne(project_id: str, ticket_id: str, pr: int, on_event: object) -> None:
        appels.append(pr)
        if len(appels) == 1:
            raise RuntimeError("watcher indisponible")

    async def etat_pr(project_id: str, pr: int) -> str:
        return "open"

    async def lire_tete(project_id: str, pr: int) -> str | None:
        return PUSHED

    superviseur = SuperviseurPr(_Watcher(), une_panne, etat_pr, lire_tete)
    assert (await superviseur.reconfier(_run(), _ignorer)).verdict == "a_toi"
    assert (await superviseur.reconfier(_run(), _ignorer)).verdict == "agir"
    assert appels == [913, 913]


def test_stop_cause_is_read_from_the_stop_line() -> None:
    assert cause_de_l_arret(COUPURE) == "infrastructure"
    assert cause_de_l_arret("ConnectError: réseau, CI rouge") == "ci_rouge"
    assert cause_de_l_arret("tête de la PR #3 n'est plus le commit poussé") == "autre"
    assert cause_de_l_arret(None) == "autre"


def test_spot_keeps_only_the_runs_worth_a_look() -> None:
    gardes = [_run(), _run(approuve=False), _run(resolveur=True), _run(arret="CI rouge")]

    assert reperer(gardes) == [gardes[0]]


def test_module_never_calls_a_merge_or_a_push() -> None:
    source = Path(superviseur_pr.__file__).read_text(encoding="utf-8")
    arbre = ast.parse(source)
    appels = {
        noeud.func.attr if isinstance(noeud.func, ast.Attribute) else getattr(noeud.func, "id", "")
        for noeud in ast.walk(arbre) if isinstance(noeud, ast.Call)
    }
    importes = {
        noeud.module or "" for noeud in ast.walk(arbre) if isinstance(noeud, ast.ImportFrom)
    }

    assert not [nom for nom in appels if "merge" in nom.lower() or "push" in nom.lower()]
    assert not [mod for mod in importes if "subprocess" in mod or "github" in mod or "git_workspace" in mod]
