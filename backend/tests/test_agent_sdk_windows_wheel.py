"""The locked claude-agent-sdk must ship a Windows wheel with its bundled CLI."""

import tomllib
from pathlib import Path

_LOCK = Path(__file__).resolve().parents[1] / "uv.lock"


def _paquet_sdk() -> dict:
    lock = tomllib.loads(_LOCK.read_text(encoding="utf-8"))
    return next(p for p in lock["package"] if p["name"] == "claude-agent-sdk")


def test_locked_agent_sdk_has_a_windows_wheel() -> None:
    # Sans wheel win_amd64, uv construit le SDK depuis le sdist, sans le
    # claude.exe embarqué : le SDK se rabat sur le `claude.CMD` du PATH, qu'il
    # refuse d'exécuter, et chaque run échoue sous Windows (0.2.160 à 0.2.163).
    paquet = _paquet_sdk()
    roues = [w["url"] for w in paquet.get("wheels", [])]
    assert any("win_amd64" in url for url in roues), (
        f"claude-agent-sdk {paquet['version']} n'a pas de wheel Windows"
    )
