"""The secrets command moves .env secrets into the vault (ticket-797, ADR-073).

In-memory vault, throwaway .env in ``tmp_path`` with fictitious values: the
repository .env is never read nor written.
"""
import io
from pathlib import Path

import pytest

from tessera import coffre_cli
from tessera.coffre import CoffreAbsent, CoffreEnErreur
from tests.coffre_double import CoffreDouble, ouvrant

FAUX_VERCEL = "faux-vercel-jeton-0042"
FAUX_STATIC = "faux-static-jeton-0042"
_RACINE = Path(__file__).resolve().parents[2]


class _CoffreQuiTronque(CoffreDouble):
    """Vault whose write fails its read-back."""

    def ecrire(self, nom: str, valeur: str) -> None:
        raise CoffreEnErreur("écriture dans le coffre : la relecture diffère")


@pytest.fixture
def double(monkeypatch: pytest.MonkeyPatch) -> CoffreDouble:
    coffre = CoffreDouble()
    monkeypatch.setattr(coffre_cli, "coffre_du_systeme", ouvrant(coffre))
    return coffre


def _dotenv(tmp_path: Path, texte: str) -> Path:
    fichier = tmp_path / ".env"
    fichier.write_text(texte, encoding="utf-8")
    return fichier


def _lancer(fichier: Path, *argv: str, entree: str = "") -> int:
    return coffre_cli.main([*argv, "--env-file", str(fichier)], entree=io.StringIO(entree))


def test_migrer_moves_a_secret_and_replaces_its_line_by_a_comment(
    double: CoffreDouble, tmp_path: Path
) -> None:
    fichier = _dotenv(tmp_path, f"VERCEL_TOKEN={FAUX_VERCEL}\n")

    assert _lancer(fichier, "migrer") == 0

    assert double.entrees == {"VERCEL_TOKEN": FAUX_VERCEL}
    texte = fichier.read_text(encoding="utf-8")
    assert FAUX_VERCEL not in texte
    assert "# VERCEL_TOKEN : dans le coffre (tessera.ps1 secrets)" in texte


def test_migrer_keeps_comments_and_other_settings_untouched(
    double: CoffreDouble, tmp_path: Path
) -> None:
    fichier = _dotenv(
        tmp_path,
        "# Réglages de la machine\nLLM_PROVIDER=agent_sdk\n"
        f"STATIC_TOKEN={FAUX_STATIC}\nVERCEL_TEAM_ID=team_factice\n",
    )

    _lancer(fichier, "migrer")

    lignes = fichier.read_text(encoding="utf-8").splitlines()
    assert lignes[:2] == ["# Réglages de la machine", "LLM_PROVIDER=agent_sdk"]
    assert lignes[3] == "VERCEL_TEAM_ID=team_factice"


def test_migrer_skips_empty_and_placeholder_values(double: CoffreDouble, tmp_path: Path) -> None:
    texte = "ANTHROPIC_API_KEY=sk-ant-...\nGITHUB_TOKEN=\nNEON_API_KEY=ghp_...\n"
    fichier = _dotenv(tmp_path, texte)

    assert _lancer(fichier, "migrer") == 0

    assert double.entrees == {}
    assert fichier.read_text(encoding="utf-8").startswith(texte)


def test_migrer_does_not_overwrite_a_different_vault_value(
    double: CoffreDouble, tmp_path: Path
) -> None:
    double.entrees["VERCEL_TOKEN"] = "autre-valeur-du-coffre"
    fichier = _dotenv(tmp_path, f"VERCEL_TOKEN={FAUX_VERCEL}\n")

    assert _lancer(fichier, "migrer") != 0

    assert double.entrees["VERCEL_TOKEN"] == "autre-valeur-du-coffre"
    assert f"VERCEL_TOKEN={FAUX_VERCEL}" in fichier.read_text(encoding="utf-8")


def test_migrer_keeps_the_line_when_the_readback_differs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(coffre_cli, "coffre_du_systeme", ouvrant(_CoffreQuiTronque()))
    fichier = _dotenv(tmp_path, f"VERCEL_TOKEN={FAUX_VERCEL}\n")

    assert _lancer(fichier, "migrer") != 0

    assert f"VERCEL_TOKEN={FAUX_VERCEL}" in fichier.read_text(encoding="utf-8")


def test_migrer_is_idempotent(double: CoffreDouble, tmp_path: Path) -> None:
    fichier = _dotenv(tmp_path, f"VERCEL_TOKEN={FAUX_VERCEL}\n")
    _lancer(fichier, "migrer")
    apres_un = fichier.read_text(encoding="utf-8")

    assert _lancer(fichier, "migrer") == 0

    assert fichier.read_text(encoding="utf-8") == apres_un


