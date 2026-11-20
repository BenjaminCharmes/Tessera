"""The supervisor decides each proposed block once — ticket-914, ADR-080."""
from pathlib import Path

from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.services.supervision.superviseur_actions import Action, Decision, Verdict
from tessera.services.supervision.superviseur_boucle import SuperviseurBoucle
from tessera.services.supervision.superviseur_boucle_ports import Candidat, ProjetSupervise
from tessera.services.supervision.superviseur_collecte import _candidats_decision
from tessera.services.supervision.superviseur_decision import Passe, ResultatDecision
from tessera.services.supervision.superviseur_decision_blocs import blocs_proposes
from tests.test_superviseur_boucle import _Banc
from tests.test_superviseur_boucle_a_toi import _Journal

_A = "- Quand on ajoute une route, régénérer le schéma. (source : ticket-1, 2026-11-06)"
_A_MODIFIEE = "- Quand on ajoute une route, régénérer le schéma OpenAPI. (source : ticket-1, 2026-11-06)"
_B = "- Quand un test échoue, lire la trace. (source : ticket-2, 2026-11-07)"


class _Decision:
    """A decision double: records the targets it is asked about and answers one verdict."""

    def __init__(self, verdict: Verdict) -> None:
        self.verdict = verdict
        self.cibles: list[str] = []
        self.passes: list[Passe | None] = []

    async def decider_bloc(self, project_id: str, project_path: Path, cible: str, passe: Passe | None = None) -> list[ResultatDecision]:
        self.passes.append(passe)
        self.cibles.append(cible)
        texte = (project_path / "memory" / "lecons.md").read_text(encoding="utf-8")
        bloc = next(b for b in blocs_proposes(texte, "lecon") if b.cible == cible)
        return [ResultatDecision(Decision(Action.DECIDER, cible, self.verdict, "raison"), bloc)]


def _ecrire(projet: Path, *blocs: str) -> None:
    memoire = projet / "memory"
    memoire.mkdir(exist_ok=True)
    corps = "\n".join(blocs)
    (memoire / "lecons.md").write_text(f"# Leçons\n\n## Proposées\n{corps}\n\n## En vigueur\n", encoding="utf-8")


def _banc(tmp_path: Path, monkeypatch: object, verdict: Verdict) -> tuple[_Banc, _Decision, _Journal, SuperviseurBoucle]:
    projet = tmp_path / "demo"
    projet.mkdir()
    banc, journal, decision = _Banc(tmp_path), _Journal(), _Decision(verdict)
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "tessera.services.supervision.superviseur_collecte.superviseur_decision_pour", lambda *_: decision,
    )

    async def collecter(project_id: str, project_path: Path) -> list[Candidat]:
        return _candidats_decision(project_id, project_path)

    projets = [ProjetSupervise("demo", projet, ConfigSuperviseur())]
    boucle = SuperviseurBoucle(
        banc.registre, banc.hub, lambda: projets, collecter, banc._lire_depense, banc.etat, journaliser=journal,
    )
    return banc, decision, journal, boucle


async def test_a_new_block_alone_is_submitted_after_a_sweep_that_decided_the_first(tmp_path: Path, monkeypatch: object) -> None:
    _, decision, _, boucle = _banc(tmp_path, monkeypatch, "agir")
    _ecrire(tmp_path / "demo", _A)
    await boucle.passe()
    cible_a = decision.cibles[0]
    _ecrire(tmp_path / "demo", _A, _B)

    await boucle.passe()

    assert len(decision.cibles) == 2
    assert decision.cibles[1] != cible_a


async def test_a_block_whose_text_changed_is_submitted_again(tmp_path: Path, monkeypatch: object) -> None:
    _, decision, _, boucle = _banc(tmp_path, monkeypatch, "agir")
    _ecrire(tmp_path / "demo", _A)
    await boucle.passe()
    _ecrire(tmp_path / "demo", _A_MODIFIEE)

    await boucle.passe()

    assert len(decision.cibles) == 2


async def test_a_block_handed_to_a_toi_writes_no_second_line_when_another_appears(tmp_path: Path, monkeypatch: object) -> None:
    _, decision, journal, boucle = _banc(tmp_path, monkeypatch, "a_toi")
    _ecrire(tmp_path / "demo", _A)
    await boucle.passe()
    _ecrire(tmp_path / "demo", _A, _B)

    await boucle.passe()

    cibles = [d.cible for _, decisions in journal.appels for d in decisions]
    assert len(cibles) == 2
    assert len(set(cibles)) == 2
    assert len(decision.cibles) == 2


async def test_the_blocks_of_one_sweep_share_one_passe(tmp_path: Path, monkeypatch: object) -> None:
    _, decision, _, boucle = _banc(tmp_path, monkeypatch, "agir")
    _ecrire(tmp_path / "demo", _A, _B)

    await boucle.passe()

    assert len(decision.passes) == 2
    assert decision.passes[0] is not None and decision.passes[0] is decision.passes[1]
