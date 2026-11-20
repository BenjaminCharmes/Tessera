"""History scan before publishing — ticket-230."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path


def _charger() -> object:
    chemin = Path(__file__).resolve().parents[2] / "scripts" / "scan_historique.py"
    loader = importlib.machinery.SourceFileLoader("scan_historique", str(chemin))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


SCAN = _charger()


def test_a_term_matches_across_case_accents_and_separators() -> None:
    motif = SCAN.motif("Zorg Lub")  # type: ignore[attr-defined]
    for texte in ("zorg-lub", "ZORGLUB", "Zôrg_lub", "chez zorg.lub."):
        assert motif.search(SCAN.normaliser(texte)), texte  # type: ignore[attr-defined]


def test_a_term_does_not_match_inside_a_longer_word() -> None:
    motif = SCAN.motif("lub")  # type: ignore[attr-defined]
    assert not motif.search(SCAN.normaliser("zorglubien"))  # type: ignore[attr-defined]


def test_findings_name_locations_never_terms() -> None:
    SCAN.MOTIFS.clear()  # type: ignore[attr-defined]
    SCAN.TROUVES.clear()  # type: ignore[attr-defined]
    SCAN.MOTIFS.append(SCAN.motif("zorglub"))  # type: ignore[attr-defined]
    SCAN.examiner("PR #1 corps", "built for Zorglub")  # type: ignore[attr-defined]
    assert list(SCAN.TROUVES) == ["PR #1 corps"]  # type: ignore[attr-defined]


def test_scan_historique_reads_terms_through_the_resolver() -> None:
    # ticket-798 : plus aucune lecture de `.env`, le backend résout la liste.
    import subprocess

    import pytest

    appels: list[list[str]] = []

    def lancer(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        appels.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="zorglub, bidule", stderr="")

    assert SCAN.termes(lancer=lancer) == ["zorglub", "bidule"]  # type: ignore[attr-defined]
    assert appels[0][-3:] == ["-m", "tessera.coffre_cli", "termes"]
    assert "--project" in appels[0]

    def en_echec(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="")

    with pytest.raises(SystemExit):
        SCAN.termes(lancer=en_echec)  # type: ignore[attr-defined]
