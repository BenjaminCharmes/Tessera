"""Tests for scripts/seconde_revue_corpus.py (ticket-841).

No model is called and `tessera` is not imported: git runs only on a
temporary repository created by the test.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from seconde_revue_corpus import (  # noqa: E402
    Corpus,
    CorpusInvalide,
    Entree,
    charger_corpus,
    diff_de,
    est_sensible,
    shas_manquants,
    somme_gel,
    verifier_taille,
)


def _defaut(n: int, sensible: bool = False) -> Entree:
    return Entree(
        id=f"d{n}", ticket=f"ticket-{n}", sha=f"{n:040x}", classe="defaut",
        preuve=f"fix-{n}", fichiers_defaut=(f"src/f{n}.py",),
        defaut=f"defaut {n}", sensible=sensible,
    )


def _sain(n: int) -> Entree:
    return Entree(
        id=f"s{n}", ticket=f"ticket-{100 + n}", sha=f"{100 + n:040x}", classe="sain",
        preuve="", fichiers_defaut=(), defaut="", sensible=False,
    )


def _brut(entree: Entree) -> dict[str, Any]:
    return {
        "id": entree.id, "ticket": entree.ticket, "sha": entree.sha,
        "classe": entree.classe, "preuve": entree.preuve,
        "fichiers_defaut": list(entree.fichiers_defaut), "defaut": entree.defaut,
        "sensible": entree.sensible,
    }


def _ecrire(chemin: Path, entrees: list[Entree], gel: str | None = None) -> Path:
    contenu = {
        "gel_sha256": gel if gel is not None else somme_gel(entrees),
        "entrees": [_brut(e) for e in entrees],
    }
    chemin.write_text(json.dumps(contenu), encoding="utf-8")
    return chemin


def _ecrire_brut(chemin: Path, brutes: list[dict[str, Any]]) -> Path:
    # Le gel est calculé sur les entrées telles qu'écrites, pour que seule la
    # cause testée fasse refuser le fichier.
    entrees = [Entree(**{**b, "fichiers_defaut": tuple(b["fichiers_defaut"])}) for b in brutes]
    chemin.write_text(
        json.dumps({"gel_sha256": somme_gel(entrees), "entrees": brutes}), encoding="utf-8"
    )
    return chemin


def test_est_sensible_true_for_a_guard_and_false_for_the_frontend() -> None:
    assert est_sensible(["backend/src/tessera/services/providers/git_guard.py"])
    assert not est_sensible(["frontend/src/App.tsx"])


def test_est_sensible_reads_windows_separators_and_other_guards() -> None:
    assert est_sensible(["scripts\\hooks\\pre-push"])
    assert est_sensible([".github/workflows/ci.yml"])
    assert est_sensible(["backend/src/tessera/services/chemins_proteges.py"])
    assert est_sensible(["x", "backend/src/tessera/services/refus_cli.py"])
    assert not est_sensible([])


def test_somme_gel_is_stable_when_the_order_changes() -> None:
    a, b = _defaut(1), _sain(1)
    assert somme_gel([a, b]) == somme_gel([b, a])


def test_somme_gel_differs_when_an_entry_changes() -> None:
    a = _defaut(1)
    assert somme_gel([a]) != somme_gel([replace(a, defaut="autre")])


def test_charger_corpus_reads_a_valid_file(tmp_path: Path) -> None:
    entrees = [_defaut(1, sensible=True), _sain(1)]
    corpus = charger_corpus(_ecrire(tmp_path / "c.json", entrees))
    assert set(corpus.entrees) == set(entrees)
    assert corpus.gel_sha256 == somme_gel(entrees)


def test_charger_corpus_refuses_a_missing_field(tmp_path: Path) -> None:
    brut = _brut(_defaut(1))
    del brut["ticket"]
    chemin = tmp_path / "c.json"
    chemin.write_text(json.dumps({"gel_sha256": "x", "entrees": [brut]}))
    with pytest.raises(CorpusInvalide, match="ticket"):
        charger_corpus(chemin)


def test_charger_corpus_refuses_a_wrong_type(tmp_path: Path) -> None:
    brut = _brut(_defaut(1))
    brut["sensible"] = "oui"
    chemin = tmp_path / "c.json"
    chemin.write_text(json.dumps({"gel_sha256": "x", "entrees": [brut]}))
    with pytest.raises(CorpusInvalide, match="sensible"):
        charger_corpus(chemin)


def test_charger_corpus_refuses_an_unknown_class(tmp_path: Path) -> None:
    brut = _brut(_sain(1))
    brut["classe"] = "douteux"
    with pytest.raises(CorpusInvalide, match="classe"):
        charger_corpus(_ecrire_brut(tmp_path / "c.json", [brut]))


def test_charger_corpus_refuses_a_duplicate_id(tmp_path: Path) -> None:
    a, b = _brut(_sain(1)), _brut(_sain(2))
    b["id"] = a["id"]
    with pytest.raises(CorpusInvalide, match="`id`"):
        charger_corpus(_ecrire_brut(tmp_path / "c.json", [a, b]))


def test_charger_corpus_refuses_a_duplicate_sha(tmp_path: Path) -> None:
    a, b = _brut(_sain(1)), _brut(_sain(2))
    b["sha"] = a["sha"]
    with pytest.raises(CorpusInvalide, match="`sha`"):
        charger_corpus(_ecrire_brut(tmp_path / "c.json", [a, b]))


def test_charger_corpus_refuses_a_defect_without_proof(tmp_path: Path) -> None:
    brut = _brut(_defaut(1))
    brut["preuve"] = ""
    with pytest.raises(CorpusInvalide, match="preuve"):
        charger_corpus(_ecrire_brut(tmp_path / "c.json", [brut]))


def test_charger_corpus_refuses_a_defect_without_files_or_sentence(tmp_path: Path) -> None:
    sans_fichiers = _brut(_defaut(1))
    sans_fichiers["fichiers_defaut"] = []
    with pytest.raises(CorpusInvalide, match="fichiers_defaut"):
        charger_corpus(_ecrire_brut(tmp_path / "c.json", [sans_fichiers]))
    sans_phrase = _brut(_defaut(2))
    sans_phrase["defaut"] = ""
    with pytest.raises(CorpusInvalide, match="`defaut`"):
        charger_corpus(_ecrire_brut(tmp_path / "d.json", [sans_phrase]))


def test_charger_corpus_refuses_a_healthy_entry_with_defect_files(tmp_path: Path) -> None:
    brut = _brut(_sain(1))
    brut["fichiers_defaut"] = ["a.py"]
    with pytest.raises(CorpusInvalide, match="sain"):
        charger_corpus(_ecrire_brut(tmp_path / "c.json", [brut]))


def test_charger_corpus_refuses_a_wrong_freeze_sum(tmp_path: Path) -> None:
    with pytest.raises(CorpusInvalide, match="gel_sha256"):
        charger_corpus(_ecrire(tmp_path / "c.json", [_sain(1)], gel="0" * 64))


def test_charger_corpus_refuses_unreadable_json(tmp_path: Path) -> None:
    chemin = tmp_path / "c.json"
    chemin.write_text("{pas du json")
    with pytest.raises(CorpusInvalide):
        charger_corpus(chemin)


def test_verifier_taille_reports_every_missed_threshold() -> None:
    corpus = Corpus(entrees=(_defaut(1), _sain(1)), gel_sha256="x")
    assert len(verifier_taille(corpus)) == 3


def test_verifier_taille_accepts_a_conforming_corpus() -> None:
    entrees = [_defaut(n, sensible=n < 4) for n in range(10)] + [_sain(n) for n in range(10)]
    assert verifier_taille(Corpus(entrees=tuple(entrees), gel_sha256="x")) == []


def _git(depot: Path, *args: str) -> str:
    sortie = subprocess.run(
        ["git", "-C", str(depot), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        check=True, capture_output=True, text=True,
    )
    return sortie.stdout.strip()


@pytest.fixture
def depot(tmp_path: Path) -> tuple[Path, str]:
    racine = tmp_path / "depot"
    racine.mkdir()
    _git(racine, "init", "-q")
    (racine / "a.txt").write_text("un\n")
    _git(racine, "add", "a.txt")
    _git(racine, "commit", "-q", "-m", "one")
    (racine / "a.txt").write_text("un\ndeux\n")
    _git(racine, "commit", "-q", "-a", "-m", "two")
    return racine, _git(racine, "rev-parse", "HEAD")


def test_shas_manquants_lists_only_unknown_commits(depot: tuple[Path, str]) -> None:
    racine, tete = depot
    connu = replace(_sain(1), sha=tete)
    inconnu = _sain(2)
    corpus = Corpus(entrees=(connu, inconnu), gel_sha256="x")
    assert shas_manquants(corpus, racine) == [inconnu.sha]


def test_diff_de_returns_the_squash_diff(depot: tuple[Path, str]) -> None:
    racine, tete = depot
    texte = diff_de(replace(_sain(1), sha=tete), racine)
    assert "+deux" in texte
    assert "-un" not in texte
