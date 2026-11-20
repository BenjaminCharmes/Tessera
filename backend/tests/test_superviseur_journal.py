"""The supervision journal: one dated line per action, read without ever raising (ticket-853)."""
from datetime import date
from pathlib import Path

import pytest

from tessera.services.supervision.superviseur_journal import LigneJournal, ajouter_ligne, cas_a_toi_ouverts, lire_journal

JOUR = date(2026, 11, 6)


def _ajouter(memory: Path, action: str, cible: str, *, jour: date = JOUR, sha: str = "abc1234") -> None:
    ajouter_ligne(memory, jour=jour, action=action, cible=cible, sha=sha, resume="un résumé")


def test_add_then_read_round_trips(tmp_path: Path) -> None:
    ajouter_ligne(
        tmp_path, jour=JOUR, action="trier", cible="ticket-900", sha="abc1234",
        resume="Rapport transformé en ticket | sans perte",
    )
    ajouter_ligne(tmp_path, jour=JOUR, action="a_toi", cible="regle-3", sha="", resume="Touche une porte")

    assert lire_journal(tmp_path) == [
        LigneJournal(JOUR, "trier", "ticket-900", "abc1234", "Rapport transformé en ticket | sans perte"),
        LigneJournal(JOUR, "a_toi", "regle-3", "", "Touche une porte"),
    ]
    texte = (tmp_path / "supervision.md").read_text(encoding="utf-8")
    assert "- 2026-11-06 | trier | ticket-900 | abc1234 | Rapport" in texte


def test_since_filters_older_lines(tmp_path: Path) -> None:
    _ajouter(tmp_path, "trier", "ticket-1", jour=date(2026, 11, 1))
    _ajouter(tmp_path, "decider", "lecon-2", jour=date(2026, 11, 5))
    _ajouter(tmp_path, "relancer_file", "file-3", jour=date(2026, 11, 6))

    assert [x.cible for x in lire_journal(tmp_path, depuis=date(2026, 11, 5))] == ["lecon-2", "file-3"]
    assert len(lire_journal(tmp_path)) == 3


def test_unreadable_file_reads_as_empty(tmp_path: Path) -> None:
    assert lire_journal(tmp_path / "absent") == []

    (tmp_path / "supervision.md").write_bytes(b"\xff\xfe\x00- 2026-11-06 | trier")
    assert lire_journal(tmp_path) == []

    # Un dossier à la place du fichier : illisible, donc vide.
    autre = tmp_path / "autre"
    (autre / "supervision.md").mkdir(parents=True)
    assert lire_journal(autre) == []


def test_lines_that_are_not_journal_lines_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "supervision.md").write_text(
        "# Journal\n\ntexte libre\n- pas une ligne\n- 2026-13-40 | trier | x | s | r\n"
        "- 2026-11-06 | inconnue | x | s | r\n- 2026-11-06 | trier | x | s | bon\n",
        encoding="utf-8",
    )

    assert [x.resume for x in lire_journal(tmp_path)] == ["bon"]


def test_multiline_summary_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="single line"):
        ajouter_ligne(tmp_path, jour=JOUR, action="trier", cible="t", sha="s", resume="a\nb")
    with pytest.raises(ValueError, match="at most 200"):
        ajouter_ligne(tmp_path, jour=JOUR, action="trier", cible="t", sha="s", resume="x" * 201)

    assert not (tmp_path / "supervision.md").exists()


@pytest.mark.parametrize(
    ("action", "cible", "sha"),
    [("supprimer", "t", "s"), ("trier", "", "s"), ("trier", "a|b", "s"), ("trier", "a\nb", "s"), ("trier", "t", "a|b")],
)
def test_a_line_that_cannot_be_read_back_is_refused(tmp_path: Path, action: str, cible: str, sha: str) -> None:
    with pytest.raises(ValueError):
        ajouter_ligne(tmp_path, jour=JOUR, action=action, cible=cible, sha=sha, resume="r")

    assert lire_journal(tmp_path) == []


def test_a_summary_of_exactly_the_limit_is_kept(tmp_path: Path) -> None:
    ajouter_ligne(tmp_path, jour=JOUR, action="trier", cible="t", sha="s", resume="x" * 200)

    assert len(lire_journal(tmp_path)[0].resume) == 200


def test_a_toi_case_is_open_until_a_resolu_line_follows(tmp_path: Path) -> None:
    _ajouter(tmp_path, "a_toi", "regle-1", sha="")
    _ajouter(tmp_path, "a_toi", "regle-2", sha="")
    assert [x.cible for x in cas_a_toi_ouverts(lire_journal(tmp_path))] == ["regle-1", "regle-2"]

    _ajouter(tmp_path, "resolu", "regle-1", sha="")
    assert [x.cible for x in cas_a_toi_ouverts(lire_journal(tmp_path))] == ["regle-2"]

    # Un `resolu` qui précède un nouveau `a_toi` de même cible ne le clôt pas.
    _ajouter(tmp_path, "a_toi", "regle-1", sha="")
    assert [x.cible for x in cas_a_toi_ouverts(lire_journal(tmp_path))] == ["regle-2", "regle-1"]


def test_only_a_toi_lines_are_cases(tmp_path: Path) -> None:
    _ajouter(tmp_path, "trier", "ticket-1")
    _ajouter(tmp_path, "resolu", "ticket-1", sha="")

    assert cas_a_toi_ouverts(lire_journal(tmp_path)) == []
