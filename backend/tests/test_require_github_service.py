"""The shared GitHub guard lives in routers/dependencies — ticket-701."""
import pytest
from fastapi import HTTPException

from tessera.config import settings
from tessera.routers.dependencies import require_github_service
from tessera.services.github_service import GitHubService


def test_refuses_without_github_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "github_token", "ghp_test")
    with pytest.raises(HTTPException) as exc:
        require_github_service(None)
    assert exc.value.status_code == 422
    assert exc.value.detail == (
        "Ce projet n'a pas de github_remote configuré dans agents.json."
    )


def test_refuses_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "github_token", "")
    with pytest.raises(HTTPException) as exc:
        require_github_service("owner/repo")
    assert exc.value.status_code == 422
    assert exc.value.detail == "GITHUB_TOKEN non configuré dans les settings."


def test_returns_service_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "github_token", "ghp_test")
    assert isinstance(require_github_service("owner/repo"), GitHubService)


def test_no_router_imports_another_router_private_name() -> None:
    from pathlib import Path

    import tessera.routers as routers

    for source in Path(routers.__file__).parent.glob("*.py"):
        assert "routers.tickets import" not in source.read_text(encoding="utf-8")
