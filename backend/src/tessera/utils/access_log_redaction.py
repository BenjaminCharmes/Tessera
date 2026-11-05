"""Keeps the WebSocket `?token=` out of uvicorn's request logs (ticket-758).

A browser cannot attach a header to `new WebSocket(url)`, so the static token
travels in the query string. uvicorn writes the full path, query included, in
its access log and in its "WebSocket ... [accepted]" line: the token would end
up in a log file. The filter blanks the value before any handler sees it.
"""
import logging
import re

#: Loggers uvicorn writes the request path to: HTTP access lines, and the
#: WebSocket handshake lines on the error logger.
_UVICORN_LOGGERS = ("uvicorn.access", "uvicorn.error")

_TOKEN_PARAM = re.compile(r"([?&]token=)[^&\s\"]*", re.IGNORECASE)
_MASK = "***"


def redact_token(text: str) -> str:
    """Return `text` with the value of any `token=` query parameter blanked."""
    return _TOKEN_PARAM.sub(lambda m: m.group(1) + _MASK, text)


class TokenRedactionFilter(logging.Filter):
    """Rewrites the message and string arguments of a record; never drops it."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_token(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact_token(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


def install_token_redaction() -> None:
    """Attach the filter to the uvicorn loggers, once."""
    for name in _UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        if not any(isinstance(f, TokenRedactionFilter) for f in logger.filters):
            logger.addFilter(TokenRedactionFilter())
