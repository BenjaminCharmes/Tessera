"""A test command chained with `&&`, split into steps — ticket-337."""
import pytest

from tessera.services.commande_chainee import CommandeNonGeree, decouper


def test_a_single_command_is_one_step() -> None:
    assert decouper('uv run python ../scripts/verifier.py') == [
        ["uv", "run", "python", "../scripts/verifier.py"]
    ]


def test_and_chains_become_steps_in_order() -> None:
    assert decouper("npm run typecheck && npm run test -- --run && npm run build") == [
        ["npm", "run", "typecheck"],
        ["npm", "run", "test", "--", "--run"],
        ["npm", "run", "build"],
    ]


def test_a_quoted_ampersand_is_an_argument_not_a_separator() -> None:
    assert decouper('node -e "a && b"') == [["node", "-e", "a && b"]]


@pytest.mark.parametrize("cmd", ["a | b", "a || b", "a ; b", "a > out.txt", "a &"])
def test_other_shell_operators_are_refused(cmd: str) -> None:
    # Sans shell, ils seraient passés en arguments au premier programme :
    # le reste de la commande ne tournerait jamais, en silence.
    with pytest.raises(CommandeNonGeree):
        decouper(cmd)


@pytest.mark.parametrize("cmd", ["", "&& a", "a &&", "a && && b"])
def test_an_empty_step_is_refused(cmd: str) -> None:
    with pytest.raises(CommandeNonGeree):
        decouper(cmd)
