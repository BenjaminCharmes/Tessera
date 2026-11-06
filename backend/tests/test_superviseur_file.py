"""The supervisor reopens a queue cut by the infrastructure, and only then (ticket-858)."""
from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.services.supervision.superviseur_actions import Action
from tessera.services.supervision.superviseur_file import (
    FileCoupee,
    SuperviseurFile,
    classer_interruption,
    interruptions_du_journal,
    raison_de_l_interruption,
    tickets_restants,
)

PREFIXE = "- 2026-11-05 03:12:44 UTC — [demo] file interrompue : "
COUPURE = PREFIXE + "GitCommandError: git fetch a échoué (réseau coupé)"
NON_APPROUVE = PREFIXE + "ticket-759 non approuvé"
ABSENT = PREFIXE + "Ticket introuvable : ticket-900"


class _Banc:
    """A fake queue starter and the readings the supervisor takes."""

    def __init__(self, *, depense: float = 0.0, quota_bas: bool | None = False, occupe: bool = False) -> None:
        self.depense = depense
        self.quota_bas = quota_bas
        self.occupe = occupe
        self.ouvertures: list[tuple[str, list[str]]] = []

    async def rouvrir(self, project_id: str, ticket_ids: list[str]) -> str:
        self.ouvertures.append((project_id, ticket_ids))
        return f"run-{len(self.ouvertures)}"

    async def lire_depense(self) -> float:
        return self.depense

    async def lire_quota(self) -> bool:
        if self.quota_bas is None:
            raise RuntimeError("quota inconnu")
        return self.quota_bas

    def est_occupe(self, project_id: str) -> bool:
        return self.occupe


def _superviseur(banc: _Banc, *, relance: bool = True) -> SuperviseurFile:
    config = ConfigSuperviseur(relance_file=relance)
    return SuperviseurFile(config, banc.rouvrir, banc.est_occupe, banc.lire_depense, banc.lire_quota)


def _coupee(ligne: str = COUPURE, run_id: str = "run-0", restants: tuple[str, ...] = ("ticket-760", "ticket-761")) -> FileCoupee:
    return FileCoupee("demo", run_id, ligne, restants)


def test_network_cut_is_classified_infrastructure() -> None:
    assert classer_interruption(COUPURE) == "infrastructure"
    assert classer_interruption(PREFIXE + "ConnectError: la veille a coupé la connexion") == "infrastructure"
    assert classer_interruption("GitCommandError: push refusé") == "infrastructure"


async def test_unapproved_ticket_is_classified_verdict_and_not_relaunched() -> None:
    banc = _Banc()
    decision = await _superviseur(banc).relancer(_coupee(NON_APPROUVE))

    assert classer_interruption(NON_APPROUVE) == "verdict"
    assert decision.action is Action.RELANCER_FILE
    assert decision.verdict == "rien"
    assert banc.ouvertures == []


async def test_missing_ticket_is_never_relaunched() -> None:
    banc = _Banc()
    decision = await _superviseur(banc).relancer(_coupee(ABSENT))

    assert classer_interruption(ABSENT) == "introuvable"
    assert decision.verdict == "rien"
    assert banc.ouvertures == []


async def test_one_relaunch_per_cause_per_queue() -> None:
    banc = _Banc()
    superviseur = _superviseur(banc)

    premiere = await superviseur.relancer(_coupee())
    assert (premiere.verdict, banc.ouvertures) == ("agir", [("demo", ["ticket-760", "ticket-761"])])
    # La même interruption relue au tour suivant ne rouvre rien.
    assert (await superviseur.relancer(_coupee())).verdict == "rien"
    # La file rouverte (run-1) coupée par la même cause : « À toi », pas de troisième tentative.
    seconde = await superviseur.relancer(_coupee(run_id="run-1", restants=("ticket-761",)))

    assert seconde.verdict == "a_toi"
    assert len(banc.ouvertures) == 1


async def test_relaunch_is_off_unless_declared() -> None:
    banc = _Banc()
    decision = await _superviseur(banc, relance=False).relancer(_coupee())

    assert decision.verdict == "rien"
    assert "relance_file" in decision.raison
    assert banc.ouvertures == []


async def test_spent_daily_budget_blocks_the_relaunch() -> None:
    banc = _Banc(depense=2.0)
    decision = await _superviseur(banc).relancer(_coupee())

    assert decision.verdict == "a_toi"
    assert banc.ouvertures == []


async def test_low_quota_waits_but_unknown_quota_never_blocks() -> None:
    bas = _Banc(quota_bas=True)
    assert (await _superviseur(bas).relancer(_coupee())).verdict == "rien"
    assert bas.ouvertures == []

    inconnu = _Banc(quota_bas=None)
    assert (await _superviseur(inconnu).relancer(_coupee())).verdict == "agir"


async def test_nothing_left_or_project_held_never_reopens() -> None:
    vide = _Banc()
    assert (await _superviseur(vide).relancer(_coupee(restants=()))).verdict == "rien"

    tenu = _Banc(occupe=True)
    assert (await _superviseur(tenu).relancer(_coupee())).verdict == "rien"
    assert vide.ouvertures == [] and tenu.ouvertures == []


async def test_failed_reopening_goes_to_a_toi_and_is_not_recorded() -> None:
    appels: list[str] = []

    async def rouvrir(project_id: str, ticket_ids: list[str]) -> str:
        appels.append(project_id)
        if len(appels) == 1:
            raise RuntimeError("démarrage impossible")
        return "run-1"

    banc = _Banc()
    superviseur = SuperviseurFile(ConfigSuperviseur(relance_file=True), rouvrir, banc.est_occupe, banc.lire_depense, banc.lire_quota)

    assert (await superviseur.relancer(_coupee())).verdict == "a_toi"
    assert (await superviseur.relancer(_coupee())).verdict == "agir"


def test_money_stop_and_unknown_lines_are_never_infrastructure() -> None:
    assert classer_interruption(PREFIXE + "plafond de dépense (4.10 $ / 4.00 $)") == "inconnue"
    assert classer_interruption(PREFIXE + "quota épuisé") == "inconnue"
    assert classer_interruption(PREFIXE + "ticket-5 non approuvé après un ConnectError") == "verdict"
    assert classer_interruption(PREFIXE + "quelque chose d'inattendu") == "inconnue"


def test_log_lines_are_read_by_project() -> None:
    journal = "\n".join([COUPURE, "- 2026-11-05 — [autre] file interrompue : réseau", "texte libre", NON_APPROUVE])

    assert interruptions_du_journal(journal, "demo") == [COUPURE, NON_APPROUVE]
    assert raison_de_l_interruption(NON_APPROUVE) == "ticket-759 non approuvé"


def test_remaining_tickets_keep_their_order() -> None:
    assert tickets_restants(["a", "b", "c", "d"], ["b", "a"]) == ("c", "d")
