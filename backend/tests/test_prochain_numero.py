"""`scripts/prochain_numero.py` rend le plus grand numéro pris + 1 — ticket-659.

Couverture :
- un numéro de ticket présent seulement sur une branche `origin/ticket-*` compte ;
- un numéro d'ADR ajouté seulement sur une branche `origin/ticket-*` compte ;
- le numéro d'une branche sans fiche (nom seul) compte aussi ;
- l'arbre non commité et `origin/develop` comptent ;
- un dépôt sans remote répond avec son seul arbre ;
- la ligne de commande imprime le numéro ;
- ticket-848 : `reserver` ne rend jamais deux fois un numéro, partage la réservation
  entre worktrees d'un projet, sépare deux dépôts, ne crée rien avec `--sans-reserver`
  et met de côté un fichier illisible.
"""
import json
import sys
from pathlib import Path

import pytest

from tessera.services.noyau import reservation
from tessera.services.noyau.numerotation import GitIllisible, numeros_pris, prochain_numero, reserver
from tests.depot_numerotation import creer_depot, ecrire, fiche, git, pousser_une_branche

_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from prochain_numero import main  # noqa: E402


def test_ticket_number_only_on_a_ticket_branch_is_counted(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    assert prochain_numero(clone, "ticket") == 612
    pousser_une_branche(
        tmp_path, "ticket-700-ailleurs",
        {"tickets/todo/ticket-700-ailleurs.md": fiche(700, "ailleurs")},
    )
    git(clone, "fetch", "-q", "origin")

    assert 700 in numeros_pris(clone, "ticket")
    assert prochain_numero(clone, "ticket") == 701


def test_tickets_created_by_a_design_branch_are_all_counted(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    pousser_une_branche(
        tmp_path, "ticket-570-conception",
        {f"tickets/todo/ticket-{n}-suite.md": fiche(n, "suite") for n in (612, 613, 614)},
    )
    git(clone, "fetch", "-q", "origin")

    assert prochain_numero(clone, "ticket") == 615


def test_adr_number_only_on_a_ticket_branch_is_counted(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    pousser_une_branche(
        tmp_path, "ticket-576-autre-adr",
        {"memory/decisions.md": "# Décisions\n\n## ADR-001 — Un\n\n## ADR-061 — Base\n\n## ADR-070 — Ailleurs\n"},
    )
    git(clone, "fetch", "-q", "origin")

    assert prochain_numero(clone, "adr") == 71


def test_branch_name_alone_counts_as_a_taken_ticket_number(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    pousser_une_branche(tmp_path, "ticket-800-sans-fiche", {"code.py": "x = 1\n"})
    git(clone, "fetch", "-q", "origin")

    assert prochain_numero(clone, "ticket") == 801


def test_uncommitted_tree_is_counted(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    ecrire(clone, "tickets/todo/ticket-900-local.md", fiche(900, "local"))

    assert prochain_numero(clone, "ticket") == 901


def test_repository_without_remote_answers_from_its_tree(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    git(clone, "remote", "remove", "origin")

    assert prochain_numero(clone, "ticket") == 612
    with pytest.raises(GitIllisible):
        numeros_pris(clone, "ticket", strict=True)


def test_command_line_prints_the_next_number(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    clone = creer_depot(tmp_path)
    monkeypatch.setenv("IDE_STATE_DIR", str(tmp_path / "etat"))

    assert main(["adr", "--projet", str(clone)]) == 0
    assert capsys.readouterr().out.strip() == "62"


def test_two_calls_return_distinct_numbers(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    etat = tmp_path / "etat"

    assert reserver(clone, "ticket", "develop", etat) == 612
    assert reserver(clone, "ticket", "develop", etat) == 613
    assert reserver(clone, "adr", "develop", etat) == 62
    assert git(clone, "status", "--porcelain") == ""


def test_reserved_number_is_never_reissued_after_tree_catches_up(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    etat = tmp_path / "etat"

    numero = reserver(clone, "ticket", "develop", etat)
    ecrire(clone, f"tickets/todo/ticket-{numero}-ecrit.md", fiche(numero, "ecrit"))

    assert reserver(clone, "ticket", "develop", etat) == numero + 1


def test_reservation_is_shared_by_the_worktrees_of_a_project(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    git(clone, "worktree", "add", "-q", "-b", "run", str(tmp_path / "wt"))
    etat = tmp_path / "etat"

    assert reserver(clone, "ticket", "develop", etat) == 612
    assert reserver(tmp_path / "wt", "ticket", "develop", etat) == 613


def test_two_repositories_do_not_share_their_numbers(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    premier = creer_depot(tmp_path / "a")
    second = creer_depot(tmp_path / "b")
    etat = tmp_path / "etat"

    assert reserver(premier, "ticket", "develop", etat) == 612
    assert reserver(second, "ticket", "develop", etat) == 612


def test_without_reserve_reads_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    clone = creer_depot(tmp_path)
    etat = tmp_path / "etat"
    monkeypatch.setenv("IDE_STATE_DIR", str(etat))

    assert main(["ticket", "--projet", str(clone), "--sans-reserver"]) == 0
    assert main(["ticket", "--projet", str(clone), "--sans-reserver"]) == 0

    assert capsys.readouterr().out.split() == ["612", "612"]
    assert not etat.exists()


def test_corrupt_reservation_file_is_set_aside(tmp_path: Path) -> None:
    clone = creer_depot(tmp_path)
    etat = tmp_path / "etat"
    etat.mkdir()
    (etat / "numeros_reserves.json").write_text("{pas du json", encoding="utf-8")

    assert reserver(clone, "ticket", "develop", etat) == 612

    assert (etat / "numeros_reserves.json.corrompu").read_text(encoding="utf-8") == "{pas du json"
    assert json.loads((etat / "numeros_reserves.json").read_text(encoding="utf-8"))
    assert reserver(clone, "ticket", "develop", etat) == 613


def test_reservation_file_of_the_wrong_shape_is_set_aside(tmp_path: Path) -> None:
    etat = tmp_path / "etat"
    etat.mkdir()
    fichier = etat / "numeros_reserves.json"
    fichier.write_text('{"depot": {"ticket": "douze"}}', encoding="utf-8")

    assert reservation.lire(fichier) == {}
    assert not fichier.exists()
    assert fichier.with_name(fichier.name + ".corrompu").exists()


def test_reservation_round_trip_and_lock(tmp_path: Path) -> None:
    fichier = tmp_path / "numeros_reserves.json"
    assert reservation.lire(fichier) == {}

    with reservation.verrou(tmp_path / "x.lock"):
        reservation.ecrire(fichier, {"d": {"ticket": 5}})

    assert reservation.lire(fichier) == {"d": {"ticket": 5}}
    assert not fichier.with_name(fichier.name + ".tmp").exists()
