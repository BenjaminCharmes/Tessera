"""A service runs apart from the backend's console — ticket-664."""
from tessera.services.lancement import options_de_lancement


def test_on_windows_a_service_gets_its_own_hidden_console_and_process_group() -> None:
    # Un `uvicorn --reload` qui recharge envoie CTRL_C_EVENT à toute sa console :
    # partagée, elle arrêtait le backend de Tessera (28/10, Curio).
    drapeaux = options_de_lancement("nt")["creationflags"]

    assert drapeaux & 0x08000000  # CREATE_NO_WINDOW : une console à lui
    assert drapeaux & 0x00000200  # CREATE_NEW_PROCESS_GROUP


def test_elsewhere_a_service_gets_its_own_session() -> None:
    assert options_de_lancement("posix") == {"start_new_session": True}
