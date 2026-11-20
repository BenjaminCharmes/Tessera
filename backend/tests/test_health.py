"""GET /health says where the secrets come from, never which (ticket-800)."""
import pytest
from fastapi.testclient import TestClient

import tessera.main
from tessera import config_coffre


@pytest.mark.parametrize("source", ["coffre", "env", "env-repli"])
def test_health_reports_the_secrets_mode_only(
    monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    monkeypatch.setattr(config_coffre, "_source_effective", source)
    client = TestClient(tessera.main.app, raise_server_exceptions=True)

    corps = client.get("/health").json()

    assert corps["secrets"] == source
    texte = str(corps)
    for nom in ("TOKEN", "KEY", "FORBIDDEN"):
        assert nom not in texte
