"""Consecutive blocks with the same cause — ticket-838 (ADR-078)."""
from pathlib import Path

from tessera.services.anomalies.lecture_historique import derniers_runs_finis
from tessera.services.anomalies.modeles import RunFini
from tessera.services.anomalies.regles_historiques import blocages_identiques, signature_d_arret
from tests.anomalies_base import base_neuve, ligne_de_run

# Un vrai `arret` de livraison coupée par le réseau (relevé dans `pipeline_runs`),
# et sa variante : même cause, autre dépôt, autre délai, autre ticket.
RESEAU = (
    "La base distante « main » est illisible (fatal: unable to access "
    "'https://github.com/depot-a/projet-a.git/': Failed to connect to github.com "
    "port 443 after 21094 ms: Could not connect to server) : ce ticket dépend d'un autre,"
)
RESEAU_BIS = (
    "La base distante « develop » est illisible (fatal: unable to access "
    "'https://github.com/depot-b/projet-b.git/': Failed to connect to github.com "
    "port 443 after 21177 ms: Could not connect to server) : ce ticket dépend d'un autre,"
)


def _run(id_: str, statut: str = "blocked", arret: str | None = RESEAU) -> RunFini:
    return RunFini(id=id_, ticket_id="ticket-001", final_status=statut, arret=arret)


def test_signature_d_arret_ignores_numbers_hashes_paths_and_quoted_strings() -> None:
    assert signature_d_arret(RESEAU) == signature_d_arret(RESEAU_BIS)
    diverge_a = "La branche locale « main » (066c72e) a divergé de la base distante (a635570)."
    diverge_b = "La branche locale « develop » (cc7b272) a divergé de la base distante (5f3235d)."
    assert signature_d_arret(diverge_a) == signature_d_arret(diverge_b)
    chemin_a = "Écriture refusée hors du projet : C:\\Users\\x\\depot\\f.py (tour 2)"
    chemin_b = "Écriture refusée hors du projet : /home/u/depot/g.py (tour 3)"
    assert signature_d_arret(chemin_a) == signature_d_arret(chemin_b)


def test_signature_d_arret_keeps_different_words_apart() -> None:
    assert signature_d_arret(RESEAU) != signature_d_arret(
        "Le rebase a produit un conflit sur « main »."
    )


def test_signature_d_arret_keeps_apostrophes_of_ordinary_words() -> None:
    sig = signature_d_arret("Ce ticket dépend d'un autre ticket, et l'autre est bloqué.")
    assert sig is not None and "d'un autre" in sig and "l'autre est bloqué" in sig


def test_signature_d_arret_empty_or_blank_is_none() -> None:
    assert signature_d_arret(None) is None
    assert signature_d_arret("") is None
    assert signature_d_arret("  \n  ") is None


def test_signature_d_arret_uses_the_first_line_only() -> None:
    assert signature_d_arret("cause\ndétail 1") == signature_d_arret("cause\nautre détail")


def test_signature_d_arret_cuts_at_120_chars() -> None:
    assert signature_d_arret("a" * 120 + "x") == signature_d_arret("a" * 120 + "y")
    assert signature_d_arret("a" * 119 + "x") != signature_d_arret("a" * 119 + "y")


def test_blocages_identiques_two_blocked_with_the_same_cause_reports() -> None:
    a = blocages_identiques([_run("r2", arret=RESEAU_BIS), _run("r1")])
    assert a is not None
    assert (a.regle, a.cle, a.ticket_id, a.mesure, a.unite) == (
        "blocages_identiques", "blocages:r2", "ticket-001", 2.0, "runs",
    )


def test_blocages_identiques_one_run_only_is_none() -> None:
    assert blocages_identiques([_run("r1")]) is None
    assert blocages_identiques([]) is None


def test_blocages_identiques_a_different_cause_is_none() -> None:
    assert blocages_identiques([_run("r2", arret="Le rebase a produit un conflit."), _run("r1")]) is None


def test_blocages_identiques_an_empty_cause_never_counts() -> None:
    assert blocages_identiques([_run("r2", arret=None), _run("r1", arret=None)]) is None


def test_blocages_identiques_an_approved_run_in_between_is_none() -> None:
    assert blocages_identiques([_run("r2"), _run("r1", statut="approved")]) is None
    assert blocages_identiques([_run("r2", statut="approved"), _run("r1")]) is None


def test_blocages_identiques_only_the_two_latest_runs_count() -> None:
    plus_ancien = _run("r0", arret="Le rebase a produit un conflit.")
    assert blocages_identiques([_run("r2"), _run("r1"), plus_ancien]) is not None


async def test_derniers_runs_finis_excludes_envelopes_and_the_open_row(tmp_path: Path) -> None:
    db = await base_neuve(tmp_path / "t.db")
    fin = "2026-11-01T12:00:00+00:00"
    await ligne_de_run(db, "vieux", started_at="2026-11-01T08:00:00+00:00", finished_at=fin,
                       final_status="blocked", arret="a")
    await ligne_de_run(db, "r1", started_at="2026-11-01T09:00:00+00:00", finished_at=fin,
                       final_status="blocked", arret="b")
    await ligne_de_run(db, "r2", started_at="2026-11-01T10:00:00+00:00", finished_at=fin,
                       final_status="approved")
    await ligne_de_run(db, "env", mode="queue", ticket_id="queue", finished_at=fin,
                       final_status="blocked", arret="x", started_at="2026-11-01T11:00:00+00:00")
    await ligne_de_run(db, "ouvert", started_at="2026-11-01T11:30:00+00:00")
    await ligne_de_run(db, "autre", ticket_id="ticket-002", finished_at=fin, final_status="blocked")
    runs = await derniers_runs_finis(db, "p", "ticket-001")
    assert [(r.id, r.final_status, r.arret) for r in runs] == [
        ("r2", "approved", None), ("r1", "blocked", "b"),
    ]
    assert len(await derniers_runs_finis(db, "p", "ticket-001", n=3)) == 3
