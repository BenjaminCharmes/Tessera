"""Reconnaître un service déclaré à sa ligne de commande — ticket-438."""
import pytest

from tessera.services.signature_commande import commande_porte, signature
from tessera.services.sonde_systeme import InfoProcessus


def _proc(commande: str) -> InfoProcessus:
    return InfoProcessus(ppid=1, memoire_mo=1.0, demarre_a=None, commande=commande)


def test_module_after_dash_m_is_the_signature() -> None:
    assert signature("python -m app.worker") == "app.worker"


def test_launcher_module_keeps_its_positional_target() -> None:
    assert signature("python -m uvicorn app.main:app --port 8000") == "uvicorn app.main:app"


def test_script_is_the_signature_without_dash_m() -> None:
    assert signature('"C:\\x\\python.exe" app/worker.py --debug') == "app/worker.py"


@pytest.mark.parametrize("commande", ["npm run dev", "node_modules/.bin/vite", ""])
def test_command_without_a_reliable_signature_gives_none(commande: str) -> None:
    assert signature(commande) is None


def test_process_carrying_the_module_matches() -> None:
    assert commande_porte("app.worker", _proc("C:\\p\\.venv\\python.exe -m app.worker"))


def test_module_prefix_of_another_module_does_not_match() -> None:
    assert not commande_porte("app.worker", _proc("python -m app.worker_extra"))
    assert not commande_porte("app.worker", _proc("python -m myapp.worker"))


def test_relative_script_matches_an_absolute_path() -> None:
    assert commande_porte("app/worker.py", _proc("python C:\\p\\app\\worker.py"))
