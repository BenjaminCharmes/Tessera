"""Tests for scripts/banc_codeur_bras.py (ticket-1054). No model is called."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import banc_codeur_bras as bb  # noqa: E402
from banc_codeur_bras import Bras, BrasIndisponible, BrasInvalide, charger_bras, construire_provider, manifeste_temporaire  # noqa: E402

from tessera.services.providers.noms import ProviderIndisponible  # noqa: E402

_RACINE = _SCRIPTS_DIR.parent
_ESSAI = _RACINE / "docs" / "essais" / "banc-codeur"
_IDE = _RACINE / "projects" / "ide-core"


def _roles(chemin: Path) -> dict[str, dict[str, object]]:
    return {r["role"]: r for r in json.loads(chemin.read_text(encoding="utf-8"))["agents"]}


def _bras() -> dict[str, Bras]:
    return {b.id: b for b in charger_bras(_ESSAI / "bras.json")}


def _sommes() -> dict[str, str]:
    fichiers = [_IDE / "agents.json", *(_RACINE / "agents" / "prompts").glob("*.md"),
                *(_IDE / ".claude" / "skills").rglob("*.md")]
    return {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in fichiers}


def test_bras_declares_three_arms() -> None:
    bras = _bras()
    assert set(bras) == {"A", "M", "P"}
    assert bras["M"].modele == "claude-opus-5-5"
    assert bras["P"].modele == bras["A"].modele
    assert bras["P"].prompt == "prompts/codeur-p.md"


def test_prompt_p_is_prompt_a_plus_one_addition() -> None:
    a = (_ESSAI / "prompts" / "codeur-a.md").read_text(encoding="utf-8")
    p = (_ESSAI / "prompts" / "codeur-p.md").read_text(encoding="utf-8")
    assert p.startswith(a.rstrip("\n"))
    ajout = p[len(a.rstrip("\n")):]
    assert ajout.count("\n## ") == 1
    assert "Ce que ça ne fait pas" in ajout and "tests ciblés" in ajout


def test_charger_bras_rejects_bad_file(tmp_path: Path) -> None:
    (tmp_path / "bras.json").write_text('{"bras": [{"id": "A"}]}', encoding="utf-8")
    with pytest.raises(BrasInvalide):
        charger_bras(tmp_path / "bras.json")
    with pytest.raises(BrasInvalide):
        charger_bras(tmp_path / "absent.json")


@pytest.mark.parametrize("ident", ["A", "M", "P"])
def test_manifeste_swaps_only_the_coder(tmp_path: Path, ident: str) -> None:
    bras = _bras()[ident]
    dossier = manifeste_temporaire(bras, dossier=tmp_path / "x")
    temporaire, ide = _roles(dossier / "agents.json"), _roles(_IDE / "agents.json")
    assert temporaire["codeur"]["model"] == bras.modele
    assert "fallback" not in temporaire["codeur"]
    for role in ("reviewer", "validateur"):
        assert temporaire[role] == ide[role]
    assert set(temporaire) == {"codeur", "reviewer", "validateur"}
    prompt = (dossier / "agents" / "prompts" / "codeur.md").read_text(encoding="utf-8")
    assert prompt == (_ESSAI / bras.prompt).read_text(encoding="utf-8")
    assert (dossier / ".claude" / "skills" / "verifier-mon-travail" / "SKILL.md").is_file()


def test_manifeste_never_writes_in_ide_core(tmp_path: Path) -> None:
    avant = _sommes()
    for bras in _bras().values():
        manifeste_temporaire(bras, dossier=tmp_path / bras.id)
    assert _sommes() == avant


def test_manifeste_default_folder_is_new() -> None:
    a = manifeste_temporaire(_bras()["A"])
    b = manifeste_temporaire(_bras()["A"])
    assert a != b and (a / "agents.json").is_file()


def test_unavailable_provider_raises_named_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_a: object, **_k: object) -> None:
        raise ProviderIndisponible("absent")

    monkeypatch.setattr(bb, "provider_pour_role", refuse)
    with pytest.raises(BrasIndisponible, match="bras M"):
        construire_provider(_bras()["M"], tmp_path)
