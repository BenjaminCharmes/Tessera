"""The journal line of an « À toi » case: one run, one commit that carries only the journal — ticket-868, ADR-080."""
from datetime import datetime
from pathlib import Path

from tessera.services.livraison.livraison_intervention import ControleDuDiff
from tessera.services.livraison.livraison_resultat import Livraison
from tessera.services.pipeline.run_registry import RunRegistry
from tessera.services.supervision.intervention import Resultat
from tessera.services.supervision.intervention_a_toi import journaliser_a_toi
from tessera.services.supervision.intervention_controle import JOURNAL, controle_du_journal_seul
from tessera.services.supervision.superviseur_actions import Action, Decision, Verdict
from tessera.services.supervision.superviseur_journal import cas_a_toi_ouverts, lire_journal

_MAINTENANT = datetime(2026, 11, 9, 9, 30, 0)


class _FauxChantier:
    """A chantier on a temp folder: what is written there is 'modified' until committed."""

    def __init__(self, racine: Path, *, echec_commit: bool = False) -> None:
        self.racine = racine
        self.echec_commit = echec_commit
        self.ouvert = False
        self.ferme = False
        self.commits: list[tuple[str, list[str]]] = []
        self.livraisons: list[tuple[str, str, str]] = []
        self.controle: ControleDuDiff | None = None
        self.en_attente: set[str] = set()

    async def ouvrir(self, branche: str) -> Path:
        self.ouvert = True
        return self.racine

    async def fichiers_modifies(self) -> list[str]:
        courants = {p.relative_to(self.racine).as_posix() for p in self.racine.rglob("*") if p.is_file()}
        return sorted(courants - {c for _, chemins in self.commits for c in chemins} | self.en_attente)

    async def commiter(self, message: str, chemins: list[str]) -> str | None:
        if self.echec_commit:
            raise RuntimeError("git commit a échoué")
        self.commits.append((message, list(chemins)))
        return f"{len(self.commits):x}" * 40

    async def livrer(self, branche: str, sha: str, controle: ControleDuDiff, titre: str) -> Livraison:
        self.livraisons.append((branche, sha, titre))
        self.controle = controle
        return Livraison(pr_number=7)

    async def fermer(self) -> None:
        self.ferme = True


def _decision(cible: str = "regle-3", verdict: Verdict = "a_toi", raison: str = "touche une porte") -> Decision:
    return Decision(Action.DECIDER, cible, verdict, raison)


async def _journaliser(
    chantier: _FauxChantier, decisions: list[Decision], registre: RunRegistry | None = None, delai_max_s: float = 1.0
) -> Resultat | None:
    return await journaliser_a_toi(
        "demo", decisions, registre=registre or RunRegistry(), nouveau_chantier=lambda _pid: chantier,
        delai_max_s=delai_max_s, maintenant=lambda: _MAINTENANT,
    )


async def test_an_a_toi_case_leaves_exactly_one_journal_line(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    resultat = await _journaliser(chantier, [_decision()])

    lignes = lire_journal(tmp_path / "memory")
    assert [(ligne.action, ligne.cible, ligne.sha) for ligne in lignes] == [("a_toi", "regle-3", "")]
    assert lignes[0].jour == _MAINTENANT.date()
    assert lignes[0].resume == "decider : touche une porte"
    assert [c.cible for c in cas_a_toi_ouverts(lignes)] == ["regle-3"]
    assert resultat is not None and resultat.statut == "livre"


async def test_the_commit_and_the_delivery_carry_only_the_journal(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    await _journaliser(chantier, [_decision()])

    assert chantier.commits == [("chore(supervision): a_toi regle-3", [JOURNAL])]
    assert chantier.livraisons == [("supervision-20261109-093000", "1" * 40, "a_toi regle-3")]
    assert chantier.ouvert and chantier.ferme
    assert chantier.controle is not None
    assert chantier.controle([JOURNAL]) is None
    assert chantier.controle([JOURNAL, "backend/src/x.py"]) is not None


async def test_a_run_of_a_toi_cases_writes_one_line_each_in_one_commit(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    await _journaliser(chantier, [_decision("a"), _decision("b", raison="autre")])

    assert [ligne.cible for ligne in lire_journal(tmp_path / "memory")] == ["a", "b"]
    assert len(chantier.commits) == 1


async def test_agir_and_rien_decisions_write_nothing(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    resultat = await _journaliser(chantier, [_decision(verdict="agir"), _decision("b", verdict="rien")])

    assert resultat is None
    assert not chantier.ouvert and chantier.commits == []
    assert not (tmp_path / "memory").exists()


async def test_a_line_already_in_the_journal_is_not_written_twice(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)
    await _journaliser(chantier, [_decision()])

    suivant = _FauxChantier(tmp_path)
    resultat = await _journaliser(suivant, [_decision(), _decision()])

    assert resultat is not None and resultat.statut == "rien"
    assert len(lire_journal(tmp_path / "memory")) == 1
    assert suivant.commits == [] and suivant.livraisons == []


async def test_a_target_and_a_reason_are_written_on_one_line_without_the_separator(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    await _journaliser(chantier, [_decision("a | b\nc", raison="x\ny" + "z" * 400)])

    ligne = lire_journal(tmp_path / "memory")[0]
    assert ligne.cible == "a / b c"
    assert "\n" not in ligne.resume and len(ligne.resume) <= 200


async def test_the_run_gives_up_when_the_project_stays_held(tmp_path: Path) -> None:
    registre = RunRegistry()
    registre.ouvrir("demo", None, mode="autonomous")
    chantier = _FauxChantier(tmp_path)

    resultat = await _journaliser(chantier, [_decision()], registre, delai_max_s=0.05)

    assert resultat is not None and resultat.statut == "abandonne"
    assert not chantier.ouvert and not (tmp_path / "memory").exists()


async def test_a_failed_commit_ends_blocked_and_never_delivers(tmp_path: Path) -> None:
    registre = RunRegistry()
    chantier = _FauxChantier(tmp_path, echec_commit=True)

    resultat = await _journaliser(chantier, [_decision()], registre)

    assert resultat is not None and resultat.statut == "blocked"
    assert chantier.livraisons == [] and chantier.ferme
    assert not registre.projet_occupe("demo")


async def test_another_changed_file_blocks_the_journal_run(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)
    chantier.en_attente = {"backend/src/x.py"}

    resultat = await _journaliser(chantier, [_decision()])

    assert resultat is not None and resultat.statut == "blocked"
    assert chantier.livraisons == []


def test_the_delivery_check_admits_only_the_journal() -> None:
    assert controle_du_journal_seul([JOURNAL]) is None
    assert controle_du_journal_seul(["MEMORY\\supervision.md"]) is None
    assert "tickets/todo/t.md" in (controle_du_journal_seul([JOURNAL, "tickets/todo/t.md"]) or "")
