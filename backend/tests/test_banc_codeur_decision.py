"""Tests for scripts/banc_codeur_decision.py (ticket-1056). Pure functions only."""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from banc_codeur_cellule import Resultat  # noqa: E402
from banc_codeur_corpus import Corpus, Entree  # noqa: E402
from banc_codeur_decision import DEBUT_CONCLUSION, FIN_CONCLUSION, MesureBras, Mesures, decision, ecrire_rapport, mesures_depuis, rapport  # noqa: E402

GEL = "g" * 64


def _corpus(n: int = 20) -> Corpus:
    entrees = tuple(
        Entree(f"e{i:02d}", str(i), "s", "b", "t.md", "h", ("x.py",), 40, False) for i in range(n)
    )
    return Corpus(entrees=entrees, gel_sha256=GEL)


def _res(i: int, bras: str, *, t1: bool = True, etat: str = "ok", cout: float = 1.0,
         final: bool = True, duree: int = 1000) -> Resultat:
    return Resultat(
        id=f"e{i:02d}", bras=bras, gel_sha256=GEL, modele="m", etat=etat, tours=1,
        approuve_t1=t1, approuve_final=final, tests_verts=final, tests_reference_verts=True,
        cout_codeur_usd=cout, duree_ms={"codeur": duree, "total": duree},
    )


def _bras(bras: str, t1_count: int, **kw: float) -> list[Resultat]:
    return [_res(i, bras, t1=i < t1_count, **kw) for i in range(20)]  # type: ignore[arg-type]


def _mb(id: str, **kw: float) -> MesureBras:
    base = MesureBras(id, 20, 20, 10, 18, 1.0, 1.0, 2.0, (1, 2, 3), 1000, 2000, 5)
    return replace(base, **kw)  # type: ignore[arg-type]


def _m(*candidats: MesureBras, non_concluant: str | None = None) -> Mesures:
    return Mesures(non_concluant=non_concluant, a=_mb("A"), candidats=candidats, bruit="")


def test_non_concluant_comes_first() -> None:
    v = decision(_m(_mb("M", t1=20), non_concluant="A reproduit 3 entrée(s)"))
    assert v.decision == "non concluant" and v.bras is None


def test_meilleur() -> None:
    v = decision(_m(_mb("M", t1=13)))
    assert (v.decision, v.bras) == ("meilleur", "M")


def test_meilleur_refused_when_tests_or_duration_regress() -> None:
    assert decision(_m(_mb("M", t1=13, v=17))).decision == "garder A"
    assert decision(_m(_mb("M", t1=13, duree_moyenne_ms=2001))).decision == "garder A"
    assert decision(_m(_mb("M", t1=13, duree_moyenne_ms=2000))).decision == "meilleur"


def test_meilleur_gap_is_two_entries() -> None:
    assert decision(_m(_mb("M", t1=11))).decision == "garder A"


def test_moins_cher() -> None:
    v = decision(_m(_mb("P", t1=9, cout_moyen=0.5)))
    assert (v.decision, v.bras) == ("moins cher", "P")


def test_moins_cher_equality_at_sixty_percent_and_one_entry() -> None:
    a = replace(_mb("A"), cout_moyen=5.0)
    x = _mb("P", t1=9, cout_moyen=3.0)
    assert decision(Mesures(None, a, (x,), "")).decision == "moins cher"
    assert decision(Mesures(None, a, (replace(x, cout_moyen=3.1),), "")).decision == "garder A"
    assert decision(Mesures(None, a, (replace(x, t1=8, cout_moyen=1.0),), "")).decision == "garder A"


def test_garder_a() -> None:
    assert decision(_m(_mb("M", t1=11, cout_moyen=0.9))).decision == "garder A"


def test_tie_between_two_arms_takes_larger_t1_then_cheaper_then_id() -> None:
    assert decision(_m(_mb("M", t1=13), _mb("P", t1=14))).bras == "P"
    assert decision(_m(_mb("M", t1=14, cout_moyen=1.5), _mb("P", t1=14, cout_moyen=1.2))).bras == "P"
    assert decision(_m(_mb("P", t1=14), _mb("M", t1=14))).bras == "M"


def test_echec_env_leaves_every_arm_before_any_count() -> None:
    res = _bras("A", 10) + _bras("M", 10)
    res[0] = _res(0, "A", etat="echec_env")
    m = mesures_depuis(_corpus(), res)
    assert m.a.retenues == 19 and m.candidats[0].retenues == 19


def test_indisponible_cell_counts_as_excluded() -> None:
    res = _bras("A", 10) + [_res(i, "M", etat="indisponible") for i in range(5)] + _bras("M", 10)[5:]
    m = mesures_depuis(_corpus(), res)
    assert m.non_concluant is not None and "M" in m.non_concluant


def test_exclusion_threshold_is_two() -> None:
    res = _bras("A", 10) + [_res(i, "M", etat="indisponible") for i in range(2)] + _bras("M", 10)[2:]
    assert mesures_depuis(_corpus(), res).non_concluant is None


def test_a_reproducing_fewer_than_seven_is_inconclusive() -> None:
    res = [_res(i, "A", final=i < 6) for i in range(9)]
    assert "A reproduit 6" in str(mesures_depuis(_corpus(), res).non_concluant)


def test_noise_between_a_and_a2() -> None:
    res = _bras("A", 20) + [_res(i, "A2", t1=i >= 2) for i in range(5)]
    assert "A/A2" in mesures_depuis(_corpus(), res).bruit
    assert mesures_depuis(_corpus(), res).non_concluant is None
    res = _bras("A", 20) + [_res(i, "A2", t1=i >= 3) for i in range(5)]
    assert "divergent sur 3" in str(mesures_depuis(_corpus(), res).non_concluant)


def test_pairing_uses_only_entries_ok_in_every_arm() -> None:
    res = _bras("A", 10) + _bras("M", 10)
    res[20 + 0] = _res(0, "M", etat="indisponible")
    m = mesures_depuis(_corpus(), res)
    assert m.a.retenues == 19 and m.a.cellules == 20


def test_reference_tests_do_not_enter_the_decision() -> None:
    res = _bras("A", 10) + _bras("M", 13)
    for r in res:
        r.tests_reference_verts = r.bras == "M"
    assert decision(mesures_depuis(_corpus(), res)).decision == "meilleur"


def test_gel_mismatch_is_refused() -> None:
    res = _bras("A", 10)
    res[0].gel_sha256 = "autre"
    with pytest.raises(ValueError):
        mesures_depuis(_corpus(), res)


def test_rapport_has_the_table_and_the_marked_conclusion() -> None:
    texte = rapport(_corpus(), _bras("A", 10) + _bras("M", 13, cout=2.0))
    assert "| A | 20 | 20 | 10 | 20 |" in texte
    assert "tests de référence verts" in texte
    assert DEBUT_CONCLUSION in texte and FIN_CONCLUSION in texte
    assert "l'ADR qui décide appartient à un humain" in texte
    assert "Recommandation : meilleur : M" in texte


def test_rapport_is_identical_on_a_rerun(tmp_path: Path) -> None:
    res = _bras("A", 10) + _bras("M", 13)
    ecrire_rapport(_corpus(), res, tmp_path / "r" / "banc.md")
    ecrire_rapport(_corpus(), list(reversed(res)), tmp_path / "r" / "banc2.md")
    assert (tmp_path / "r" / "banc.md").read_bytes() == (tmp_path / "r" / "banc2.md").read_bytes()
