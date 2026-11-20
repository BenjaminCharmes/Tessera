"""Tests for scripts/seconde_revue_decision.py (ticket-845). Pure functions only."""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from seconde_revue_corpus import Corpus, Entree  # noqa: E402
from seconde_revue_decision import DEBUT_CONCLUSION, FIN_CONCLUSION, Jugement, Mesures, decision, lire_relecture, mesures_depuis, rapport  # noqa: E402
from seconde_revue_lecture import Resultat  # noqa: E402


def _mesures(**changes: Any) -> Mesures:
    base = Mesures(
        valide=True, defauts_en_plus=3, defauts_en_plus_sensibles=0,
        faux_positifs_en_plus=0, faux_positifs_en_plus_sensibles=0,
        duree_ajoutee_ms=1000, cout_c_moyen=0.0, cout_b_moyen=0.5,
    )
    return replace(base, **changes)


def test_decision_non_concluant_when_the_replay_is_not_valid() -> None:
    assert decision(_mesures(valide=False, defauts_en_plus=9)).decision == "non concluant"


def test_decision_adopter() -> None:
    assert decision(_mesures()).decision == "adopter"


def test_decision_reserver() -> None:
    m = _mesures(defauts_en_plus=1, defauts_en_plus_sensibles=2, faux_positifs_en_plus_sensibles=1)
    assert decision(m).decision == "reserver"


def test_decision_abandonner() -> None:
    assert decision(_mesures(defauts_en_plus=1)).decision == "abandonner"


def test_decision_three_extra_defects_adopt_and_two_do_not() -> None:
    assert decision(_mesures(defauts_en_plus=3)).decision == "adopter"
    assert decision(_mesures(defauts_en_plus=2)).decision == "abandonner"


def test_decision_two_extra_false_positives_adopt_and_three_do_not() -> None:
    assert decision(_mesures(faux_positifs_en_plus=2)).decision == "adopter"
    assert decision(_mesures(faux_positifs_en_plus=3)).decision == "abandonner"


def test_decision_duration_bound_is_300000_ms_included() -> None:
    assert decision(_mesures(duree_ajoutee_ms=300_000)).decision == "adopter"
    assert decision(_mesures(duree_ajoutee_ms=300_001)).decision == "abandonner"


def test_decision_a_dearer_candidate_falls_back_to_reserver() -> None:
    cher = _mesures(
        cout_c_moyen=1.0, cout_b_moyen=0.5,
        defauts_en_plus_sensibles=2, faux_positifs_en_plus_sensibles=1,
    )
    assert decision(cher).decision == "reserver"
    assert decision(replace(cher, defauts_en_plus_sensibles=1)).decision == "abandonner"


def _entree(ident: str, classe: str, sensible: bool = False) -> Entree:
    defaut = classe == "defaut"
    return Entree(
        id=ident, ticket="ticket-1", sha=ident.ljust(40, "0"), classe=classe,  # type: ignore[arg-type]
        preuve="fix" if defaut else "", fichiers_defaut=("a.py",) if defaut else (),
        defaut="d" if defaut else "", sensible=sensible,
    )


def _res(ident: str, bras: str, leve: bool | None, etat: str = "ok", cout: float = 0.0,
         duree: int = 100) -> Resultat:
    return Resultat(
        id=ident, bras=bras, modele="m", gel_sha256="g", etat=etat,  # type: ignore[arg-type]
        leve=leve, remarques=(), cout_usd=cout, duree_ms=duree,
    )


def _jug(ident: str, jugement: str, bras: str = "C") -> Jugement:
    return Jugement(id=ident, bras=bras, rang=1, jugement=jugement)  # type: ignore[arg-type]


def _petit() -> Corpus:
    entrees = (_entree("d1", "defaut", True), _entree("s1", "sain"))
    return Corpus(entrees=entrees, gel_sha256="g")


def test_mesures_depuis_counts_a_confirmed_extra_defect() -> None:
    resultats = [_res("d1", "B", False), _res("d1", "C", True),
                 _res("s1", "B", False), _res("s1", "C", False)]
    m = mesures_depuis(_petit(), resultats, [_jug("d1", "autre_defaut")])
    assert (m.defauts_en_plus, m.defauts_en_plus_sensibles) == (1, 1)
    assert m.faux_positifs_en_plus == 0


