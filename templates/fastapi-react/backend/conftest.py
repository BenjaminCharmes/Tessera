"""Root conftest — Windows AppLocker compatibility for jiter (ticket-016).

On Windows, jiter.pyd (Rust extension required by pydantic-core) can be
blocked by AppLocker/WDAC policies before it reaches the disk loader.
pydantic-core imports jiter via Python's import system (PyImport_ImportModule),
which checks sys.modules first. Pre-loading a minimal stub here prevents the
DLL from ever being requested, so pydantic-core initialises normally.

This file has no effect in CI (Ubuntu) or on machines where jiter loads fine:
the try/import returns immediately when the real jiter is available.

"""
from __future__ import annotations

import json
import sys
import types


# Marqueur ajouté au stub pour que pytest_configure puisse le détecter.
_STUB_MARKER: str = "_is_stub"


def _maybe_stub_jiter() -> None:
    """Install a stdlib-backed jiter stub if the real extension is unavailable."""
    if "jiter" in sys.modules:
        return  # real jiter (or a previous stub) already present

    try:
        import jiter as _real  # noqa: F401
        return  # real jiter loaded — nothing to do
    except ImportError:
        pass  # DLL blocked or missing — install stub below

    stub = types.ModuleType("jiter")

    class _PydanticFasterJSONParser:
        """Minimal JSON parser backed by stdlib json.

        Matches the interface pydantic-core expects from jiter:
        constructor(bytes, allow_inf_nan, allow_partial) + get_value().
        """

        def __init__(
            self,
            data: bytes,
            allow_inf_nan: bool = True,
            allow_partial: bool | str = False,
        ) -> None:
            self._data = data
            self._allow_inf_nan = allow_inf_nan

        def get_value(self) -> object:
            return json.loads(self._data)

    stub.PydanticFasterJSONParser = _PydanticFasterJSONParser  # type: ignore[attr-defined]
    # cache_string is used for string interning; identity is a safe no-op stub.
    stub.cache_string = str  # type: ignore[attr-defined]
    stub.cache_usage = lambda: 0  # type: ignore[attr-defined]
    # Marqueur consultable par pytest_configure et les tests.
    setattr(stub, _STUB_MARKER, True)

    sys.modules["jiter"] = stub


_maybe_stub_jiter()


def pytest_configure(config: object) -> None:  # type: ignore[override]
    """Avertit dans l'en-tête pytest si le stub jiter est actif.

    Le message apparaît une seule fois au démarrage de la session et signale
    que les tests tournent avec le mécanisme de secours, non avec le
    DLL Rust d'origine. Aucun avertissement n'est émis quand le vrai jiter
    est chargé.
    """
    import warnings  # noqa: PLC0415

    import jiter as _j  # noqa: PLC0415

    if getattr(_j, _STUB_MARKER, False):
        warnings.warn(
            "jiter DLL stub actif — json stdlib utilisé à la place du DLL Rust.\n"
            "Les tests passent ; le serveur uvicorn nécessite l'une des solutions\n"
            "décrites dans README.md § Développement local sur Windows.",
            UserWarning,
            stacklevel=2,
        )
