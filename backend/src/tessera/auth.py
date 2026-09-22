"""Static bearer-token protection for every route, HTTP and WebSocket alike.

Pure ASGI middleware, deliberately not a `BaseHTTPMiddleware`: that base class
only calls `dispatch` for `http` scopes and lets every other scope through
untouched. The three `@router.websocket` routes were therefore open even with
`STATIC_TOKEN` set (ticket-120).
"""
import hmac
from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from tessera.config import settings

#: Code de fermeture WebSocket dans la plage applicative (4000-4999), calqué
#: sur le 401 HTTP pour que le client comprenne la cause sans texte.
WS_UNAUTHORIZED = 4401

#: Routes servies sans token : la sonde de santé n'expose rien, et le
#: préflight CORS est envoyé par le navigateur lui-même, sans en-tête.
_OPEN_PATHS = frozenset({"/health"})


def _header(scope: Scope, name: bytes) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return str(value.decode("latin-1"))
    return ""


def _presented_token(scope: Scope) -> str:
    """The token the caller presented: a Bearer header, or `?token=` on a WebSocket.

    Browsers cannot attach headers to `new WebSocket(url)`, so the query string
    is the only channel left for them. It is accepted on WebSockets only: an
    HTTP request can always carry a header, and a token in a URL ends up in
    access logs.
    """
    auth = _header(scope, b"authorization")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    if scope["type"] == "websocket":
        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        return str(query.get("token", [""])[0])
    return ""


def _is_authorized(scope: Scope, expected: str) -> bool:
    if scope["path"] in _OPEN_PATHS:
        return True
    if scope["type"] == "http" and scope["method"] == "OPTIONS":
        return True
    # Comparaison en temps constant : `!=` s'arrête au premier octet différent
    # et laisse mesurer combien de caractères du token sont justes.
    return hmac.compare_digest(_presented_token(scope).encode(), expected.encode())


class StaticTokenMiddleware:
    """Requires `STATIC_TOKEN` on every HTTP request and WebSocket handshake.

    The token is read from `settings` on each call, not captured at startup,
    so an empty value keeps the API open and a configured one protects every
    route without the application having to be rebuilt.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        expected = settings.static_token
        if not expected or scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return
        if _is_authorized(scope, expected):
            await self._app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": WS_UNAUTHORIZED, "reason": "Unauthorized"})
            return
        response = JSONResponse({"detail": "Unauthorized"}, status_code=401)
        await response(scope, receive, send)