def test_mesures_depuis_an_unfounded_remark_is_not_a_defect() -> None:
    resultats = [_res("d1", "B", False), _res("d1", "C", True)]
    m = mesures_depuis(_petit(), resultats, [_jug("d1", "infonde")])
    assert m.defauts_en_plus == 0


def test_mesures_depuis_a_defect_b_raises_too_does_not_count() -> None:
    resultats = [_res("d1", "B", True), _res("d1", "C", True)]
    m = mesures_depuis(_petit(), resultats, [_jug("d1", "confirme")])
    assert m.defauts_en_plus == 0


def test_mesures_depuis_counts_an_extra_false_positive() -> None:
    resultats = [_res("s1", "B", False), _res("s1", "C", True)]
    m = mesures_depuis(_petit(), resultats, [_jug("s1", "infonde")])
    assert m.faux_positifs_en_plus == 1


def test_mesures_depuis_excludes_an_entry_out_of_window() -> None:
    resultats = [_res("d1", "B", False), _res("d1", "C", None, etat="hors_fenetre")]
    m = mesures_depuis(_petit(), resultats, [_jug("d1", "confirme")])
    assert m.defauts_en_plus == 0


def _grand(approuvees_b: int, exclues_c: int) -> tuple[Corpus, list[Resultat]]:
    entrees = tuple(_entree(f"s{i:03d}", "sain") for i in range(100))
    resultats: list[Resultat] = []
    for i, entree in enumerate(entrees):
        resultats.append(_res(entree.id, "B", leve=i >= approuvees_b, cout=0.5, duree=10))
        if i < exclues_c:
            resultats.append(_res(entree.id, "C", None, etat="hors_fenetre"))
        else:
            resultats.append(_res(entree.id, "C", False, cout=0.0, duree=200))
    return Corpus(entrees=entrees, gel_sha256="g"), resultats


def test_mesures_depuis_valid_needs_eighty_percent_of_b_approvals() -> None:
    corpus, resultats = _grand(approuvees_b=79, exclues_c=0)
    assert mesures_depuis(corpus, resultats, []).valide is False
    corpus, resultats = _grand(approuvees_b=80, exclues_c=0)
    assert mesures_depuis(corpus, resultats, []).valide is True


def test_mesures_depuis_valid_needs_c_exclusions_under_twenty_five_percent() -> None:
    corpus, resultats = _grand(approuvees_b=100, exclues_c=25)
    assert mesures_depuis(corpus, resultats, []).valide is False
    corpus, resultats = _grand(approuvees_b=100, exclues_c=24)
    assert mesures_depuis(corpus, resultats, []).valide is True


def test_mesures_depuis_averages_cost_and_duration() -> None:
    corpus, resultats = _grand(approuvees_b=100, exclues_c=0)
    m = mesures_depuis(corpus, resultats, [])
    assert m.cout_b_moyen == 0.5 and m.cout_c_moyen == 0.0 and m.duree_ajoutee_ms == 200


def test_rapport_holds_the_marked_block_with_the_decision() -> None:
    corpus, resultats = _grand(approuvees_b=100, exclues_c=0)
    texte = rapport(corpus, resultats, [])
    assert DEBUT_CONCLUSION in texte and FIN_CONCLUSION in texte
    bloc = texte.split(DEBUT_CONCLUSION)[1].split(FIN_CONCLUSION)[0]
    attendu = decision(mesures_depuis(corpus, resultats, [])).decision
    assert f"Recommandation : {attendu}" in bloc


def test_lire_relecture_reads_lines_a_list_and_a_missing_file(tmp_path: Path) -> None:
    ligne = '{"id": "d1", "bras": "C", "rang": 1, "jugement": "confirme"}'
    en_lignes = tmp_path / "lignes.json"
    en_lignes.write_text(ligne + "\n" + ligne.replace("confirme", "infonde") + "\n", encoding="utf-8")
    assert [j.jugement for j in lire_relecture(en_lignes)] == ["confirme", "infonde"]
    en_liste = tmp_path / "liste.json"
    en_liste.write_text("[" + ligne + "]", encoding="utf-8")
    assert lire_relecture(en_liste) == [_jug("d1", "confirme")]
    assert lire_relecture(tmp_path / "absent.json") == []
