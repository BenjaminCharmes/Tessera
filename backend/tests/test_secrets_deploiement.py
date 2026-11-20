"""The env example and Docker say where the secrets live (ticket-800, ADR-073)."""
from pathlib import Path

_RACINE = Path(__file__).resolve().parents[2]


def test_env_example_documents_secrets_source() -> None:
    exemple = (_RACINE / ".env.example").read_text(encoding="utf-8")

    assert "SECRETS_SOURCE" in exemple
    assert "tessera.ps1 secrets" in exemple
    # Les secrets restent en exemple commenté : aucune ligne active.
    for nom in ("ANTHROPIC_API_KEY", "FORBIDDEN_TERMS", "GITHUB_TOKEN", "STATIC_TOKEN"):
        assert not any(ligne.startswith(f"{nom}=") for ligne in exemple.splitlines()), nom


def test_docker_compose_declares_the_env_secrets_mode() -> None:
    compose = (_RACINE / "docker-compose.yml").read_text(encoding="utf-8")

    assert "- SECRETS_SOURCE=env" in compose


def test_setup_points_to_the_migration_command() -> None:
    script = (_RACINE / "scripts" / "tessera.ps1").read_text(encoding="utf-8-sig")
    debut = script.index("function Invoke-Setup")
    corps = script[debut : script.index("\nfunction ", debut + 1)]

    assert "secrets migrer" in corps
