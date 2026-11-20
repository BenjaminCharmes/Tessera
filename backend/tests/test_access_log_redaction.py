"""The WebSocket token never reaches uvicorn's logs (ticket-758)."""
import io
import logging
from collections.abc import Iterator

import pytest

import tessera.main  # noqa: F401  # installe le filtre au chargement
from tessera.utils.access_log_redaction import redact_token


@pytest.fixture
def uvicorn_output() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("uvicorn.access")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield stream
    logger.removeHandler(handler)


def test_access_log_does_not_show_the_ws_token(uvicorn_output: io.StringIO) -> None:
    # Les arguments sont ceux que uvicorn passe à sa ligne d'accès.
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d',
        "127.0.0.1:5000", "GET", "/api/v1/agents/stream?token=abc&x=1", "1.1", 200,
    )

    line = uvicorn_output.getvalue()
    assert "abc" not in line
    assert "/api/v1/agents/stream?token=***&x=1" in line


def test_websocket_handshake_line_does_not_show_the_token() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("uvicorn.error")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        logger.info('%s - "WebSocket %s" [accepted]', "127.0.0.1:1", "/ws?token=abc")
    finally:
        logger.removeHandler(handler)

    assert "abc" not in stream.getvalue()


def test_redact_token_leaves_other_parameters_alone() -> None:
    assert redact_token("/p?a=1&token=abc&b=2") == "/p?a=1&token=***&b=2"
    assert redact_token("/p?a=1") == "/p?a=1"
