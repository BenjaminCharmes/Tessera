"""The concluded second-review trial agrees with its own data (ticket-846).

Reads the three files the trial left in the repository: results, the human
review and the report. The conclusion block must be the one the rule gives on
those files, so a report edited by hand cannot drift from its figures.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_RACINE = Path(__file__).resolve().parent.parent.parent
if str(_RACINE / "scripts") not in sys.path:
    sys.path.insert(0, str(_RACINE / "scripts"))

from seconde_revue_corpus import charger_corpus  # noqa: E402
from seconde_revue_decision import DEBUT_CONCLUSION, FIN_CONCLUSION, decision, lire_relecture, mesures_depuis  # noqa: E402
from seconde_revue_lecture import lire_resultats  # noqa: E402

_ESSAI = _RACINE / "docs" / "essais" / "seconde-revue"
_RAPPORT = _RACINE / "docs" / "essais" / "seconde-revue.md"


def _bloc_de_conclusion() -> str:
    texte = _RAPPORT.read_text(encoding="utf-8")
    debut = texte.index(DEBUT_CONCLUSION) + len(DEBUT_CONCLUSION)
    return texte[debut:texte.index(FIN_CONCLUSION)]


def test_report_conclusion_is_the_rule_applied_to_the_files() -> None:
    corpus = charger_corpus(_ESSAI / "corpus.json")
    resultats = lire_resultats(_ESSAI / "resultats.jsonl")
    relecture = lire_relecture(_ESSAI / "relecture.json")
    verdict = decision(mesures_depuis(corpus, resultats, relecture))
    assert f"**Recommandation : {verdict.decision}.**" in _bloc_de_conclusion()


def test_report_cites_the_freeze_sum_of_the_corpus() -> None:
    corpus = charger_corpus(_ESSAI / "corpus.json")
    assert corpus.gel_sha256 in _RAPPORT.read_text(encoding="utf-8")


def test_every_result_line_carries_the_freeze_sum_and_one_per_entry_and_arm() -> None:
    corpus = charger_corpus(_ESSAI / "corpus.json")
    resultats = lire_resultats(_ESSAI / "resultats.jsonl")
    assert {r.gel_sha256 for r in resultats} == {corpus.gel_sha256}
    cles = [(r.id, r.bras) for r in resultats]
    assert len(cles) == len(set(cles)) == 2 * len(corpus.entrees)


def test_every_raised_remark_has_one_human_judgement() -> None:
    brut = json.loads((_ESSAI / "relecture.json").read_text(encoding="utf-8"))
    juges = {(j["id"], j["bras"], j["rang"]) for j in brut}
    levees = {
        (r.id, r.bras, rang)
        for r in lire_resultats(_ESSAI / "resultats.jsonl")
        for rang in range(1, len(r.remarques) + 1)
    }
    assert juges == levees
