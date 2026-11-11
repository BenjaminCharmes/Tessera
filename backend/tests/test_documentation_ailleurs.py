"""A project's description never takes another subject's — ticket-936."""
import json
from pathlib import Path

import pytest

from tessera.services.documentation.documentation import DocumentationService
from tessera.services.documentation.documentation_ailleurs import phrases_interdites, premiere_phrase
from tessera.services.documentation.documentation_base import EditionRefusee
from tessera.services.documentation.documentation_code import DiffDeTicket, MatiereCode
from tessera.services.documentation.documentation_description import ecrire_description
from tessera.services.documentation.documentation_preuve import ControleDePreuve
from tessera.services.providers.base import ProviderResult
from tests.matiere_factice import matiere_factice

_TESSERA = "Tessera est un IDE multi-projets avec orchestration d'agents IA, auto-hébergé."
_AUTRE = "Un tableau de bord qui suit les sondes du réseau."
_PREUVE = [{"fichier": "src/m.py", "extrait": "def decrire("}]


_DIFF = "diff --git a/src/m.py b/src/m.py\n+def decrire(x):\n"


def _monde(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Tessera's root, the workspace and the hosted project, all invented."""
    racine = tmp_path / "tessera"
    racine.mkdir()
    (racine / "CLAUDE.md").write_text(f"# CLAUDE.md — Tessera\n\n{_TESSERA} Suite.\n", encoding="utf-8")
    espace = tmp_path / "espace"
    voisin = espace / "autre"
    voisin.mkdir(parents=True)
    (voisin / "agents.json").write_text(json.dumps({"description": f"{_AUTRE} Plus."}), encoding="utf-8")
    projet = espace / "hote"
    projet.mkdir()
    (projet / "agents.json").write_text('{\n  "description": "ancienne"\n}\n', encoding="utf-8")
    return racine, espace, projet


def _controle() -> ControleDePreuve:
    return ControleDePreuve(
        MatiereCode(
            diffs=[DiffDeTicket("ticket-001", _DIFF, ["src/m.py"])],
            fichiers=[],
            sans_diff=[],
        ),
        "",
    )


def _ecrire(projet: Path, texte: str, autres: list[str]) -> bool:
    return ecrire_description(
        projet / "agents.json", {"texte": texte, "preuve": _PREUVE}, _controle(), autres
    )


def test_first_sentence_is_normalised() -> None:
    assert premiere_phrase("  Un  IDE.\nSuite ici. ") == "un ide."


def test_description_starting_like_the_tessera_claude_md_is_refused(tmp_path: Path) -> None:
    racine, espace, projet = _monde(tmp_path)
    autres = phrases_interdites(projet, espace, racine)

    with pytest.raises(EditionRefusee, match="CLAUDE.md de Tessera"):
        _ecrire(projet, f"{_TESSERA} Le tableau de bord est servi.", autres)


def test_description_taking_another_project_s_is_refused(tmp_path: Path) -> None:
    racine, espace, projet = _monde(tmp_path)
    autres = phrases_interdites(projet, espace, racine)

    with pytest.raises(EditionRefusee, match="autre sujet"):
        _ecrire(projet, _AUTRE.upper(), autres)


def test_description_citing_tessera_in_passing_is_accepted(tmp_path: Path) -> None:
    racine, espace, projet = _monde(tmp_path)
    autres = phrases_interdites(projet, espace, racine)

    assert _ecrire(projet, "Sert à mesurer l'orchestration de Tessera.", autres) is True


def test_own_description_is_not_forbidden_to_itself_and_ide_core_may_use_tessera_s(tmp_path: Path) -> None:
    racine, espace, projet = _monde(tmp_path)
    interne = racine / "projects" / "ide-core"
    interne.mkdir(parents=True)

    assert premiere_phrase(_TESSERA) not in phrases_interdites(interne, espace, racine)
    assert premiere_phrase("ancienne") not in phrases_interdites(projet, espace, racine)


def test_missing_or_unreadable_sources_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "ws" / "x").mkdir(parents=True)
    (tmp_path / "ws" / "x" / "agents.json").write_text("pas du json", encoding="utf-8")

    assert phrases_interdites(tmp_path / "ws" / "p", tmp_path / "ws", tmp_path / "vide") == []


class _Enregistreur:
    def __init__(self) -> None:
        self.appels: list[dict[str, object]] = []

    async def complete(self, **kwargs: object) -> ProviderResult:
        self.appels.append(kwargs)
        return ProviderResult(content='{"editions": []}', input_tokens=0, output_tokens=0)


async def test_hosted_project_brief_has_no_tessera_claude_md_and_cwd_reaches_provider(tmp_path: Path) -> None:
    racine, espace, projet = _monde(tmp_path)
    (projet / "memory").mkdir()
    (projet / "memory" / "documentation.json").write_text('{"documentes": []}', encoding="utf-8")
    (projet / "tickets" / "done").mkdir(parents=True)
    (projet / "tickets" / "done" / "ticket-001-x.md").write_text('---\ntitle: "x"\n---\n# x\n', encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for role in ("doc-technique", "doc-fonctionnelle"):
        (prompts / f"{role}.md").write_text("sys", encoding="utf-8")
    enregistreur = _Enregistreur()
    service = DocumentationService(
        enregistreur,  # type: ignore[arg-type]
        prompts, matiere=matiere_factice(),
    )

    await service.mettre_a_jour(projet, racine_doc=projet)

    assert enregistreur.appels
    for appel in enregistreur.appels:
        assert appel["cwd"] == projet
        assert "Tessera est un IDE" not in str(appel["user"])