def test_migrer_resumes_after_an_interruption(double: CoffreDouble, tmp_path: Path) -> None:
    # Coffre écrit, `.env` pas encore réécrit : la relance retire la ligne.
    double.entrees["VERCEL_TOKEN"] = FAUX_VERCEL
    fichier = _dotenv(tmp_path, f"VERCEL_TOKEN={FAUX_VERCEL}\n")

    assert _lancer(fichier, "migrer") == 0

    assert FAUX_VERCEL not in fichier.read_text(encoding="utf-8")


def test_migrer_adds_secrets_source_once(double: CoffreDouble, tmp_path: Path) -> None:
    fichier = _dotenv(tmp_path, f"VERCEL_TOKEN={FAUX_VERCEL}")
    _lancer(fichier, "migrer")
    _lancer(fichier, "migrer")

    texte = fichier.read_text(encoding="utf-8")
    assert texte.count("SECRETS_SOURCE=") == 1
    assert "\nSECRETS_SOURCE=coffre\n" in texte


def test_migrer_leaves_no_backup_and_no_temp_file(double: CoffreDouble, tmp_path: Path) -> None:
    fichier = _dotenv(tmp_path, f"VERCEL_TOKEN={FAUX_VERCEL}\n")

    _lancer(fichier, "migrer")

    assert [p.name for p in tmp_path.iterdir()] == [".env"]


def test_no_subcommand_output_contains_a_secret_value(
    double: CoffreDouble, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    double.entrees["NEON_API_KEY"] = "faux-neon-en-conflit"
    fichier = _dotenv(
        tmp_path, f"VERCEL_TOKEN={FAUX_VERCEL}\nNEON_API_KEY=faux-neon-du-dotenv\n"
    )

    _lancer(fichier, "migrer")
    _lancer(fichier, "set", "STATIC_TOKEN", entree=FAUX_STATIC + "\n")
    _lancer(fichier, "lister")

    sortie = capsys.readouterr()
    for valeur in (FAUX_VERCEL, FAUX_STATIC, "faux-neon-en-conflit", "faux-neon-du-dotenv"):
        assert valeur not in sortie.out + sortie.err


def test_set_reads_the_value_from_stdin_only(double: CoffreDouble, tmp_path: Path) -> None:
    fichier = _dotenv(tmp_path, "")

    assert _lancer(fichier, "set", "STATIC_TOKEN", entree=FAUX_STATIC + "\r\n") == 0
    assert double.entrees == {"STATIC_TOKEN": FAUX_STATIC}

    with pytest.raises(SystemExit):
        _lancer(fichier, "set", "STATIC_TOKEN", "valeur-en-argument")
    assert _lancer(fichier, "set", "STATIC_TOKEN", entree="") != 0
    assert _lancer(fichier, "set", "LLM_PROVIDER", entree="x") != 0


def test_lister_reports_where_each_name_lives(
    double: CoffreDouble, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    double.entrees["GITHUB_TOKEN"] = "faux-github"
    fichier = _dotenv(tmp_path, f"VERCEL_TOKEN={FAUX_VERCEL}\nANTHROPIC_API_KEY=sk-ant-...\n")

    assert _lancer(fichier, "lister") == 0

    lignes = dict(
        ligne.split(" : ", 1) for ligne in capsys.readouterr().out.splitlines() if " : " in ligne
    )
    assert lignes["GITHUB_TOKEN"] == "coffre"
    assert lignes["VERCEL_TOKEN"] == ".env"
    assert lignes["ANTHROPIC_API_KEY"] == "absent"
    assert lignes["FORBIDDEN_TERMS"] == "absent"


def test_migrer_refuses_when_the_vault_is_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(coffre_cli, "coffre_du_systeme", ouvrant(erreur=CoffreAbsent("x")))
    texte = f"VERCEL_TOKEN={FAUX_VERCEL}\n"
    fichier = _dotenv(tmp_path, texte)

    assert _lancer(fichier, "migrer") != 0

    assert fichier.read_text(encoding="utf-8") == texte


def test_tessera_ps1_lists_the_secrets_verb() -> None:
    script = (_RACINE / "scripts" / "tessera.ps1").read_text(encoding="utf-8-sig")

    assert "'secrets'" in script
    for sous_verbe in ("migrer", "set", "supprimer", "lister"):
        assert f"'{sous_verbe}'" in script
    assert "Read-Host -AsSecureString" in script
    assert "tessera.coffre_cli" in script
