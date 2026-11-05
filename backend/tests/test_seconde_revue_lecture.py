"""Tests for scripts/seconde_revue_lecture.py (ticket-843).

No provider is called: the functions read plain dictionaries.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from seconde_revue_lecture import (  # noqa: E402
    Resultat,
    composer_entree,
    corps_du_ticket,
    designe_le_defaut,
    leve,
    lire_resultats,
    remarques_au_seuil,
    vers_ligne,
)


def _remarque(confiance: int, texte: str = "problème", lieu: str | None = None) -> dict[str, Any]:
    brute: dict[str, Any] = {"text": texte, "confidence": confiance}
    if lieu is not None:
        brute["location"] = lieu
    return brute


def _sortie(verdict: str, *remarques: dict[str, Any]) -> dict[str, Any]:
    return {"verdict": verdict, "summary": "bilan", "blocking": list(remarques)}


def test_corps_du_ticket_found_in_done_then_absent(tmp_path: Path) -> None:
    dossier = tmp_path / "done"
    dossier.mkdir()
    (dossier / "ticket-900-un-titre.md").write_text("# corps du ticket\n", encoding="utf-8")
    assert corps_du_ticket("ticket-900", tmp_path) == "# corps du ticket\n"
    with pytest.raises(ValueError, match="ticket-901"):
        corps_du_ticket("ticket-901", tmp_path)


def test_corps_du_ticket_does_not_confuse_a_longer_number(tmp_path: Path) -> None:
    dossier = tmp_path / "todo"
    dossier.mkdir()
    (dossier / "ticket-9000-autre.md").write_text("autre", encoding="utf-8")
    with pytest.raises(ValueError):
        corps_du_ticket("ticket-900", tmp_path)


def test_composer_entree_holds_ticket_and_diff_and_nothing_else() -> None:
    texte = composer_entree("OBJECTIF du ticket", "+ligne ajoutee")
    assert "OBJECTIF du ticket" in texte
    assert "## Code produit par le codeur" in texte
    assert "+ligne ajoutee" in texte
    assert texte.index("OBJECTIF") < texte.index("+ligne ajoutee")
    for interdit in ("test", "audit"):
        assert f"## {interdit}".lower() not in texte.lower()
        assert "résultat des tests" not in texte.lower()


def test_leve_false_for_an_approval() -> None:
    assert leve(_sortie("APPROVED"), 80) is False


def test_leve_true_for_a_remark_at_the_threshold() -> None:
    assert leve(_sortie("CHANGES_REQUESTED", _remarque(80)), 80) is True


def test_leve_false_when_every_remark_is_under_the_threshold() -> None:
    assert leve(_sortie("CHANGES_REQUESTED", _remarque(79), _remarque(10)), 80) is False


def test_leve_true_for_none_and_for_an_off_schema_answer() -> None:
    assert leve(None, 80) is True
    assert leve({"verdict": "PEUT-ETRE"}, 80) is True


def test_remarques_au_seuil_keeps_only_remarks_at_or_over_the_threshold() -> None:
    sortie = _sortie("CHANGES_REQUESTED", _remarque(90, "haut"), _remarque(50, "bas"))
    assert [r["text"] for r in remarques_au_seuil(sortie, 80)] == ["haut"]
    assert remarques_au_seuil(None, 80) == ()
    assert remarques_au_seuil(_sortie("APPROVED"), 80) == ()


def test_leve_and_remarques_au_seuil_follow_the_threshold() -> None:
    sortie = _sortie("CHANGES_REQUESTED", _remarque(60))
    assert leve(sortie, 80) is False and remarques_au_seuil(sortie, 80) == ()
    assert leve(sortie, 50) is True and len(remarques_au_seuil(sortie, 50)) == 1


def test_designe_le_defaut_reads_a_windows_and_a_posix_path() -> None:
    fichiers = ["backend\\src\\tessera\\services\\git_guard.py"]
    assert designe_le_defaut(_remarque(90, lieu="backend/src/tessera/services/git_guard.py:85"), fichiers)
    posix = ["backend/src/tessera/services/git_guard.py"]
    assert designe_le_defaut(_remarque(90, "bug dans backend\\src\\tessera\\services\\GIT_GUARD.py"), posix)


def test_designe_le_defaut_false_when_no_file_appears() -> None:
    assert not designe_le_defaut(_remarque(90, "rien", "autre.py:3"), ["src/git_guard.py"])
    assert not designe_le_defaut(_remarque(90, "rien"), [])


def _resultat(**changes: Any) -> Resultat:
    base: dict[str, Any] = dict(
        id="e1", bras="C", modele="ollama:m", gel_sha256="abc", etat="ok", leve=True,
        remarques=({"text": "à voir\nsur deux lignes", "confidence": 90},),
        cout_usd=0.0, duree_ms=1234,
    )
    base.update(changes)
    return Resultat(**base)


def test_vers_ligne_and_lire_resultats_round_trip(tmp_path: Path) -> None:
    premier, second = _resultat(), _resultat(id="e2", bras="B", etat="hors_fenetre", leve=None, remarques=())
    ligne = vers_ligne(premier)
    assert "\n" not in ligne
    chemin = tmp_path / "resultats.jsonl"
    chemin.write_text(ligne + "\n" + vers_ligne(second) + "\n", encoding="utf-8")
    assert lire_resultats(chemin) == [premier, second]


def test_lire_resultats_returns_empty_for_a_missing_file(tmp_path: Path) -> None:
    assert lire_resultats(tmp_path / "absent.jsonl") == []
