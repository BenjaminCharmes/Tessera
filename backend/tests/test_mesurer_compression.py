"""Tests for scripts/mesurer_compression.py and its helpers (ticket-605).

Neither headroom nor a model is called: compression is a stub passed in, and
the database is a temporary SQLite file holding only the columns read.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import argparse  # noqa: E402

from mesure_calculs import (  # noqa: E402
    ReleveRole,
    cellule,
    estimer_tokens,
    lignes_perdues,
    raison_non_mesurable,
    releve_par_role,
    run_mesurable,
)
from mesure_headroom import (  # noqa: E402
    CompresseurIndisponible,
    compresser,
    diff_du_run,
    taux_retire,
)
from mesure_rendu import (  # noqa: E402
    LigneDiff,
    LigneTableau,
    ecrire_blocs,
    remplacer_bloc,
    rendre_conclusion,
    rendre_diffs,
    rendre_tableau,
)
from mesure_verdict import Mesures, verdict  # noqa: E402
from mesurer_compression import (  # noqa: E402
    agreger,
    ligne_du_diff,
    ligne_du_role,
    mesurer,
)
from sonde_usage import cumule_les_tours, entree_totale, ligne_de_sortie  # noqa: E402

_SORTIE_ROUGE = """\
=========== FAILURES ===========
___ test_a ___
E   AssertionError: boom
=========== short test summary info ===========
FAILED tests/test_a.py::test_a - AssertionError: boom
FAILED tests/test_b.py::test_b - assert 0
========= 2 failed, 3 passed in 1.20s =========
"""


def _base(tmp_path: Path) -> Path:
    db = tmp_path / "t.db"
    with sqlite3.connect(db) as con:
        con.execute(
            "CREATE TABLE agent_calls (run_id TEXT, role TEXT, model TEXT,"
            " input_tokens INT, output_tokens INT, cache_read_tokens INT,"
            " cache_creation_tokens INT)"
        )
        con.execute("CREATE TABLE pipeline_runs (id TEXT, pushed_sha TEXT)")
        con.executemany(
            "INSERT INTO agent_calls VALUES (?,?,?,?,?,?,?)",
            [
                ("r1", "codeur", "claude-sonnet-5-5", 100, 10, 900, 300),
                ("r1", "codeur", "claude-sonnet-5-5", 50, 5, 450, 0),
                ("r1", "reviewer", "claude-opus-5-5", 2000, 40, 0, 500),
                ("old", "codeur", "claude-sonnet-5-5", 100, 10, 900, 0),
            ],
        )
        con.execute("INSERT INTO pipeline_runs VALUES ('r1', NULL)")
    return db


def test_releve_par_role_sums_each_column_per_role(tmp_path: Path) -> None:
    releve = releve_par_role(_base(tmp_path), ["r1"])
    codeur = releve["codeur"]
    assert (codeur.appels, codeur.input_tokens) == (2, 150)
    assert (codeur.cache_read_tokens, codeur.cache_creation_tokens) == (1350, 300)
    assert releve["reviewer"].cout_entree_usd > 0


def test_releve_par_role_without_runs_is_empty(tmp_path: Path) -> None:
    assert releve_par_role(_base(tmp_path), []) == {}


def test_run_mesurable_false_before_cache_creation_was_kept(tmp_path: Path) -> None:
    db = _base(tmp_path)
    assert run_mesurable(db, "r1") is True
    assert run_mesurable(db, "old") is False


def test_lignes_perdues_reports_the_missing_failed_line() -> None:
    compresse = "\n".join(
        ligne for ligne in _SORTIE_ROUGE.splitlines() if "test_b" not in ligne
    )
    perdues = lignes_perdues(_SORTIE_ROUGE, compresse)
    assert perdues and all("test_b" in ligne for ligne in perdues)


def test_lignes_perdues_is_empty_when_nothing_is_missing() -> None:
    assert lignes_perdues(_SORTIE_ROUGE, _SORTIE_ROUGE + "\nextra") == []


def test_cellule_says_non_mesure_with_its_reason() -> None:
    assert cellule(None, "antérieur au ticket-604") == "non mesuré (antérieur au ticket-604)"
    assert cellule(None) == "non mesuré"
    assert cellule(1234567) == "1 234 567"


def test_rendre_tableau_renders_a_non_mesure_cell() -> None:
    ligne = LigneTableau("abcdef123", "codeur", 10, None, None, "prompts non stockés")
    rendu = rendre_tableau([ligne])
    assert "non mesuré (prompts non stockés)" in rendu and "| abcdef12 |" in rendu
    assert "aucun run donné" in rendre_tableau([])


def test_remplacer_bloc_only_touches_what_sits_between_markers() -> None:
    texte = "avant\n<!-- x:debut -->\nvieux\n<!-- x:fin -->\naprès\n"
    assert remplacer_bloc(texte, "x", "neuf") == (
        "avant\n<!-- x:debut -->\nneuf\n<!-- x:fin -->\naprès\n"
    )
    with pytest.raises(ValueError):
        remplacer_bloc("sans marqueur", "x", "neuf")


def test_ecrire_blocs_writes_nothing_when_a_marker_is_missing(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("<!-- a:debut -->\n1\n<!-- a:fin -->\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ecrire_blocs(spec, {"a": "2", "b": "3"})
    assert "1" in spec.read_text(encoding="utf-8")
    ecrire_blocs(spec, {"a": "2"})
    assert "\n2\n" in spec.read_text(encoding="utf-8")


def _sans_la_ligne_b(texte: str) -> str:
    return "\n".join(x for x in texte.splitlines() if "test_b" not in x)


def _releve(role: str, tmp_path: Path) -> ReleveRole:
    return releve_par_role(_base(tmp_path), ["r1"])[role]


def test_ligne_du_role_counts_the_lost_line_and_the_removed_tokens(tmp_path: Path) -> None:
    textes = {"diff": "d" * 4000, "tests": _SORTIE_ROUGE}
    ligne = ligne_du_role(
        "r1", _releve("reviewer", tmp_path), textes,
        lambda t: t[: len(t) // 2] if t.startswith("d") else _sans_la_ligne_b(t),
    )
    assert ligne.perdues == 1 and ligne.apres is not None
    assert ligne.entree is not None and ligne.entree - ligne.apres >= 500


def test_ligne_du_role_codeur_is_non_mesure(tmp_path: Path) -> None:
    ligne = ligne_du_role("r1", _releve("codeur", tmp_path), {"diff": "x"}, lambda t: t)
    assert ligne.apres is None and "non stockés" in ligne.raison


def test_ligne_du_role_survives_a_compressor_that_is_missing(tmp_path: Path) -> None:
    def absent(_: str) -> str:
        raise CompresseurIndisponible("headroom absent")

    ligne = ligne_du_role("r1", _releve("reviewer", tmp_path), {"diff": "x"}, absent)
    assert ligne.apres is None and ligne.raison == "headroom absent"


def test_compresser_raises_when_headroom_is_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "headroom", None)
    with pytest.raises(CompresseurIndisponible):
        compresser("texte")


def test_diff_du_run_explains_a_missing_pushed_sha(tmp_path: Path) -> None:
    diff, raison = diff_du_run(tmp_path, _base(tmp_path), "r1", "develop")
    assert diff == "" and "pushed_sha" in raison


def test_agreger_reads_the_three_figures(tmp_path: Path) -> None:
    lignes = [
        LigneTableau("r1", "reviewer", 100, 80, 0, "", 10.0, 3.0),
        LigneTableau("r1", "securite", 100, 90, None, "", 10.0, 1.0),
    ]
    diffs = [LigneDiff("r1", 100, 90), LigneDiff("r2", 100, 60), LigneDiff("r3", None, None, "x")]
    mesures = agreger(lignes, [_releve("codeur", tmp_path)], diffs, 2)
    assert mesures.taux_diff == pytest.approx(0.4)
    assert mesures.ratio_texte == pytest.approx(0.2)
    assert mesures.lignes_perdues == 0
    assert mesures.part_entree_codeur == pytest.approx(450 / 1815)


def test_estimer_tokens_is_characters_over_four() -> None:
    assert estimer_tokens("a" * 400) == 100


def _m(ratio: float | None, perdues: int | None, part: float | None, runs: int = 2) -> Mesures:
    return Mesures(runs, ratio, perdues, part)


def test_verdict_adopts_above_the_text_threshold_with_no_line_lost() -> None:
    assert verdict(_m(0.2, 0, 0.1)).decision == "adopter"


def test_verdict_one_lost_line_closes_the_text_path() -> None:
    resultat = verdict(_m(0.6, 1, 0.1))
    assert resultat.decision == "écarter" and "perdue" in resultat.motif


def test_verdict_drops_when_both_thresholds_are_missed() -> None:
    assert verdict(_m(0.05, 0, 0.1)).decision == "écarter"


def test_verdict_defers_on_a_big_codeur_input_or_missing_data() -> None:
    assert verdict(_m(0.05, 0, 0.4)).decision == "reporter"
    assert verdict(_m(None, None, None)).decision == "reporter"
    assert verdict(_m(0.5, 0, 0.1, runs=1)).decision == "reporter"


def test_rendre_conclusion_quotes_the_figures() -> None:
    mesures = _m(0.2, 0, None)
    texte = rendre_conclusion(verdict(mesures), mesures)
    assert "adopter" in texte and "20.0%" in texte and "non mesurée" in texte


def test_sonde_reads_cumulative_and_single_turn_usage() -> None:
    assert cumule_les_tours([100, 200, 300], 600) is True
    assert cumule_les_tours([100, 200, 300], 300) is False
    assert cumule_les_tours([100, 200, 300], 450) is None
    assert cumule_les_tours([100], 100) is None
    assert "cumule les tours" in ligne_de_sortie([1, 2], 3)


def test_entree_totale_adds_fresh_read_and_created_tokens() -> None:
    usage = {"input_tokens": 1, "cache_read_input_tokens": 20, "cache_creation_input_tokens": 300}
    assert entree_totale(usage) == 321


def test_releve_par_role_sums_a_role_split_over_two_models(tmp_path: Path) -> None:
    db = _base(tmp_path)
    with sqlite3.connect(db) as con:
        con.execute(
            "INSERT INTO agent_calls VALUES ('r1','reviewer','claude-haiku-4-5',7,1,3,5)"
        )
        con.execute("INSERT INTO agent_calls VALUES ('r1','reviewer','claude-opus-5-5',0,0,0,0)")
    reviewer = releve_par_role(db, ["r1"])["reviewer"]
    assert (reviewer.appels, reviewer.input_tokens) == (3, 2007)
    assert (reviewer.cache_read_tokens, reviewer.cache_creation_tokens) == (3, 505)
    assert reviewer.modele == "claude-opus-5-5"  # the busier line prices the rest


def test_raison_non_mesurable_names_an_absent_column(tmp_path: Path) -> None:
    db = tmp_path / "ancienne.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE agent_calls (run_id TEXT, role TEXT)")
    assert "migration 9" in raison_non_mesurable(db, "r1")
    assert raison_non_mesurable(_base(tmp_path), "r1") == ""
    assert "antérieur" in raison_non_mesurable(_base_sans_neuf(tmp_path), "old")


def _base_sans_neuf(tmp_path: Path) -> Path:
    autre = tmp_path / "autre"
    autre.mkdir()
    return _base(autre)


def test_ligne_du_role_passes_on_the_reason_the_diff_is_missing(tmp_path: Path) -> None:
    ligne = ligne_du_role(
        "r1", _releve("reviewer", tmp_path), {}, lambda t: t, "commit 1234abcd introuvable localement"
    )
    assert ligne.raison == "commit 1234abcd introuvable localement"


def test_compresser_asks_headroom_to_compress_user_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    appels: list[dict[str, object]] = []

    class _Resultat:
        messages = [{"role": "user", "content": "court"}]

    class _Faux:
        @staticmethod
        def compress(messages: list[dict[str, str]], **kwargs: object) -> _Resultat:
            appels.append(kwargs)
            return _Resultat()

    monkeypatch.setitem(sys.modules, "headroom", _Faux)
    assert compresser("un texte long") == "court"
    assert appels == [{"compress_user_messages": True}]


def test_taux_retire_and_ligne_du_diff() -> None:
    assert taux_retire("a" * 400, "a" * 300) == pytest.approx(0.25)
    assert taux_retire("", "") == 0.0
    ligne = ligne_du_diff("r1", "a" * 400, "", lambda t: t[:300])
    assert (ligne.avant, ligne.apres) == (100, 75) and ligne.taux == pytest.approx(0.25)
    assert ligne_du_diff("r1", "", "pas de pushed_sha", lambda t: t).taux is None


def test_rendre_diffs_renders_the_rate_and_the_reason() -> None:
    rendu = rendre_diffs([LigneDiff("abcdef123", 100, 75), LigneDiff("r2", None, None, "sans sha")])
    assert "| abcdef12 | 100 | 75 | 25.0% |" in rendu
    assert "non mesuré (sans sha)" in rendu


def test_verdict_a_diff_rate_under_the_threshold_closes_the_text_path() -> None:
    mesures = Mesures(2, None, None, None, taux_diff=0.04)
    resultat = verdict(mesures)
    assert resultat.decision == "reporter" and "plafond" in resultat.motif
    assert verdict(Mesures(2, None, None, 0.1, taux_diff=0.04)).decision == "écarter"
    assert verdict(Mesures(2, None, None, None, taux_diff=0.5)).decision == "reporter"


def test_mesurer_reports_every_run_of_an_unmigrated_database(tmp_path: Path) -> None:
    db = tmp_path / "ancienne.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE agent_calls (run_id TEXT, role TEXT)")
        con.execute("CREATE TABLE pipeline_runs (id TEXT, pushed_sha TEXT)")
    args = argparse.Namespace(
        db=str(db), runs=["a", "b"], repo=str(tmp_path), base="develop",
        sortie_test=None, run_rouge="",
    )
    lignes, diffs, mesures = mesurer(args, lambda t: t)
    assert [x.raison for x in lignes] == ["colonne cache_creation_tokens absente (migration 9 non appliquée)"] * 2
    assert all("pushed_sha" in d.raison for d in diffs)
    assert mesures.runs_mesures == 0 and mesures.taux_diff is None
