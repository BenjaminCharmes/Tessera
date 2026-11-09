"""The loop leaves one journal line per « À toi » key, and none for the other verdicts — ticket-868, ADR-080."""
from pathlib import Path

from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.services.supervision.intervention import Resultat, Statut
from tessera.services.supervision.superviseur_actions import Action, Decision, Verdict
from tessera.services.supervision.superviseur_boucle import SuperviseurBoucle
from tessera.services.supervision.superviseur_boucle_ports import Candidat, ProjetSupervise
from tests.test_superviseur_boucle import _Banc


class _Journal:
    """A journal port that records what it is asked to write."""

    def __init__(self, *, en_panne: bool = False, statut: Statut = "livre") -> None:
        self.appels: list[tuple[str, list[Decision]]] = []
        self.en_panne = en_panne
        self.statut = statut

    async def __call__(self, project_id: str, decisions: list[Decision]) -> Resultat | None:
        self.appels.append((project_id, decisions))
        if self.en_panne:
            raise RuntimeError("journal en panne")
        return Resultat(self.statut, Action.TRIER)


def _boucle(banc: _Banc, tmp_path: Path, journal: _Journal) -> SuperviseurBoucle:
    projets = [ProjetSupervise("demo", tmp_path, ConfigSuperviseur())]
    return SuperviseurBoucle(
        banc.registre, banc.hub, lambda: projets, banc._collecter, banc._lire_depense, banc.etat, journaliser=journal,
    )


async def test_an_a_toi_verdict_writes_its_line_once(tmp_path: Path) -> None:
    banc, journal = _Banc(tmp_path), _Journal()
    banc.candidat("ticket-1", verdict="a_toi")
    boucle = _boucle(banc, tmp_path, journal)

    await boucle.passe()

    assert [(projet, [d.cible for d in decisions]) for projet, decisions in journal.appels] == [("demo", ["ticket-1"])]
    assert journal.appels[0][1][0].verdict == "a_toi"


async def test_an_agir_verdict_adds_no_line(tmp_path: Path) -> None:
    banc, journal = _Banc(tmp_path), _Journal()
    banc.candidat("ticket-1", verdict="agir")

    await _boucle(banc, tmp_path, journal).passe()

    assert journal.appels == []


async def test_a_rien_verdict_adds_no_line(tmp_path: Path) -> None:
    banc, journal = _Banc(tmp_path), _Journal()
    banc.candidat("ticket-1", verdict="rien", sans_modele=True)
    boucle = _boucle(banc, tmp_path, journal)

    await boucle.passe()
    await boucle.passe()

    assert journal.appels == []


async def test_a_case_already_journaled_is_not_written_again_on_the_next_sweep(tmp_path: Path) -> None:
    banc, journal = _Banc(tmp_path), _Journal()
    banc.candidat("ticket-1", verdict="a_toi")
    boucle = _boucle(banc, tmp_path, journal)

    await boucle.passe()
    await boucle.passe()
    await boucle.passe()

    assert len(journal.appels) == 1
    assert banc.executions == ["ticket-1"]


async def test_two_failures_hand_the_key_to_a_toi_and_write_its_line_once(tmp_path: Path) -> None:
    banc, journal = _Banc(tmp_path), _Journal()
    banc.candidat("ticket-1", echoue=True)
    boucle = _boucle(banc, tmp_path, journal)

    await boucle.passe()
    assert journal.appels == []
    await boucle.passe()
    await boucle.passe()

    assert len(journal.appels) == 1
    assert [d.verdict for d in journal.appels[0][1]] == ["a_toi"]
    assert "2 échecs de suite" in journal.appels[0][1][0].raison


async def test_only_the_a_toi_decisions_of_a_key_are_written(tmp_path: Path) -> None:
    banc, journal = _Banc(tmp_path), _Journal()

    async def executer() -> list[Decision]:
        verdicts: list[Verdict] = ["agir", "a_toi", "rien", "a_toi"]
        return [Decision(Action.DECIDER, f"bloc-{i}", v, "raison") for i, v in enumerate(verdicts)]

    banc.candidats.append(Candidat("demo", Action.DECIDER, "demo", "abc", False, executer))

    await _boucle(banc, tmp_path, journal).passe()

    assert len(journal.appels) == 1
    assert [d.cible for d in journal.appels[0][1]] == ["bloc-1", "bloc-3"]


async def test_a_failing_journal_never_reaches_the_loop(tmp_path: Path) -> None:
    banc, journal = _Banc(tmp_path), _Journal(en_panne=True)
    banc.candidat("ticket-1", verdict="a_toi")
    boucle = _boucle(banc, tmp_path, journal)

    decisions = await boucle.passe()
    await boucle.passe()

    assert [d.verdict for d in decisions] == ["a_toi"]
    assert len(banc.evenements()) == 1  # annoncé une fois, malgré le journal
    assert len(journal.appels) == 1


async def test_a_blocked_journal_write_is_logged_not_raised(tmp_path: Path) -> None:
    banc, journal = _Banc(tmp_path), _Journal(statut="blocked")
    banc.candidat("ticket-1", verdict="a_toi")

    decisions = await _boucle(banc, tmp_path, journal).passe()

    assert [d.verdict for d in decisions] == ["a_toi"]
    assert len(journal.appels) == 1


async def test_a_loop_without_a_journal_port_still_announces(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    banc.candidat("ticket-1", verdict="a_toi")

    decisions = await banc.boucle.passe()

    assert [d.verdict for d in decisions] == ["a_toi"]
