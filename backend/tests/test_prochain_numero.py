"""`scripts/prochain_numero.py` rend le plus grand numéro pris + 1 — ticket-659.

Couverture :
- un numéro de ticket présent seulement sur une branche `origin/ticket-*` compte ;
- un numéro d'ADR ajouté seulement sur une branche `origin/ticket-*` compte ;
- le numéro d'une branche sans fiche (nom seul) compte aussi ;
- l'arbre non commité et `origin/develop` comptent ;
- un dépôt sans remote répond avec son seul arbre ;
- la ligne de commande imprime le numéro.
"""
import sys
from pathlib import Path

import pytest

from tests.depot_numerotation import creer_depot, ecrire, fiche, git, pousser_une_branche
from tessera.services.numerotation import GitIllisible, numeros_pris, prochain_numero

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
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clone = creer_depot(tmp_path)

    assert main(["adr", "--projet", str(clone)]) == 0
    assert capsys.readouterr().out.strip() == "62"
