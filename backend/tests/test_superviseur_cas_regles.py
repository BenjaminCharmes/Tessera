"""A settled target closes its « À toi » case on read (ticket-1059)."""
from datetime import date
from pathlib import Path

import pytest

from tessera.services.supervision.superviseur_cas_regles import cas_a_toi_a_relire, cas_encore_ouverts
from tessera.services.supervision.superviseur_decision_blocs import Genre, cible_de
from tessera.services.supervision.superviseur_journal import LigneJournal

BLOC = "- **Une règle.** (ADR-1)"


def _cas(cible: str) -> LigneJournal:
    return LigneJournal(date(2026, 11, 1), "a_toi", cible, "", "r")


@pytest.mark.parametrize("dossier,reste", [("done", False), ("cancelled", False), ("todo", True)])
def test_ticket_case_follows_its_folder(tmp_path: Path, dossier: str, reste: bool) -> None:
    memoire = tmp_path / "memory"
    memoire.mkdir()
    (memoire / "supervision.md").write_text("- 2026-11-01 | a_toi | ticket-5 | | r\n", encoding="utf-8")
    (tmp_path / "tickets" / dossier).mkdir(parents=True)
    (tmp_path / "tickets" / dossier / "ticket-5-titre.md").write_text("x", encoding="utf-8")

    assert bool(cas_a_toi_a_relire(memoire)) is reste


@pytest.mark.parametrize("genre,fichier", [("regle", "contraintes"), ("lecon", "lecons")])
def test_block_case_closes_when_block_leaves_proposees(genre: Genre, fichier: str) -> None:
    cible = cible_de(genre, BLOC)
    textes = {"contraintes": "", "lecons": ""}
    textes[fichier] = f"## Proposées\n\n{BLOC}\n"
    assert cas_encore_ouverts([_cas(cible)], frozenset(), textes["contraintes"], textes["lecons"])
    textes[fichier] = f"## Proposées\n\n## En vigueur\n\n{BLOC}\n"
    assert not cas_encore_ouverts([_cas(cible)], frozenset(), textes["contraintes"], textes["lecons"])


def test_other_target_stays_open() -> None:
    assert len(cas_encore_ouverts([_cas("pr-12"), _cas("autre")], frozenset({"ticket-1"}), "", "")) == 2
