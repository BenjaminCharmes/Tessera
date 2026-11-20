"""Every route of the app refuses a request without the session token — ticket-878.

Le test parcourt `app.routes`, sous-routeurs inclus : une route ajoutée plus tard
est couverte d'office, sans que personne ait à y penser. Seul `/health` reste
ouvert (sonde de santé). Les routes de documentation (`/docs`, `/openapi.json`)
sont des routes de l'app comme les autres : elles exigent le jeton aussi.
"""
import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from starlette.routing import BaseRoute
from starlette.websockets import WebSocketDisconnect

from tessera.main import app

pytestmark = pytest.mark.sans_jeton_par_defaut

_OUVERTES = frozenset({"/health"})
# Une origine déclarée : l'écriture des réglages en exige une (ticket-808), et le
# refus doit venir du jeton, pas d'un contrôle d'`Origin` placé avant lui.
_ORIGINE = {"Origin": "http://localhost:5173"}
_PARAMETRE = re.compile(r"\{[^}]*\}")


def _parcourir(routes: list[BaseRoute], prefixe: str = "") -> Iterator[tuple[str, str, str]]:
    """Yield `(kind, path, method)` for each route, nested routers and mounts included.

    `kind` vaut `http` ou `websocket`. Une route d'un type inconnu lève : le test
    échoue plutôt que d'ignorer en silence ce qu'il ne sait pas lire.
    """
    for route in routes:
        contexte = getattr(route, "include_context", None)
        if contexte is not None:
            yield from _parcourir(route.original_router.routes, prefixe + contexte.prefix)  # type: ignore[attr-defined]
        elif hasattr(route, "routes"):
            yield from _parcourir(route.routes, prefixe + route.path)  # type: ignore[attr-defined]
        elif "WebSocket" in type(route).__name__:
            yield "websocket", prefixe + route.path, "GET"  # type: ignore[attr-defined]
        else:
            for methode in sorted(getattr(route, "methods", None) or {"GET"}):
                yield "http", prefixe + route.path, methode  # type: ignore[attr-defined]


def _routes_a_verifier() -> list[tuple[str, str, str]]:
    toutes = list(_parcourir(app.routes))
    return [r for r in toutes if _PARAMETRE.sub("x", r[1]) not in _OUVERTES]


_ROUTES = _routes_a_verifier()


def test_the_walk_sees_the_nested_routers() -> None:
    chemins = {chemin for _, chemin, _ in _ROUTES}

    assert "/api/v1/projects" in chemins
    assert "/api/v1/orchestrator/observe" in chemins
    assert "/docs" in chemins
    assert "/health" not in chemins
    assert len(_ROUTES) > 50


@pytest.mark.parametrize(("genre", "chemin", "methode"), _ROUTES)
def test_every_route_refuses_a_request_without_a_token(genre: str, chemin: str, methode: str) -> None:
    client = TestClient(app)
    url = _PARAMETRE.sub("x", chemin)

    if genre == "websocket":
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(url, headers=_ORIGINE):
                pass
        assert exc.value.code == 4401
    else:
        assert client.request(methode, url, headers=_ORIGINE).status_code == 401
