"""Session bearer-token protection for every route, HTTP and WebSocket alike.

The token is `STATIC_TOKEN` when set, else one drawn at startup (ticket-878):
an empty `STATIC_TOKEN` no longer opens the API.

Pure ASGI middleware, deliberately not a `BaseHTTPMiddleware`: that base class
only calls `dispatch` for `http` scopes and lets every other scope through
untouched. The three `@router.websocket` routes were therefore open even with
`STATIC_TOKEN` set (ticket-120).
"""
import hmac
from urllib.parse import parse_qs, urlsplit

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from tessera.config import settings
from tessera.services.noyau import jeton_de_session

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


def _is_authorized(scope: Scope, expected: str | None) -> bool:
    if scope["path"] in _OPEN_PATHS:
        return True
    if scope["type"] == "http" and scope["method"] == "OPTIONS":
        return True
    if expected is None:
        return False
    # Comparaison en temps constant : `!=` s'arrête au premier octet différent
    # et laisse mesurer combien de caractères du token sont justes.
    return hmac.compare_digest(_presented_token(scope).encode(), expected.encode())


#: Code de fermeture WebSocket d'un `Host` ou d'un `Origin` étranger, calqué sur
#: le 403 HTTP (ticket-704).
WS_FORBIDDEN = 4403

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})
_LOOPBACK_ORIGIN_NAMES = frozenset({"127.0.0.1", "localhost", "::1"})
#: Origines de l'app Tauri selon la plateforme : aucune n'est loopback.
_TAURI_ORIGINS = frozenset(
    {"tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"}
)


def _host_without_port(host: str) -> str:
    """Lowercase host name of a `Host` header, port removed, IPv6 brackets kept."""
    host = host.strip().lower()
    if host.startswith("["):
        return host[: host.find("]") + 1] if "]" in host else host
    return host.split(":", 1)[0]


def _allowed_host_names() -> frozenset[str]:
    declared = (_host_without_port(h) for h in settings.allowed_hosts.split(","))
    return _LOOPBACK_HOSTS | {name for name in declared if name}


def _is_allowed_origin(origin: str) -> bool:
    origin = origin.strip().lower()
    if origin in _TAURI_ORIGINS:
        return True
    try:
        parts = urlsplit(origin)
        _ = parts.port  # lève ValueError sur un port illisible
    except ValueError:
        return False
    bare = not (parts.path or parts.query or parts.fragment or parts.username)
    return parts.scheme == "http" and bare and parts.hostname in _LOOPBACK_ORIGIN_NAMES


#: Ports du Vite de dev et de ses variantes (ticket-754).
_DEFAULT_ORIGIN_PORTS = range(5173, 5177)


def _declared_origins() -> frozenset[str]:
    """Origins a WebSocket may come from: the defaults plus `ALLOWED_ORIGINS`."""
    defaults = {
        f"http://{name}:{port}"
        for name in ("localhost", "127.0.0.1")
        for port in _DEFAULT_ORIGIN_PORTS
    }
    added = {o.strip().lower().rstrip("/") for o in settings.allowed_origins.split(",")}
    return frozenset(defaults | _TAURI_ORIGINS | {o for o in added if o})


def _is_declared_origin(origin: str) -> bool:
    return origin.strip().lower() in _declared_origins()


def is_declared_origin(origin: str) -> bool:
    """Whether an `Origin` header value is one the interface declares (ADR-075).

    An empty value is never declared: a script that omits the header is refused.
    """
    return _is_declared_origin(origin)


#: Préfixe des réglages : une écriture y exige un `Origin` déclaré (ticket-808).
_REGLAGES_PREFIX = "/api/v1/reglages"


def _is_settings_write(scope: Scope) -> bool:
    """A PUT or DELETE on the settings route (ADR-075)."""
    if scope["type"] != "http" or str(scope["method"]) not in ("PUT", "DELETE"):
        return False
    path = str(scope["path"]).lower().rstrip("/")
    return path == _REGLAGES_PREFIX or path.startswith(_REGLAGES_PREFIX + "/")


def _is_trusted_origin_and_host(scope: Scope) -> bool:
    """False for a `Host` outside the allowed names or a foreign `Origin`.

    Un `Origin` absent passe : les outils, curl et les tests n'en envoient pas,
    et un navigateur en joint toujours un aux requêtes qu'une page tierce émet
    vers l'API. Une WebSocket n'est admise que depuis une origine déclarée : le
    loopback sert aussi les apps que les agents écrivent, sur des ports quelconques
    (ticket-754). En HTTP, le préflight CORS tient déjà ces pages à l'écart.
    """
    if scope["path"] in _OPEN_PATHS:
        return True
    if _host_without_port(_header(scope, b"host")) not in _allowed_host_names():
        return False
    origin = _header(scope, b"origin")
    if _is_settings_write(scope):
        # Un navigateur en envoie toujours un sur un PUT, curl non : ici l'absence
        # refuse, et seule une origine déclarée passe, pas tout port loopback.
        return bool(origin) and _is_declared_origin(origin)
    if not origin:
        return True
    if scope["type"] == "websocket":
        return _is_declared_origin(origin)
    return _is_allowed_origin(origin)


class HostOriginMiddleware:
    """Refuses a foreign `Host` (DNS rebinding) and a foreign `Origin` (ticket-704).

    CORS only stops a third-party page from *reading* a response, and does not
    apply to WebSockets. A page the user visits must not reach the API by
    rebinding a name to 127.0.0.1 or by opening a WebSocket, token or not. Pure ASGI, like `StaticTokenMiddleware`,
    for the same reason: `BaseHTTPMiddleware` never sees WebSocket scopes.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket") or _is_trusted_origin_and_host(scope):
            await self._app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": WS_FORBIDDEN, "reason": "Forbidden"})
            return
        response = JSONResponse({"detail": "Forbidden"}, status_code=403)
        await response(scope, receive, send)


class StaticTokenMiddleware:
    """Requires the session token on every HTTP request and WebSocket handshake.

    The token is read from `jeton_de_session.courant()` on each call, not
    captured at startup. No token at all (neither `STATIC_TOKEN` nor a drawn
    one) refuses every route but `/health`: there is no open mode (ticket-878).
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return
        expected = jeton_de_session.courant()
        if _is_authorized(scope, expected):
            await self._app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": WS_UNAUTHORIZED, "reason": "Unauthorized"})
            return
        response = JSONResponse({"detail": "Unauthorized"}, status_code=401)
        await response(scope, receive, send)
