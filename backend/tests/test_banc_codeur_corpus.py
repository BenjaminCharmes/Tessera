"""Tests for scripts/banc_codeur_corpus.py and banc_codeur_proposer.py (ticket-1053).

No model is called and `tessera` is not imported: git runs only on a
temporary repository created by the test.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from banc_codeur_corpus import (  # noqa: E402
    Corpus,
    CorpusInvalide,
    Entree,
    charger,
    chemin_du_ticket,
    sans_frontmatter,
    somme_gel,
    somme_texte,
    texte_ticket,
    textes_divergents,
    verifier,
)
from banc_codeur_proposer import Ecart, ecrire, motif_exclusion, proposer  # noqa: E402

_CORPS = "## Objectif\n\nFaire une chose.\n"
_TICKET_DIR = "projects/ide-core/tickets/todo"


def _entree(n: int, pilote: bool = False) -> Entree:
    return Entree(
        id=f"e{n}", ticket=f"ticket-{n}", sha=f"{n:040x}", base_sha=f"{n + 1000:040x}",
        ticket_chemin=f"tickets/done/ticket-{n}-x.md", ticket_sha256=f"{n:064x}",
        fichiers=(f"backend/f{n}.py",), lignes_ajoutees=50, pilote=pilote,
    )


def _corpus(entrees: tuple[Entree, ...]) -> Corpus:
    return Corpus(entrees=entrees, gel_sha256=somme_gel(entrees))


def test_somme_gel_ignores_order_and_pilots() -> None:
    a, b, p = _entree(1), _entree(2), _entree(3, pilote=True)
    assert somme_gel([a, b]) == somme_gel([b, a, p])
    assert somme_gel([a, b]) != somme_gel([a, replace(b, base_sha="0" * 40)])


def test_verifier_accepts_a_frozen_corpus_of_sixteen() -> None:
    verifier(_corpus(tuple(_entree(n) for n in range(16))))


def test_verifier_refuses_a_wrong_sum() -> None:
    entrees = tuple(_entree(n) for n in range(16))
    with pytest.raises(CorpusInvalide, match="gel_sha256"):
        verifier(Corpus(entrees=entrees, gel_sha256="0" * 64))


def test_verifier_refuses_fewer_than_sixteen_outside_pilot() -> None:
    entrees = tuple(_entree(n) for n in range(15)) + tuple(_entree(n, True) for n in range(20, 24))
    with pytest.raises(CorpusInvalide, match="hors pilote"):
        verifier(_corpus(entrees))


def test_charger_roundtrip_and_rejections(tmp_path: Path) -> None:
    entrees = [_entree(1), _entree(2, pilote=True)]
    chemin = tmp_path / "corpus.json"
    ecrire(chemin, entrees, [Ecart("ticket-9", "a" * 40, "aucun fichier de test")])
    corpus = charger(chemin)
    assert corpus.entrees == tuple(entrees)
    assert corpus.gel_sha256 == somme_gel(entrees)
    chemin.write_text("pas du json", encoding="utf-8")
    with pytest.raises(CorpusInvalide):
        charger(chemin)
    brut = {"gel_sha256": "x", "entrees": [{"id": "a"}]}
    chemin.write_text(json.dumps(brut), encoding="utf-8")
    with pytest.raises(CorpusInvalide, match="champ absent"):
        charger(chemin)


def test_charger_refuses_duplicate_ids(tmp_path: Path) -> None:
    chemin = tmp_path / "corpus.json"
    ecrire(chemin, [_entree(1), _entree(1)], [])
    with pytest.raises(CorpusInvalide, match="double"):
        charger(chemin)


def test_sans_frontmatter_and_somme_texte() -> None:
    avec = "---\nid: t\n---\n" + _CORPS
    assert sans_frontmatter(avec) == _CORPS
    assert sans_frontmatter(avec.replace("\n", "\r\n")) == _CORPS
    assert sans_frontmatter(_CORPS) == _CORPS
    assert len(somme_texte(_CORPS)) == 64


@pytest.mark.parametrize(
    ("lignes", "preuve", "attendu"),
    [
        ({"backend/src/a.py": 40, "backend/tests/test_a.py": 20}, False, None),
        ({"backend/src/a.py": 60, "backend/tests/test_a.py": 20}, True, "preuve_reelle"),
        ({"backend/src/tessera/services/worktrees/a.py": 60, "backend/tests/test_a.py": 9}, False, "zone exclue"),
        ({"backend/src/compte_agent.py": 60, "backend/tests/test_a.py": 9}, False, "zone exclue"),
        ({"projects/ide-core/agents.json": 60, "backend/tests/test_a.py": 9}, False, "zone exclue"),
        ({".github/workflows/ci.yml": 60, "backend/tests/test_a.py": 9}, False, "zone exclue"),
        ({"scripts/hooks/pre-push": 60, "backend/tests/test_a.py": 9}, False, "zone exclue"),
        ({"backend/src/coffre.py": 60, "backend/tests/test_a.py": 9}, False, "zone exclue"),
        ({"frontend/src/a.tsx": 60, "backend/tests/test_a.py": 9}, False, "frontend"),
        ({"docs/a.md": 60, "backend/tests/test_a.py": 9}, False, "hors périmètre"),
        ({"backend/src/a.py": 60}, False, "aucun fichier de test"),
        ({"backend/src/a.py": 10, "backend/tests/test_a.py": 19}, False, "hors de 30 à 600"),
        ({"backend/src/a.py": 590, "backend/tests/test_a.py": 11}, False, "hors de 30 à 600"),
        ({"backend/src/a.py": 400, "backend/tests/test_a.py": 200}, False, None),
    ],
)
def test_motif_exclusion(lignes: dict[str, int], preuve: bool, attendu: str | None) -> None:
    motif = motif_exclusion(lignes, preuve)
    if attendu is None:
        assert motif is None
    else:
        assert motif is not None and attendu in motif


# --- Dépôt git temporaire ---------------------------------------------------

def _run(depot: Path, *args: str) -> str:
    sortie = subprocess.run(
        ["git", "-C", str(depot), "-c", "user.name=T", "-c", "user.email=t@example.com",
         "-c", "commit.gpgsign=false", *args],
        capture_output=True, text=True, check=True, encoding="utf-8",
    )
    return sortie.stdout.strip()


def _ecrire(depot: Path, chemin: str, contenu: str) -> None:
    cible = depot / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(contenu, encoding="utf-8", newline="\n")


def _commit(depot: Path, message: str) -> str:
    _run(depot, "add", "-A")
    _run(depot, "commit", "-m", message)
    return _run(depot, "rev-parse", "HEAD")


def _ticket(numero: int, corps: str, extra: str = "") -> str:
    return f"---\nid: ticket-{numero}\n{extra}status: todo\n---\n{corps}"


def _depot_avec_historique(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    depot = tmp_path / "depot"
    depot.mkdir()
    _run(depot, "init", "-b", "develop")
    t5 = f"{_TICKET_DIR}/ticket-5-chose.md"
    _ecrire(depot, t5, _ticket(5, _CORPS))
    _ecrire(depot, f"{_TICKET_DIR}/ticket-6-preuve.md", _ticket(6, _CORPS, "preuve_reelle: true\n"))
    base5 = _commit(depot, "docs: tickets 5 and 6")
    # Squash du ticket 5 : le code, ses tests, et une retouche du ticket lui-même.
    _ecrire(depot, "backend/src/a.py", "x = 1\n" * 40)
    _ecrire(depot, "backend/tests/test_a.py", "y = 1\n" * 10)
    _ecrire(depot, t5, _ticket(5, _CORPS + "\nSection ajoutée au squash.\n"))
    sha5 = _commit(depot, "feat: ticket-5 — Do a thing (#1)")
    base6 = sha5
    _ecrire(depot, "backend/src/b.py", "x = 1\n" * 40)
    _ecrire(depot, "backend/tests/test_b.py", "y = 1\n" * 10)
    sha6 = _commit(depot, "fix: ticket-6 — Real proof (#2)")
    # Squash du ticket 7 : sa fiche naît dans le squash même.
    _ecrire(depot, "backend/src/c.py", "x = 1\n" * 40)
    _ecrire(depot, "backend/tests/test_c.py", "y = 1\n" * 10)
    _ecrire(depot, "projects/ide-core/tickets/done/ticket-7-neuf.md", _ticket(7, _CORPS))
    sha7 = _commit(depot, "chore: ticket-7 — Born in squash (#3)")
    return depot, {"base5": base5, "sha5": sha5, "base6": base6, "sha6": sha6, "sha7": sha7}


def test_text_read_at_base_is_the_one_before_the_next_commit(tmp_path: Path) -> None:
    depot, shas = _depot_avec_historique(tmp_path)
    chemin = chemin_du_ticket(depot, shas["base5"], "5")
    assert chemin == f"{_TICKET_DIR}/ticket-5-chose.md"
    assert texte_ticket(depot, shas["base5"], chemin) == _CORPS
    assert "Section ajoutée" in texte_ticket(depot, shas["sha5"], chemin)


def test_chemin_du_ticket_does_not_confuse_prefixes(tmp_path: Path) -> None:
    depot, shas = _depot_avec_historique(tmp_path)
    assert chemin_du_ticket(depot, shas["base5"], "50") is None
    assert chemin_du_ticket(depot, shas["base5"], "7") is None


def test_texte_ticket_raises_when_absent(tmp_path: Path) -> None:
    depot, shas = _depot_avec_historique(tmp_path)
    with pytest.raises(CorpusInvalide):
        texte_ticket(depot, shas["base5"], "tickets/nope.md")


def test_proposer_keeps_ticket_5_and_explains_the_others(tmp_path: Path) -> None:
    depot, shas = _depot_avec_historique(tmp_path)
    entrees, ecartes = proposer(depot, "develop", taille=5, pilote=0)
    assert [e.ticket for e in entrees] == ["ticket-5"]
    e = entrees[0]
    assert e.sha == shas["sha5"] and e.base_sha == shas["base5"]
    assert e.ticket_sha256 == somme_texte(_CORPS)
    assert e.lignes_ajoutees == 52 and e.pilote is False
    motifs = {x.ticket: x.motif for x in ecartes}
    assert motifs["ticket-7"] == "ticket absent à la base"
    assert motifs["ticket-6"] == "preuve_reelle"


def test_proposer_flags_the_oldest_as_pilot_and_stays_frozen(tmp_path: Path) -> None:
    depot, shas = _depot_avec_historique(tmp_path)
    _ecrire(depot, "backend/src/d.py", "x = 1\n" * 40)
    _ecrire(depot, "backend/tests/test_d.py", "y = 1\n" * 10)
    _ecrire(depot, f"{_TICKET_DIR}/ticket-8-autre.md", _ticket(8, _CORPS))
    _commit(depot, "docs: ticket 8")
    _ecrire(depot, "backend/src/e.py", "x = 1\n" * 40)
    _ecrire(depot, "backend/tests/test_e.py", "y = 1\n" * 10)
    _commit(depot, "feat: ticket-8 — Another (#4)")
    entrees, _ = proposer(depot, "develop", taille=1, pilote=1)
    assert [(e.ticket, e.pilote) for e in entrees] == [("ticket-8", False), ("ticket-5", True)]
    assert somme_gel(entrees) == somme_gel(entrees[:1])
    chemin = tmp_path / "out" / "corpus.json"
    ecrire(chemin, entrees, [])
    assert textes_divergents(charger(chemin), depot) == []
    faux = replace(entrees[1], ticket_sha256="0" * 64)
    assert textes_divergents(_corpus((faux,)), depot) == [faux.id]
