"""The frozen corpus of the second-review trial reads and is sized (ticket-842).

SHA existence is not tested here: a shallow clone does not carry the history.
`shas_manquants` is run by hand on a full clone.
"""
from __future__ import annotations

import sys
from pathlib import Path

_RACINE = Path(__file__).resolve().parent.parent.parent
if str(_RACINE / "scripts") not in sys.path:
    sys.path.insert(0, str(_RACINE / "scripts"))

from seconde_revue_corpus import charger_corpus, somme_gel, verifier_taille  # noqa: E402

_CORPUS = _RACINE / "docs" / "essais" / "seconde-revue" / "corpus.json"


def test_real_corpus_loads_and_meets_the_size_thresholds() -> None:
    corpus = charger_corpus(_CORPUS)
    assert verifier_taille(corpus) == []


def test_real_corpus_freeze_sum_matches_its_entries() -> None:
    corpus = charger_corpus(_CORPUS)
    assert corpus.gel_sha256 == somme_gel(corpus.entrees)
